"""
Error diagnostic and handling module for iOS device communication.
Translates low-level pymobiledevice3, usbmux, and lockdown exceptions into
clear, actionable instructions for the user.
"""

from typing import Tuple


def diagnose_device_error(exc: Exception) -> Tuple[str, str, str]:
    """
    Analyzes an exception and returns a 3-tuple:
    (short_title, friendly_message, actionable_troubleshooting_step)
    """
    exc_type = type(exc).__name__
    exc_str = str(exc).lower()

    # 1. Developer Mode Not Enabled
    if "developermode" in exc_type.lower() or "developermode" in exc_str or "developer mode" in exc_str:
        return (
            "Developer Mode Required",
            "Developer Mode is disabled on this iPhone.",
            "1. On your iPhone, open Settings → Privacy & Security.\n"
            "2. Scroll to the bottom and tap 'Developer Mode'.\n"
            "3. Toggle Developer Mode ON and tap 'Restart'.\n"
            "4. After restarting, unlock your phone and tap 'Turn On'."
        )

    # 2. Device Locked / Password Required / Trust Dialog Pending
    if "passwordrequired" in exc_type.lower() or "pairingdialogresponsepending" in exc_type.lower() or ("password" in exc_str and "required" in exc_str):
        return (
            "Passcode & Trust Required",
            "Your iPhone is locked or waiting for trust approval.",
            "1. Unlock your iPhone screen with your passcode.\n"
            "2. When prompted 'Trust This Computer?', tap 'Trust'.\n"
            "3. Enter your device passcode to confirm."
        )

    # 3. Not Trusted / User Denied Pairing
    if "nottrusted" in exc_type.lower() or "userdeniedpairing" in exc_type.lower() or "trusted" in exc_str:
        return (
            "Computer Untrusted",
            "This Mac has not been trusted by the connected iPhone.",
            "1. Disconnect and reconnect the USB cable.\n"
            "2. Unlock your iPhone and tap 'Trust This Computer'.\n"
            "3. Enter your passcode."
        )

    # 4. Device Not Connected / USB Mux Issue
    if "nodeviceconnected" in exc_type.lower() or "connectionfailedtousbmuxd" in exc_type.lower() or "no device" in exc_str:
        return (
            "No Device Detected",
            "No trusted iOS device was detected over USB.",
            "1. Ensure your iPhone is securely connected via USB/Lightning cable.\n"
            "2. Ensure Finder / iTunes can see the device.\n"
            "3. Check if the cable supports data transfer."
        )

    # 5. Developer Disk Image (DDI) / Cryptex Not Mounted
    if "DeveloperDiskImage" in exc_type or "NotMounted" in exc_type or "cryptex" in exc_str.lower():
        return (
            "Developer Image Required",
            "The iOS Developer Disk Image (DDI) is not yet mounted.",
            "1. Ensure you have an active internet connection on your Mac so the DDI can be downloaded.\n"
            "2. The app will attempt to mount it automatically.\n"
            "3. Alternatively run: pymobiledevice3 cryptex auto-install in Terminal."
        )

    # 6. Tunnel / RemoteXPC Connection Error
    if "Tunnel" in exc_type or "RSD" in exc_type or "remoted" in exc_str.lower():
        return (
            "RSD Tunnel Error",
            "Could not establish Remote Service Discovery (RSD) tunnel to iOS 17+ device.",
            "1. Verify your iPhone is running iOS 17.0 or later.\n"
            "2. Keep the device unlocked.\n"
            "3. Disconnect and re-plug the USB cable."
        )

    # Default fallback for generic exceptions
    return (
        "Device Communication Error",
        f"An error occurred: {exc_str or exc_type}",
        "1. Check USB connection.\n"
        "2. Ensure iPhone is unlocked and Developer Mode is enabled.\n"
        "3. Restart iPhone and try again."
    )
