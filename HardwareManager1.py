# install the driver software NI-DAQ™mx
# install all the necessary libaries and debugger/compiler(python, python debugger, git etc.) to get it running on VS code
# install with py -m pip install in the terminal all the necessary packages
# matplotlib maybe also required
import time
import numpy as np
import PressureSensor
import ValveControl
import Mathfunctions
import CSVManager
import MSA500
import queue
import threading

kp_base = 0.9  # 0.95 als konstanter parameter funktioniert ganz gut

ki_base = 0.05  # letzter stand 0.001 funtioniert könnte aber noch strärker sein
# 0.0005 #0.0001  # 0.2 #standartmäßig

kd_base = 0  # vllt 0.1 oder 0.05 #5e-6
dt = 0.1

counter_limit = 500

data_queue = queue.Queue()

def csv_writer_worker(measuredData):
    while True:
        item = data_queue.get()
        if item is None:  # Sentinel value to stop thread
            data_queue.task_done()
            break
        measuredData.writeToCSV(**item)
        data_queue.task_done()

# hier regelung muss noch komplett bearbeitet und angepasst werden.
def regelung(sensor, valves, lutData, measuredData, sollwert, startzeit, MSA, controlUnit, Math):
    global counter_limit, kp_base, ki_base, kd_base, dt

    rel_fehler = 1
    lokale_zeit = 0
    loop_start = time.perf_counter()
    istwert = sensor.wait_for_next_value() or sensor.pressure

    compare_pressure = istwert
    V_ein_fallend = Math.interpolierte_Funktion(lutData.stab_v_einlass_fallend, lutData.stab_druck_einlass_fallend)
    if V_ein_fallend is None:
        print("Fehler: Interpolation fehlgeschlagen, LUT leer?")
        return
    Math.v_ein = V_ein_fallend(sollwert)
    Math.steigung(lutData.stab_v_einlass_fallend, lutData.stab_druck_einlass_fallend)
    print(
        f"Anfängliche Kp: {kp_base:.4f} | Sensitivität Sollwert: {Math.steigung_v_ein:.4f} | Max Sensitivität: {Math.max_steigung:.4f}")
    if Math.steigung_v_ein < 1e-3:
        Math.steigung_v_ein = 1e-3
    prev_kp = controlUnit.kp
    # da muss man sich nochmehr gedanken machen....
    kp = kp_base * (Math.max_steigung / Math.steigung_v_ein) ** (
                1 / 7)  # man könnte hier auch mit einem anderen Exponenten arbeiten, um die Anpassung abzuschwächen
    ki = ki_base * (Math.max_steigung / Math.steigung_v_ein) ** (1 / 5)
    controlUnit.kp = kp
    controlUnit.ki = ki
    print(f"Angepasster Kp basierend auf Sensitivität: {kp:.4f}")
    controlUnit.reset()
    tangent_counter = 0

    measuredData.TxtFile(sollwert=sollwert, alter_kp=prev_kp, kp=kp, ki=ki, kd=kd_base, dt=dt,
                         steigung_bei_sollwert=Math.steigung_v_ein, max_steigung=Math.max_steigung,
                         druck_max_steigung=Math.druck_bei_max_steigung)

    scan_status = 2
    scan_started = False
    scan_finished = False
    
    while not scan_finished and istwert >= 0.001:  # relativer Fehler kleiner 1%
        prev_pressure = istwert
        neuer_druck = sensor.wait_for_next_value()
        if neuer_druck is None:
            print("Warnung: Sensor-Timeout!")
            continue
        istwert = neuer_druck

        now = time.perf_counter()
        lokale_zeit = time.time() - startzeit
        controlUnit.dt = min((now - loop_start), 1.0)
        loop_start = now
        print(f"Dauer einer iteration(dt): {controlUnit.dt:.4f}")
        Stellgroesse, rel_fehler = controlUnit.logarithmicPID(istwert)
        v_durch = 10

        # V_ein muss noch bestimmt werden
        v_ein = np.clip(Math.v_ein + Stellgroesse, 0, 10)
        valves.applyVoltage(v_durch, v_ein)

        # Stabilitätscheck
        schwankung = (istwert - prev_pressure) / prev_pressure if prev_pressure != 0 else 1e-4
        schwankung_in_relation_zum_vergleich = (istwert - compare_pressure) / compare_pressure 
        dur_str = ""
        if abs(schwankung) <= sensor.fehler_grenze and abs(
                schwankung_in_relation_zum_vergleich) <= sensor.rel_fehler_grenze and rel_fehler < 0.02:
            if (tangent_counter >= counter_limit):
                dur_str = f"{(lokale_zeit):.3f}".replace('.', ',')
                if not scan_started:
                    MSA.StartScan()
                    scan_started = True
            tangent_counter += 1
        else:
            tangent_counter = 0
            compare_pressure = istwert 

        #problem: wenn wärend scan druckstatus zu False fällt muss es nach dem scan wieder erstmal zu True wieder werden. 
        # Sonst fährt es nicht den nächsten druckwert an.... das ist ein problem! Regelung ausbessern, so dass weniger schwankung.
        if scan_started: 
            scan_status = MSA.statusAbfrage()
            if scan_status == 0:
                print("Scan erfolgreich durchgeführt und abgeschlossen.")
                scan_finished = True
            elif scan_status == 5: 
                print("Softwareseitiger Fehler: Scan abgebrochen")
                scan_finished = True

        data_queue.put({
            "zeit": lokale_zeit,
            "druck": istwert,
            "v_durchlass": v_durch,
            "v_einlass": v_ein,
            "stellgroesse": Stellgroesse,
            "response": sensor.response_array,
            "duration": dur_str,
            "p_anteil": controlUnit.p_anteil,
            "i_anteil": controlUnit.i_anteil,
            "d_anteil": controlUnit.d_anteil,
        })

        print(
            f"relativer Fehler:{rel_fehler: .4} | Dauer: {lokale_zeit:.3f} s | "
            f"Druck: {istwert:.5f} mBar ({sensor.sensorwahl})| V_Ein: {v_ein:.4f}V | "
            f"P-Anteil: {controlUnit.p_anteil: .6f} | I-Anteil: {controlUnit.i_anteil: .6f} | D-Anteil: {controlUnit.d_anteil: .6f} | "
            f"Stellgroesse: {Stellgroesse: .4f} | Tangent Counter: {tangent_counter} | "
            f"Schwankung: {schwankung:.5f} | rel. Schwankung: {schwankung_in_relation_zum_vergleich:.5f} | "
            f"dt: {controlUnit.dt:.4f}s"
        )
    

def main():
    # Pfad = input("Geben Sie den Pfad zur CSV-Datei ein: ").strip().replace('"', '')
    pfad = r"C:\Users\messung\PycharmProjects\Automatisierung_Vakuumregelung_mit_MSAmessung\Regulierung_LUT\messung_ventil_mehr_stützpunkte_gut.csv"

    # LutCSV = CSVManager.CSVReader()
    # LutCSV.inputPath()
    LutCSV = CSVManager.CSVReader(pfad)
    LutCSV.extractData()

    CSVfile = CSVManager.CreateFile()
    CSVfile.allocateCSV()
    log_thread = threading.Thread(target=csv_writer_worker, args=(CSVfile,), daemon=True)
                
    log_thread.start()

    sensor = PressureSensor.PressureSensor()
    valves = ValveControl.ValveControl(valve_name="Dev1")
    excelfile_path = input("Bitte geben Sie den kompletten Pfad mit der Exceldatei ein: ")
    MSA = MSA500.MSA500()
    try:
        if not sensor.connect():
            raise RuntimeError("Verbindung zum Drucksensor fehlgeschlagen.")
        sensor.start_listener()

        if not valves.connect():
            raise RuntimeError("Ventil-Initialisierung fehlgeschlagen.")

        if not MSA.connect():
            raise RuntimeError("MSA500-Software-Initialisierung fehlgeschlagen.")
        MSA.sollwert_exceltabelle_path = excelfile_path
        if not MSA.excelVectorGenerator():
            raise RuntimeError("Problem bei der Extrahierung der Solldruckwerte von der Exceldatei....")

        MSA.reference_file = input("Geben Sie den Pfad der Referenz-Scandatei von PSV ein: ")
        MSA.pathRequest(path=None)
        startzeit = time.time()
        for solldruck in MSA.sollwert_tabelle:
            controlUnit = Mathfunctions.ControllSystem(kp=kp_base, ki=ki_base, kd=kd_base, sollwert=solldruck, dt=dt)
            Math = Mathfunctions.Interpolation(solldruck)
            folder_name = fr"ScanMSA500_{solldruck}mBar"
            file = fr"Scan_{solldruck}mBar.svd"
            MSA.allocateFile(folder_name=folder_name, file_name = file)
            valves.ambientPressure()
            regelung(sensor=sensor, valves=valves, lutData=LutCSV, measuredData=CSVfile, sollwert=solldruck,
                     startzeit=startzeit, MSA=MSA, controlUnit=controlUnit, Math=Math)

        print('Erfolgreich abgeschlossen. Verbindung wird beendet')
    except KeyboardInterrupt:
        print("Programm unterbrochen.")
    except UnicodeDecodeError as e:
        print(f'Fehler bei der Dekodierung: {e}')
    finally:
        if log_thread.is_alive():
            data_queue.put(None)
            data_queue.join()
        valves.ambientPressure()
        valves.shutdown()  # Alle Ausgänge auf 0 setzen
        valves.close()
        sensor.disconnect()

if __name__ == "__main__":
    main()