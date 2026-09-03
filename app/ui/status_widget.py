"""
Status Widget showing USB connection status, active device details,
and device selection controls.
"""

from typing import Dict, List, Any, Optional
from PyQt6.QtCore import pyqtSignal, Qt, QPropertyAnimation, QEasingCurve, QRect
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QComboBox, QPushButton, QFrame, QCheckBox
)
from app.core.notifications import play_system_sound, is_sound_enabled, set_sound_enabled


class StatusWidget(QWidget):
    """Displays device connection status, device metadata, and device selector."""

    sig_device_selected = pyqtSignal(str, bool)  # (udid, is_ios17)
    sig_refresh_clicked = pyqtSignal()
    sig_keep_awake_toggled = pyqtSignal(bool)
    sig_sound_toggled = pyqtSignal(bool)
    sig_emergency_kill_clicked = pyqtSignal()

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
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)

        # Status Pill
        self.status_frame = QFrame(self)
        self.status_frame.setObjectName("StatusPill")
        pill_layout = QHBoxLayout(self.status_frame)
        pill_layout.setContentsMargins(10, 5, 12, 5)
        pill_layout.setSpacing(7)

        # Clean circular dot indicator
        self.dot = QFrame(self.status_frame)
        self.dot.setFixedSize(8, 8)
        pill_layout.addWidget(self.dot)

        self.state_label = QLabel("Scanning USB...", self.status_frame)
        self.state_label.setStyleSheet("border: none; background: transparent; font-weight: 600; font-size: 12px;")
        pill_layout.addWidget(self.state_label)

        layout.addWidget(self.status_frame)

        # Device Details Label (compact battery & connection indicator)
        self.device_info_label = QLabel("", self)
        self.device_info_label.setStyleSheet("color: #94a3b8; font-size: 12px; font-weight: 500;")
        layout.addWidget(self.device_info_label)

        layout.addStretch()

        # Device Selector Combo
        self.combo_devices = QComboBox(self)
        self.combo_devices.setMinimumWidth(160)
        self.combo_devices.setMaximumWidth(220)
        self.combo_devices.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        self.combo_devices.currentIndexChanged.connect(self._on_device_combo_changed)
        layout.addWidget(self.combo_devices)

        # Refresh Devices Button
        self.btn_refresh = QPushButton("Refresh", self)
        self.btn_refresh.setProperty("class", "SecondaryBtn")
        self.btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_refresh.clicked.connect(self.sig_refresh_clicked.emit)
        layout.addWidget(self.btn_refresh)

        # Sound Toggle Button
        self.btn_sound = QPushButton("🔊 Sound", self)
        self.btn_sound.setObjectName("SoundToggleBtn")
        self.btn_sound.setCheckable(True)
        self.btn_sound.setChecked(True)
        self.btn_sound.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_sound.setToolTip("Toggle macOS sound effects")
        self.btn_sound.toggled.connect(self._on_sound_toggled)
        layout.addWidget(self.btn_sound)

        # Keep Awake Toggle Button
        self.btn_keep_awake = QPushButton("☕ Awake: ON", self)
        self.btn_keep_awake.setObjectName("KeepAwakeBtn")
        self.btn_keep_awake.setCheckable(True)
        self.btn_keep_awake.setChecked(True)
        self.btn_keep_awake.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_keep_awake.setToolTip("Prevents macOS from sleeping so USB and GPS stay connected")
        self.btn_keep_awake.toggled.connect(self._on_keep_awake_toggled)
        layout.addWidget(self.btn_keep_awake)

        # Emergency Kill Switch Button
        self.btn_emergency_kill = QPushButton("🛑 Reset", self)
        self.btn_emergency_kill.setObjectName("EmergencyKillBtn")
        self.btn_emergency_kill.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_emergency_kill.setToolTip("Immediately restores device physical GPS and closes tunnels")
        self.btn_emergency_kill.clicked.connect(self.sig_emergency_kill_clicked.emit)
        layout.addWidget(self.btn_emergency_kill)

        self.set_status("NO_DEVICE")

    def _on_sound_toggled(self, checked: bool):
        set_sound_enabled(checked)
        self.btn_sound.setText("🔊 Sound" if checked else "🔇 Muted")
        self.sig_sound_toggled.emit(checked)

    def _on_keep_awake_toggled(self, checked: bool):
        self.btn_keep_awake.setText("☕ Awake: ON" if checked else "☕ Awake: OFF")
        self.sig_keep_awake_toggled.emit(checked)

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
            f"font-size: 12px; "
            f"border: none; "
            f"background: transparent;"
        )
        self.status_frame.setStyleSheet(
            f"QFrame#StatusPill {{ "
            f"background-color: {cfg['bg']}; "
            f"border: 1px solid {cfg['border']}; "
            f"border-radius: 8px; "
            f"}}"
        )

    MODEL_MAP = {
        "iPhone17,1": "iPhone 16 Pro",
        "iPhone17,2": "iPhone 16 Pro Max",
        "iPhone17,3": "iPhone 16",
        "iPhone17,4": "iPhone 16 Plus",
        "iPhone16,1": "iPhone 15 Pro Max",
        "iPhone16,2": "iPhone 15 Pro",
        "iPhone15,4": "iPhone 15",
        "iPhone15,5": "iPhone 15 Plus",
        "iPhone15,2": "iPhone 14 Pro",
        "iPhone15,3": "iPhone 14 Pro Max",
        "iPhone14,7": "iPhone 14",
        "iPhone14,8": "iPhone 14 Plus",
        "iPhone14,2": "iPhone 13 Pro",
        "iPhone14,3": "iPhone 13 Pro Max",
        "iPhone14,5": "iPhone 13",
    }

    def update_devices(self, devices: List[Dict[str, Any]]):
        was_empty = len(self._devices) == 0 and len(devices) > 0
        self._devices = devices
        self.combo_devices.blockSignals(True)
        self.combo_devices.clear()

        if not devices:
            self.combo_devices.addItem("No devices found", None)
            self.combo_devices.setEnabled(False)
            self.device_info_label.setText("")
            self.set_status("NO_DEVICE")
        else:
            for dev in devices:
                model_name = self.MODEL_MAP.get(dev["model"], dev["model"])
                if dev["name"] and dev["name"] not in ("iOS Device", "iPhone"):
                    label = f"{dev['name']} ({model_name}) • iOS {dev['version']}"
                else:
                    label = f"{model_name} • iOS {dev['version']}"
                self.combo_devices.addItem(label, dev)
                idx = self.combo_devices.count() - 1
                self.combo_devices.setItemData(idx, label, Qt.ItemDataRole.ToolTipRole)

            self.combo_devices.setEnabled(True)

            primary = devices[0]
            batt_str = f"🔋 {primary['battery_level']}%" if primary.get("battery_level") is not None else ""
            conn_str = primary.get("connection_type", "USB")
            info_parts = [p for p in [batt_str, conn_str] if p]
            self.device_info_label.setText(" • ".join(info_parts))
            self.set_status("CONNECTED")

            if was_empty:
                self._animate_connect()
                play_system_sound("Pop")

        self.combo_devices.blockSignals(False)

    def _animate_connect(self):
        """Dynamic Island style expanding spring animation on USB connect."""
        anim = QPropertyAnimation(self.status_frame, b"geometry", self)
        anim.setDuration(450)
        anim.setEasingCurve(QEasingCurve.Type.OutBack)
        orig_geo = self.status_frame.geometry()
        start_geo = QRect(orig_geo.x(), orig_geo.y(), max(20, orig_geo.width() - 35), orig_geo.height())
        anim.setStartValue(start_geo)
        anim.setEndValue(orig_geo)
        anim.start()

    def _on_device_combo_changed(self, index: int):
        data = self.combo_devices.itemData(index)
        if data and isinstance(data, dict):
            batt_str = f"🔋 {data['battery_level']}%" if data.get("battery_level") is not None else ""
            conn_str = data.get("connection_type", "USB")
            info_parts = [p for p in [batt_str, conn_str] if p]
            self.device_info_label.setText(" • ".join(info_parts))
            self.sig_device_selected.emit(data["udid"], data.get("is_ios17_plus", True))
