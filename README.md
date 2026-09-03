# iOS 17+ Location Spoofer (macOS Desktop App)

[![Current Version](https://img.shields.io/badge/version-v1.3.2-0a84ff.svg)](https://github.com/jatgm/location_spoofer/releases)
[![macOS Compatible](https://img.shields.io/badge/platform-macOS%2012%2B-lightgrey.svg)]()
[![iOS Support](https://img.shields.io/badge/iOS-17.0%2B-blue.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A modern desktop application for macOS to simulate and spoof system-wide GPS locations on physical iPhones running **iOS 17 or later** (compatible with Apple Maps, Find My, and all CoreLocation-based apps).

Built with **Python 3**, **PyQt6**, **QWebEngineView (Leaflet.js)**, and **pymobiledevice3**.

---

## Key Features

- **iOS 17+ Native RSD / DVT Support**: Leverages Apple's Remote Service Discovery (RSD) and DVT Instruments over CoreDevice protocols (`pymobiledevice3`).
- **No Root / sudo Required**: Piggybacks macOS's native `remoted` tunnel for low-latency, rootless communication.
- **Persistent Session Manager**: Maintains an active tunnel and DVT channel across coordinate shifts, enabling instant (<10ms) location updates without connection tearing.
- **Responsive Asynchronous Architecture**: All USB discovery, handshakes, and location commands run inside a dedicated background worker (`QThread` + `asyncio`), keeping the UI silky smooth.
- **Interactive Leaflet Map**:
  - Click or drag pin anywhere on the world map to set target coordinates.
  - Live two-way synchronization between the map and numeric coordinate inputs.
  - Sleek dark tile layer with glowing pulse indicator.
  - Integrated OpenStreetMap Nominatim search (search any city, landmark, or address).
- **Quick Landmark Presets**: 1-click test locations (Apple Park, Times Square, Eiffel Tower, Shibuya Crossing, Big Ben, Sydney Opera House, and more).
- **Precision Coordinate Controls**: High-precision 6-decimal inputs for Latitude and Longitude.
- **Diagnostics & Activity Console**: Real-time monospace log console with color-coded status chips and actionable troubleshooting guidance for iOS pairing or Developer Mode issues.

---

## Device Prerequisites (iOS 17+)

Before using the application with a physical iPhone, ensure the following one-time device configuration is complete:

1. **Enable Developer Mode on iPhone**:
   - Open **Settings → Privacy & Security**.
   - Scroll down to the bottom and tap **Developer Mode**.
   - Toggle **Developer Mode ON** and tap **Restart**.
   - After the iPhone restarts, unlock it and tap **Turn On** on the prompt, then enter your passcode.
2. **Trust This Computer**:
   - Connect the iPhone to your Mac via a USB / Lightning / USB-C cable.
   - Unlock your iPhone screen.
   - When prompted with **Trust This Computer?**, tap **Trust** and enter your passcode.
3. **Keep iPhone Unlocked**:
   - Ensure the iPhone is unlocked during initial handshake so the pairing records can be accessed.

---

## Quick Start

### 1. Automated Launch (Recommended)

Simply run the launcher script from Terminal:

```bash
./run.sh
```

This script will automatically:
1. Create a Python virtual environment (`.venv`) if one does not already exist.
2. Install or verify all dependencies from `requirements.txt`.
3. Launch the desktop application.

### 2. Manual Installation

```bash
# 1. Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Upgrade pip and install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 3. Launch the app
python3 app/main.py
```

---

## How to Use

1. **Connect iPhone**: Plug your iPhone into your Mac with a USB cable.
2. **Connection Status**: The top status bar will automatically detect your iPhone via `usbmuxd` and show:
   - Status badge: `Device Connected & Ready` (Green)
   - Device details: Model (e.g. `iPhone 15 Pro`), iOS version (e.g. `iOS 17.5.1`), and UDID.
3. **Select Coordinates**:
   - **On the Map**: Click anywhere or drag the glowing pin.
   - **Search**: Type an address or landmark into the floating map search bar and press Enter.
   - **Presets**: Click any preset button (e.g., *Apple Park*, *Times Square*, *Eiffel Tower*).
   - **Manual Input**: Type exact latitude and longitude values in the spinboxes.
4. **Spoof Location**:
   - Click the **📍 Spoof Location** button.
   - The status bar will turn blue (`GPS Simulation Active`), and the console will log success.
   - Open **Apple Maps** or **Find My** on your iPhone to verify your simulated location!
5. **Reset Location**:
   - Click the **↺ Reset to Physical GPS** button.
   - The simulation stops, and your iPhone immediately restores its real physical GPS.

---

## Architecture Overview

```
location_spoofer/
├── app/
│   ├── main.py                     # Application entry point & Qt event loop
│   ├── core/
│   │   ├── device_service.py       # RSD Tunnel, DvtProvider, & LocationSimulation session manager
│   │   ├── worker_thread.py        # QThread background worker with asyncio event loop
│   │   └── error_handler.py        # Diagnostics mapper for Developer Mode & lockdown exceptions
│   ├── ui/
│   │   ├── main_window.py          # Primary PyQt6 modern dark-mode application window
│   │   ├── map_widget.py           # QWebEngineView Leaflet wrapper + QWebChannel bridge
│   │   ├── controls_widget.py      # Numeric inputs, action buttons, landmark presets
│   │   ├── status_widget.py        # USB connection status badge & device selector
│   │   ├── log_widget.py           # Color-coded monospace activity console
│   │   └── styles.py               # macOS Cupertino dark theme stylesheet
│   └── assets/
│       └── map.html                # Leaflet.js interactive map template with search & pulse pin
├── requirements.txt                # Dependencies specification
├── run.sh                          # Helper startup script
└── README.md                       # Documentation
```

---

## Troubleshooting

| Issue / Alert | Cause | Solution |
| :--- | :--- | :--- |
| **Developer Mode Required** | Developer Mode is off on the iPhone | Go to iPhone **Settings → Privacy & Security → Developer Mode**, toggle ON, restart iPhone, and confirm Turn On. |
| **Passcode & Trust Required** | iPhone screen locked or awaiting Trust | Unlock your iPhone screen and tap **Trust** when prompted. |
| **No Device Detected** | Bad cable or usbmuxd not running | Ensure cable supports data transfer; confirm the device appears in Finder. |
| **Developer Disk Image Required** | DDI not yet mounted on device | Ensure Mac has internet access; `pymobiledevice3` will auto-mount the cryptex. |
| **Tunnel Connection Error** | RemoteXPC handshake interrupted | Keep iPhone unlocked, disconnect and re-plug USB cable. |

---

## License

MIT License. Educational and authorized testing purposes only.
