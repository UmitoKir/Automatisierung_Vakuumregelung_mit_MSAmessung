import nidaqmx
import time

class ValveControl:
    def __init__(self, print_flag=True, valve_name = "Dev1_MSA", ao0_name = "ao0", ao1_name = "ao1"): #hier muss evtl der valve_name geändert werden.
        self.valve_name = valve_name
        self.channel_name_0 = f"{valve_name}/{ao0_name}"
        self.channel_name_1 = f"{valve_name}/{ao1_name}"
        self.task = None
        self.print_flag = print_flag
    
    def connect(self):
        self.close()
        try: 
            device = nidaqmx.system.Device(self.valve_name)
            device.reset_device()
            time.sleep(0.5)
            #um zu sehen welche DAQ-geräte angeschlossen sind kommentiere den folgenden Abschnitt aus
            # system = nidaqmx.system.System.local()
            # print("Verfügbare der DAQ-Geräte:")
            # for dev in system.devices:
            #     print(dev.name, "-", dev.product_type)
            
            task = nidaqmx.Task()
            task.ao_channels.add_ao_voltage_chan(self.channel_name_0)
            task.ao_channels.add_ao_voltage_chan(self.channel_name_1)
            self.task = task
            if self.print_flag:
                print(f"DAQ-Kanäle ({self.valve_name}) erfolgreich initialisiert.")
            return True
        except Exception as e:
            if self.print_flag:
                print(f"Fehler bei der Ventil-Initialisierung: {e}")
            self.close()
            return False
        
    def applyVoltage(self, v_durch, v_ein):
        if self.task is None:
            if self.print_flag:
                print("Ventile nicht initialisiert....")
            return False
        v_durch = max(0.0, min(10.0, float(v_durch)))
        v_ein = max(0.0, min(10.0, float(v_ein)))

        try: 
            self.task.write([v_durch, v_ein], auto_start=True)
            return True 
        except Exception as e:
            if self.print_flag:
                print(f"DAQmx Schreibfehler ({e}). Versuche automatisches Re-Connect...")
            if self.connect():
                try:
                    self.task.write([v_durch, v_ein], auto_start=True)
                    if self.print_flag:
                        print("Re-Connect erfolgreich! Regelung läuft weiter.")
                    return True
                except Exception as ex:
                    if self.print_flag:
                        print(f"Erneuter Fehler nach Re-Connect: {ex}")
            return False
        
    def ambientPressure(self):
        if self.print_flag:
            print("ao0: 0 , ao1: 5.5")
        self.applyVoltage(0.0, 5.0)
        time.sleep(5)
        
        if self.print_flag:
            print("ao0: 0 , ao1: 6")
        self.applyVoltage(0.0, 6.0)
        time.sleep(5)
        
        if self.print_flag:
            print("ao0: 0 , ao1: 7.5")
        self.applyVoltage(0.0, 7.5)
        time.sleep(4)

        if self.print_flag:
            print("ao0: 0 , ao1: 10")
        self.applyVoltage(0.0, 10.0)
        time.sleep(3)

    def shutdown(self):
        try: 
            self.task.write([0.0, 0.0])
            return True 
        except Exception as e:
            if self.print_flag:
                print(f"Fehler bei Schließung der Ventile(shutdown): {e}")
            return False
        
    def close(self):
        if self.task is not None:
            try:
                self.shutdown()
                self.task.stop()
                self.task.close()
                if self.print_flag:
                    print("DAQmx-Task sauber beendet.")
            except Exception as e:
                if self.print_flag:
                    print(f"Fehler beim Schließen der DAQmx-Task: {e}")
            finally:
                self.task = None

if __name__ == "__main__":
    valves = ValveControl(valve_name="Dev1")
    task_completed = False
    try:    
        if not valves.connect():
            raise RuntimeError("Ventil-Initialisierung fehlgeschlagen.")
        
        print("ao0: 10 , ao1: 0")
        valves.applyVoltage(10.0, 0.0)
        time.sleep(10)

        valves.ambientPressure()
        
        task_completed = True
        if task_completed:
            print('Erfolgreich abgeschlossen.')
    except Exception as e:
        print(f"Ein Fehler ist aufgetreten: {e}")
    finally:
        valves.close()