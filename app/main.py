import atexit
import logging
import os
import signal
import sys
import time
from pathlib import Path

# Ensure repository root is on sys.path regardless of how script is executed
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from app.ui.main_window import MainWindow

LOCK_FILE = Path("/tmp/ios_location_spoofer.pid")


def enforce_single_instance():
    """
    Ensures only a single instance of the application runs at any time.
    If another instance is detected, terminates it so this new instance takes over.
    Uses only Python standard library (no extra dependencies).
    """
    current_pid = os.getpid()
    if LOCK_FILE.exists():
        try:
            content = LOCK_FILE.read_text().strip()
            if content.isdigit():
                old_pid = int(content)
                if old_pid != current_pid:
                    try:
                        # Check if old process is still alive
                        os.kill(old_pid, 0)
                        print(f"Existing instance detected (PID: {old_pid}). Terminating it to take over...")
                        os.kill(old_pid, signal.SIGTERM)
                        for _ in range(15):
                            time.sleep(0.05)
                            try:
                                os.kill(old_pid, 0)
                            except OSError:
                                break
                        else:
                            try:
                                os.kill(old_pid, signal.SIGKILL)
                            except OSError:
                                pass
                    except OSError:
                        # Process not running (stale lock file)
                        pass
        except Exception as e:
            logging.debug(f"Could not read PID lockfile: {e}")

    try:
        LOCK_FILE.write_text(str(current_pid))
    except Exception as e:
        logging.warning(f"Could not write PID lockfile: {e}")

    # Remove lockfile on normal exit
    atexit.register(_cleanup_lockfile, current_pid)


def _cleanup_lockfile(pid: int):
    try:
        if LOCK_FILE.exists() and LOCK_FILE.read_text().strip() == str(pid):
            LOCK_FILE.unlink(missing_ok=True)
    except Exception:
        pass


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] (%(name)s) %(message)s",
        datefmt="%H:%M:%S",
    )


def main():
    # Enforce single instance before initializing GUI
    enforce_single_instance()

    # Handle SIGTERM gracefully
    signal.signal(signal.SIGTERM, lambda sig, frame: sys.exit(0))

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
