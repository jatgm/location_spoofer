"""
Status Widget showing USB connection status, active device details,
and device selection controls.
"""

from typing import Dict, List, Any, Optional
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QComboBox, QPushButton, QFrame
)


class StatusWidget(QWidget):
    """Displays device connection status, device metadata, and device selector."""

    sig_device_selected = pyqtSignal(str, bool)  # (udid, is_ios17)
    sig_refresh_clicked = pyqtSignal()

    STATUS_STYLES = {
        "NO_DEVICE": {
            "dot": "#8e8e93",
            "text": "No iOS Device Connected",
            "bg": "rgba(142, 142, 147, 0.12)",
            "border": "rgba(142, 142, 147, 0.3)"
        },
        "CONNECTED": {
            "dot": "#30d158",
            "text": "Device Connected & Ready",
            "bg": "rgba(48, 209, 88, 0.12)",
            "border": "rgba(48, 209, 88, 0.35)"
        },
        "CONNECTING": {
            "dot": "#ff9f0a",
            "text": "Communicating with Device...",
            "bg": "rgba(255, 159, 10, 0.12)",
            "border": "rgba(255, 159, 10, 0.35)"
        },
        "SPOOFING": {
            "dot": "#0a84ff",
            "text": "GPS Simulation Active",
            "bg": "rgba(10, 132, 255, 0.15)",
            "border": "rgba(10, 132, 255, 0.4)"
        },
        "ERROR": {
            "dot": "#ff453a",
            "text": "Connection Alert",
            "bg": "rgba(255, 69, 58, 0.12)",
            "border": "rgba(255, 69, 58, 0.35)"
        }
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._devices: List[Dict[str, Any]] = []
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(14)

        # Status Pill
        self.status_frame = QFrame(self)
        self.status_frame.setObjectName("StatusPill")
        pill_layout = QHBoxLayout(self.status_frame)
        pill_layout.setContentsMargins(12, 6, 14, 6)
        pill_layout.setSpacing(8)

        # Clean circular dot indicator (no text glyph / border artifacts)
        self.dot = QFrame(self.status_frame)
        self.dot.setFixedSize(8, 8)
        pill_layout.addWidget(self.dot)

        self.state_label = QLabel("Scanning USB...", self.status_frame)
        self.state_label.setStyleSheet("border: none; background: transparent; font-weight: 600; font-size: 13px;")
        pill_layout.addWidget(self.state_label)

        layout.addWidget(self.status_frame)

        # Device Details Label
        self.device_info_label = QLabel("Connect an iPhone running iOS 17+ via USB", self)
        self.device_info_label.setStyleSheet("color: #8b95a5; font-size: 12px; font-weight: 500;")
        layout.addWidget(self.device_info_label)

        layout.addStretch()

        # Device Selector Combo
        self.combo_devices = QComboBox(self)
        self.combo_devices.setMinimumWidth(220)
        self.combo_devices.currentIndexChanged.connect(self._on_device_combo_changed)
        layout.addWidget(self.combo_devices)

        # Refresh Devices Button
        self.btn_refresh = QPushButton("Refresh", self)
        self.btn_refresh.setProperty("class", "SecondaryBtn")
        self.btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_refresh.clicked.connect(self.sig_refresh_clicked.emit)
        layout.addWidget(self.btn_refresh)

        self.set_status("NO_DEVICE")

    def set_status(self, status_key: str, custom_text: Optional[str] = None):
        cfg = self.STATUS_STYLES.get(status_key, self.STATUS_STYLES["NO_DEVICE"])
        text = custom_text or cfg["text"]

        self.dot.setStyleSheet(
            f"background-color: {cfg['dot']}; "
            f"border-radius: 4px; "
            f"border: none;"
        )
        self.state_label.setText(text)
        self.state_label.setStyleSheet(
            f"color: {cfg['dot']}; "
            f"font-weight: 600; "
            f"font-size: 13px; "
            f"border: none; "
            f"background: transparent;"
        )
        self.status_frame.setStyleSheet(
            f"QFrame#StatusPill {{ "
            f"  background-color: {cfg['bg']}; "
            f"  border: 1px solid {cfg['border']}; "
            f"  border-radius: 15px; "
            f"}} "
            f"QFrame#StatusPill QLabel {{ "
            f"  border: none; "
            f"  background: transparent; "
            f"}}"
        )

    def update_devices(self, devices: List[Dict[str, Any]]):
        self._devices = devices
        self.combo_devices.blockSignals(True)
        self.combo_devices.clear()

        if not devices:
            self.combo_devices.addItem("No devices found", None)
            self.combo_devices.setEnabled(False)
            self.device_info_label.setText("Connect an iPhone running iOS 17+ via USB")
            self.set_status("NO_DEVICE")
        else:
            for dev in devices:
                label = f"{dev['name']} ({dev['model']}) - iOS {dev['version']}"
                self.combo_devices.addItem(label, dev)
            self.combo_devices.setEnabled(True)

            primary = devices[0]
            self.device_info_label.setText(
                f"UDID: {primary['udid'][:12]}... • {primary['connection_type']} • iOS {primary['version']}"
            )
            self.set_status("CONNECTED")

        self.combo_devices.blockSignals(False)

    def _on_device_combo_changed(self, index: int):
        data = self.combo_devices.itemData(index)
        if data and isinstance(data, dict):
            self.device_info_label.setText(
                f"UDID: {data['udid'][:12]}... • {data['connection_type']} • iOS {data['version']}"
            )
            self.sig_device_selected.emit(data["udid"], data.get("is_ios17_plus", True))
