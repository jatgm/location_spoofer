"""
Application Entrypoint for iOS 17+ Location Spoofer.
"""

import sys
import logging
from pathlib import Path

# Ensure repository root is on sys.path regardless of how script is executed
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from app.ui.main_window import MainWindow


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] (%(name)s) %(message)s",
        datefmt="%H:%M:%S",
    )


def main():
    setup_logging()

    # Enable modern High-DPI support on macOS Retina displays
    app = QApplication(sys.argv)
    app.setApplicationName("iOS Location Spoofer")
    app.setOrganizationName("LocationSpoofer")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
