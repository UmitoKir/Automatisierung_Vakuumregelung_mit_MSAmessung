# install the driver software NI-DAQ™mx
# install all the necessary libaries and debugger/compiler(python, python debugger, git etc.) to get it running on VS code
# install with py -m pip install in the terminal all the necessary packages
# matplotlib maybe also required
import time
import numpy as np
import queue
import threading
import pythoncom

import PressureSensor
import ValveControl
import Mathfunctions
import CSVManager
import MSA500

kp_base = 0.8  # 0.95 als konstanter parameter funktioniert ganz gut

ki_base = 0.01  # letzter stand 0.001 funtioniert könnte aber noch strärker sein
# 0.0005 #0.0001  # 0.2 #standartmäßig

kd_base = 0  # vllt 0.1 oder 0.05 #5e-6
dt = 0.1





class HardwareManager():
    
    def __init__(self, print_flag = False, data_callback=None):
        self.sensor = PressureSensor.PressureSensor(print_flag=print_flag)
        self.valves = ValveControl.ValveControl(print_flag=print_flag, valve_name="Dev1")
        self.msa = None
        self.ref_scan_path = None
        self.excel_path = None
        self.csv_path = None

        lut_pfad = r"C:\Users\messung\PycharmProjects\Automatisierung_Vakuumregelung_mit_MSAmessung\Regulierung_LUT\messung_ventil_mehr_stützpunkte_gut.csv"
            
        self.lut_csv = CSVManager.CSVReader(pfad = lut_pfad, print_flag=print_flag)
        self.lut_csv.extractData()


        self.data_queue = queue.Queue()
        self.data_callback = data_callback
        
        self.regler = None
        self.regler_worker_thread = None
        self.print_flag = print_flag
        self.hm_connection_alive_flag = False


    def _csv_writer_worker(self):
        while True:
            item = self.data_queue.get()
            if item is None:
                self.data_queue.task_done()
                break
            try:
               self.csv_file.writeToCSV(**item)
            except Exception as e:
                if self.print_flag:
                    print(f"CSV Schreibfehler: {e}")
            finally:
                self.data_queue.task_done()

    def connect_all(self):
        if not self.csv_path:
            raise ValueError("CSV-Pfad wurde nicht angegeben!")
        self.csv_file = CSVManager.CreateFile(print_flag=self.print_flag)
        self.csv_file.allocateCSVfile(csv_location=self.csv_path)
        self.write_to_csv_thread = threading.Thread(target=self._csv_writer_worker, daemon=True)

        self.msa = MSA500.MSA500(print_flag=self.print_flag)

        if not self.sensor.connect():
            raise RuntimeError("Sensorverbindung fehlgeschlagen")
        self.sensor.start_listener()

        if not self.valves.connect():
            raise RuntimeError("Ventilsteuerung fehlgeschlagen")
        
        if not self.msa.connect():
            raise RuntimeError("MSA500 Verbindungsaufbau(connect_all()) fehlgeschlagen")
        

        self.write_to_csv_thread.start()

    def connectAllForGUI(self):
        if not self.csv_path:
            raise ValueError("CSV-Pfad wurde nicht angegeben!")
        self.csv_file = CSVManager.CreateFile(print_flag=self.print_flag)
        self.csv_file.allocateCSVfileforGUI(csv_location=self.csv_path)
        self.write_to_csv_thread = threading.Thread(target=self._csv_writer_worker, daemon=True)

        self.msa = MSA500.MSA500(print_flag=self.print_flag)

        if not self.sensor.connect():
            raise RuntimeError("Sensorverbindung fehlgeschlagen")
        self.sensor.start_listener()

        if not self.valves.connect():
            raise RuntimeError("Ventilsteuerung fehlgeschlagen")
        
        if not self.msa.connect():
            raise RuntimeError("MSA500 Verbindungsaufbau(connect_all()) fehlgeschlagen")
        
        self.write_to_csv_thread.start()
        self.hm_connection_alive_flag = True

    def connectForPressureControlGUI(self):
        if not self.csv_path:
            raise ValueError("CSV-Pfad wurde nicht angegeben!")
        self.csv_file = CSVManager.CreateFile(print_flag=self.print_flag)
        self.csv_file.allocateCSVfileforGUI(csv_location=self.csv_path)
        self.write_to_csv_thread = threading.Thread(target=self._csv_writer_worker, daemon=True)

        self.msa = None

        if not self.sensor.connect():
            raise RuntimeError("Sensorverbindung fehlgeschlagen")
        self.sensor.start_listener()

        if not self.valves.connect():
            raise RuntimeError("Ventilsteuerung fehlgeschlagen")

        self.write_to_csv_thread.start()
        self.hm_connection_alive_flag = True

    def initialize_regler(self):
        if not self.regler or not self.regler.is_alive():
            self.regler = VakuumRegler(
                sensor=self.sensor,
                valves=self.valves,
                msa=self.msa,
                lut_reader=self.lut_csv,
                csv_writer=self.csv_file,
                queue_data=self.data_queue,
                csv_path=self.csv_path,
                data_callback=self.data_callback
            )
            self.regler.print_flag = self.print_flag
            #self.regler_thread.start()

    def starte_einzel_regelung(self, solldruck):
        """Startet die Einzelpunktregelung sauber in einem Hintergrund-Thread."""
        if self.regler:
            self.regler.is_running = True
            self.regler_worker_thread = threading.Thread(
                target=self.regler.regelungOnePressure, 
                args=(solldruck,), 
                daemon=True
            )
            self.regler_worker_thread.start()

    def starteAutomatedScanGUI(self):
        if self.regler:
            self.regler.excel_path = self.excel_path
            self.regler.ref_scan_path = self.ref_scan_path
            self.regler.is_running = True
                                    
            self.regler_worker_thread = threading.Thread(
                target=self.regler.runAutomatedScanGUI,
                daemon=True
            )
            self.regler_worker_thread.start()

    
    def stoppe_einzel_regelung(self):
        if self.regler:
            self.regler.stop() 

    def stop_regler(self):
        if self.regler:
            self.regler.stop()
            if self.regler_worker_thread and self.regler_worker_thread.is_alive():
                self.regler_worker_thread.join(timeout=2.0)

    def shutdown(self):
        self.stop_regler()

        if self.write_to_csv_thread.is_alive():
            self.data_queue.put(None)
            self.data_queue.join()

        if self.valves:
            self.valves.shutdown()
            self.valves.close()

        if self.sensor:
            self.sensor.disconnect()

class VakuumRegler(threading.Thread):
    def __init__(self, sensor, valves, msa, lut_reader, csv_writer, queue_data, csv_path ,data_callback=None):
        super().__init__()
        self.sensor = sensor
        self.valves = valves
        self.msa = msa
        self.lut_reader = lut_reader
        self.csv_writer = csv_writer
        self.data_queue = queue_data
        
        self.current_sollwert = 1000.0
        
        # Basis-Parameter
        self.kp_base = 0.8
        self.ki_base = 0.01
        self.kd_base = 0.005
        self.dt = 0.1

        self.counter_limit = 600
        self.print_flag = False
        self.is_running = True
        self.single_pressurevalue_control_stop_btn_flag = False
        self.druck_status = False

        self.solldruck = 1000
        self.ref_scan_path = None
        self.excel_path = None
        self.csv_path = csv_path
        self.data_callback = data_callback

        self.ControlUnit = None
        self.Math = None
        

    def path_control(self):
        if self.ref_scan_path is not None:
            self.msa.reference_file = self.ref_scan_path
        else:
            self.msa.pathRequest(path=None)

    def runAutomatedScan(self):
        startzeit = time.time()
        self.msa.sollwert_exceltabelle_path=self.excel_path
        if not self.msa.excelVectorGenerator():
            raise RuntimeError("MSA500 Druckwertgenerierung(excelVectorGenerator()) fehlgeschlagen")
        if self.ref_scan_path is not None:
            self.msa.reference_file = self.ref_scan_path
        else: 
            self.msa.pathRequest(path=None)

        

        for self.solldruck in self.msa.sollwert_tabelle:
            if not self.is_running:
                break
            self.ControlUnit = Mathfunctions.ControllSystem(kp=self.kp_base, ki=self.ki_base, kd=self.kd_base, sollwert=self.solldruck, print_flag=self.print_flag, dt=self.dt)
            self.Math = Mathfunctions.Interpolation(sollwert=self.solldruck, print_flag=self.print_flag)
            folder= fr"ScanMSA500_{self.solldruck}mBar"
            file = fr"Scan_{self.solldruck}mBar.svd"
            self.msa.allocateFile(folder_name=folder, file_name=file)
            self.valves.ambientPressure()
            self._regelung_single_point(self.solldruck, startzeit, self.ControlUnit, self.Math)

    def runAutomatedScanGUI(self):
        # COM-Apartment für diesen Thread initialisieren
        pythoncom.CoInitialize()
        try:
            self.msa = MSA500.MSA500(print_flag=self.print_flag)
            #self.msa.general_folder_path = self.ref_scan_path
            self.msa.connect()
            startzeit = time.time()
            self.msa.sollwert_exceltabelle_path=self.excel_path
            if not self.msa.excelVectorGenerator():
                raise RuntimeError("MSA500 Druckwertgenerierung(excelVectorGenerator()) fehlgeschlagen")
            if self.ref_scan_path is not None:
                self.msa.reference_file = self.ref_scan_path
            else: 
                self.msa.pathRequest(path=None)
            for self.solldruck in self.msa.sollwert_tabelle:
                if not self.is_running:
                    break
                self.druck_status = False
                self.ControlUnit = Mathfunctions.ControllSystem(kp=self.kp_base, ki=self.ki_base, kd=self.kd_base, sollwert=self.solldruck, print_flag=self.print_flag, dt=self.dt)
                self.Math = Mathfunctions.Interpolation(sollwert=self.solldruck, print_flag=self.print_flag)
                folder= fr"ScanMSA500_{self.solldruck}mBar"
                file = fr"Scan_{self.solldruck}mBar.svd"
                self.msa.allocateFileForGUI(folder_name=folder, file_name=file)
                self.valves.ambientPressure()
                self._regelung_single_point(self.solldruck, startzeit, self.ControlUnit, self.Math)
        finally:
            # COM-Ressourcen beim Beenden des Threads freigeben
            pythoncom.CoUninitialize()

                

    def _regelung_single_point(self, sollwert, startzeit, ControlUnit, Math):
        
        rel_fehler = 1
        lokale_zeit = 0
        tangent_counter = 0
        loop_start = time.perf_counter()
        istwert = self.sensor.wait_for_next_value() or self.sensor.pressure
        compare_pressure = istwert

        v_ein_fallend = Math.interpolierte_Funktion(
            self.lut_reader.stab_v_einlass_fallend, self.lut_reader.stab_druck_einlass_fallend
        )
        if v_ein_fallend is None:
            if self.print_flag:
                print("Fehler: Interpolation fehlgeschlagen, LUT leer?")
            return

        Math.v_ein = v_ein_fallend(sollwert)
        Math.steigung(self.lut_reader.stab_v_einlass_fallend, self.lut_reader.stab_druck_einlass_fallend)

        prev_kp = ControlUnit.kp
        kp = self.kp_base * (Math.max_steigung / max(Math.steigung_v_ein, 1e-3)) ** (1 / 7)
        ki = self.ki_base * (Math.max_steigung / max(Math.steigung_v_ein, 1e-3)) ** (1 / 5)
        ControlUnit.kp, ControlUnit.ki = kp, ki

        if self.print_flag:
            print(f"Sensitivität Sollwert: {Math.steigung_v_ein:.4f} | Max Sensitivität: {Math.max_steigung:.4f}")
            print(f"Anfängliche Kp: {self.kp_base:.4f} | Angepasster Kp: {ControlUnit.kp:.4f}")

        self.csv_writer.TxtFile(
            sollwert=sollwert, 
            alter_kp=prev_kp, 
            kp=kp, 
            ki=ki, 
            kd=kd_base, 
            dt=dt,
            steigung_bei_sollwert=Math.steigung_v_ein, 
            max_steigung=Math.max_steigung,
            druck_max_steigung=Math.druck_bei_max_steigung
        )
        
        self.druck_status = False
        scan_status, scan_started = 2, False

        while self.is_running and (scan_status != 0 or not self.druck_status) and istwert >= 0.001:
            prev_pressure = istwert
            neuer_druck = self.sensor.wait_for_next_value()
            if neuer_druck is None:
                if self.print_flag:
                    print("Warnung: Sensor-Timeout!")
                continue
            istwert = neuer_druck

            now = time.perf_counter()
            lokale_zeit = time.time() - startzeit
            #signal an GUI fürs Plotten
            scan_aktiv = scan_started and (scan_status != 0)
            if self.data_callback:
                self.data_callback(lokale_zeit, istwert, sollwert, scan_aktiv)
            ControlUnit.dt = min((now - loop_start), 1.0)
            loop_start = now
            if self.print_flag:
                print(f"Dauer einer iteration(dt): {ControlUnit.dt:.4f}")

            v_durch = 10
            stellgroesse, rel_fehler = ControlUnit.logarithmicPID(istwert)
            v_ein = np.clip(Math.v_ein + stellgroesse, 0, 10)
            self.valves.applyVoltage(v_durch, v_ein)

            schwankung = abs(istwert - prev_pressure)
            schwankung_in_relation_zum_vergleich = (istwert - compare_pressure)
            dur_str = ""

            if (abs(schwankung) <= self.sensor.fehler_grenze 
                and abs(schwankung_in_relation_zum_vergleich) <= self.sensor.rel_fehler_grenze 
                and rel_fehler < 0.01):
                if tangent_counter == self.counter_limit:
                    self.druck_status = True
                    dur_str = f"{(lokale_zeit):.3f}".replace('.', ',')
                elif tangent_counter > self.counter_limit:
                    self.druck_status = True
                else: 
                    self.druck_status = False
                tangent_counter += 1
            else:
                tangent_counter = 0
                compare_pressure = istwert
                self.druck_status = False
            if self.druck_status:
                stabilität = 1
            else: 
                stabilität = 0

            self.data_queue.put({
                "zeit": lokale_zeit, 
                "druck": istwert, 
                "v_durchlass": v_durch,
                "v_einlass": v_ein,
                "stellgroesse": stellgroesse, 
                "duration": dur_str,
                "p_anteil": ControlUnit.p_anteil,
                "i_anteil": ControlUnit.i_anteil,
                "d_anteil": ControlUnit.d_anteil,
                "stabilität": stabilität
            })
            if self.print_flag:
                print(
                    f"relativer Fehler:{rel_fehler: .4} | Dauer: {lokale_zeit:.3f} s | "
                    f"Druck: {istwert:.5f} mBar  ({self.sensor.sensorwahl})| V_Ein: {v_ein:.4f}V | "
                    f"P-Anteil: {ControlUnit.p_anteil: .6f} | I-Anteil: {ControlUnit.i_anteil: .6f} | D-Anteil: {ControlUnit.d_anteil: .6f} | "
                    f"Stellgroesse: {stellgroesse: .4f} | Tangent Counter: {tangent_counter} | "
                    f"Schwankung: {schwankung:.5f} | rel. Schwankung: {schwankung_in_relation_zum_vergleich:.5f} | "
                    f"dt: {ControlUnit.dt:.4f}s"
                )

            if self.druck_status:
                if not scan_started:
                    self.msa.StartScan()
                    scan_started = True
                else:
                    scan_status = self.msa.statusAbfrage()

    def regelungOnePressure(self, solldruck):
        if self.csv_path is None:
            if self.print_flag:
                print("Kein Pfad eingegeben zur Speicherung der Druckwerte!")
                return
            
        self.ControlUnit = Mathfunctions.ControllSystem(kp=self.kp_base, ki=self.ki_base, kd=self.kd_base, sollwert=solldruck, print_flag=self.print_flag, dt=self.dt)
        self.Math = Mathfunctions.Interpolation(sollwert=solldruck, print_flag=self.print_flag)
        rel_fehler = 1
        lokale_zeit = 0
        tangent_counter = 0
        loop_start = time.perf_counter()
        startzeit = time.time()
        
        istwert = self.sensor.wait_for_next_value() or self.sensor.pressure

        if istwert < 900:
                    self.valves.ambientPressure()
                    
        compare_pressure = istwert
        
        v_ein_fallend = self.Math.interpolierte_Funktion(
            self.lut_reader.stab_v_einlass_fallend, self.lut_reader.stab_druck_einlass_fallend
        )
        if v_ein_fallend is None:
            if self.print_flag:
                print("Fehler: Interpolation fehlgeschlagen, LUT leer?")
            return

        self.Math.v_ein = v_ein_fallend(solldruck)
        self.Math.steigung(self.lut_reader.stab_v_einlass_fallend, self.lut_reader.stab_druck_einlass_fallend)

        prev_kp = self.ControlUnit.kp
        kp = self.kp_base * (self.Math.max_steigung / max(self.Math.steigung_v_ein, 1e-3)) ** (1 / 7)
        ki = self.ki_base * (self.Math.max_steigung / max(self.Math.steigung_v_ein, 1e-3)) ** (1 / 5)
        self.ControlUnit.kp, self.ControlUnit.ki = kp, ki

        if self.print_flag:
            print(f"Sensitivität Sollwert: {self.Math.steigung_v_ein:.4f} | Max Sensitivität: {self.Math.max_steigung:.4f}")
            print(f"Anfängliche Kp: {self.kp_base:.4f} | Angepasster Kp: {self.ControlUnit.kp:.4f}")

        self.csv_writer.TxtFile(
            sollwert=solldruck, 
            alter_kp=prev_kp, 
            kp=kp, 
            ki=ki, 
            kd=kd_base, 
            dt=dt,
            steigung_bei_sollwert=self.Math.steigung_v_ein, 
            max_steigung=self.Math.max_steigung,
            druck_max_steigung=self.Math.druck_bei_max_steigung
        )
        self.druck_status = False
        self.single_pressurevalue_control_stop_btn_flag = False

        while self.is_running and not self.single_pressurevalue_control_stop_btn_flag and istwert >= 0.001:
            prev_pressure = istwert
            neuer_druck = self.sensor.wait_for_next_value()
            if neuer_druck is None:
                if self.print_flag:
                    print("Warnung: Sensor-Timeout!")
                continue
            istwert = neuer_druck

            now = time.perf_counter()
            lokale_zeit = time.time() - startzeit
            if self.data_callback:
                self.data_callback(lokale_zeit, istwert, solldruck, False)

            self.ControlUnit.dt = min((now - loop_start), 1.0)
            loop_start = now
            if self.print_flag:
                print(f"Dauer einer iteration(dt): {self.ControlUnit.dt:.4f}")

            v_durch = 10
            stellgroesse, rel_fehler = self.ControlUnit.logarithmicPID(istwert)
            v_ein = np.clip(self.Math.v_ein + stellgroesse, 0, 10)
            self.valves.applyVoltage(v_durch, v_ein)

            schwankung = (istwert - prev_pressure) / prev_pressure if prev_pressure != 0 else 1e-4
            schwankung_in_relation_zum_vergleich = (istwert - compare_pressure) / compare_pressure
            dur_str = ""

            if (abs(schwankung) <= self.sensor.fehler_grenze 
                and abs(schwankung_in_relation_zum_vergleich) <= self.sensor.rel_fehler_grenze 
                and rel_fehler < 0.01):
                if tangent_counter == self.counter_limit:
                    dur_str = f"{(lokale_zeit):.3f}".replace('.', ',')
                    self.druck_status = True
                elif tangent_counter >= self.counter_limit:
                    self.druck_status = True
                else: 
                    self.druck_status = False
                tangent_counter += 1
            else:
                tangent_counter = 0
                compare_pressure = istwert
                self.druck_status = False
            if self.druck_status:
                stabilität = 1
            else: 
                stabilität = 0
                
            self.data_queue.put({
                "zeit": lokale_zeit, 
                "druck": istwert, 
                "v_durchlass": v_durch,
                "v_einlass": v_ein,
                "stellgroesse": stellgroesse, 
                "duration": dur_str,
                "p_anteil": self.ControlUnit.p_anteil,
                "i_anteil": self.ControlUnit.i_anteil,
                "d_anteil": self.ControlUnit.d_anteil,
                "stabilität": stabilität
            })
            if self.print_flag:
                print(
                    f"relativer Fehler:{rel_fehler: .4} | Dauer: {lokale_zeit:.3f} s | "
                    f"Druck: {istwert:.5f} mBar  ({self.sensor.sensorwahl})| V_Ein: {v_ein:.4f}V | "
                    f"P-Anteil: {self.ControlUnit.p_anteil: .6f} | I-Anteil: {self.ControlUnit.i_anteil: .6f} | D-Anteil: {self.ControlUnit.d_anteil: .6f} | "
                    f"Stellgroesse: {stellgroesse: .4f} | Tangent Counter: {tangent_counter} | "
                    f"Schwankung: {schwankung:.5f} | rel. Schwankung: {schwankung_in_relation_zum_vergleich:.5f} | "
                    f"dt: {self.ControlUnit.dt:.4f}s"
                )
        self.valves.ambientPressure()

        

    def stop(self):
        self.is_running = False
        self.valves.ambientPressure()

if __name__ == "__main__":
    task_completed = False
    csv_path = input("Bitte geben Sie an wo die CSV-Datei gespeichert werden soll: ").strip().strip('"').strip("'")
    #excel_path = input("Bitte geben Sie den Pfad von der Solldruck-Exceldatei ein: ")
    #ref_scan_path = input("Geben Sie den Pfad der Referenz-Scandatei von PSV ein: ")
    solldruck_eingabe = input("Solldruck: ")
    solldruck = float(solldruck_eingabe)

    HM = HardwareManager(print_flag=True)
    #HM.ref_scan_path = ref_scan_path
    #HM.excel_path = excel_path
    HM.csv_path = csv_path

    try: 
        HM.connect_all()
        if HM.csv_path:
            HM.initialize_regler()
            HM.regler.regelungOnePressure(solldruck)
            task_completed = True

        if task_completed:
            print('Erfolgreich abgeschlossen. Verbindung wird beendet')
    except KeyboardInterrupt:
        print("Programm unterbrochen.")
    except UnicodeDecodeError as e:
        print(f'Fehler bei der Dekodierung: {e}')
    finally:
        HM.shutdown()
        print("Alles beendet und abgeschlossen")