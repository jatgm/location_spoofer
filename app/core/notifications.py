"""
macOS Native Notifications & System Audio Feedback.
Provides audio feedback and desktop notification banners using native macOS tools.
Zero third-party dependencies.
"""

import logging
import subprocess
import threading
from pathlib import Path
from typing import Optional

logger = logging.getLogger("Notifications")

SOUNDS_DIR = Path("/System/Library/Sounds")

# Global sound toggle state
_sound_enabled: bool = True


def is_sound_enabled() -> bool:
    """Returns True if system audio feedback is active."""
    global _sound_enabled
    return _sound_enabled


def set_sound_enabled(enabled: bool):
    """Enables or disables system sound effects."""
    global _sound_enabled
    _sound_enabled = enabled


def play_system_sound(name: str):
    """
    Plays a macOS system sound non-blockingly.
    Common sounds: 'Tink', 'Pop', 'Sosumi', 'Glass', 'Purr', 'Basso'.
    """
    if not _sound_enabled:
        return

    sound_file = SOUNDS_DIR / f"{name}.aiff"
    if not sound_file.exists():
        return

    def _worker():
        try:
            subprocess.run(
                ["/usr/bin/afplay", str(sound_file)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=2.0
            )
        except Exception:
            pass

    threading.Thread(target=_worker, daemon=True).start()


def send_macos_notification(title: str, message: str, sound_name: Optional[str] = "Sosumi"):
    """
    Displays a native macOS system notification banner.
    Optionally plays an alert sound alongside the notification.
    """
    if sound_name:
        play_system_sound(sound_name)

    def _worker():
        try:
            # Escape quotation marks for AppleScript
            clean_title = title.replace('"', '\\"')
            clean_msg = message.replace('"', '\\"')
            script = f'display notification "{clean_msg}" with title "{clean_title}"'
            subprocess.run(
                ["/usr/bin/osascript", "-e", script],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=3.0
            )
        except Exception as e:
            logger.debug(f"Failed to display notification: {e}")

    threading.Thread(target=_worker, daemon=True).start()
