"""
Route Simulation Widget for configuring travel speeds, selecting destinations,
importing GPX files, and controlling continuous route playback.
"""

from typing import Optional
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QDoubleSpinBox, QPushButton, QSlider, QProgressBar,
    QFileDialog, QFrame, QGridLayout
)


class RouteWidget(QWidget):
    """Control panel for turn-by-turn road and GPX route simulation."""

    sig_start_route = pyqtSignal(float, float, float, float, float)  # start_lat, start_lon, dest_lat, dest_lon, speed
    sig_start_gpx = pyqtSignal(str, float)                          # filepath, speed
    sig_pause_route = pyqtSignal()
    sig_resume_route = pyqtSignal()
    sig_stop_route = pyqtSignal()

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
        self.speed_spin.valueChanged.connect(self._on_spin_changed)
        slider_row.addWidget(self.speed_spin)

        sc_layout.addLayout(slider_row)
        layout.addWidget(speed_card)

        # 2. Destination Waypoints Card
        dest_card = QFrame(self)
        dest_card.setProperty("class", "CardPanel")
        dc_layout = QVBoxLayout(dest_card)
        dc_layout.setContentsMargins(14, 14, 14, 14)
        dc_layout.setSpacing(10)

        dest_title = QLabel("Route Destination", self)
        dest_title.setProperty("class", "SectionTitle")
        dc_layout.addWidget(dest_title)

        # Start & Destination Coordinates Grid
        coord_grid = QGridLayout()
        coord_grid.setSpacing(8)

        lbl_s = QLabel("START COORDS (Current)", self)
        lbl_s.setProperty("class", "FieldLabel")
        coord_grid.addWidget(lbl_s, 0, 0, 1, 2)

        self.start_lat = QDoubleSpinBox(self)
        self.start_lat.setRange(-90.0, 90.0)
        self.start_lat.setDecimals(6)
        self.start_lat.setValue(37.334900)
        coord_grid.addWidget(self.start_lat, 1, 0)

        self.start_lon = QDoubleSpinBox(self)
        self.start_lon.setRange(-180.0, 180.0)
        self.start_lon.setDecimals(6)
        self.start_lon.setValue(-122.009020)
        coord_grid.addWidget(self.start_lon, 1, 1)

        lbl_d = QLabel("DESTINATION COORDS", self)
        lbl_d.setProperty("class", "FieldLabel")
        coord_grid.addWidget(lbl_d, 2, 0, 1, 2)

        self.dest_lat = QDoubleSpinBox(self)
        self.dest_lat.setRange(-90.0, 90.0)
        self.dest_lat.setDecimals(6)
        self.dest_lat.setValue(37.352000)
        coord_grid.addWidget(self.dest_lat, 3, 0)

        self.dest_lon = QDoubleSpinBox(self)
        self.dest_lon.setRange(-180.0, 180.0)
        self.dest_lon.setDecimals(6)
        self.dest_lon.setValue(-122.015000)
        coord_grid.addWidget(self.dest_lon, 3, 1)

        dc_layout.addLayout(coord_grid)

        # Set from Map button
        self.btn_set_dest_from_map = QPushButton("Use Selected Pin as Destination", self)
        self.btn_set_dest_from_map.setProperty("class", "SecondaryBtn")
        self.btn_set_dest_from_map.setCursor(Qt.CursorShape.PointingHandCursor)
        dc_layout.addWidget(self.btn_set_dest_from_map)

        # GPX Option
        self.btn_load_gpx = QPushButton("Load GPX File...", self)
        self.btn_load_gpx.setProperty("class", "SecondaryBtn")
        self.btn_load_gpx.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_load_gpx.clicked.connect(self._on_load_gpx_clicked)
        dc_layout.addWidget(self.btn_load_gpx)

        self.lbl_gpx_name = QLabel("", self)
        self.lbl_gpx_name.setStyleSheet("color: #38bdf8; font-size: 11px;")
        self.lbl_gpx_name.setVisible(False)
        dc_layout.addWidget(self.lbl_gpx_name)

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

    def set_start_location(self, lat: float, lon: float):
        self.start_lat.setValue(lat)
        self.start_lon.setValue(lon)

    def set_destination(self, lat: float, lon: float):
        self.dest_lat.setValue(lat)
        self.dest_lon.setValue(lon)
        self.gpx_filepath = None
        self.lbl_gpx_name.setVisible(False)

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

    def _on_play_clicked(self):
        speed = self.speed_spin.value()
        if self.is_paused:
            self.is_paused = False
            self.btn_pause.setText("⏸ Pause")
            self.sig_resume_route.emit()
            return

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
            self.sig_start_route.emit(s_lat, s_lon, d_lat, d_lon, speed)

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
