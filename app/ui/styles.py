"""
Curated macOS Dark Mode Stylesheet for Location Spoofer.
Combines SF-style typography, subtle borders, translucent cards, and vibrant accents.
"""

DARK_STYLESHEET = """
QMainWindow {
    background-color: #0d0f15;
    color: #f0f3f8;
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", sans-serif;
}

QWidget {
    color: #e2e8f0;
    font-size: 13px;
}

/* Card Panels */
QFrame.CardPanel {
    background-color: #161922;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
}

QFrame.SubCard {
    background-color: #1c202b;
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 8px;
}

/* Tab Widget */
QTabWidget::pane {
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    background-color: #161922;
    top: -1px;
}

QTabBar::tab {
    background: #11141c;
    color: #8b95a5;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-bottom: none;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    padding: 8px 18px;
    font-weight: 600;
    font-size: 13px;
    margin-right: 4px;
}

QTabBar::tab:selected {
    background: #161922;
    color: #38bdf8;
    border-bottom: 2px solid #0a84ff;
}

QTabBar::tab:hover:!selected {
    background: #181c26;
    color: #cbd5e1;
}

/* Section Header Labels */
QLabel.SectionTitle {
    font-size: 14px;
    font-weight: 600;
    color: #f1f5f9;
    letter-spacing: 0.3px;
}

QLabel.FieldLabel {
    font-size: 11px;
    font-weight: 600;
    color: #8b95a5;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

/* Double Spin Boxes for Coordinates */
QDoubleSpinBox {
    background-color: #12141c;
    border: 1px solid #262b3a;
    border-radius: 8px;
    padding: 8px 12px;
    font-family: "SF Mono", Menlo, Monaco, Consolas, monospace;
    font-size: 14px;
    font-weight: 600;
    color: #38bdf8;
    selection-background-color: #0a84ff;
}

QDoubleSpinBox:focus {
    border: 1px solid #0a84ff;
    background-color: #141722;
}

/* Remove stepper buttons so the box has a uniform, single color throughout */
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
    width: 0px;
    height: 0px;
    border: none;
    background: transparent;
}

/* Large, easy-to-grab splitter divider with hover highlight */
QSplitter::handle {
    background-color: #141722;
}

QSplitter::handle:horizontal {
    width: 10px;
    border-left: 1px solid #232a3b;
    border-right: 1px solid #232a3b;
}

QSplitter::handle:horizontal:hover {
    background-color: #0a84ff;
    border-left: 1px solid #38bdf8;
    border-right: 1px solid #38bdf8;
}

QSplitter::handle:vertical {
    height: 10px;
    border-top: 1px solid #232a3b;
    border-bottom: 1px solid #232a3b;
}

QSplitter::handle:vertical:hover {
    background-color: #0a84ff;
    border-top: 1px solid #38bdf8;
    border-bottom: 1px solid #38bdf8;
}

/* Address Search Input */
QLineEdit#AddressSearchInput {
    background-color: #12141c;
    border: 1px solid #262b3a;
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 13px;
    color: #f1f5f9;
}

QLineEdit#AddressSearchInput:focus {
    border: 1px solid #0a84ff;
    background-color: #141722;
}

/* Suggestions Dropdown */
QListWidget#AddressSuggestionsList {
    background-color: #161922;
    border: 1px solid #2e3549;
    border-radius: 8px;
    color: #e2e8f0;
    font-size: 12px;
    outline: none;
    padding: 4px;
}

QListWidget#AddressSuggestionsList::item {
    padding: 7px 10px;
    border-radius: 6px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.04);
}

QListWidget#AddressSuggestionsList::item:hover {
    background-color: #202534;
    color: #38bdf8;
}

QListWidget#AddressSuggestionsList::item:selected {
    background-color: #0a84ff;
    color: #ffffff;
}

/* Keep Awake Toggle Button */
QPushButton#KeepAwakeBtn {
    background-color: #161c28;
    border: 1px solid #2a3a54;
    border-radius: 8px;
    color: #64748b;
    font-size: 12px;
    font-weight: 600;
    padding: 6px 14px;
}

QPushButton#KeepAwakeBtn:hover {
    border: 1px solid #38bdf8;
    color: #94a3b8;
}

QPushButton#KeepAwakeBtn:checked {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1a2c4e, stop:1 #132038);
    border: 1px solid #0284c7;
    color: #38bdf8;
}

QPushButton#KeepAwakeBtn:checked:hover {
    border: 1px solid #38bdf8;
    background-color: #1e345c;
}

/* Primary Spoof Button */
QPushButton#SpoofButton {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #0a84ff, stop:1 #0070e0);
    border: 1px solid #208fff;
    border-radius: 10px;
    color: #ffffff;
    font-size: 14px;
    font-weight: 600;
    padding: 12px 20px;
    letter-spacing: 0.2px;
}

QPushButton#SpoofButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1a8cff, stop:1 #0a7aff);
}

QPushButton#SpoofButton:pressed {
    background: #0060c4;
}

QPushButton#SpoofButton:disabled {
    background: #202430;
    border: 1px solid #2a3040;
    color: #555e70;
}

/* Reset Location Button */
QPushButton#ResetButton {
    background-color: #241a1e;
    border: 1px solid rgba(255, 69, 58, 0.35);
    border-radius: 10px;
    color: #ff453a;
    font-size: 13px;
    font-weight: 600;
    padding: 10px 18px;
}

QPushButton#ResetButton:hover {
    background-color: #332025;
    border-color: rgba(255, 69, 58, 0.6);
}

QPushButton#ResetButton:pressed {
    background-color: #401f25;
}

QPushButton#ResetButton:disabled {
    background-color: #181a22;
    border-color: #252834;
    color: #555e70;
}

/* Preset Landmark Buttons */
QPushButton.PresetBtn {
    background-color: #191c26;
    border: 1px solid #262a38;
    border-radius: 7px;
    color: #cbd5e1;
    font-size: 12px;
    font-weight: 500;
    padding: 6px 10px;
}

QPushButton.PresetBtn:hover {
    background-color: #222736;
    border-color: #3b435a;
    color: #38bdf8;
}

QPushButton.PresetBtn:pressed {
    background-color: #151821;
}

/* General Buttons */
QPushButton.SecondaryBtn {
    background-color: #1c202c;
    border: 1px solid #2a3042;
    border-radius: 7px;
    color: #cbd5e1;
    font-size: 12px;
    padding: 6px 12px;
}

QPushButton.SecondaryBtn:hover {
    background-color: #242938;
    border-color: #3a435c;
    color: #ffffff;
}

/* Console Log View */
QTextEdit#LogConsole {
    background-color: #0c0e14;
    border: 1px solid #1c202c;
    border-radius: 8px;
    font-family: "SF Mono", Menlo, Monaco, Consolas, monospace;
    font-size: 11px;
    line-height: 1.4;
    color: #d1d5db;
    padding: 8px;
}

/* Scroll Bars */
QScrollBar:vertical {
    border: none;
    background: #0f1117;
    width: 8px;
    margin: 0px 0px 0px 0px;
    border-radius: 4px;
}

QScrollBar::handle:vertical {
    background: #2a2f40;
    min-height: 20px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background: #3b4259;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    border: none;
    background: none;
    height: 0px;
}

/* Device Selector ComboBox */
QComboBox {
    background-color: #161922;
    border: 1px solid #282e3f;
    border-radius: 8px;
    padding: 6px 12px;
    color: #f1f5f9;
    font-weight: 500;
}

QComboBox:hover {
    border-color: #3b445c;
}

QComboBox::drop-down {
    border: none;
    width: 24px;
}

QComboBox QAbstractItemView {
    background-color: #161922;
    border: 1px solid #2e3549;
    selection-background-color: #0a84ff;
    selection-color: #ffffff;
    outline: none;
    padding: 4px;
    border-radius: 6px;
}
"""
