"""
Background Worker Thread managing asyncio event loop, device polling,
and asynchronous location spoofing tasks without blocking the PyQt UI.
"""

import asyncio
import logging
from typing import Optional, List, Dict, Any, Tuple
from PyQt6.QtCore import QThread, pyqtSignal

from app.core.device_service import DeviceService, DeviceInfo
from app.core.error_handler import diagnose_device_error
from app.core.geolocation import get_actual_location
from app.core.route_simulator import (
    fetch_osrm_route, parse_gpx_file, build_interpolated_timeline, haversine_distance
)

logger = logging.getLogger("DeviceWorker")


class DeviceWorker(QThread):
    """
    QThread running an independent asyncio event loop to execute pymobiledevice3
    asynchronous operations, periodic device polling, and continuous route simulation.
    """

    # Signals to GUI
    sig_devices_updated = pyqtSignal(list)          # list of device dicts
    sig_device_connected = pyqtSignal(dict)         # connected device dict
    sig_device_disconnected = pyqtSignal()          # device detached
    sig_status_changed = pyqtSignal(str, str)       # (status_state, message)
    sig_spoof_success = pyqtSignal(float, float)    # (latitude, longitude)
    sig_clear_success = pyqtSignal()                # location simulation cleared
    sig_log = pyqtSignal(str, str)                  # (level: INFO/SUCCESS/WARN/ERROR, text)
    sig_error = pyqtSignal(str, str, str)           # (title, message, advice)
    sig_real_location_detected = pyqtSignal(float, float, str)  # (lat, lon, description)

    # Route Simulation Signals
    sig_route_started = pyqtSignal(list)            # list of (lat, lon) for map polyline
    sig_route_progress = pyqtSignal(float, float, float, str)  # (lat, lon, percent, eta_str)
    sig_route_finished = pyqtSignal()
    sig_route_stopped = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.service = DeviceService()
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self._running: bool = True
        self._poll_interval: float = 2.5
        self._last_device_udids: set = set()
        self._active_udid: Optional[str] = None
        self._is_ios17: bool = True

        # Route Simulation State
        self._route_task: Optional[asyncio.Task] = None
        self._route_paused: bool = False
        self._route_stopped: bool = False

    def run(self):
        """Thread main entry: runs the asyncio event loop."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        # Schedule background polling & initial real location detection
        self.loop.create_task(self._poll_loop())
        self.loop.create_task(self._async_detect_real_location())

        try:
            self.loop.run_forever()
        finally:
            # Cleanup active device sessions
            if self.service:
                try:
                    self.loop.run_until_complete(self.service.close_session())
                except Exception:
                    pass

            # Cleanly cancel any pending tasks (poll loops, route tasks)
            pending = asyncio.all_tasks(self.loop)
            for t in pending:
                t.cancel()
            if pending:
                try:
                    self.loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                except Exception:
                    pass

            self.loop.close()

    def stop(self):
        """Gracefully stops the worker thread and event loop."""
        self._running = False
        if self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)
        self.wait(3000)

    # ================= Public thread-safe API =================

    def set_target_device(self, udid: Optional[str], is_ios17: bool = True):
        """Sets the selected device for commands."""
        self._active_udid = udid
        self._is_ios17 = is_ios17

    def spoof_location(self, latitude: float, longitude: float):
        """Queues a location simulation task on the event loop."""
        if self.loop and self.loop.is_running():
            asyncio.run_coroutine_threadsafe(
                self._async_spoof_location(latitude, longitude),
                self.loop
            )

    def reset_location(self):
        """Queues a clear simulation task on the event loop."""
        if self.loop and self.loop.is_running():
            asyncio.run_coroutine_threadsafe(
                self._async_reset_location(),
                self.loop
            )

    def refresh_devices_now(self):
        """Triggers an immediate device scan."""
        if self.loop and self.loop.is_running():
            asyncio.run_coroutine_threadsafe(
                self._async_poll_devices(),
                self.loop
            )

    def detect_real_location_now(self):
        """Triggers physical location detection."""
        if self.loop and self.loop.is_running():
            asyncio.run_coroutine_threadsafe(
                self._async_detect_real_location(),
                self.loop
            )

    # ================= Async Internal Tasks =================

    async def _async_detect_real_location(self):
        """Determines the user's actual physical location via IP geolocation."""
        try:
            loc = await asyncio.to_thread(get_actual_location)
            if loc:
                lat, lon, desc = loc
                self.sig_real_location_detected.emit(lat, lon, desc)
                self.sig_log.emit("INFO", f"Actual physical location detected: {desc} ({lat:.4f}, {lon:.4f})")
        except Exception as e:
            logger.debug(f"Failed to detect physical location: {e}")

    async def _poll_loop(self):
        """Periodically scans for connected iOS devices via usbmux."""
        while self._running:
            try:
                await self._async_poll_devices()
            except Exception as e:
                logger.debug(f"Device poll exception: {e}")
            await asyncio.sleep(self._poll_interval)

    async def _async_poll_devices(self):
        try:
            devices = await self.service.list_devices()
            current_udids = {d.udid for d in devices}

            # Check if active device got disconnected
            if self._active_udid and self._active_udid not in current_udids:
                self.sig_log.emit("WARN", f"Device {self._active_udid} was disconnected.")
                self.sig_device_disconnected.emit()
                self._active_udid = None
                await self.service.close_session()

            # Emit update if device list changed or newly discovered
            if current_udids != self._last_device_udids or (not self._active_udid and devices):
                self._last_device_udids = current_udids
                device_dicts = [d.to_dict() for d in devices]
                self.sig_devices_updated.emit(device_dicts)

                if devices and not self._active_udid:
                    # Auto-select first device
                    primary = devices[0]
                    self._active_udid = primary.udid
                    self._is_ios17 = primary.is_ios17_plus
                    self.sig_device_connected.emit(primary.to_dict())
                    self.sig_log.emit(
                        "INFO",
                        f"Detected {primary.name} ({primary.model}, iOS {primary.version}) over {primary.connection_type}"
                    )
                elif not devices:
                    self.sig_status_changed.emit("NO_DEVICE", "No iOS device connected")

        except Exception as e:
            logger.debug(f"Error in poll devices: {e}")

    async def _async_spoof_location(self, lat: float, lon: float):
        try:
            self.sig_status_changed.emit("CONNECTING", f"Sending location ({lat:.4f}, {lon:.4f})...")
            self.sig_log.emit("INFO", f"Connecting DVT session & spoofing location: ({lat:.6f}, {lon:.6f})")

            await self.service.set_location(
                latitude=lat,
                longitude=lon,
                udid=self._active_udid,
                is_ios17=self._is_ios17
            )

            self.sig_status_changed.emit("SPOOFING", f"Active GPS Spoof: ({lat:.4f}, {lon:.4f})")
            self.sig_spoof_success.emit(lat, lon)
            self.sig_log.emit("SUCCESS", f"System-wide GPS location updated to ({lat:.6f}, {lon:.6f})")

        except Exception as exc:
            title, msg, advice = diagnose_device_error(exc)
            self.sig_status_changed.emit("ERROR", f"Error: {title}")
            self.sig_log.emit("ERROR", f"{title}: {msg}")
            self.sig_error.emit(title, msg, advice)

    async def _async_reset_location(self):
        try:
            self.sig_status_changed.emit("CONNECTING", "Clearing location simulation...")
            self.sig_log.emit("INFO", "Clearing location simulation via DVT...")

            await self.service.clear_location()

            self.sig_status_changed.emit("CONNECTED", "Physical GPS Restored")
            self.sig_clear_success.emit()
            self.sig_log.emit("SUCCESS", "Simulation stopped. Real physical GPS restored on device.")

        except Exception as exc:
            title, msg, advice = diagnose_device_error(exc)
            self.sig_status_changed.emit("ERROR", f"Error: {title}")
            self.sig_log.emit("ERROR", f"Failed to reset location: {msg}")
            self.sig_error.emit(title, msg, advice)

    # ================= Route Simulation API =================

    def start_route_simulation(self, start_lat: float, start_lon: float, dest_lat: float, dest_lon: float, speed_kmh: float):
        """Starts turn-by-turn road route simulation between two points."""
        self._route_stopped = False
        self._route_paused = False
        if self.loop and self.loop.is_running():
            asyncio.run_coroutine_threadsafe(
                self._async_start_route(start_lat, start_lon, dest_lat, dest_lon, speed_kmh),
                self.loop
            )

    def start_gpx_simulation(self, gpx_filepath: str, speed_kmh: float):
        """Starts route playback along a GPX file track."""
        self._route_stopped = False
        self._route_paused = False
        if self.loop and self.loop.is_running():
            asyncio.run_coroutine_threadsafe(
                self._async_start_gpx(gpx_filepath, speed_kmh),
                self.loop
            )

    def pause_route_simulation(self):
        self._route_paused = True
        self.sig_log.emit("INFO", "Route simulation paused.")
        self.sig_status_changed.emit("SPOOFING", "Route Simulation Paused")

    def resume_route_simulation(self):
        self._route_paused = False
        self.sig_log.emit("INFO", "Route simulation resumed.")
        self.sig_status_changed.emit("SPOOFING", "Route Simulation Running")

    def stop_route_simulation(self):
        self._route_stopped = True
        self._route_paused = False
        if self._route_task and not self._route_task.done():
            self._route_task.cancel()
        self.sig_route_stopped.emit()
        self.sig_log.emit("INFO", "Route simulation stopped.")
        self.sig_status_changed.emit("CONNECTED", "Route Stopped")

    async def _async_start_route(self, s_lat: float, s_lon: float, d_lat: float, d_lon: float, speed_kmh: float):
        try:
            self.sig_log.emit("INFO", f"Calculating road route to ({d_lat:.4f}, {d_lon:.4f}) at {speed_kmh} km/h...")
            raw_pts = await asyncio.to_thread(fetch_osrm_route, s_lat, s_lon, d_lat, d_lon)
            self.sig_route_started.emit(raw_pts)

            timeline = build_interpolated_timeline(raw_pts, speed_kmh, tick_interval_sec=1.0)
            self._route_task = asyncio.create_task(self._async_run_route_loop(timeline, speed_kmh))
        except Exception as e:
            self.sig_log.emit("ERROR", f"Failed to initiate route: {e}")

    async def _async_start_gpx(self, filepath: str, speed_kmh: float):
        try:
            self.sig_log.emit("INFO", f"Loading GPX route from {filepath}...")
            raw_pts = await asyncio.to_thread(parse_gpx_file, filepath)
            if not raw_pts:
                self.sig_log.emit("ERROR", "No valid GPS track points found in GPX file.")
                return

            self.sig_route_started.emit(raw_pts)
            timeline = build_interpolated_timeline(raw_pts, speed_kmh, tick_interval_sec=1.0)
            self._route_task = asyncio.create_task(self._async_run_route_loop(timeline, speed_kmh))
        except Exception as e:
            self.sig_log.emit("ERROR", f"Failed to load GPX track: {e}")

    async def _async_run_route_loop(self, timeline: List[Tuple[float, float]], speed_kmh: float):
        total_steps = len(timeline)
        if total_steps == 0:
            return

        self.sig_log.emit("SUCCESS", f"Route simulation started ({total_steps} points, {speed_kmh} km/h)")
        self.sig_status_changed.emit("SPOOFING", f"Simulating Route ({speed_kmh} km/h)")

        for idx, (lat, lon) in enumerate(timeline):
            if self._route_stopped:
                break

            while self._route_paused and not self._route_stopped:
                await asyncio.sleep(0.5)

            if self._route_stopped:
                break

            # Send coordinate to device
            try:
                await self.service.set_location(
                    latitude=lat,
                    longitude=lon,
                    udid=self._active_udid,
                    is_ios17=self._is_ios17
                )
            except Exception as e:
                self.sig_log.emit("WARN", f"Location update warning: {e}")

            # Compute ETA
            remaining_seconds = total_steps - idx - 1
            mins, secs = divmod(remaining_seconds, 60)
            eta_str = f"{mins}m {secs}s" if mins > 0 else f"{secs}s"
            pct = ((idx + 1) / total_steps) * 100.0

            self.sig_route_progress.emit(lat, lon, pct, eta_str)
            await asyncio.sleep(1.0)

        if not self._route_stopped:
            self.sig_route_finished.emit()
            self.sig_log.emit("SUCCESS", "Route simulation completed! Arrived at destination.")
            self.sig_status_changed.emit("SPOOFING", "Arrived at Destination")
