import serial
import serial.tools.list_ports
import time
import threading
import queue

class PressureSensor:
    def __init__(self, print_flag=True, port=None, baudrate = 38400, timeout = 0.05):
        self.port = port
        self.ser = None
        self.baudrate = baudrate
        self.timeout = timeout  
        self.wait_timeout = 0.3 
        self.prev_pressure = 1000
        self.untere_hysterese = False
        self.obere_hysterese = False
        self.pressure = 1000
        self.pressure_Error = False
        self.response_array = None
        self.fehler_grenze = None
        self.rel_fehler_grenze = None
        self.pressure_buffer = []
        self.sensorwahl = ""
        self.print_flag = print_flag
        self.data_queue = queue.Queue(maxsize=100)
        self._running = False


    def findDevice(self):
        #this function gets automatically triggered when the connect function is called. So Don't call this function directly, because it is not designed to be called directly.
        ports = list(serial.tools.list_ports.comports()) #ruft eine Liste mit allen existierenden Anschlüssen an Ihrem Computer ab
        if self.print_flag:
            print(f'Liste der angeschlossenen Geräte: {ports}')
        for p in ports:
            if 'ATEN'in p.description:
                if self.print_flag:
                    print(f'this is the Device: {p.device}')
                self.port = p.device
                return self.port
        if self.port is None:
            if self.print_flag:
                print('Das Gerät wurde nicht gefunden.')
            return None

    def connect(self):
        if self.port is None:
            self.findDevice()
        if self.port is None:
            if self.print_flag:
                print("Kein gültiger Port gefunden. Verbindung fehlgeschlagen.")
            return False
        
        try:
            self.ser = serial.Serial(port=self.port, baudrate = self.baudrate, timeout = self.timeout)
            if self.print_flag:
                print(f"Erfolgreich mit {self.port} verbunden.")
            # Send device command in ASCII:  C O M , a <CR> <LF>
            self.ser.reset_input_buffer()
            self.ser.write(b'COM,0\r\n')
            time.sleep(0.1)
            return True
        except serial.SerialException as e:
            if self.print_flag:
                print(f"Fehler beim Verbinden mit {self.port}: {e}")
            return False
    
    def disconnect(self):
        if self._running:
            self.stop_listener()
        if self.ser and self.ser.is_open:
            self.ser.close()
            if self.print_flag:
                print(f"Verbindung zu {self.port} geschlossen.")

    def _readPressure(self):
        #this function gets automatically triggered when the get_pressure function is called. So Don't call this function directly, because it is not designed to be called directly.
        if not self.ser or not self.ser.is_open:
            if self.print_flag:
                print("No serial channel connected")
            return None 
        try:
            if self.ser.in_waiting > 0: 
                raw = self.ser.readline()
            else: 
                if self.print_flag:
                    print("No bytes in stack")
                return None
            resp = raw.decode('utf-8', errors='ignore').strip()
            if resp:
                values = resp.split(",")
                pressure = [float(values[1]), float(values[3])]
                self.response_array = resp
                return pressure 
        except Exception as e :
                self.ser.flushInput()
        return None
    
#_____________pressure reading with event calling as soon as new pressure value arrives_____________    
    def _readPressureContinous(self):
        if not self.ser or not self.ser.is_open:
            if self.print_flag:
                print("No serial channel connected")
            return False
        try:
            if self.ser.in_waiting > 200:
                self.ser.reset_input_buffer()
            raw = self.ser.readline()
            if raw:
                resp = raw.decode('utf-8', errors='ignore').strip()
                if resp and "," in resp:
                    values = resp.split(",")
                    if len(values) >= 4:
                        pressure = [float(values[1]), float(values[3])]
                        self.response_array = resp
                        self.prev_pressure = self.pressure

                        self.SensorwahlmitHystereseGUI(pressure=pressure)
                        #Falls nicht über GUI/HardwareManager Sensor ausgelesen wird,
                        #SensorwahlmitHystereseGUI auskommentieren und die folgenden 2 Zeilen nutzen  
                        
                        #self.SensorwahlmitHysterese(pressure=pressure)
                        #self.maxFehlerBestimmung()
                        
                        return True
        except (ValueError, IndexError):
            # Abfangen von unvollständigen/beschädigten Sensorstrings
            pass
        except Exception as e:
            if self.print_flag:
                print(f"Fehler beim kontinueirlichem Einlesen des Sensors: {e}")
            if self.ser and self.ser.is_open:
                self.ser.flushInput()
        return False

    def start_listener(self):
        #starts the thread to continously read from the RS232 channel
        self._running = True
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()
        if self.print_flag:
            print("Sensor-listener gestartet!")

    def stop_listener(self):
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
            if self.print_flag:
                print("Sensor-Listener gestoppt!")

    def _worker(self):
        while self._running:
            if self._readPressureContinous():
                # FLAG SET!
                if self.data_queue.full():
                    try:
                        self.data_queue.get_nowait()# Ältesten Wert droppen wenn voll
                    except queue.Empty:
                        pass
                self.data_queue.put(self.pressure)
            else:
                time.sleep(0.001)

    def wait_for_next_value(self):
        try:
            # Holt den nächsten verfügbaren Wert aus der Queue
            val = self.data_queue.get(timeout=self.wait_timeout)
            self.data_queue.task_done()
            return val
        except queue.Empty:
            return False
#________________________end of continous pressure reading block___________________________


    def _filterPressure(self, new_pressure):
        median_length = 3

        self.pressure_buffer.append(new_pressure)
        if len(self.pressure_buffer)>median_length:
            self.pressure_buffer.pop(0)
        if len(self.pressure_buffer)==median_length:
            return sorted(self.pressure_buffer)[1]
        else:
            return new_pressure

    def getPressure(self):
        if self.pressure:
            self.prev_pressure = self.pressure
        pressure = self._readPressure()
        counter = 0
        while pressure is None and counter < 20:
            pressure = self._readPressure()
            counter += 1
            time.sleep(0.01)
        if pressure is None:
            print("Kritischer Fehler: Antwort vom Sensor auch nach 20 versuchen nicht sauber")
            self.pressure_Error = True
            return None
        
        self.SensorwahlmitHysterese(pressure)
        self.maxFehlerBestimmung()
        return self.pressure
    
    def SensorwahlmitHysterese(self, pressure):
        if pressure[0]>= 1.3: # ab >= 1mBar immer sensor 1 verwenden
            temp_pressure = pressure[0] #round(self.pressure[0], 2) #round(hp_smooth, 2)
            self.untere_hysterese = False
            self.obere_hysterese = False
            self.sensorwahl = "HP sensor"
        elif pressure[1]< 1.0: #ab <1mBar immer sensor 2 verwenden
            temp_pressure = pressure[1]
            self.obere_hysterese = False
            self.untere_hysterese = False
            self.sensorwahl = "LP sensor"
        elif self.untere_hysterese == True:
            temp_pressure = pressure[1]
            self.sensorwahl = "LP sensor"
        elif self.obere_hysterese == True:
            temp_pressure = pressure[0]
            self.sensorwahl = "HP sensor"
        elif pressure[1] >= 1.0 and self.prev_pressure < pressure[1] and self.prev_pressure < 1.0: #wenn man von < 1.0 mBar kommt und < 1.3 mBar ist. -> sensor 2 verwenden
            temp_pressure = pressure[1]
            self.untere_hysterese = True
            self.sensorwahl = "LP sensor"
        elif pressure[0] < 1.3 and self.prev_pressure >= pressure[0] and self.prev_pressure >=1.3: #wenn man von > 1.3 mBar kommt und > 1.0 mBar ist. -> sensor 1 verwenden
            temp_pressure = pressure[0]
            self.obere_hysterese = True
            self.sensorwahl = "HP sensor"
        else:
            temp_pressure = pressure[0]
            self.sensorwahl = "HP sensor"
        if temp_pressure <=0:
            temp_pressure = 1e-4
        #hier wird noch gefiltert damit es keine messfehler wie signalrauschen eine instabilität in die regelung wirft
        temp_pressure = self._filterPressure(temp_pressure)
        self.pressure = temp_pressure

    def SensorwahlmitHystereseGUI(self, pressure):
        if pressure[0]>= 1.3: # ab >= 1mBar immer sensor 1 verwenden
            temp_pressure = pressure[0] #round(self.pressure[0], 2) #round(hp_smooth, 2)
            self.untere_hysterese = False
            self.obere_hysterese = False
            self.sensorwahl = "HP sensor"
            self.fehler_grenze = 0.05
        elif pressure[1]< 1.0: #ab <1mBar immer sensor 2 verwenden
            temp_pressure = pressure[1]
            self.obere_hysterese = False
            self.untere_hysterese = False
            self.sensorwahl = "LP sensor"
            self.fehler_grenze = 1e-3
        elif self.untere_hysterese == True:
            temp_pressure = pressure[1]
            self.sensorwahl = "LP sensor"
            self.fehler_grenze = 1e-3
        elif self.obere_hysterese == True:
            temp_pressure = pressure[0]
            self.sensorwahl = "HP sensor"
            self.fehler_grenze = 0.05
        elif pressure[1] >= 1.0 and self.prev_pressure < pressure[1] and self.prev_pressure < 1.0: #wenn man von < 1.0 mBar kommt und < 1.3 mBar ist. -> sensor 2 verwenden
            temp_pressure = pressure[1]
            self.untere_hysterese = True
            self.sensorwahl = "LP sensor"
            self.fehler_grenze = 1e-3
        elif pressure[0] < 1.3 and self.prev_pressure >= pressure[0] and self.prev_pressure >=1.3: #wenn man von > 1.3 mBar kommt und > 1.0 mBar ist. -> sensor 1 verwenden
            temp_pressure = pressure[0]
            self.obere_hysterese = True
            self.sensorwahl = "HP sensor"
            self.fehler_grenze = 0.05
        else:
            temp_pressure = pressure[0]
            self.sensorwahl = "HP sensor"
            self.fehler_grenze = 0.05
        if temp_pressure <=0:
            temp_pressure = 1e-4
        #hier wird noch gefiltert damit es keine messfehler wie signalrauschen eine instabilität in die regelung wirft
        temp_pressure = self._filterPressure(temp_pressure)
        self.pressure = temp_pressure
        self.rel_fehler_grenze = self.fehler_grenze * 3

    def maxFehlerBestimmung(self):
        if self.pressure < 7.5 * 1e-4:
            fehler_grenze = 0.02
        elif self.pressure < 1e-3:
            fehler_grenze = 0.0134
        elif self.pressure < 2.5*1e-3:
            fehler_grenze = 0.01
        elif self.pressure < 5*1e-3 and self.pressure < 5*1e-1:
            fehler_grenze = 0.005
        elif self.pressure >= 5*1e-1 and self.pressure < 7.5*1e-1:
            fehler_grenze = 0.02
        elif self.pressure >= 7.5 * 1e-1 and self.pressure < 1.0:
            fehler_grenze = 0.015
        elif self.pressure >= 1.0 and self.pressure < 2.5:
            fehler_grenze = 0.01
        elif self.pressure >= 2.5:
            fehler_grenze = 0.005   
        self.fehler_grenze = fehler_grenze
        self.rel_fehler_grenze = self.fehler_grenze * 3

if __name__ == "__main__":
    sensor = PressureSensor() 
    if sensor.connect():
        try:
            end_time = time.time() + 10  # Lese den Druck für 10 Sekunden
            while time.time() < end_time:
                pressure = sensor.getPressure()
                print(f"Aktueller Druck: {pressure} mBar")
                #time.sleep(0.09)  # Warte 1 s zwischen den Messungen
        finally:
            sensor.disconnect()