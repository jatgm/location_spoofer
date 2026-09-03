"""
Controls Widget for manual coordinate inputs, landmark presets,
and spoof / reset action triggers.
"""

from typing import Optional
from PyQt6.QtCore import pyqtSignal, Qt, QTimer, QThread
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QDoubleSpinBox, QPushButton, QGridLayout, QFrame,
    QLineEdit, QListWidget, QListWidgetItem
)
from app.core.geolocation import search_addresses


class GeocodeSearchThread(QThread):
    sig_results = pyqtSignal(list)

    def __init__(self, query: str, parent=None):
        super().__init__(parent)
        self.query = query

    def run(self):
        results = search_addresses(self.query, limit=5)
        self.sig_results.emit(results)


class ControlsWidget(QWidget):
    """Control panel for coordinate configuration, address search, and spoof actions."""

    sig_spoof_requested = pyqtSignal(float, float)
    sig_reset_requested = pyqtSignal()
    sig_coords_changed = pyqtSignal(float, float)
    sig_actual_location_requested = pyqtSignal()

    PRESETS = [
        ("Apple Park", 37.334900, -122.009020),
        ("Times Square", 40.758000, -73.985500),
        ("Eiffel Tower", 48.858400, 2.294500),
        ("Shibuya Tokyo", 35.659500, 139.700500),
        ("Big Ben", 51.500700, -0.124600),
        ("Sydney Opera", -33.856800, 151.215300),
        ("Colosseum Rome", 41.890200, 12.492200),
        ("Waikiki Beach", 21.276600, -157.827300),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._block_signals = False
        self._search_thread: Optional[GeocodeSearchThread] = None

        # Search debounce timer
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(350)
        self._search_timer.timeout.connect(self._do_search)

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # 1. Target Coordinates Card
        coord_card = QFrame(self)
        coord_card.setProperty("class", "CardPanel")
        card_layout = QVBoxLayout(coord_card)
        card_layout.setContentsMargins(14, 14, 14, 14)
        card_layout.setSpacing(10)

        title = QLabel("Target GPS Coordinates", self)
        title.setProperty("class", "SectionTitle")
        card_layout.addWidget(title)

        # --- Address Autocomplete Search ---
        lbl_search = QLabel("SEARCH ADDRESS OR PLACE", self)
        lbl_search.setProperty("class", "FieldLabel")
        card_layout.addWidget(lbl_search)

        self.search_input = QLineEdit(self)
        self.search_input.setObjectName("AddressSearchInput")
        self.search_input.setPlaceholderText("Type address or landmark (e.g. Times Square)...")
        self.search_input.setFixedHeight(34)
        self.search_input.textChanged.connect(self._on_search_text_changed)
        self.search_input.returnPressed.connect(self._do_search)
        card_layout.addWidget(self.search_input)

        # Dropdown list for search suggestions
        self.suggestions_list = QListWidget(self)
        self.suggestions_list.setObjectName("AddressSuggestionsList")
        self.suggestions_list.setMaximumHeight(130)
        self.suggestions_list.setVisible(False)
        self.suggestions_list.itemClicked.connect(self._on_suggestion_clicked)
        card_layout.addWidget(self.suggestions_list)

        # Confirmed address feedback
        self.lbl_confirmed = QLabel("", self)
        self.lbl_confirmed.setStyleSheet("color: #38bdf8; font-size: 11px; font-weight: 500;")
        self.lbl_confirmed.setVisible(False)
        card_layout.addWidget(self.lbl_confirmed)

        # --- Manual Numeric Inputs ---
        lbl_coords = QLabel("MANUAL COORDINATES", self)
        lbl_coords.setProperty("class", "FieldLabel")
        card_layout.addWidget(lbl_coords)

        # Inputs Grid
        grid = QGridLayout()
        grid.setSpacing(10)

        # Latitude
        lbl_lat = QLabel("LATITUDE", self)
        lbl_lat.setProperty("class", "FieldLabel")
        self.spin_lat = QDoubleSpinBox(self)
        self.spin_lat.setRange(-90.0, 90.0)
        self.spin_lat.setDecimals(6)
        self.spin_lat.setSingleStep(0.001)
        self.spin_lat.setValue(37.334900)
        self.spin_lat.setFixedHeight(34)
        self.spin_lat.valueChanged.connect(self._on_spin_changed)

        grid.addWidget(lbl_lat, 0, 0)
        grid.addWidget(self.spin_lat, 1, 0)

        # Longitude
        lbl_lon = QLabel("LONGITUDE", self)
        lbl_lon.setProperty("class", "FieldLabel")
        self.spin_lon = QDoubleSpinBox(self)
        self.spin_lon.setRange(-180.0, 180.0)
        self.spin_lon.setDecimals(6)
        self.spin_lon.setSingleStep(0.001)
        self.spin_lon.setValue(-122.009020)
        self.spin_lon.setFixedHeight(34)
        self.spin_lon.valueChanged.connect(self._on_spin_changed)

        grid.addWidget(lbl_lon, 0, 1)
        grid.addWidget(self.spin_lon, 1, 1)

        card_layout.addLayout(grid)

        # Quick button: My Actual Location
        self.btn_my_loc = QPushButton("Jump to Current Location", self)
        self.btn_my_loc.setProperty("class", "SecondaryBtn")
        self.btn_my_loc.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_my_loc.setFixedHeight(32)
        self.btn_my_loc.clicked.connect(self.sig_actual_location_requested.emit)
        card_layout.addWidget(self.btn_my_loc)

        layout.addWidget(coord_card)

        # 2. Action Controls Card
        action_card = QFrame(self)
        action_card.setProperty("class", "CardPanel")
        action_layout = QVBoxLayout(action_card)
        action_layout.setContentsMargins(14, 14, 14, 14)
        action_layout.setSpacing(10)

        action_title = QLabel("Simulation Controls", self)
        action_title.setProperty("class", "SectionTitle")
        action_layout.addWidget(action_title)

        # Spoof Location Button
        self.btn_spoof = QPushButton("Spoof Location", self)
        self.btn_spoof.setObjectName("SpoofButton")
        self.btn_spoof.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_spoof.clicked.connect(self._on_spoof_clicked)
        action_layout.addWidget(self.btn_spoof)

        # Reset Location Button
        self.btn_reset = QPushButton("Reset to Physical GPS", self)
        self.btn_reset.setObjectName("ResetButton")
        self.btn_reset.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_reset.clicked.connect(self.sig_reset_requested.emit)
        action_layout.addWidget(self.btn_reset)

        layout.addWidget(action_card)

        # 3. Quick Landmark Presets Card
        preset_card = QFrame(self)
        preset_card.setProperty("class", "CardPanel")
        preset_layout = QVBoxLayout(preset_card)
        preset_layout.setContentsMargins(14, 14, 14, 14)
        preset_layout.setSpacing(10)

        preset_title = QLabel("Quick Landmark Presets", self)
        preset_title.setProperty("class", "SectionTitle")
        preset_layout.addWidget(preset_title)

        preset_grid = QGridLayout()
        preset_grid.setSpacing(8)

        row, col = 0, 0
        for name, lat, lon in self.PRESETS:
            btn = QPushButton(name, self)
            btn.setProperty("class", "PresetBtn")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, la=lat, lo=lon: self._apply_preset(la, lo))
            preset_grid.addWidget(btn, row, col)
            col += 1
            if col > 1:
                col = 0
                row += 1

        preset_layout.addLayout(preset_grid)
        layout.addWidget(preset_card)

        layout.addStretch()

    def _on_search_text_changed(self, text: str):
        if len(text.strip()) < 2:
            self.suggestions_list.clear()
            self.suggestions_list.setVisible(False)
            self._search_timer.stop()
            self.lbl_confirmed.setVisible(False)
        else:
            self._search_timer.start()

    def _do_search(self):
        query = self.search_input.text().strip()
        if len(query) < 2:
            return

        if self._search_thread and self._search_thread.isRunning():
            self._search_thread.terminate()

        self._search_thread = GeocodeSearchThread(query, self)
        self._search_thread.sig_results.connect(self._on_search_results)
        self._search_thread.start()

    def _on_search_results(self, results: list):
        self.suggestions_list.clear()
        if not results:
            self.suggestions_list.setVisible(False)
            return

        for item in results:
            list_item = QListWidgetItem(item["name"])
            list_item.setToolTip(item.get("full_name", item["name"]))
            list_item.setData(Qt.ItemDataRole.UserRole, item)
            self.suggestions_list.addItem(list_item)

        self.suggestions_list.setVisible(True)

    def _on_suggestion_clicked(self, list_item: QListWidgetItem):
        data = list_item.data(Qt.ItemDataRole.UserRole)
        if not data:
            return

        self.suggestions_list.setVisible(False)
        self.search_input.blockSignals(True)
        self.search_input.setText(data["name"])
        self.search_input.blockSignals(False)

        lat = data["lat"]
        lon = data["lon"]

        self.set_coordinates(lat, lon)
        self.lbl_confirmed.setText(f"Confirmed on map: {data['name']}")
        self.lbl_confirmed.setVisible(True)

        # Notify MainWindow to move the Leaflet map and position the pin
        self.sig_coords_changed.emit(lat, lon)

    def _on_spin_changed(self):
        if not self._block_signals:
            lat = self.spin_lat.value()
            lon = self.spin_lon.value()
            self.sig_coords_changed.emit(lat, lon)

    def _on_spoof_clicked(self):
        lat = self.spin_lat.value()
        lon = self.spin_lon.value()
        self.sig_spoof_requested.emit(lat, lon)

    def _apply_preset(self, lat: float, lon: float):
        self.set_coordinates(lat, lon)
        self.sig_coords_changed.emit(lat, lon)

    def set_coordinates(self, lat: float, lon: float):
        """Sets spinbox values without emitting loopback signals."""
        self._block_signals = True
        self.spin_lat.setValue(lat)
        self.spin_lon.setValue(lon)
        self._block_signals = False

    def set_controls_enabled(self, enabled: bool):
        self.btn_spoof.setEnabled(enabled)
        self.btn_reset.setEnabled(enabled)

    def set_spoofing_state(self, is_spoofing: bool):
        if is_spoofing:
            self.btn_spoof.setText("Update Spoofed Location")
        else:
            self.btn_spoof.setText("Spoof Location")
