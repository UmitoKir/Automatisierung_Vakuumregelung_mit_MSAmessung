import sys
import os
from collections import deque 
import pyqtgraph as pg

# Ändere den Import zu PyQt5:
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget,
                            QLabel, QLineEdit, QPushButton, QFileDialog, QGroupBox, QMessageBox, 
                            QScrollBar, QShortcut)
from PyQt5.QtCore import Qt, QObject, pyqtSignal
from PyQt5.QtGui import QFont, QKeySequence
import pyqtgraph as pg
import HardwareManager

class DataBridge(QObject):
    # Signal überträgt (lokale_zeit, ist_druck)
    neuer_wert_signal = pyqtSignal(float, float, float, bool)

class HauptFenster(QWidget):
    def __init__(self):
        super().__init__()
        self.pfad1 = ""
        self.pfad2 = ""
        self.pfad3 = ""
        self.pfad4 = ""
        self.previous_page = 0
        self.solldruck = 0.0

        self.MAX_POINTS = 36000*3 # = 108000 = 3h; 1h=36000
        self.plot_zeit = deque(maxlen=self.MAX_POINTS)
        self.plot_druck = deque(maxlen=self.MAX_POINTS)
        self.plot_soll = deque(maxlen=self.MAX_POINTS)
        self.stabile_regionen = []
        self.aktuelle_stabile_region = None
        self.ist_stabil = None

        self.autoScan_init_flag = False
        self.onepressure_init_flag = False


        self.bridge = DataBridge()
        self.bridge.neuer_wert_signal.connect(self.on_hardware_data_received)


        self.live_plot_active_flag = False
        self.HM = HardwareManager.HardwareManager(data_callback=self.bridge.neuer_wert_signal.emit)

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
        self.page_shortcuts = self.erstelle_shortcuts_seite()
        
        self.stacked_widget.addWidget(self.page_home)     # Index 0
        self.stacked_widget.addWidget(self.page_scan)    # Index 1
        self.stacked_widget.addWidget(self.page_druckeingabe)  # Index 2
        self.stacked_widget.addWidget(self.page_einstellungen)  # Index 3
        self.stacked_widget.addWidget(self.page_live_plot)     # Index 4
        self.stacked_widget.addWidget(self.page_shortcuts)     # Index 5


        # Starte auf dem Home-Screen
        self.globalShortcuts()
        self.setStyleSheet("""
                QPushButton:focus {
                    border: 2px solid #0078d7;
                    background-color: #e5f1fb;
                }
            """)
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
        btn_scan.clicked.connect(self.home_zu_Pfadauswahl)
        layout.addWidget(btn_scan)

        # Button 2: Beispiel für eine weitere Funktion
        btn_option2 = QPushButton("2. Manuelle Druck eingabe")
        btn_option2.setFont(QFont("Arial", 11))
        btn_option2.setFixedHeight(45)
        btn_option2.clicked.connect(self.home_zu_druckeingabe)
        layout.addWidget(btn_option2)

        # Button 3: Beispiel für eine weitere Funktion
        btn_option3 = QPushButton("3. Einstellungen")
        btn_option3.setFont(QFont("Arial", 11))
        btn_option3.setFixedHeight(45)
        btn_option3.clicked.connect(self.zeige_einstellungen)
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

        btn_back = QPushButton("Zurück")
        #btn_back.setShortcut("Esc")
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
        btn_druck.setShortcut("A")
        btn_druck.clicked.connect(self.bestaetige_druckeingabe)
        layout_druck.addWidget(label_druck)
        layout_druck.addWidget(self.line_edit_druck)
        layout_druck.addWidget(btn_druck)

        layout.addLayout(layout_druck)
        layout.addSpacing(30)

        btn_layout = QHBoxLayout()
        btn_back = QPushButton("Zurück")
        #btn_back.setShortcut("Esc")
        btn_back.clicked.connect(self.zeige_home)
        btn_speichern = QPushButton("zum Live-Plot")
        btn_speichern.clicked.connect(self.zeige_live_plot)
        btn_layout.addWidget(btn_back)
        btn_layout.addWidget(btn_speichern)

        layout.addLayout(btn_layout)

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

        default_lut_pfad = r"C:\Users\messung\PycharmProjects\Automatisierung_Vakuumregelung_mit_MSAmessung\Regulierung_LUT\messung_ventil_mehr_stützpunkte_gut.csv"
        layout_lut = QHBoxLayout()
        label1 = QLabel("LUT-Datei für die Regelung:")
        label1.setFixedWidth(180)
        self.line_edit_lut = QLineEdit()
        self.line_edit_lut.setText(default_lut_pfad)
        btn_lut = QPushButton("Ändern")
        btn_lut.clicked.connect(self.waehle_lut_datei)
        layout_lut.addWidget(label1)
        layout_lut.addWidget(self.line_edit_lut)
        layout_lut.addWidget(btn_lut)
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

        
        group_box.setLayout(group_layout)
        layout.addWidget(group_box)

        btn_shortcuts = QPushButton("Shortcut-Verzeichnis")
        btn_shortcuts.setFont(QFont("Arial", 10))
        btn_shortcuts.clicked.connect(self.zeige_shortcuts)
        layout.addWidget(btn_shortcuts)


        btn_layout = QHBoxLayout()
        btn_back = QPushButton("Zurück")
        #btn_back.setShortcut("Esc")
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
        header_layout.addWidget(self.ampel_label)
        layout.addLayout(header_layout)

        # Plot-Widget von pyqtgraph initialisieren
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('w')  # Weißer Hintergrund
        self.plot_widget.setTitle("Druckverlauf über Zeit", color="k", size="12pt")
        self.plot_widget.setLabel('left', 'Druck', units='mBar', color='k')
        self.plot_widget.setLabel('bottom', 'Zeit', units='s', color='k')

        

        self.plot_widget.setLogMode(x=False, y=False)
        self.plot_widget.showGrid(x=True, y=True)
        self.plot_widget.enableAutoRange(axis=pg.ViewBox.XAxis, enable=False)
        self.plot_widget.enableAutoRange(axis=pg.ViewBox.YAxis, enable=False)
        # Plot-Linie (Blau, 2px dick)
        self.curve = self.plot_widget.plot(pen=pg.mkPen(color='b', width=2))
        #gestrichelte rote Linie bei Solldruck
        self.soll_curve = self.plot_widget.plot(pen=pg.mkPen(color='r', width=2, style=Qt.DashLine))

        # LEGENDE
        # === LEGENDE OBERHALB DES PLOTS ===
        legend_layout = QHBoxLayout()
        legend_layout.setContentsMargins(0, 2, 0, 8)
        legend_layout.setAlignment(Qt.AlignCenter)

        def create_legend_entry(color_style, text):
            container = QHBoxLayout()
            container.setSpacing(6)
            
            # Farbfeld / Indikator
            icon = QLabel()
            icon.setFixedSize(18, 12)
            icon.setStyleSheet(color_style)
            
            # Textbeschreibung
            lbl = QLabel(text)
            lbl.setFont(QFont("Arial", 9, QFont.Bold))
            lbl.setStyleSheet("color: #333;")
            
            container.addWidget(icon)
            container.addWidget(lbl)
            return container
        legend_layout.addLayout(create_legend_entry("border-top: 2px solid #0000FF;background: transparent; margin-top: 5px;", "Ist-Druck"))
        legend_layout.addSpacing(20)
        legend_layout.addLayout(create_legend_entry("border-top: 2px dashed #FF0000; background: transparent; margin-top: 5px;", "Solldruck"))
        legend_layout.addSpacing(20)
        legend_layout.addLayout(create_legend_entry("background-color: rgba(0, 255, 0, 0.4); border: 1px solid green; border-radius: 2px;", "Druck stabil"))
        legend_layout.addSpacing(20)
        legend_layout.addLayout(create_legend_entry("background-color: rgba(255, 255, 0, 0.5); border: 1px solid #d4ac0d; border-radius: 2px;", "Scan aktiv"))

        # Legende VOR dem Plot-Widget zum Layout hinzufügen
        layout.addLayout(legend_layout)
        layout.addWidget(self.plot_widget)

        self.plot_widget.setDownsampling(auto=True, mode='peak')
        self.plot_widget.setClipToView(True)
        layout.addWidget(self.plot_widget)

        self.set_ampel_status()

        #scrollbar
        self.scrollbar = QScrollBar(Qt.Horizontal)
        self.scrollbar.setMinimum(0)
        self.scrollbar.setMaximum(0)
        self.scrollbar.valueChanged.connect(self.on_scroll)
        layout.addWidget(self.scrollbar)

        # Steuerungs-Buttons unter dem Graphen
        btn_layout = QHBoxLayout()        
        btn_back = QPushButton("Zurück")
        #btn_back.setShortcut("Esc")
        btn_back.setFont(QFont("Arial", 10))
        btn_back.clicked.connect(self.zeige_vorherige_seite)
        self.btn_speichern = QPushButton()
        self.update_control_button()
        self.btn_speichern.clicked.connect(self.stop_or_restart_live_plot)
        btn_layout.addWidget(btn_back)
        btn_layout.addWidget(self.btn_speichern)

        layout.addLayout(btn_layout)
        return page

    #======================SEITE 5: SHORTCUT VERZEICHNIS=====================================
    def erstelle_shortcuts_seite(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        titel = QLabel("Shortcut-Verzeichnis")
        titel.setAlignment(Qt.AlignCenter)
        titel.setFont(QFont("Arial", 14, QFont.Bold))
        layout.addWidget(titel)

        group_box = QGroupBox("Tastaturkürzel Übersicht")
        group_layout = QVBoxLayout()

        shortcut_liste = (
            "<b>Ctrl + 1:</b> Automatisierter Scan (Pfadauswahl)<br>"
            "<b>Ctrl + 2:</b> Manuelle Druckeingabe<br>"
            "<b>Ctrl + 3:</b> Einstellungen<br>"
            "<b>Ctrl + L:</b> Live-Plot anzeigen<br>"
            "<b>Ctrl + H:</b> Hauptmenü aufrufen<br>"
            "<b>Ctrl + K:</b> Shortcut Verzeichnis aufrufen<br>"
            "<b>Ctrl + 0:</b> Anwendung beenden<br><br>"
            "<b>Esc:</b> Zurück zur vorherigen Seite<br>"
            "<b>A:</b> Druck ansteuern (in Druckeingabe)<br>"
            "<b>Pfeil Oben / Unten:</b> Navigation zwischen Elementen<br>"
            "<b>Enter:</b> Auswählen / Button aktivieren"
        )

        lbl_shortcuts = QLabel(shortcut_liste)
        lbl_shortcuts.setFont(QFont("Arial", 10))
        group_layout.addWidget(lbl_shortcuts)
        group_box.setLayout(group_layout)
        layout.addWidget(group_box)

        btn_back = QPushButton("Zurück")
        btn_back.setFont(QFont("Arial", 10))
        btn_back.clicked.connect(self.zeige_vorherige_seite)
        layout.addWidget(btn_back)

        layout.addStretch()
        return page

    # ==================== HILFSFUNKTIONEN & LOGIK ===================================
    # ================================================================================
    def zeige_home(self):
        self.stacked_widget.setCurrentIndex(0)
        self.page_home.findChild(QPushButton).setFocus()

    def zeige_pfadauswahl(self):
        self.previous_page = 0
        self.stacked_widget.setCurrentIndex(1)

    def zeige_druckeingabe(self):
        self.previous_page = 0
        self.stacked_widget.setCurrentIndex(2)

    def zeige_einstellungen(self):
        self.previous_page = 0
        self.stacked_widget.setCurrentIndex(3)
        

    def zeige_live_plot(self):
        self.stacked_widget.setCurrentIndex(4)
        self.btn_speichern.setFocus()

    def zeige_shortcuts(self):
        self.previous_page = 3
        self.stacked_widget.setCurrentIndex(5)

    def zeige_vorherige_seite(self):
        if self.previous_page == self.stacked_widget.currentIndex():
            self.stacked_widget.setCurrentIndex(0)
        else:
            self.stacked_widget.setCurrentIndex(self.previous_page)

    def home_zu_Pfadauswahl(self):
        if not self.HM.hm_connection_alive_flag:
            try: 
                self.HM.csv_path = self.line_edit_csv.text().strip()
                self.HM.connectAllForGUI()
                self.HM.initialize_regler()
            except Exception as e:
                QMessageBox.critical(self, "Hardware-Fehler", f"Verbindung/Start fehlgeschlagen:\n{e}")
                return
        self.stacked_widget.setCurrentIndex(1)
        self.previous_page = 0
        self.line_edit_pfad2.setFocus()

    def home_zu_druckeingabe(self):
        if not self.HM.hm_connection_alive_flag:
            try: 
                self.HM.csv_path = self.line_edit_csv.text().strip()
                self.HM.connectForPressureControlGUI()
                self.HM.initialize_regler()
            except Exception as e:
                self.onepressure_init_flag = True
                QMessageBox.critical(self, "Hardware-Fehler", f"Verbindung/Start fehlgeschlagen:\n{e}")
                return
        self.stacked_widget.setCurrentIndex(2)
        self.previous_page = 0

    def bestaetige_druckeingabe(self):
        wert = self.line_edit_druck.text().strip()  
        try:
            druck_val = float(wert)
            if 1e-3 <= druck_val <= 1000:
                self.solldruck = druck_val
                self.previous_page = 2
                self.HM.starte_einzel_regelung(self.solldruck)
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
        self.pfad2 = self.line_edit_pfad2.text().strip() #pressurevalues_excelfile_path
        self.pfad3 = self.line_edit_pfad3.text().strip() #ref_scan_path
        self.pfad4 = self.line_edit_pfad4.text().strip() #Speicherort
        # Validierung: Prüfen ob alle Pfade angegeben wurden
        if not self.pfad2 or not self.pfad3 or not self.pfad4:
            QMessageBox.warning(
                self, 
                "Eingabe unvollständig", 
                "Bitte wählen Sie alle drei Pfade aus, bevor Sie fortfahren."
            )
        ungueltige_pfade = []
        if not os.path.isfile(self.pfad2):
            ungueltige_pfade.append("• Pfad 2 (Solldruck-Datei existiert nicht)")
        if not os.path.isfile(self.pfad3):
            ungueltige_pfade.append("• Pfad 3 (Referenz-Scan-Datei existiert nicht)")
        if not os.path.isdir(self.pfad4):
            ungueltige_pfade.append("• Pfad 4 (Speicherort/Ordner existiert nicht oder ist kein Ordner)")
        if ungueltige_pfade:
            fehler_text = (
                "Folgende Pfade konnten nicht gefunden werden:\n\n"
                + "\n".join(ungueltige_pfade)
            )
            QMessageBox.warning(self, "Pfade ungültig", fehler_text)
        else: 
            self.previous_page = 1
            self.HM.excel_path = self.pfad2
            self.HM.ref_scan_path =self.pfad3
            self.HM.msa.general_folder_path = self.pfad4
            self.HM.starteAutomatedScanGUI()
            self.starte_live_plot()

    def starte_live_plot(self):
        #alte grünmarkierte regionen löschen falls vorhanden    
        if hasattr(self, 'stabile_regionen'):
            for region in self.stabile_regionen:
                self.plot_widget.removeItem(region)
        self.stabile_regionen = []
        self.aktuelle_stabile_region = None

        if hasattr(self, 'scan_regionen'):
            for region in self.scan_regionen:
                self.plot_widget.removeItem(region)
        self.scan_regionen = []
        self.aktuelle_scan_region = None

        self.ist_stabil = False

        # Daten zurücksetzen
        self.plot_zeit = deque(maxlen=self.MAX_POINTS)
        self.plot_druck = deque(maxlen=self.MAX_POINTS)
        self.plot_soll = deque(maxlen=self.MAX_POINTS)
        self.curve.setData([], [])
        self.scrollbar.setMaximum(0)
        self.scrollbar.setValue(0)
        #plot limits
        self.plot_widget.setXRange(0, 100, padding=0)
        self.plot_widget.setYRange(0, 1000, padding=0.02)

        # Info-Text aktualisieren
        self.label_plot_info.setText(f"Live-Regelung | Solldruck: {self.solldruck} mBar")
        self.live_plot_active_flag = True
        self.update_control_button()
        self.stacked_widget.setCurrentIndex(4)

    def on_scroll(self, value):
        """Wird aufgerufen, wenn der Benutzer die Scrollbar bewegt"""
        start_zeit = value / 10.0  # Umrechnung zurück in Sekunden
        end_zeit = start_zeit + 100.0
        self.plot_widget.setXRange(start_zeit, end_zeit, padding=0)

    def stop_or_restart_live_plot(self):
        if self.live_plot_active_flag:
            if hasattr(self.HM, 'regler') and self.HM.regler:
                self.HM.regler.single_pressurevalue_control_stop_btn_flag = True
                self.HM.regler.is_running = False
            self.live_plot_active_flag = False
            self.label_plot_info.setText("Messung gestoppt")
        else: 
            self.bestaetige_druckeingabe()
        self.update_control_button()

    def update_control_button(self):
        if self.live_plot_active_flag:
            self.btn_speichern.setText("Stop (Ventil öffnen)")
        else:
            self.btn_speichern.setText("Restart")

    def set_ampel_status(self):
        if hasattr(self.HM, 'regler') and self.HM.regler is not None:
            self.ist_stabil = getattr(self.HM.regler, 'druck_status', False)
        elif hasattr(self.HM, 'regler_thread') and self.HM.regler_thread is not None:
            self.ist_stabil = getattr(self.HM.regler_thread, 'druck_status', False)
        else:
            self.ist_stabil = False

        if self.ist_stabil:
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

    def bereinige_alte_regionen(self):
        """Löscht oder verkürzt Farbblöcke, deren Zeitstempel aus dem Deque-Speicher gelöscht wurden."""
        if not self.plot_zeit:
            return
        
        min_zeit = self.plot_zeit[0]  # Ältester Zeitstempel im Speicher

        for regionen_liste in [self.stabile_regionen, self.scan_regionen]:
            for region in list(regionen_liste):
                start, end = region.getRegion()
                
                # Fall 1: Region liegt komplett vor der ältesten gespeicherten Zeit -> Löschen
                if end < min_zeit:
                    self.plot_widget.removeItem(region)
                    regionen_liste.remove(region)
                    if region == self.aktuelle_stabile_region:
                        self.aktuelle_stabile_region = None
                    if region == self.aktuelle_scan_region:
                        self.aktuelle_scan_region = None

                # Fall 2: Region schneidet die Grenze -> Startzeit an die Grenze anpassen
                elif start < min_zeit:
                    region.setRegion([min_zeit, end])


#_______________________________Daten Annahme Funktion__________________________________________
#_______________________________________________________________________________________________
    def on_hardware_data_received(self, zeit, istwert, solldruck, scan_aktiv):
        """Wird durch das pyqtSignal aufgerufen, sobald wait_for_next_value() im Regler auslöst."""
        if not self.live_plot_active_flag:
            return
        #Solldruck aktualisieren, wenn er sich ändert
        if self.solldruck != solldruck:
            self.solldruck = solldruck
            self.aktuelle_stabile_region = None 
            self.aktuelle_scan_region = None
            self.label_plot_info.setText(f"Live-Regelung | Solldruck: {self.solldruck} mBar")
        
        # Daten zur Deque hinzufügen
        self.plot_zeit.append(zeit)
        self.plot_druck.append(istwert)
        self.plot_soll.append(self.solldruck)
        self.bereinige_alte_regionen()
        # Plot aktualisieren (im exakten Sensor-Takt)
        self.curve.setData(list(self.plot_zeit), list(self.plot_druck))
        self.soll_curve.setData(list(self.plot_zeit), list(self.plot_soll))

        # Ampel-Status prüfen
        self.set_ampel_status()

        # GRÜNE ZEITMARKIERUNG(Druck stabil):
        if self.ist_stabil:
            if self.aktuelle_stabile_region is None:
                # Neuer stabiler Abschnitt beginnt -> Neues grünes Band erzeugen
                region = pg.LinearRegionItem(
                    values=[zeit, zeit],
                    orientation=pg.LinearRegionItem.Vertical,
                    movable=False,
                    brush=pg.mkBrush(0, 255, 0, 40)  # Transparente grüne Füllung
                )
                for line in region.lines:
                    line.setPen(pg.mkPen(None))  # Begrenzungslinien ausblenden
                
                self.plot_widget.addItem(region)
                self.aktuelle_stabile_region = region
                self.stabile_regionen.append(region)
            else:
                # Druck bleibt weiterhin stabil -> Band nach rechts mitziehen
                start_zeit = self.aktuelle_stabile_region.getRegion()[0]
                self.aktuelle_stabile_region.setRegion([start_zeit, zeit])
        else:
            # Druck instabil -> Aktuellen grünen Block abschließen
            self.aktuelle_stabile_region = None

        # GELBE ZEITMARKIERUNG (SCAN LÄUFT):
        if scan_aktiv:
            if self.aktuelle_scan_region is None:
                region = pg.LinearRegionItem(
                    values=[zeit, zeit],
                    orientation=pg.LinearRegionItem.Vertical,
                    movable=False,
                    brush=pg.mkBrush(255, 255, 0, 50)  # Halbtransparentes Gelb
                )
                for line in region.lines:
                    line.setPen(pg.mkPen(None))
                self.plot_widget.addItem(region)
                self.aktuelle_scan_region = region
                self.scan_regionen.append(region)
            else:
                start_zeit = self.aktuelle_scan_region.getRegion()[0]
                self.aktuelle_scan_region.setRegion([start_zeit, zeit])
        else:
            self.aktuelle_scan_region = None

        # Auto-Scroll-Logik anwenden
        fenster_groesse = 100.0
        if zeit > fenster_groesse:
            max_scroll = int((zeit - fenster_groesse) * 10)
            war_am_ende = (self.scrollbar.value() >= self.scrollbar.maximum() - 1)
            
            self.scrollbar.blockSignals(True)
            self.scrollbar.setMaximum(max_scroll)      
            if war_am_ende:
                self.scrollbar.setValue(max_scroll)
                self.plot_widget.setXRange(zeit - fenster_groesse, zeit, padding=0)            
            self.scrollbar.blockSignals(False)
        else:
            self.plot_widget.setXRange(0, fenster_groesse, padding=0)

    def startAutomatedScan(self):
        ...

    #_____________________Keyboard interactions__________________________________

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Down:
            self.focusNextChild()
            event.accept()
        elif event.key() == Qt.Key_Up:
            self.focusPreviousChild()
            event.accept()
        elif event.key() in (Qt.Key_Return, Qt.Key_Enter):
            focused_widget = QApplication.focusWidget()
            if isinstance(focused_widget, QPushButton):
                focused_widget.animateClick()  # Animates visual press and triggers clicked
                event.accept()
            else:
                super().keyPressEvent(event)

        # Retain Escape shortcut functionality
        elif event.key() == Qt.Key_Escape:
            event.accept()
            self.zeige_vorherige_seite()
        else:
            super().keyPressEvent(event)

    def globalShortcuts(self):
        # Ctrl+1 -> Seite 1 (Pfadauswahl / Auto-Scan)
        self.sc_page1 = QShortcut(QKeySequence("Ctrl+1"), self)
        self.sc_page1.setContext(Qt.WindowShortcut)
        # if self.autoScan_init_flag and not self.onepressure_init_flag:
        #     self.sc_page1.activated.connect(self.zeige_pfadauswahl)
        # elif not self.autoScan_init_flag and not self.onepressure_init_flag:
        #     self.sc_page1.activated.connect(self.home_zu_Pfadauswahl)
        # elif self.onepressure_init_flag:

        self.sc_page1.activated.connect(self.home_zu_Pfadauswahl)

        # Ctrl+2 -> Seite 2 (Manuelle Druckeingabe)
        self.sc_page2 = QShortcut(QKeySequence("Ctrl+2"), self)
        self.sc_page2.setContext(Qt.WindowShortcut)
        # if not self.autoScan_init_flag and self.onepressure_init_flag:
        #     self.sc_page2.activated.connect(self.zeige_druckeingabe)
        # elif not self.autoScan_init_flag and not self.onepressure_init_flag:
        #     self.sc_page2.activated.connect(self.home_zu_druckeingabe)
        # elif self.autoScan_init_flag:
        self.sc_page2.activated.connect(self.home_zu_druckeingabe)
        

        # Ctrl+3 -> Seite 3 (Einstellungen)
        self.sc_page3 = QShortcut(QKeySequence("Ctrl+3"), self)
        self.sc_page3.setContext(Qt.WindowShortcut)
        self.sc_page3.activated.connect(self.zeige_einstellungen)

        # Ctrl+L -> Seite 4 (Live-Plot direkt aufrufen)
        self.sc_page4 = QShortcut(QKeySequence("Ctrl+L"), self)
        self.sc_page4.setContext(Qt.WindowShortcut)
        self.sc_page4.activated.connect(self.zeige_live_plot)

        # ctrl+H -> IMMER zurück zum Hauptmenü (egal wo man ist)
        self.sc_home = QShortcut(QKeySequence("Ctrl+H"), self)
        self.sc_home.setContext(Qt.WindowShortcut)
        self.sc_home.activated.connect(self.zeige_home)

        #Ctrl+K -> Seite 5: Shortcut Verzeichnis 
        self.sc_verzeichnis = QShortcut(QKeySequence("Ctrl+K"), self)
        self.sc_verzeichnis.setContext(Qt.WindowShortcut)
        self.sc_verzeichnis.activated.connect(self.zeige_shortcuts)

        # ctrl+0 -> Programm Beenden
        self.sc_close = QShortcut(QKeySequence("Ctrl+0"), self)
        self.sc_close.setContext(Qt.WindowShortcut)
        self.sc_close.activated.connect(self.close)



if __name__ == "__main__":
    app = QApplication(sys.argv)
    fenster = HauptFenster()
    fenster.show()
    # sys.exit(app.exec())
    app.exec()
