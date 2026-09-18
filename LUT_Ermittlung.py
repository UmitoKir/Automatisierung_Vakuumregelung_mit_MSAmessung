#install all the necessary libaries and debugger/compiler(python, python debugger, git etc.) to get it running on VS code
#install with py -m pip install in the terminal all the necessary packages
#matplotlib maybe also required
import time
import numpy as np 
import PressureSensor
import ValveControl
import Mathfunctions
import CSVManager
import queue
import threading


Dauer = 60*30 
counter_limit = 10*60*3

einlassventil_fallend = [10.0, 9, 8.5, 8, 7.5, 7, 6.5, 6, 5.5, 5, 4.5, 4, 3.5, 3, 2.5, 2, 1.5, 1, 0]
einlassventil_steigend = [0, 1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5, 5.5, 6, 6.5, 7, 7.5, 8, 8.5, 9, 10]

data_queue = queue.Queue()

def _csv_writer_worker(measuredData):
    while True:
        item = data_queue.get()
        if item is None:  # Sentinel value to stop thread
            data_queue.task_done()
            break
        try:
            measuredData.writeToCSVforLUT(**item)
        except Exception as e:
            print(f"\n[FEHLER im CSV-writer-Thread]: {e}\n")
        finally:
            data_queue.task_done()

def measurement(valves, sensor, v_ein, startzeit):
    global Dauer, counter_limit
    loop_start = time.perf_counter()
    v_durch = 10.0 - v_ein
    valves.applyVoltage(v_durch, v_ein)
    lokale_zeit = 0
    istwert = sensor.wait_for_next_value() or sensor.pressure
    compare_pressure = istwert
    tangent_counter = 0
    while(lokale_zeit <= Dauer):
        prev_pressure = istwert
        neuer_druck = sensor.wait_for_next_value()
        if neuer_druck is None:
            print("Warnung: Sensor-Timeout!")
            continue
        istwert = neuer_druck
        now = time.perf_counter()
        dt = min((now - loop_start), 1.0)
        loop_start = now
        lokale_zeit = time.time() - startzeit
        print(f"Dauer einer iteration(dt): {dt:.4f}")
        schwankung = (istwert - prev_pressure) / prev_pressure
        schwankung_in_relation_zum_vergleich = (istwert - compare_pressure) / compare_pressure 
        duration = None
        if abs(schwankung) <= sensor.fehler_grenze and abs(
                schwankung_in_relation_zum_vergleich) <= sensor.rel_fehler_grenze:
            if (tangent_counter == counter_limit):
                duration = lokale_zeit
            elif tangent_counter > counter_limit:
                break
            tangent_counter += 1
        else:
            tangent_counter = 0
            compare_pressure = istwert                 
        if lokale_zeit >= Dauer - 0.15:
            duration = Dauer

        data_queue.put({
            "zeit": lokale_zeit,
            "druck": istwert,
            "v_durchlass": v_durch,
            "v_einlass": v_ein,
            "duration": duration,
            })
        print(
            f"Dauer: {lokale_zeit: .3f} s | Druck: {istwert:.5f} mBar ({sensor.sensorwahl})| "
            f"V_Ein: {v_ein:.4f}V | V_Durch: {v_durch:.4f}V | Tangent Counter: {tangent_counter} | "
            f"Schwankung: {schwankung:.5f} | rel. Schwankung: {schwankung_in_relation_zum_vergleich:.5f} | "
            f"dt: {dt:.4f}s"
        )


def main():
    global einlassventil_steigend, einlassventil_fallend
    
    string = ['Zeit_s', 'Druck_mBar', 'V_Durchlass', 'V_Einlass', 'Dauer']
    CSVfile = CSVManager.CreateFile()
    folder_path = r"C:\Users\messung\PycharmProjects\Automatisierung_Vakuumregelung_mit_MSAmessung\Regulierung_LUT"
    #filename = f"LUT_Messung_{time.strftime('%Y%m%d_%H%M%S')}.csv"
    
    if folder_path != "." and not folder_path.endswith('\\') and not folder_path.endswith('/'):
        folder_path += '\\'
    CSVfile.path = folder_path # + filename
    CSVfile.allocateCSV(stringchain=string)
    log_thread = threading.Thread(target=_csv_writer_worker, args=(CSVfile,), daemon=True)
                
    log_thread.start()

    task_completed = False

    sensor = PressureSensor.PressureSensor()
    valves = ValveControl.ValveControl(valve_name="Dev1")

    try:
        if not sensor.connect():
            raise RuntimeError("Verbindung zum Drucksensor fehlgeschlagen.")
        sensor.start_listener()

        if not valves.connect():
            raise RuntimeError("Ventil-Initialisierung fehlgeschlagen.")

        for v_ein in einlassventil_fallend:
            startzeit = time.time()
            measurement(valves=valves, sensor=sensor, v_ein=v_ein, startzeit=startzeit)

        for v_ein in einlassventil_steigend:
            startzeit = time.time()
            measurement(valves=valves, sensor=sensor, v_ein=v_ein, startzeit=startzeit)
        
        task_completed = True
        if task_completed:
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
