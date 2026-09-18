import win32com.client
import time
import os
import pandas as pd

class MSA500():
    #work flow order to start a scan succesfully
    # 1) initialize class with MSA500.init(excel_filepath) excelfile_path = path of the excelfile with the pressure values
    # 2) start connecting to the interface of the MSA software via MSA500.connect()
    # 3) generate an array with the pressure values with MSA500.excelvectorGenerator()
    # 4) get path of the reference scanfile: MSA500.reference_file = input('')
    # 5) get the path where the scanned data should be stored at: MSA500.pathRequest()
    # 6) create the folder where the scanned data is getting stored at: MSA500.allocateFolder
    # 7) when pressure ready start scan:
    # 8) end scan 
    def __init__(self, print_flag=True):
        self.scan_status = 0
        self.reference_file = None
        self.new_folder_path = None
        self.new_file = None
        self.general_folder_path = None
        self.sollwert_tabelle = []
        self.sollwert = None
        self.AcquisitionInstance = win32com.client.Dispatch('PSV.AcquisitionInstance')
        self.app = self.AcquisitionInstance.GetApplication(True, 10000)
        self.sollwert_exceltabelle_path = ""
        self.print_flag=print_flag

    def connect(self):
        self.app.Application.Activate()
        buffer = self.app.ActiveDocument.Name
        if self.print_flag:
            print(buffer)
        if buffer is None:
            return False
        else:
            return True

    def copy_binary_file(self):
        # Check if the reference file exists
        if not os.path.exists(self.reference_file):
            if self.print_flag:
                print(f"Reference file '{self.reference_file}' does not exist.")
            return

        # Open the reference file in binary mode for reading
        with open(self.reference_file, 'rb') as ref_file:
            # Read the binary content
            binary_content = ref_file.read()

        # Open the new file in binary mode for writing
        with open(self.new_file, 'wb') as new_file_obj:
            # Write the binary content to the new file
            new_file_obj.write(binary_content)

        if self.print_flag:
            print(f"Binary content copied from '{self.reference_file}' to '{self.new_file}'.")

    def statusAbfrage(self):
        self.scan_status = self.app.Application.Acquisition.State
        #print(type(self.scan_status))
        #print(self.scan_status)
        if self.scan_status == 3:  # wenn gescanned wird ist status 3, wenn fertig 0 und wenn abgebrochen 5
            time.sleep(1)
            return 3
        elif self.scan_status == 0:
            if self.print_flag:
                print('Scan war erfolgreich.')
            return 0
        else:
            if self.print_flag:
                print(f"neuer status: {self.scan_status}")
            return self.scan_status

    def pathRequest(self, path):
        if path == None: 
            pfad = input("Geben Sie den Pfad/Ort an, an der die MSA-Scan-Dateien gespeichert werden sollen: ").strip().replace('"','')
        else: pfad = r"C:\Users\messung\PycharmProjects\Automatisierung_Vakuumregelung_mit_MSAmessung\test_messungen\MSA500_tests"
        self.general_folder_path = pfad
        if self.general_folder_path != "." and not self.general_folder_path.endswith('\\') and not self.general_folder_path.endswith('/'):
            self.general_folder_path += '\\'
        test_filename = f"{self.general_folder_path}__test_write_permission__.tmp"
        try:
            # Try to open a temporary file for writing
            with open(test_filename, mode='w') as f:
                pass
            # Lösche die Testdatei wieder, wenn das Schreiben erfolgreich war
            if os.path.exists(test_filename):
                os.remove(test_filename)
        except FileNotFoundError as e:
            error_msg = str(e)
            if self.general_folder_path != "." and pfad not in error_msg and "No such file or directory" in error_msg:
                if self.print_flag:
                    print(f"\n[FEHLER]: Der Pfad '{pfad}' ist ungültig oder existiert nicht.")
                    print("Bitte überprüfen Sie die Schreibweise oder erstellen Sie den Ordner manuell.\n")
                # Recall itself to ask the user again
                return self.pathRequest()
            else:
                # The folder exists! (It only complained that the validation file wasn't inside it)
                if self.print_flag:
                    print(f"Pfad erfolgreich verifiziert: {self.general_folder_path}")
        except (PermissionError, OSError):
            if self.print_flag:
                print(f"\n[FEHLER]: Zugriff verweigert oder ungültige Pfadsyntax für '{pfad}'.\n")
            return self.pathRequest()

    def allocateFile(self, folder_name, file_name):
        if folder_name != "." and not folder_name.endswith('\\') and not folder_name.endswith('/'):
                    folder_name += '\\'
        if not self.general_folder_path:
            self.pathRequest()
        if self.general_folder_path == ".":
            self.new_file = folder_name + file_name
        else:
            self.new_file = self.general_folder_path + folder_name + file_name
        #self.new_folder_path = os.path.join(self.general_folder_path, self.new_folder_name)
        target_dir = os.path.dirname(self.new_file) if self.new_file != "." else "."
        # Überprüfen, ob der Ordner bereits existiert, um ihn zu erstellen
        if not os.path.exists(target_dir) and target_dir != ".":
            os.makedirs(target_dir)
            if self.print_flag:
                print(f"Ordner '{target_dir}' wurde erfolgreich erstellt.")
            self.copy_binary_file()
            return True
        else:
            if self.print_flag:
                print(f"Der Zielordner existiert bereits.")
            return False
    def allocateFileForGUI(self, folder_name, file_name):
        """Erweiterte Funktion für die GUI-Automatisierung"""
        ref_path = getattr(self, 'reference_file', None)
        
        # Pfad explizit an pathRequest übergeben
        self.pathRequest(ref_path)
        if folder_name != "." and not folder_name.endswith('\\') and not folder_name.endswith('/'):
            folder_name += '\\'
        if not self.general_folder_path:
            self.pathRequest()
        if self.general_folder_path == ".":
            self.new_file = folder_name + file_name
        else:
            self.new_file = self.general_folder_path + folder_name + file_name
        #self.new_folder_path = os.path.join(self.general_folder_path, self.new_folder_name)
        target_dir = os.path.dirname(self.new_file) if self.new_file != "." else "."
        # Überprüfen, ob der Ordner bereits existiert, um ihn zu erstellen
        if not os.path.exists(target_dir) and target_dir != ".":
            os.makedirs(target_dir)
            if self.print_flag:
                print(f"Ordner '{target_dir}' wurde erfolgreich erstellt.")
            self.copy_binary_file()
            return True
        else:
            if self.print_flag:
                print(f"Der Zielordner existiert bereits.")
            return False


    def excelPathRequest(self):
        antwort = float(input("Möchten Sie nochmal versuchen den Pfad der Exceldatei manuel einzugeben? JA = 1; NEIN = 0: "))
        if antwort == 0:
            return False
        elif antwort == 1:
            self.sollwert_exceltabelle_path = input("geben Sie nochmal den Pfad der Datei ein: ")
            return True
        else:
            if self.print_flag:
                print("Ungültige Eingabe. Bitte wählen Sie 1 oder 0.")
            return self.excelPathRequest()  # Rekursion für Fehleingaben

    def excelVectorGenerator(self):
        try:
            # Überprüfen, ob die Datei existiert
            if not os.path.isfile(self.sollwert_exceltabelle_path):
                if self.print_flag:
                    print("Die Datei wurde nicht gefunden.")
                if self.excelPathRequest():
                    return self.excelVectorGenerator()
                else:
                    return False

            # Erkennen des Dateiformats anhand der Dateiendung
            file_extension = self.sollwert_exceltabelle_path.lower().split('.')[-1]

            if file_extension == 'xlsx' or file_extension == 'xls':
                # Excel-Datei einlesen
                df = pd.read_excel(self.sollwert_exceltabelle_path)
                if self.print_flag:
                    print("Excel-Datei erfolgreich geladen.")
            elif file_extension == 'csv': # CSV-Datei einlesen
                df = pd.read_csv(self.sollwert_exceltabelle_path)
                if self.print_flag:
                    print("CSV-Datei erfolgreich geladen.")
            else:
                if self.print_flag:
                    print("Nur Excel- (.xlsx, .xls) und CSV-Dateien (.csv) werden unterstützt.")
                if self.excelPathRequest():
                    return self.excelVectorGenerator()
                else:
                    return False

            # Entfernen von führenden/nachfolgenden Leerzeichen in den Spaltenüberschriften
            df.columns = df.columns.str.strip()
            if self.print_flag:
                print("Verfügbare Spalten:", df.columns)
            # Überprüfen, ob eine der Spalten 'Drücke:' enthält, unabhängig von zusätzlichen Zeichen
            matching_column = None
            for column in df.columns:
                if 'Drücke' in column:  # Suche nach 'Drücke' in der Spaltenüberschrift
                    matching_column = column
                    break

            if matching_column is None:
                if self.print_flag:
                    print("Spalte 'Drücke:' wurde nicht gefunden.")
                if self.excelPathRequest():
                    return self.excelVectorGenerator()
                else:
                    return False
            if self.print_flag:
                print(f"Gefundene Spalte: {matching_column}")
            druck_index = 0
            if ";;" in matching_column:
                header_parts = matching_column.split(";;")
                for idx, part in enumerate(header_parts):
                    if "druck" in part.lower():
                        druck_index = idx
                        break
            # Werte der 'Drücke:;;Zeitsabstände:'-Spalte aufteilen und nur die Druckwerte extrahieren
            for value in df[matching_column].dropna():
                val_str = str(value).strip()
                if ";;" in val_str:
                    split_values = val_str.split(";;")
                    if len(split_values) > druck_index:
                        raw_druck = split_values[druck_index]
                    else:
                        raw_druck = split_values[0]
                else:
                # Normale Zelle (nur die Zahl)
                    raw_druck = val_str
                raw_druck = raw_druck.replace(",", ".")

                # Überprüfen, ob der Wert numerisch ist
                try:
                    # Versuche, den Wert in eine Zahl zu konvertieren
                    druckwert_f = float(raw_druck)  # Wenn erfolgreich, ist es ein gültiger Druckwert
                    self.sollwert_tabelle.append(druckwert_f)  # Füge den Druckwert hinzu
                except ValueError:
                    # Wenn der Wert keine Zahl ist, überspringe ihn
                    continue

            if self.print_flag:
                print(f"Druckwerte: {self.sollwert_tabelle}")
            return True

        except Exception as e:
            if self.print_flag:
                print(f"Ein Fehler ist aufgetreten: {e}")
            return False
        
    def StartScan(self):
        self.app.Application.Acquisition.ScanFileName = self.new_file
        self.app.Application.Acquisition.Scan(0)
        if self.print_flag:
            print('app.Application.ActiveDocument.Name: ', self.app.Application.ActiveDocument.Name)
        
    def GeneratorSetAmplitude(self, amplitude):
        self.app.Application.Acquisition.ActiveProperties.GeneratorsProperties.Item(1).Amplitude = amplitude
        if self.print_flag:
            print(f"Neue Amplitude gesetzt auf: {self.app.Application.Acquisition.ActiveProperties.GeneratorsProperties.Item(1).Amplitude} ")


if __name__ == "__main__":
    try:
        
        MSA = MSA500(excelfile_path = None)
        if not MSA.connect():
            raise RuntimeError("MSA500-Software-Initialisierung fehlgeschlagen.")
        
        #MSA.reference_file = input("Geben Sie den Pfad der Referenz-Scandatei von PSV ein: ")
        MSA.reference_file = r"C:\Users\messung\PycharmProjects\Automatisierung_Vakuumregelung_mit_MSAmessung\test_referenz\ScanMSA500_0\Scan_0.svd"
        scanfile_location = r"C:\Users\messung\PycharmProjects\Automatisierung_Vakuumregelung_mit_MSAmessung\test_messungen\MSA500_tests"
        MSA.pathRequest(path= scanfile_location)
        solldruck = input("geben sie eine Nummer zur Indentifikation der neuen Scan Datei/Ordner ein: ")
        folder_name = fr"ScanMSA500_{solldruck}"
        file = fr"Scan_{solldruck}.svd"
        if not MSA.allocateFile(folder_name=folder_name, file_name = file):
            raise RuntimeError("Problem beim Anlegen der neuen Scan-Datei. ")
        else:
            print('Name der neuen Scandatei: ',MSA.new_file)

        options = [item for item in dir(MSA.app.Application.Acquisition.ActiveProperties.FftProperties) if not item.startswith("_")]
        print("Verfügbare Optionen in Acquisition:")
        for opt in options:
            print(" -", opt)

        print()
        print(MSA.app.Application.Acquisition.ActiveProperties.FftProperties.Bandwidth)
        print()

        try:
            # Oft gibt es ein Generator-Objekt oder Eigenschaften im aktiven Modus
            gen = (MSA.app.Application.Acquisition.ActiveProperties.GeneratorsProperties)  # oder acq.ActiveProperties / acq.ModeProperties
            # print("--- Eigenschaften in ActiveProperties.GeneratorsProperties ---")
            # for item in dir(gen):
            #     if not item.startswith("_"):
            #         print(" -", item)
            # print()
            
            
            print("\n--- GeneratorProperties UNTERSUCHUNG ---")
            # 1. Attribute des Unter-Objekts anzeigen
            item_members = [x for x in dir(gen.Item(1)) if not x.startswith("_")]
            print(f"Verfügbare Attribute in GeneratorProperties.Item:", item_members)

            # 2. Versuchen, typische COM-Eigenschaften direkt abzurufen
            prop = "Amplitude"
            if hasattr(gen.Item(1), prop):
                try:
                    print(f"  . {prop} = {getattr(gen.Item(1), prop)}")
                except Exception as ex:
                    print(f"  . {prop} = [Fehler beim Lesen: {ex}]")
            MSA.app.Application.Acquisition.ActiveProperties.GeneratorsProperties.Item(1).Amplitude = 1.0
            print(f"Neue Amplitude gesetzt auf: {MSA.app.Application.Acquisition.ActiveProperties.GeneratorsProperties.Item(1).Amplitude} ")
            gen = (MSA.app.Application.Acquisition.ActiveProperties.GeneratorsProperties)
            # 1. Attribute des Unter-Objekts anzeigen
            item_members = [x for x in dir(gen.Item(1)) if not x.startswith("_")]
            print(f"Verfügbare Attribute in GeneratorProperties:", item_members)
            # 2. Versuchen, typische COM-Eigenschaften direkt abzurufen
            if hasattr(gen.Item(1), prop):
                try:
                    print(f"  . {prop} = {getattr(gen.Item(1), prop)}")
                except Exception as ex:
                    print(f"  . {prop} = [Fehler beim Lesen: {ex}]")
        except Exception as e:
            print(f"Fehler beim Zugriff auf Generator: {e}")
        #start scan
        
        MSA.StartScan()
        status = MSA.statusAbfrage()
        while status == 3:
            print(f'Scan wird druchgeführt: {MSA.scan_status}')
            time.sleep(1)
            status = MSA.statusAbfrage()

        if MSA.scan_status == 0:
            print("Scan erfolgreich durchgeführt und abgeschlossen.")
        elif MSA.scan_status == 5: 
            print("Scan abgebrochen")
            #hier kann noch erweitert werden in dem erneut ein scan bei dem fehlgeschlagenen Druck wiederholt wird aber tbc

    except KeyboardInterrupt:
        print("Programm unterbrochen.")
    except UnicodeDecodeError as e:
            print(f'Fehler bei der Dekodierung: {e}')