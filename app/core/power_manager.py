"""
macOS Sleep Prevention & Power Management.
Prevents system idle sleep while location simulation is active using Apple's native caffeinate.
"""

import os
import logging
import subprocess
from typing import Optional

logger = logging.getLogger("PowerManager")


class SleepPreventionManager:
    """Manages a macOS caffeinate subprocess to prevent system sleep while spoofing."""

    def __init__(self):
        self._process: Optional[subprocess.Popen] = None

    def start_keep_awake(self, prevent_display_sleep: bool = False) -> bool:
        """
        Starts caffeinate to prevent system idle sleep.
        -i: Prevents system idle sleep
        -m: Prevents disk idle sleep
        -s: Prevents sleep on AC power
        -w <pid>: Automatically dies if this app process terminates
        """
        if self._process is not None and self._process.poll() is None:
            return True

        cmd = ["/usr/bin/caffeinate", "-i", "-m", "-s", "-w", str(os.getpid())]
        if prevent_display_sleep:
            cmd.append("-d")

        try:
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            logger.info(f"macOS sleep prevention activated (PID: {self._process.pid}).")
            return True
        except Exception as e:
            logger.warning(f"Could not start caffeinate sleep prevention: {e}")
            return False

    def stop_keep_awake(self) -> None:
        """Stops caffeinate and allows normal sleep again."""
        if self._process is not None:
            try:
                if self._process.poll() is None:
                    self._process.terminate()
                    self._process.wait(timeout=1.0)
            except Exception:
                pass
            self._process = None
            logger.info("macOS sleep prevention deactivated.")

    @property
    def is_active(self) -> bool:
        return self._process is not None and self._process.poll() is None
