"""
Main Application Window for iOS 17+ Location Spoofer.
Integrates the Map, Controls, Status, and Log widgets with the background QThread.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QMessageBox, QTabWidget, QScrollArea, QFrame
)

from app.ui.status_widget import StatusWidget
from app.ui.map_widget import MapWidget
from app.ui.controls_widget import ControlsWidget
from app.ui.route_widget import RouteWidget
from app.ui.log_widget import LogWidget
from app.ui.styles import DARK_STYLESHEET
from app.core.worker_thread import DeviceWorker
from app.core.power_manager import SleepPreventionManager


class MainWindow(QMainWindow):
    """Primary desktop application window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("iOS Location Spoofer (iOS 17+ / CoreDevice)")
        self.resize(1200, 840)
        self.setMinimumSize(960, 680)

        # Apply curated dark theme
        self.setStyleSheet(DARK_STYLESHEET)

        # Sleep Prevention Manager (caffeinate keep-awake)
        self.power_manager = SleepPreventionManager()
        self.power_manager.start_keep_awake()

        # Initialize Background Worker Thread
        self.worker = DeviceWorker(self)

        self._current_lat = 37.334900
        self._current_lon = -122.009020

        self._init_ui()
        self._connect_signals()

        # Start worker thread
        self.worker.start()

    def _init_ui(self):
        central = QWidget(self)
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Top Header & Device Status
        self.status_widget = StatusWidget(self)
        main_layout.addWidget(self.status_widget)

        # 2. Main Horizontal Splitter (Left: Full-Height Map, Right: Controls & Console)
        main_splitter = QSplitter(Qt.Orientation.Horizontal, self)
        main_splitter.setHandleWidth(3)

        # Left: Interactive Map (Spans full window height)
        self.map_widget = MapWidget(self)
        main_splitter.addWidget(self.map_widget)

        # Right: Vertical Splitter containing Controls Tabs on top & Console on bottom
        right_splitter = QSplitter(Qt.Orientation.Vertical, self)
        right_splitter.setHandleWidth(3)

        # Controls Tabs (Single Location & Route Simulation)
        self.tabs = QTabWidget(self)

        self.controls_widget = ControlsWidget(self)
        scroll_controls = QScrollArea()
        scroll_controls.setWidgetResizable(True)
        scroll_controls.setFrameShape(QFrame.Shape.NoFrame)
        scroll_controls.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_controls.setWidget(self.controls_widget)
        self.tabs.addTab(scroll_controls, "Single Location")

        self.route_widget = RouteWidget(self)
        scroll_route = QScrollArea()
        scroll_route.setWidgetResizable(True)
        scroll_route.setFrameShape(QFrame.Shape.NoFrame)
        scroll_route.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_route.setWidget(self.route_widget)
        self.tabs.addTab(scroll_route, "Route Simulation")

        right_splitter.addWidget(self.tabs)

        # Activity & Diagnostics Console placed on the right
        self.log_widget = LogWidget(self)
        right_splitter.addWidget(self.log_widget)

        # Proportions on right: 68% controls, 32% console
        right_splitter.setStretchFactor(0, 68)
        right_splitter.setStretchFactor(1, 32)

        main_splitter.addWidget(right_splitter)

        # Proportions overall: 58% Map on left, 42% Controls & Console on right
        main_splitter.setStretchFactor(0, 58)
        main_splitter.setStretchFactor(1, 42)

        main_layout.addWidget(main_splitter, 1)

    def _connect_signals(self):
        # Map <-> Controls coordinate synchronization
        self.map_widget.sig_location_changed.connect(self._on_map_coords_changed)
        self.controls_widget.sig_coords_changed.connect(self._on_controls_coords_changed)

        # Single Location Actions -> Worker
        self.controls_widget.sig_spoof_requested.connect(self.worker.spoof_location)
        self.controls_widget.sig_reset_requested.connect(self.worker.reset_location)
        self.controls_widget.sig_actual_location_requested.connect(self._jump_to_real_location)
        self.status_widget.sig_refresh_clicked.connect(self.worker.refresh_devices_now)
        self.status_widget.sig_device_selected.connect(self.worker.set_target_device)
        self.status_widget.sig_keep_awake_toggled.connect(self._on_keep_awake_toggled)

        # Route Actions -> Worker
        self.route_widget.btn_set_dest_from_map.clicked.connect(
            lambda: self.route_widget.set_destination(self._current_lat, self._current_lon)
        )
        self.route_widget.sig_start_route.connect(self.worker.start_route_simulation)
        self.route_widget.sig_start_gpx.connect(self.worker.start_gpx_simulation)
        self.route_widget.sig_pause_route.connect(self.worker.pause_route_simulation)
        self.route_widget.sig_resume_route.connect(self.worker.resume_route_simulation)
        self.route_widget.sig_stop_route.connect(self.worker.stop_route_simulation)
        self.route_widget.sig_stop_route.connect(self.map_widget.clear_route)

        # Worker -> UI Updates
        self.worker.sig_devices_updated.connect(self.status_widget.update_devices)
        self.worker.sig_status_changed.connect(self.status_widget.set_status)
        self.worker.sig_log.connect(self.log_widget.append_log)
        self.worker.sig_error.connect(self._on_device_error)
        self.worker.sig_real_location_detected.connect(self._on_real_location_detected)

        self.worker.sig_spoof_success.connect(self._on_spoof_success)
        self.worker.sig_clear_success.connect(self._on_clear_success)
        self.worker.sig_device_disconnected.connect(self._on_device_disconnected)

        # Worker Route Updates -> Map & Route Panel
        self.worker.sig_route_started.connect(self.map_widget.draw_route)
        self.worker.sig_route_progress.connect(self._on_route_progress)
        self.worker.sig_route_finished.connect(self._on_route_finished)
        self.worker.sig_route_stopped.connect(self.map_widget.clear_route)

    def _on_real_location_detected(self, lat: float, lon: float, desc: str):
        """Called upon initial app startup or on-demand location detection."""
        self._real_lat = lat
        self._real_lon = lon
        self._current_lat = lat
        self._current_lon = lon
        self.controls_widget.set_coordinates(lat, lon)
        self.route_widget.set_start_location(lat, lon)
        self.map_widget.fly_to(lat, lon, zoom=14)
        self.log_widget.append_log("SUCCESS", f"Defaulted to your actual location: {desc} ({lat:.4f}, {lon:.4f})")

    def _jump_to_real_location(self):
        """User clicked 'Jump to My Actual Location'."""
        if hasattr(self, "_real_lat") and self._real_lat is not None:
            self._current_lat = self._real_lat
            self._current_lon = self._real_lon
            self.controls_widget.set_coordinates(self._real_lat, self._real_lon)
            self.route_widget.set_start_location(self._real_lat, self._real_lon)
            self.map_widget.fly_to(self._real_lat, self._real_lon, zoom=14)
        else:
            self.worker.detect_real_location_now()

    def _on_map_coords_changed(self, lat: float, lon: float):
        """Map pin was clicked or dragged."""
        self._current_lat = lat
        self._current_lon = lon
        self.controls_widget.set_coordinates(lat, lon)
        self.route_widget.set_start_location(lat, lon)

    def _on_controls_coords_changed(self, lat: float, lon: float):
        """Spinbox values were modified or preset clicked."""
        self._current_lat = lat
        self._current_lon = lon
        self.map_widget.set_coordinates(lat, lon, pan=True)
        self.route_widget.set_start_location(lat, lon)

    def _on_route_progress(self, lat: float, lon: float, percent: float, eta_str: str):
        self._current_lat = lat
        self._current_lon = lon
        self.map_widget.set_coordinates(lat, lon, pan=False)
        self.route_widget.update_progress(lat, lon, percent, eta_str)
        self.status_widget.set_status("SPOOFING", f"Route ({percent:.0f}%) • ETA: {eta_str}")

    def _on_route_finished(self):
        self.route_widget.on_route_finished()
        self.map_widget.clear_route()
        self.status_widget.set_status("SPOOFING", "Arrived at Destination")

    def _on_spoof_success(self, lat: float, lon: float):
        self.controls_widget.set_spoofing_state(True)
        self.status_widget.set_status("SPOOFING", f"Active GPS Spoof: ({lat:.4f}, {lon:.4f})")

    def _on_clear_success(self):
        self.controls_widget.set_spoofing_state(False)
        self.status_widget.set_status("CONNECTED", "Physical GPS Restored")

    def _on_device_disconnected(self):
        self.controls_widget.set_spoofing_state(False)
        self.status_widget.set_status("NO_DEVICE", "iOS Device Disconnected")

    def _on_device_error(self, title: str, message: str, advice: str):
        """Displays a structured troubleshooting dialog."""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(title)
        msg_box.setText(f"<b>{message}</b>")
        msg_box.setInformativeText(f"\nRecommended Action:\n{advice}")
        msg_box.setIcon(QMessageBox.Icon.Warning)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg_box.exec()

    def _on_keep_awake_toggled(self, enabled: bool):
        if enabled:
            self.power_manager.start_keep_awake()
            self.log_widget.append_log("INFO", "Keep Awake active. System will stay awake while connected.")
        else:
            self.power_manager.stop_keep_awake()
            self.log_widget.append_log("INFO", "Keep Awake deactivated. Standard Mac sleep restored.")

    def closeEvent(self, event):
        """Cleanly terminates background worker and sleep prevention on window exit."""
        self.log_widget.append_log("INFO", "Shutting down background services...")
        self.power_manager.stop_keep_awake()
        self.worker.stop()
        event.accept()
