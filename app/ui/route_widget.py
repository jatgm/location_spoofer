"""
Route Simulation Widget for configuring travel speeds, selecting destinations,
importing GPX files, and controlling continuous route playback.
"""

from typing import Optional
from PyQt6.QtCore import pyqtSignal, Qt, QTimer, QThread
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QDoubleSpinBox, QPushButton, QSlider, QProgressBar,
    QFileDialog, QFrame, QGridLayout, QLineEdit,
    QListWidget, QListWidgetItem, QAbstractSpinBox,
    QCheckBox
)
from app.core.geolocation import search_addresses
from app.core.route_simulator import export_gpx, fetch_osrm_route
from app.core.notifications import play_system_sound


class GeocodeSearchThread(QThread):
    sig_results = pyqtSignal(list)

    def __init__(self, query: str, parent=None):
        super().__init__(parent)
        self.query = query

    def run(self):
        results = search_addresses(self.query, limit=5)
        self.sig_results.emit(results)


class RouteWidget(QWidget):
    """Control panel for turn-by-turn road and GPX route simulation."""

    sig_start_route = pyqtSignal(float, float, float, float, float, bool, bool)  # s_lat, s_lon, d_lat, d_lon, speed, traffic, loop
    sig_start_gpx = pyqtSignal(str, float)                          # filepath, speed
    sig_pause_route = pyqtSignal()
    sig_resume_route = pyqtSignal()
    sig_stop_route = pyqtSignal()
    sig_destination_changed = pyqtSignal(float, float)              # dest_lat, dest_lon

    SPEED_PROFILES = [
        ("Walk (5 km/h)", 5.0),
        ("Bike (20 km/h)", 20.0),
        ("Drive (50 km/h)", 50.0),
        ("Express (80 km/h)", 80.0),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_running: bool = False
        self.is_paused: bool = False
        self.gpx_filepath: Optional[str] = None
        self._search_thread: Optional[GeocodeSearchThread] = None

        # Debounce timer for destination address search
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(350)
        self._search_timer.timeout.connect(self._do_dest_search)

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        # 1. Travel Speed Profile Card
        speed_card = QFrame(self)
        speed_card.setProperty("class", "CardPanel")
        sc_layout = QVBoxLayout(speed_card)
        sc_layout.setContentsMargins(14, 14, 14, 14)
        sc_layout.setSpacing(10)

        speed_title = QLabel("Travel Mode & Speed", self)
        speed_title.setProperty("class", "SectionTitle")
        sc_layout.addWidget(speed_title)

        # Speed presets row
        preset_row = QHBoxLayout()
        preset_row.setSpacing(8)
        self.preset_btns = []
        for name, spd in self.SPEED_PROFILES:
            btn = QPushButton(name, self)
            btn.setProperty("class", "PresetBtn")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, s=spd: self._set_speed(s))
            preset_row.addWidget(btn)
            self.preset_btns.append(btn)
        sc_layout.addLayout(preset_row)

        # Speed Slider & Numeric Spinbox
        slider_row = QHBoxLayout()
        slider_row.setSpacing(12)

        self.speed_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.speed_slider.setRange(1, 130)
        self.speed_slider.setValue(50)
        self.speed_slider.valueChanged.connect(self._on_slider_changed)
        slider_row.addWidget(self.speed_slider, 1)

        self.speed_spin = QDoubleSpinBox(self)
        self.speed_spin.setRange(1.0, 150.0)
        self.speed_spin.setValue(50.0)
        self.speed_spin.setSuffix(" km/h")
        self.speed_spin.setDecimals(1)
        self.speed_spin.setFixedHeight(34)
        self.speed_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.speed_spin.valueChanged.connect(self._on_spin_changed)
        slider_row.addWidget(self.speed_spin)

        sc_layout.addLayout(slider_row)
        layout.addWidget(speed_card)

        # 2. Google Maps Directions Card
        dest_card = QFrame(self)
        dest_card.setProperty("class", "CardPanel")
        dc_layout = QVBoxLayout(dest_card)
        dc_layout.setContentsMargins(14, 14, 14, 14)
        dc_layout.setSpacing(10)

        # Top Modes Row ("Best", "Drive", "Bike", "Walk", "Express")
        mode_row = QHBoxLayout()
        mode_row.setSpacing(8)

        lbl_best = QLabel("Best", self)
        lbl_best.setStyleSheet("color: #38bdf8; font-weight: 700; font-size: 13px; margin-right: 4px;")
        mode_row.addWidget(lbl_best)

        for mode_title, spd in [("Drive", 50.0), ("Bike", 20.0), ("Walk", 5.0), ("Express", 80.0)]:
            btn_m = QPushButton(mode_title, self)
            btn_m.setProperty("class", "PresetBtn")
            btn_m.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_m.clicked.connect(lambda checked, s=spd: self._set_speed(s))
            mode_row.addWidget(btn_m)
        mode_row.addStretch()
        dc_layout.addLayout(mode_row)

        # Google Maps Directions Box: Left icons, Middle inputs, Right reverse button
        dir_frame = QFrame(self)
        dir_frame.setStyleSheet("""
            QFrame {
                background: #141721;
                border: 1px solid #282f42;
                border-radius: 12px;
            }
        """)
        dir_layout = QHBoxLayout(dir_frame)
        dir_layout.setContentsMargins(12, 12, 12, 12)
        dir_layout.setSpacing(10)

        # Left Icon Column: ○  ⋮  📍
        icon_col = QVBoxLayout()
        icon_col.setContentsMargins(0, 0, 0, 0)
        icon_col.setSpacing(2)
        icon_col.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl_origin_dot = QLabel("○", self)
        lbl_origin_dot.setStyleSheet("color: #94a3b8; font-size: 16px; font-weight: bold; background: transparent; border: none;")
        icon_col.addWidget(lbl_origin_dot, 0, Qt.AlignmentFlag.AlignCenter)

        lbl_dots = QLabel("⋮", self)
        lbl_dots.setStyleSheet("color: #64748b; font-size: 14px; font-weight: bold; background: transparent; border: none;")
        icon_col.addWidget(lbl_dots, 0, Qt.AlignmentFlag.AlignCenter)

        lbl_dest_pin = QLabel("📍", self)
        lbl_dest_pin.setStyleSheet("color: #ef4444; font-size: 15px; background: transparent; border: none;")
        icon_col.addWidget(lbl_dest_pin, 0, Qt.AlignmentFlag.AlignCenter)

        dir_layout.addLayout(icon_col)

        # Middle Inputs Column: Start (Your location) & Destination
        inputs_col = QVBoxLayout()
        inputs_col.setContentsMargins(0, 0, 0, 0)
        inputs_col.setSpacing(8)

        self.start_search_input = QLineEdit("Your location", self)
        self.start_search_input.setStyleSheet("""
            QLineEdit {
                background: #1b202c;
                border: 1px solid #333d52;
                border-radius: 8px;
                padding: 6px 12px;
                color: #f1f5f9;
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: #38bdf8;
            }
        """)
        inputs_col.addWidget(self.start_search_input)

        self.dest_search_input = QLineEdit(self)
        self.dest_search_input.setPlaceholderText("Search destination address or place (e.g. Starbucks)...")
        self.dest_search_input.setStyleSheet("""
            QLineEdit {
                background: #1b202c;
                border: 1px solid #333d52;
                border-radius: 8px;
                padding: 6px 12px;
                color: #f1f5f9;
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: #38bdf8;
            }
        """)
        self.dest_search_input.textChanged.connect(self._on_dest_search_changed)
        self.dest_search_input.returnPressed.connect(self._do_dest_search)
        inputs_col.addWidget(self.dest_search_input)

        dir_layout.addLayout(inputs_col, 1)

        # Right Swap Column: Centered Reverse Button ⇅
        swap_col = QVBoxLayout()
        swap_col.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.btn_reverse_route = QPushButton("⇅", self)
        self.btn_reverse_route.setFixedSize(34, 34)
        self.btn_reverse_route.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_reverse_route.setToolTip("Reverse direction (swap start & destination)")
        self.btn_reverse_route.setStyleSheet("""
            QPushButton {
                background: #1e2432;
                border: 1px solid #323d53;
                border-radius: 17px;
                color: #cbd5e1;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #283246;
                color: #38bdf8;
                border-color: #38bdf8;
            }
        """)
        self.btn_reverse_route.clicked.connect(self._on_reverse_route_clicked)
        swap_col.addWidget(self.btn_reverse_route)

        dir_layout.addLayout(swap_col)
        dc_layout.addWidget(dir_frame)

        # Add destination clickable button row (+ Add destination)
        self.btn_add_dest = QPushButton("⊕  Add destination", self)
        self.btn_add_dest.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add_dest.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #94a3b8;
                font-size: 12px;
                font-weight: 500;
                text-align: left;
                padding: 4px 0px;
            }
            QPushButton:hover {
                color: #38bdf8;
            }
        """)
        self.btn_add_dest.clicked.connect(lambda: self.dest_search_input.setFocus())
        dc_layout.addWidget(self.btn_add_dest)

        # Destination suggestions dropdown
        self.dest_suggestions_list = QListWidget(self)
        self.dest_suggestions_list.setObjectName("AddressSuggestionsList")
        self.dest_suggestions_list.setMaximumHeight(130)
        self.dest_suggestions_list.setVisible(False)
        self.dest_suggestions_list.itemClicked.connect(self._on_dest_suggestion_clicked)
        dc_layout.addWidget(self.dest_suggestions_list)

        # Confirmed destination feedback
        self.lbl_dest_confirmed = QLabel("", self)
        self.lbl_dest_confirmed.setStyleSheet("color: #38bdf8; font-size: 11px; font-weight: 500;")
        self.lbl_dest_confirmed.setVisible(False)
        dc_layout.addWidget(self.lbl_dest_confirmed)

        # Hidden Spinboxes (preserves full simulator API compatibility)
        self.coord_container = QWidget(self)
        self.coord_container.setVisible(False)
        cc_box = QHBoxLayout(self.coord_container)
        self.start_lat = QDoubleSpinBox(self)
        self.start_lat.setRange(-90.0, 90.0)
        self.start_lat.setValue(37.334900)
        self.start_lon = QDoubleSpinBox(self)
        self.start_lon.setRange(-180.0, 180.0)
        self.start_lon.setValue(-122.009020)
        self.dest_lat = QDoubleSpinBox(self)
        self.dest_lat.setRange(-90.0, 90.0)
        self.dest_lat.setValue(37.352000)
        self.dest_lon = QDoubleSpinBox(self)
        self.dest_lon.setRange(-180.0, 180.0)
        self.dest_lon.setValue(-122.015000)
        cc_box.addWidget(self.start_lat)
        cc_box.addWidget(self.start_lon)
        cc_box.addWidget(self.dest_lat)
        cc_box.addWidget(self.dest_lon)
        dc_layout.addWidget(self.coord_container)

        # Quick Actions: Use Map Pin, Load GPX, Export GPX
        dest_action_row = QHBoxLayout()
        dest_action_row.setSpacing(8)

        self.btn_set_dest_from_map = QPushButton("Use Map Pin", self)
        self.btn_set_dest_from_map.setProperty("class", "SecondaryBtn")
        self.btn_set_dest_from_map.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_set_dest_from_map.setFixedHeight(30)
        dest_action_row.addWidget(self.btn_set_dest_from_map)

        self.btn_load_gpx = QPushButton("Load GPX...", self)
        self.btn_load_gpx.setProperty("class", "SecondaryBtn")
        self.btn_load_gpx.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_load_gpx.setFixedHeight(30)
        self.btn_load_gpx.clicked.connect(self._on_load_gpx_clicked)
        dest_action_row.addWidget(self.btn_load_gpx)

        self.btn_export_gpx = QPushButton("Export GPX...", self)
        self.btn_export_gpx.setProperty("class", "SecondaryBtn")
        self.btn_export_gpx.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_export_gpx.setFixedHeight(30)
        self.btn_export_gpx.setToolTip("Export current route as GPX file")
        self.btn_export_gpx.clicked.connect(self._on_export_gpx_clicked)
        dest_action_row.addWidget(self.btn_export_gpx)

        dc_layout.addLayout(dest_action_row)

        self.lbl_gpx_name = QLabel("", self)
        self.lbl_gpx_name.setStyleSheet("color: #38bdf8; font-size: 11px;")
        self.lbl_gpx_name.setVisible(False)
        dc_layout.addWidget(self.lbl_gpx_name)

        # Realistic Movement Checkboxes
        self.chk_realistic_traffic = QCheckBox("Realistic Traffic & Corner Deceleration", self)
        self.chk_realistic_traffic.setStyleSheet("color: #cbd5e1; font-size: 12px; font-weight: 500;")
        self.chk_realistic_traffic.setToolTip("Applies natural speed fluctuations (±5%) and slows down along sharp turns")
        dc_layout.addWidget(self.chk_realistic_traffic)

        self.chk_loop_route = QCheckBox("Loop Route Continually", self)
        self.chk_loop_route.setStyleSheet("color: #cbd5e1; font-size: 12px; font-weight: 500;")
        self.chk_loop_route.setToolTip("Repeats the route automatically upon arriving at the destination")
        dc_layout.addWidget(self.chk_loop_route)

        layout.addWidget(dest_card)

        # 3. Route Playback & Progress Card
        ctrl_card = QFrame(self)
        ctrl_card.setProperty("class", "CardPanel")
        cc_layout = QVBoxLayout(ctrl_card)
        cc_layout.setContentsMargins(14, 14, 14, 14)
        cc_layout.setSpacing(10)

        ctrl_title = QLabel("Simulation Playback", self)
        ctrl_title.setProperty("class", "SectionTitle")
        cc_layout.addWidget(ctrl_title)

        # Buttons row: Start / Pause / Stop
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.btn_play = QPushButton("Start Route", self)
        self.btn_play.setObjectName("SpoofButton")
        self.btn_play.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_play.clicked.connect(self._on_play_clicked)
        btn_row.addWidget(self.btn_play, 2)

        self.btn_pause = QPushButton("Pause", self)
        self.btn_pause.setProperty("class", "SecondaryBtn")
        self.btn_pause.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_pause.setEnabled(False)
        self.btn_pause.clicked.connect(self._on_pause_clicked)
        btn_row.addWidget(self.btn_pause, 1)

        self.btn_stop = QPushButton("Stop Route", self)
        self.btn_stop.setObjectName("ResetButton")
        self.btn_stop.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self._on_stop_clicked)
        btn_row.addWidget(self.btn_stop, 1)

        cc_layout.addLayout(btn_row)

        # Progress Bar & ETA
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #12141c;
                border: 1px solid #262b3a;
                border-radius: 6px;
                height: 16px;
                text-align: center;
                color: #ffffff;
                font-size: 11px;
                font-weight: 600;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0a84ff, stop:1 #38bdf8);
                border-radius: 5px;
            }
        """)
        cc_layout.addWidget(self.progress_bar)

        self.lbl_eta = QLabel("Route Inactive", self)
        self.lbl_eta.setStyleSheet("color: #8e95a5; font-size: 12px; font-weight: 500;")
        cc_layout.addWidget(self.lbl_eta)

        layout.addWidget(ctrl_card)
        layout.addStretch()

    def _on_dest_search_changed(self, text: str):
        cleaned = text.strip()
        if len(cleaned) < 2:
            self.dest_suggestions_list.clear()
            self.dest_suggestions_list.setVisible(False)
            return
        self._search_timer.start()

    def _do_dest_search(self):
        query = self.dest_search_input.text().strip()
        if len(query) < 2:
            return

        if self._search_thread and self._search_thread.isRunning():
            self._search_thread.quit()
            self._search_thread.wait()

        self._search_thread = GeocodeSearchThread(query, self)
        self._search_thread.sig_results.connect(self._on_dest_search_results)
        self._search_thread.start()

    def _on_dest_search_results(self, results: list):
        self.dest_suggestions_list.clear()
        if not results:
            self.dest_suggestions_list.setVisible(False)
            return

        for item in results:
            list_item = QListWidgetItem(f"📍 {item['name']}")
            list_item.setToolTip(item["full_name"])
            list_item.setData(Qt.ItemDataRole.UserRole, item)
            self.dest_suggestions_list.addItem(list_item)

        self.dest_suggestions_list.setVisible(True)

    def _on_dest_suggestion_clicked(self, list_item: QListWidgetItem):
        data = list_item.data(Qt.ItemDataRole.UserRole)
        if not data:
            return

        self.dest_suggestions_list.setVisible(False)
        self.dest_search_input.blockSignals(True)
        self.dest_search_input.setText(data["name"])
        self.dest_search_input.blockSignals(False)

        lat = data["lat"]
        lon = data["lon"]

        self.dest_lat.blockSignals(True)
        self.dest_lon.blockSignals(True)
        self.dest_lat.setValue(lat)
        self.dest_lon.setValue(lon)
        self.dest_lat.blockSignals(False)
        self.dest_lon.blockSignals(False)

        self.lbl_dest_confirmed.setText(f"Confirmed on map: {data['name']}")
        self.lbl_dest_confirmed.setVisible(True)

        self.sig_destination_changed.emit(lat, lon)

    def _on_dest_coords_spin_changed(self):
        lat = self.dest_lat.value()
        lon = self.dest_lon.value()
        self.sig_destination_changed.emit(lat, lon)

    def set_start_location(self, lat: float, lon: float):
        self.start_lat.setValue(lat)
        self.start_lon.setValue(lon)
        if not self.start_search_input.text() or self.start_search_input.text() == "Your location":
            self.start_search_input.setText("Your location")

    def set_destination(self, lat: float, lon: float, name: Optional[str] = None):
        self.dest_lat.blockSignals(True)
        self.dest_lon.blockSignals(True)
        self.dest_lat.setValue(lat)
        self.dest_lon.setValue(lon)
        self.dest_lat.blockSignals(False)
        self.dest_lon.blockSignals(False)

        display_name = name or f"{lat:.4f}, {lon:.4f}"
        self.dest_search_input.setText(display_name)
        self.lbl_dest_confirmed.setText(f"Confirmed on map: {display_name}")
        self.lbl_dest_confirmed.setVisible(True)

        self.gpx_filepath = None
        self.lbl_gpx_name.setVisible(False)
        self.sig_destination_changed.emit(lat, lon)

    def _set_speed(self, spd: float):
        self.speed_slider.setValue(int(spd))
        self.speed_spin.setValue(spd)

    def _on_slider_changed(self, val: int):
        self.speed_spin.blockSignals(True)
        self.speed_spin.setValue(float(val))
        self.speed_spin.blockSignals(False)

    def _on_spin_changed(self, val: float):
        self.speed_slider.blockSignals(True)
        self.speed_slider.setValue(int(val))
        self.speed_slider.blockSignals(False)

    def _on_load_gpx_clicked(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Select GPX Route File", "", "GPX Files (*.gpx)"
        )
        if filepath:
            self.gpx_filepath = filepath
            filename = filepath.split("/")[-1]
            self.lbl_gpx_name.setText(f"Loaded: {filename}")
            self.lbl_gpx_name.setVisible(True)

    def _on_reverse_route_clicked(self):
        """Swaps start coordinates and destination coordinates."""
        play_system_sound("Tink")
        s_lat = self.start_lat.value()
        s_lon = self.start_lon.value()
        d_lat = self.dest_lat.value()
        d_lon = self.dest_lon.value()

        # Swap inputs text
        s_text = self.start_search_input.text()
        d_text = self.dest_search_input.text()
        self.start_search_input.setText(d_text if d_text else f"{d_lat:.4f}, {d_lon:.4f}")
        self.dest_search_input.setText(s_text if s_text else "Your location")

        self.start_lat.blockSignals(True)
        self.start_lon.blockSignals(True)
        self.dest_lat.blockSignals(True)
        self.dest_lon.blockSignals(True)

        self.start_lat.setValue(d_lat)
        self.start_lon.setValue(d_lon)
        self.dest_lat.setValue(s_lat)
        self.dest_lon.setValue(s_lon)

        self.start_lat.blockSignals(False)
        self.start_lon.blockSignals(False)
        self.dest_lat.blockSignals(False)
        self.dest_lon.blockSignals(False)

        self.lbl_dest_confirmed.setText(f"Route reversed: heading to ({s_lat:.4f}, {s_lon:.4f})")
        self.lbl_dest_confirmed.setVisible(True)
        self.sig_destination_changed.emit(s_lat, s_lon)

    def _on_export_gpx_clicked(self):
        """Calculates and exports the current road route into a .gpx track file."""
        s_lat = self.start_lat.value()
        s_lon = self.start_lon.value()
        d_lat = self.dest_lat.value()
        d_lon = self.dest_lon.value()

        filepath, _ = QFileDialog.getSaveFileName(
            self, "Save Route as GPX", "simulated_route.gpx", "GPX Files (*.gpx)"
        )
        if filepath:
            pts = fetch_osrm_route(s_lat, s_lon, d_lat, d_lon)
            if pts:
                success = export_gpx(pts, filepath)
                if success:
                    play_system_sound("Pop")
                    filename = filepath.split("/")[-1]
                    self.lbl_dest_confirmed.setText(f"✓ Route exported to {filename}")
                    self.lbl_dest_confirmed.setVisible(True)

    def _on_play_clicked(self):
        speed = self.speed_spin.value()
        traffic = self.chk_realistic_traffic.isChecked()
        loop = self.chk_loop_route.isChecked()

        if self.is_paused:
            self.is_paused = False
            self.btn_pause.setText("⏸ Pause")
            self.sig_resume_route.emit()
            return

        play_system_sound("Purr")
        self.is_running = True
        self.is_paused = False
        self.btn_play.setEnabled(False)
        self.btn_pause.setEnabled(True)
        self.btn_stop.setEnabled(True)

        if self.gpx_filepath:
            self.sig_start_gpx.emit(self.gpx_filepath, speed)
        else:
            s_lat = self.start_lat.value()
            s_lon = self.start_lon.value()
            d_lat = self.dest_lat.value()
            d_lon = self.dest_lon.value()
            self.sig_start_route.emit(s_lat, s_lon, d_lat, d_lon, speed, traffic, loop)

    def _on_pause_clicked(self):
        if not self.is_paused:
            self.is_paused = True
            self.btn_pause.setText("Resume")
            self.sig_pause_route.emit()
        else:
            self.is_paused = False
            self.btn_pause.setText("Pause")
            self.sig_resume_route.emit()

    def _on_stop_clicked(self):
        self.is_running = False
        self.is_paused = False
        self.btn_play.setEnabled(True)
        self.btn_pause.setEnabled(False)
        self.btn_stop.setEnabled(False)
        self.btn_pause.setText("Pause")
        self.progress_bar.setValue(0)
        self.lbl_eta.setText("Route Stopped")
        self.sig_stop_route.emit()

    def update_progress(self, lat: float, lon: float, percent: float, eta_str: str):
        self.progress_bar.setValue(int(percent))
        self.lbl_eta.setText(f"Speed: {self.speed_spin.value():.1f} km/h • ETA: {eta_str} ({percent:.1f}%)")

    def on_route_finished(self):
        self.is_running = False
        self.is_paused = False
        self.btn_play.setEnabled(True)
        self.btn_pause.setEnabled(False)
        self.btn_stop.setEnabled(False)
        self.progress_bar.setValue(100)
        self.lbl_eta.setText("Destination Reached")
