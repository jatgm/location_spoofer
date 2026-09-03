"""
Log Widget for displaying execution logs, device notifications, and error traces.
"""

import html
from datetime import datetime
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTextEdit, QPushButton, QApplication, QFrame
)


class LogWidget(QWidget):
    """Monospace activity log with colorized status chips and clipboard actions."""

    LEVEL_COLORS = {
        "INFO": "#38bdf8",
        "SUCCESS": "#34d399",
        "WARN": "#fbbf24",
        "ERROR": "#f87171"
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 8, 14, 14)
        layout.setSpacing(8)

        # Header Bar
        header = QHBoxLayout()
        header.setSpacing(8)

        lbl = QLabel("Activity & Diagnostics", self)
        lbl.setProperty("class", "FieldLabel")
        header.addWidget(lbl)

        header.addStretch()

        btn_copy = QPushButton("Copy Log", self)
        btn_copy.setProperty("class", "SecondaryBtn")
        btn_copy.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_copy.clicked.connect(self._copy_log)
        header.addWidget(btn_copy)

        btn_clear = QPushButton("Clear", self)
        btn_clear.setProperty("class", "SecondaryBtn")
        btn_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_clear.clicked.connect(self._clear_log)
        header.addWidget(btn_clear)

        layout.addLayout(header)

        # Console Text Box
        self.console = QTextEdit(self)
        self.console.setObjectName("LogConsole")
        self.console.setReadOnly(True)
        self.console.setMinimumHeight(110)
        layout.addWidget(self.console, 1)

        self.append_log("INFO", "Location Spoofer initialized. Scanning for iOS devices...")

    def append_log(self, level: str, message: str):
        level = level.upper()
        color = self.LEVEL_COLORS.get(level, "#94a3b8")
        timestamp = datetime.now().strftime("%H:%M:%S")

        safe_msg = html.escape(message)
        entry_html = (
            f"<div style='margin-bottom: 2px;'>"
            f"<span style='color: #64748b;'>[{timestamp}]</span> "
            f"<span style='color: {color}; font-weight: bold;'>[{level}]</span> "
            f"<span style='color: #e2e8f0;'>{safe_msg}</span>"
            f"</div>"
        )

        self.console.append(entry_html)
        # Auto-scroll to bottom
        sb = self.console.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _copy_log(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.console.toPlainText())
        self.append_log("INFO", "Logs copied to clipboard.")

    def _clear_log(self):
        self.console.clear()
        self.append_log("INFO", "Console log cleared.")
