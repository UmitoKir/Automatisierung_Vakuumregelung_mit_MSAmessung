# import sys
# #import queue
# from PySide6.QtWidgets import (
#     QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
#     QLabel, QLineEdit, QPushButton, QFileDialog, QGroupBox, QGridLayout, QMessageBox
# )
# from PySide6.QtCore import QTimer, Qt
# import pyqtgraph as pg  # Für Performantes Live-Plotting (pip install pyqtgraph)

# #Importiere deinen erstellten HardwareManager
# from HardwareManager import HardwareManager
import sys
import os
import random
# Ändere den Import zu PyQt5:
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget,
                            QLabel, QLineEdit, QPushButton, QFileDialog, QGroupBox, QMessageBox, QScrollBar)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont
import pyqtgraph as pg

class HauptFenster(QWidget):
    def __init__(self):
        super().__init__()
        self.pfad1 = ""
        self.pfad2 = ""
        self.pfad3 = ""
        self.pfad4 = ""
        self.previous_page = 0
        self.solldruck = 0.0

        self.plot_zeit = []
        self.plot_druck = []
        self.zeit_zähler = 0.0

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_live_plot)

        #__________________
        self.initUI()

    def initUI(self):
        # Fenster-Eigenschaften festlegen
        self.setWindowTitle("Automatisierter Scan-Messung mit MSA500 gekoppelt mit der Vakuumpumpe")
        self.resize(900, 600)

        # Layoutelement erstellen (ordnet Elemente vertikal untereinander an)
        self.layout = QVBoxLayout(self)

        self.stacked_widget = QStackedWidget()
        self.layout.addWidget(self.stacked_widget)

        self.page_home = self.erstelle_home_seite()
        self.page_scan = self.erstelle_scan_seite()
        self.page_druckeingabe = self.manuelle_druckeingabe()
        self.page_einstellungen = self.einstellungen()
        self.page_live_plot = self.erstelle_live_plot_seite()
        
        self.stacked_widget.addWidget(self.page_home)     # Index 0
        self.stacked_widget.addWidget(self.page_scan)    # Index 1
        self.stacked_widget.addWidget(self.page_druckeingabe)  # Index 2
        self.stacked_widget.addWidget(self.page_einstellungen)  # Index 3
        self.stacked_widget.addWidget(self.page_live_plot)     # Index 4
        

        # Starte auf dem Home-Screen
        self.zeige_home()


    # ==================== SEITE 0: HOME SCREEN ====================
    def erstelle_home_seite(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        # Titel
        titel = QLabel("Hauptmenü")
        titel.setAlignment(Qt.AlignCenter)
        titel_font = QFont()
        titel_font.setPointSize(16)
        titel_font.setBold(True)
        titel.setFont(titel_font)
        layout.addWidget(titel)

        layout.addSpacing(30)

        # Button 1: Zur Pfadauswahl / Scan starten
        btn_scan = QPushButton("1. Automatisierte Druckeinstellung mit anschließendem Scan")
        btn_scan.setFont(QFont("Arial", 11))
        btn_scan.setFixedHeight(45)
        btn_scan.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(1))
        layout.addWidget(btn_scan)

        # Button 2: Beispiel für eine weitere Funktion
        btn_option2 = QPushButton("2. Manuelle Druck eingabe")
        btn_option2.setFont(QFont("Arial", 11))
        btn_option2.setFixedHeight(45)
        btn_option2.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(2))
        layout.addWidget(btn_option2)

        # Button 3: Beispiel für eine weitere Funktion
        btn_option3 = QPushButton("3. Einstellungen")
        btn_option3.setFont(QFont("Arial", 11))
        btn_option3.setFixedHeight(45)
        btn_option3.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(3))
        layout.addWidget(btn_option3)

        # Button 4: Beenden
        btn_exit = QPushButton("Beenden")
        btn_exit.setFont(QFont("Arial", 11))
        btn_exit.setFixedHeight(40)
        btn_exit.clicked.connect(self.close)
        layout.addWidget(btn_exit)

        layout.addStretch()  # Schiebt alle Elemente nach oben
        return page

    # ==================== SEITE 1: PFADAUSWAHL ====================
    def erstelle_scan_seite(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        titel = QLabel("Bitte wählen Sie die erforderlichen Pfade aus")
        titel.setAlignment(Qt.AlignCenter)
        titel_font = QFont()
        titel_font.setPointSize(14)
        titel_font.setBold(True)
        titel.setFont(titel_font)
        layout.addWidget(titel)

        group_box = QGroupBox("Konfiguration der Input-Dateien")
        group_layout = QVBoxLayout()

        # Pfad 1
        layout_pfad2 = QHBoxLayout()
        label2 = QLabel("2. Solldruck-Datei:")
        label2.setFixedWidth(180)
        self.line_edit_pfad2 = QLineEdit()
        self.line_edit_pfad2.setPlaceholderText("Pfad zur CSV-/Excel-Datei wählen...")
        btn_pfad2 = QPushButton("Durchsuchen...")
        btn_pfad2.clicked.connect(self.waehle_datei_2)
        layout_pfad2.addWidget(label2)
        layout_pfad2.addWidget(self.line_edit_pfad2)
        layout_pfad2.addWidget(btn_pfad2)
        group_layout.addLayout(layout_pfad2)

        # Pfad 2
        layout_pfad3 = QHBoxLayout()
        label3 = QLabel("3. Referenz-Scan-Datei:")
        label3.setFixedWidth(180)
        self.line_edit_pfad3 = QLineEdit()
        self.line_edit_pfad3.setPlaceholderText("Pfad zur SVD-Datei wählen...")
        btn_pfad3 = QPushButton("Durchsuchen...")
        btn_pfad3.clicked.connect(self.waehle_svd_datei)
        layout_pfad3.addWidget(label3)
        layout_pfad3.addWidget(self.line_edit_pfad3)
        layout_pfad3.addWidget(btn_pfad3)
        group_layout.addLayout(layout_pfad3)

        # Pfad 3
        layout_pfad4 = QHBoxLayout()
        label4 = QLabel("4. Speicherort/Ordner:")
        label4.setFixedWidth(180)
        self.line_edit_pfad4 = QLineEdit()
        self.line_edit_pfad4.setPlaceholderText("Zielordner wählen...")
        btn_pfad4 = QPushButton("Durchsuchen...")
        btn_pfad4.clicked.connect(self.waehle_ordner_4)
        layout_pfad4.addWidget(label4)
        layout_pfad4.addWidget(self.line_edit_pfad4)
        layout_pfad4.addWidget(btn_pfad4)
        group_layout.addLayout(layout_pfad4)

        group_box.setLayout(group_layout)
        layout.addWidget(group_box)

        # Buttons unten: Bestätigen & Zurück
        btn_layout = QHBoxLayout()

        btn_back = QPushButton("← Zurück zum Hauptmenü")
        btn_back.setFont(QFont("Arial", 10))
        btn_back.clicked.connect(self.zeige_home)

        self.btn_start = QPushButton("Pfade übernehmen")
        self.btn_start.setFont(QFont("Arial", 10, QFont.Bold))
        self.btn_start.clicked.connect(self.bestaetige_pfade)

        btn_layout.addWidget(btn_back)
        btn_layout.addWidget(self.btn_start)

        layout.addLayout(btn_layout)
        return page

    # ==================== SEITE 2: Manuelle druckeingabe ====================
    def manuelle_druckeingabe(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        label = QLabel("Manuelle Druckeingabe")
        label.setAlignment(Qt.AlignCenter)
        label.setFont(QFont("Arial", 14, QFont.Bold))
        layout.addWidget(label)

        # Hier können z.B. Buttons zum manuellen Öffnen von Ventilen hin
        layout_druck = QHBoxLayout()
        label_druck = QLabel("Gewünschter Druck:")
        label_druck.setFixedWidth(180)
        self.line_edit_druck = QLineEdit()
        self.line_edit_druck.setPlaceholderText("Druck in mBar eingeben...")
        btn_druck = QPushButton("Ansteuern")
        btn_druck.clicked.connect(self.bestaetige_druckeingabe)
        layout_druck.addWidget(label_druck)
        layout_druck.addWidget(self.line_edit_druck)
        layout_druck.addWidget(btn_druck)

        layout.addLayout(layout_druck)
        layout.addSpacing(30)

        btn_back = QPushButton("← Zurück zum Hauptmenü")
        btn_back.clicked.connect(self.zeige_home)
        layout.addWidget(btn_back)

        layout.addStretch()
        return page

    # ==================== SEITE 3: Einstellungen ====================
    def einstellungen(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        label = QLabel("System-Einstellungen")
        label.setAlignment(Qt.AlignCenter)
        label.setFont(QFont("Arial", 14, QFont.Bold))
        layout.addWidget(label)

        group_box = QGroupBox("Hardware-Parameter")
        group_layout = QVBoxLayout()

        # Beispiel-Einstellungen
        default_lut_pfad = r"C:\Users\messung\PycharmProjects\Automatisierung_Vakuumregelung_mit_MSAmessung\Regulierung_LUT\messung_ventil_mehr_stützpunkte_gut.csv"
        layout_lut = QHBoxLayout()
        label1 = QLabel("LUT-Datei für die Regelung:")
        label1.setFixedWidth(180)
        self.line_edit_lut = QLineEdit()
        self.line_edit_lut.setText(default_lut_pfad)
        btn_pfad1 = QPushButton("Ändern")
        btn_pfad1.clicked.connect(self.waehle_lut_datei)
        layout_lut.addWidget(label1)
        layout_lut.addWidget(self.line_edit_lut)
        layout_lut.addWidget(btn_pfad1)
        group_layout.addLayout(layout_lut)

        default_csv_pfad = r"C:\Users\messung\PycharmProjects\Automatisierung_Vakuumregelung_mit_MSAmessung\test_messungen\HM_test"
        layout_csv = QHBoxLayout()
        label_csv = QLabel("CSV-Datei Speicherort für die Druckverlaufprotokollierung:")
        label_csv.setFixedWidth(180)
        self.line_edit_csv = QLineEdit()
        self.line_edit_csv.setText(default_csv_pfad)
        btn_csv = QPushButton("Ändern")
        btn_csv.clicked.connect(self.waehle_csv_datei)
        layout_csv.addWidget(label_csv)
        layout_csv.addWidget(self.line_edit_csv)
        layout_csv.addWidget(btn_csv)
        group_layout.addLayout(layout_csv)

        layout_com = QHBoxLayout()
        layout_com.addWidget(QLabel("COM-Port Vakuumpumpe:"))
        line_com = QLineEdit("COM3")
        layout_com.addWidget(line_com)
        group_layout.addLayout(layout_com)

        
        group_box.setLayout(group_layout)
        layout.addWidget(group_box)

        btn_layout = QHBoxLayout()
        btn_back = QPushButton("Zurück")
        btn_back.clicked.connect(self.zeige_home)
        btn_speichern = QPushButton("Speichern")
        btn_speichern.clicked.connect(self.zeige_home)
        btn_layout.addWidget(btn_back)
        btn_layout.addWidget(btn_speichern)

        layout.addLayout(btn_layout)

        layout.addStretch()
        return page

    #=====================SEITE 4: LIVE PLOT ========================
    def erstelle_live_plot_seite(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        header_layout = QHBoxLayout()
        self.label_plot_info = QLabel("Live Messung läuft...")
        self.label_plot_info.setAlignment(Qt.AlignCenter)
        self.label_plot_info.setFont(QFont("Arial", 13, QFont.Bold))
        header_layout.addWidget(self.label_plot_info)
        header_layout.addStretch()
        # Ampel-Anzeige (QLabel)
        self.ampel_label = QLabel("● REGELUNG...")
        self.ampel_label.setFont(QFont("Arial", 10, QFont.Bold))
        self.ampel_label.setAlignment(Qt.AlignCenter)
        self.ampel_label.setFixedWidth(160)
        self.ampel_label.setFixedHeight(32)
        self.set_ampel_status(False)  # Standard: Rot / Unstabil
        header_layout.addWidget(self.ampel_label)
        layout.addLayout(header_layout)

        # Plot-Widget von pyqtgraph initialisieren
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('w')  # Weißer Hintergrund
        self.plot_widget.setTitle("Druckverlauf über Zeit", color="k", size="12pt")
        self.plot_widget.setLabel('left', 'Druck', units='mBar', color='k')
        self.plot_widget.setLabel('bottom', 'Zeit', units='s', color='k')
        self.plot_widget.showGrid(x=True, y=True)
        self.plot_widget.enableAutoRange(axis=pg.ViewBox.XAxis, enable=False)
        self.plot_widget.setLogMode(x=False, y=True)
        # Plot-Linie (Blau, 2px dick)
        self.curve = self.plot_widget.plot(pen=pg.mkPen(color='b', width=2))
        layout.addWidget(self.plot_widget)

        #scrollbar
        self.scrollbar = QScrollBar(Qt.Horizontal)
        self.scrollbar.setMinimum(0)
        self.scrollbar.setMaximum(0)
        self.scrollbar.valueChanged.connect(self.on_scroll)
        layout.addWidget(self.scrollbar)

        # Steuerungs-Buttons unter dem Graphen
        btn_layout = QHBoxLayout()        
        btn_stop = QPushButton("Zurück")
        btn_stop.setFont(QFont("Arial", 10))
        btn_stop.clicked.connect(self.stoppe_live_plot)
        btn_layout.addWidget(btn_stop)

        layout.addLayout(btn_layout)
        return page


    # ==================== HILFSFUNKTIONEN & LOGIK ====================
    def zeige_home(self):
        self.stacked_widget.setCurrentIndex(0)
    def zeige_auto_scan_pfad(self):
        self.stacked_widget.setCurrentIndex(1)

    def bestaetige_druckeingabe(self):
        wert = self.line_edit_druck.text().strip()
        try:
            druck_val = float(wert)
            if 1e-3 <= druck_val <= 1000:
                self.solldruck = druck_val
                self.previous_page = 2
                self.starte_live_plot()
            else: 
                QMessageBox.warning(
                                self, "Ungültige Eingabe", "Bitte geben Sie eine gültige Zahl für den Druck ein."
                            )    
        except ValueError:
            QMessageBox.warning(
                self, "Ungültige Eingabe", "Bitte geben Sie eine gültige Zahl für den Druck ein."
            )

    def bestaetige_pfade(self):
        # Auslesen der aktuell eingetragenen Pfade
        self.pfad1 = self.line_edit_pfad1.text().strip()
        self.pfad2 = self.line_edit_pfad2.text().strip()
        self.pfad3 = self.line_edit_pfad3.text().strip()
        self.pfad4 = self.line_edit_pfad4.text().strip()
        # Validierung: Prüfen ob alle Pfade angegeben wurden
        if not self.pfad1 or not self.pfad2 or not self.pfad3 or not self.pfad4:
            QMessageBox.warning(
                self, 
                "Eingabe unvollständig", 
                "Bitte wählen Sie alle drei Pfade aus, bevor Sie fortfahren."
            )
        ungueltige_pfade = []
        if not os.path.isfile(self.pfad1):
            ungueltige_pfade.append("• Pfad 1 (LUT-CSV-Datei existiert nicht)")
        if not os.path.isfile(self.pfad2):
            ungueltige_pfade.append("• Pfad 2 (Solldruck-Datei existiert nicht)")
        if not os.path.isfile(self.pfad3):
            ungueltige_pfade.append("• Pfad 3 (Referenz-Scan-Datei existiert nicht)")
        if not os.path.isdir(self.pfad4):
            ungueltige_pfade.append(
                "• Pfad 4 (Speicherort/Ordner existiert nicht oder ist kein Ordner)"
            )
        if ungueltige_pfade:
            fehler_text = (
                "Folgende Pfade konnten nicht gefunden werden:\n\n"
                + "\n".join(ungueltige_pfade)
            )
            QMessageBox.warning(self, "Pfade ungültig", fehler_text)
        else: 
            self.solldruck = 10.0
            self.previous_page = 1
            self.starte_live_plot()

    def starte_live_plot(self):
        # Daten zurücksetzen
        self.plot_zeit = []
        self.plot_druck = []
        self.zeit_zähler = 0.0
        self.curve.setData([], [])
        self.scrollbar.setMaximum(0)
        self.scrollbar.setValue(0)
        self.plot_widget.setXRange(0, 100, padding=0)
        # Info-Text aktualisieren
        self.label_plot_info.setText(f"Live-Regelung | Solldruck: {self.solldruck} mBar")
        # Wechsel auf Seite 4 (Index 4)
        self.stacked_widget.setCurrentIndex(4)
        # Timer starten (Aktualisierung alle 100 ms = 10 Mal pro Sekunde)
        self.timer.start(100)

    def update_live_plot(self):
        """Wird alle 100 ms vom QTimer aufgerufen"""
        self.zeit_zähler += 0.1
        # HIER SPÄTER DEINEN ECHTEN SENSOR-MESSWERT EINLESEN:
        # z.B.: ist_druck = self.hardware_manager.get_pressure()
        #
        # Simulation: Druck schwankt leicht um den Solldruck herum
        rauschen = random.uniform(-0.02, 0.02) * self.solldruck
        ist_druck = max(1e-6, self.solldruck + rauschen)
        # Werte an Listen anhängen
        self.plot_zeit.append(self.zeit_zähler)
        self.plot_druck.append(ist_druck)
        # Graph zeichnen
        self.curve.setData(self.plot_zeit, self.plot_druck)
        fenster_groesse = 100.0
        toleranz = 0.01

        # Prüfen, ob ALLE Messwerte im Fenster innerhalb der Toleranz liegen
        abweichung = abs(ist_druck - self.solldruck) / self.solldruck
        ist_stabil = abweichung <= toleranz
        self.set_ampel_status(ist_stabil)

        if self.zeit_zähler > fenster_groesse:
            # Maximale Scroll-Position berechnen (in Zehntelsekunden, um flüssig zu bleiben)
            max_scroll = int((self.zeit_zähler - fenster_groesse) * 10)
            # Prüfen, ob der Nutzer gerade ganz rechts steht (Auto-Scroll aktiv)
            war_am_ende = (self.scrollbar.value() >= self.scrollbar.maximum() - 1)
            # Scrollbar-Maximum anpassen
            self.scrollbar.blockSignals(True)  # Verhindert unnötige Signal-Mehrfachaufrufe
            self.scrollbar.setMaximum(max_scroll)      
            if war_am_ende:
                # Scrollbar mit nach rechts schieben & Plot mitführen
                self.scrollbar.setValue(max_scroll)
                self.plot_widget.setXRange(self.zeit_zähler - fenster_groesse, self.zeit_zähler, padding=0)            
            self.scrollbar.blockSignals(False)
        else:
            # Unter 100s bleibt die Ansicht fest von 0 bis 100s
            self.plot_widget.setXRange(0, fenster_groesse, padding=0)

    def on_scroll(self, value):
        """Wird aufgerufen, wenn der Benutzer die Scrollbar bewegt"""
        start_zeit = value / 10.0  # Umrechnung zurück in Sekunden
        end_zeit = start_zeit + 100.0
        self.plot_widget.setXRange(start_zeit, end_zeit, padding=0)

    def stoppe_live_plot(self):
        self.timer.stop()
        self.stacked_widget.setCurrentIndex(self.previous_page)  # Zurück zur Druckeingabe

    def set_ampel_status(self, ist_stabil):
        if ist_stabil:
            self.ampel_label.setText("● DRUCK STABIL")
            self.ampel_label.setStyleSheet("""
                QLabel {
                    background-color: #2ecc71;
                    color: white;
                    border-radius: 6px;
                }
            """)
        else:
            self.ampel_label.setText("● DRUCK INSTABIL")
            self.ampel_label.setStyleSheet("""
                QLabel {
                    background-color: #e74c3c;
                    color: white;
                    border-radius: 6px;
                }
            """)
                    
    def waehle_lut_datei(self):
        # QFileDialog für einzelne Dateien (mit Filter für CSV)
        pfad, _ = QFileDialog.getOpenFileName(
            self, "CSV-Datei auswählen", "", "CSV-Dateien (*.csv);;Alle Dateien (*)"
        )
        if pfad:
            self.line_edit_lut.setText(pfad)
    def waehle_csv_datei(self):
        # QFileDialog für einzelne Dateien (mit Filter für CSV)
        pfad, _ = QFileDialog.getOpenFileName(
            self, "CSV-Datei auswählen", "", "CSV-Dateien (*.csv);;Alle Dateien (*)"
        )
        if pfad:
            self.line_edit_csv.setText(pfad)

    def waehle_datei_2(self):
        # QFileDialog für Excel-Dateien
        pfad, _ = QFileDialog.getOpenFileName(
            self, "Excel-Datei auswählen", "", "CSV-Dateien (*.csv);;Excel-Dateien (*.xlsx *.xls);;Alle Dateien (*)"
        )
        if pfad:
            self.line_edit_pfad2.setText(pfad)

    def waehle_svd_datei(self):
            # QFileDialog für Excel-Dateien
            pfad, _ = QFileDialog.getOpenFileName(
                self, "Excel-Datei auswählen", "", "SVD-Dateien (*.svd);;Alle Dateien (*)"
            )
            if pfad:
                self.line_edit_pfad3.setText(pfad)

    def waehle_ordner_4(self):
        # QFileDialog für reine Ordner-Auswahl
        ordner = QFileDialog.getExistingDirectory(self, "Zielordner auswählen")
        if ordner:
            self.line_edit_pfad4.setText(ordner)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    fenster = HauptFenster()
    fenster.show()
    # sys.exit(app.exec())
    app.exec()

    if fenster.pfad1:
        print("Erfolgreich beendet! Folgende Pfade wurden übernommen:")
        print("Pfad 1:", fenster.pfad1)
        print("Pfad 2:", fenster.pfad2)
        print("Pfad 3:", fenster.pfad3)
        print("Pfad 4:", fenster.pfad4)