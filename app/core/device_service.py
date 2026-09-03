"""
Core Device Service & Session Manager for iOS 17+ Location Simulation.
Manages usbmux detection, RSD tunnel creation, and persistent DVT location sessions.
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
from packaging.version import Version

from pymobiledevice3 import usbmux
from pymobiledevice3.lockdown import create_using_usbmux
from pymobiledevice3.remote.rsd_tunnel import PreferredRsdTunnel
from pymobiledevice3.services.dvt.instruments.dvt_provider import DvtProvider
from pymobiledevice3.services.dvt.instruments.location_simulation import LocationSimulation
from pymobiledevice3.services.simulate_location import DtSimulateLocation

logger = logging.getLogger("DeviceService")


class DeviceInfo:
    def __init__(
        self,
        udid: str,
        name: str = "iOS Device",
        version: str = "Unknown",
        model: str = "iPhone",
        connection_type: str = "USB",
        is_ios17_plus: bool = True,
        battery_level: Optional[int] = None,
    ):
        self.udid = udid
        self.name = name
        self.version = version
        self.model = model
        self.connection_type = connection_type
        self.is_ios17_plus = is_ios17_plus
        self.battery_level = battery_level

    def to_dict(self) -> Dict[str, Any]:
        return {
            "udid": self.udid,
            "name": self.name,
            "version": self.version,
            "model": self.model,
            "connection_type": self.connection_type,
            "is_ios17_plus": self.is_ios17_plus,
            "battery_level": self.battery_level,
        }


class DeviceService:
    """
    Manages discovery and persistent DVT location sessions.
    Maintains an active RSD tunnel and DVT channel so successive
    coordinate updates happen instantaneously without reconnecting.
    """

    def __init__(self):
        self.active_udid: Optional[str] = None
        self.active_device_info: Optional[DeviceInfo] = None

        # iOS 17+ Session objects
        self.tunnel: Optional[PreferredRsdTunnel] = None
        self.rsd = None
        self.dvt_provider: Optional[DvtProvider] = None
        self.loc_simulation: Optional[LocationSimulation] = None

        # iOS < 17 fallback objects
        self.lockdown = None
        self.legacy_loc_sim: Optional[DtSimulateLocation] = None

        self.is_spoofing: bool = False
        self.current_coords: Optional[tuple] = None
        self.natural_drift_enabled: bool = False
        self._drift_task: Optional[asyncio.Task] = None

    async def list_devices(self) -> List[DeviceInfo]:
        """Scans usbmux for connected iOS devices and queries their metadata."""
        mux_devices = await usbmux.list_devices()
        result: List[DeviceInfo] = []

        for mux_dev in mux_devices:
            # We focus on physical USB or network devices
            udid = mux_dev.serial
            conn_type = "USB" if mux_dev.is_usb else "Network"

            # Attempt a quick lockdown probe to query device name, battery & iOS version
            name = "iOS Device"
            version_str = "17.0"
            model = "iPhone"
            is_ios17 = True
            battery_pct = None

            try:
                # autopair=True allows fetching properties if already trusted
                async with await create_using_usbmux(serial=udid, autopair=True) as ld:
                    name = getattr(ld, "device_name", name) or name
                    version_str = getattr(ld, "product_version", version_str) or version_str
                    model = getattr(ld, "product_type", model) or model
                    try:
                        batt_dict = await ld.get_value(domain="com.apple.mobile.battery")
                        if batt_dict and "BatteryCurrentCapacity" in batt_dict:
                            battery_pct = int(batt_dict["BatteryCurrentCapacity"])
                    except Exception:
                        pass

                    try:
                        is_ios17 = Version(version_str) >= Version("17.0")
                    except Exception:
                        is_ios17 = True
            except Exception as e:
                logger.debug(f"Could not read full lockdown info for {udid}: {e}")

            info = DeviceInfo(
                udid=udid,
                name=name,
                version=version_str,
                model=model,
                connection_type=conn_type,
                is_ios17_plus=is_ios17,
                battery_level=battery_pct,
            )
            result.append(info)

        return result

    async def ensure_session(self, udid: Optional[str] = None, is_ios17: bool = True) -> None:
        """
        Ensures that an active location simulation session is established.
        If a session is already active for the requested device, it is reused.
        """
        if self.loc_simulation is not None and self.active_udid == udid:
            # Session is already healthy and active
            return

        # Close any previous session
        await self.close_session()

        self.active_udid = udid

        if is_ios17:
            logger.info(f"Opening iOS 17+ RSD Tunnel for device {udid or 'default'}...")
            # PreferredRsdTunnel automatically uses NativeRemotedTunnel on macOS (piggybacks remoted, no sudo)
            self.tunnel = PreferredRsdTunnel(serial=udid, prefer_native=True)
            self.rsd = await self.tunnel.aopen()

            logger.info("Opening DVT DTX instruments provider...")
            self.dvt_provider = DvtProvider(self.rsd)
            await self.dvt_provider.__aenter__()

            logger.info("Connecting LocationSimulation DTX channel...")
            self.loc_simulation = LocationSimulation(self.dvt_provider)
            await self.loc_simulation.__aenter__()
            logger.info("iOS 17+ Location Simulation session ready.")
        else:
            logger.info(f"Connecting legacy lockdown service for device {udid or 'default'} (iOS < 17)...")
            self.lockdown = await create_using_usbmux(serial=udid)
            self.legacy_loc_sim = DtSimulateLocation(self.lockdown)
            logger.info("Legacy Location Simulation session ready.")

    async def set_location(self, latitude: float, longitude: float, udid: Optional[str] = None, is_ios17: bool = True) -> None:
        """
        Simulates the device location at the given coordinates.
        Reuses the active session for near-instant updates.
        """
        await self.ensure_session(udid=udid, is_ios17=is_ios17)

        if is_ios17 and self.loc_simulation:
            await self.loc_simulation.set(latitude, longitude)
        elif self.legacy_loc_sim:
            await self.legacy_loc_sim.set(latitude, longitude)
        else:
            raise RuntimeError("No active location simulation session could be established.")

        self.is_spoofing = True
        self.current_coords = (latitude, longitude)
        logger.info(f"Simulated location set to: ({latitude}, {longitude})")

        if self.natural_drift_enabled:
            if self._drift_task and not self._drift_task.done():
                self._drift_task.cancel()
            self._drift_task = asyncio.create_task(self._drift_loop())

    def set_natural_drift(self, enabled: bool):
        """Enables or disables realistic 0.8m micro-drift when stationary."""
        self.natural_drift_enabled = enabled
        if not enabled and self._drift_task and not self._drift_task.done():
            self._drift_task.cancel()
            self._drift_task = None
        elif enabled and self.is_spoofing and (not self._drift_task or self._drift_task.done()):
            self._drift_task = asyncio.create_task(self._drift_loop())

    async def _drift_loop(self):
        """Periodically applies subtle satellite jitter (~0.8m) to mimic real GPS chips."""
        import random
        try:
            while self.is_spoofing and self.natural_drift_enabled:
                await asyncio.sleep(2.5)
                if not self.is_spoofing or not self.current_coords:
                    break
                base_lat, base_lon = self.current_coords
                # Micro-jitter within 0.000007 degrees (~0.78 meters)
                drift_lat = base_lat + random.uniform(-0.000007, 0.000007)
                drift_lon = base_lon + random.uniform(-0.000007, 0.000007)
                if self.loc_simulation:
                    await self.loc_simulation.set(drift_lat, drift_lon)
                elif self.legacy_loc_sim:
                    await self.legacy_loc_sim.set(drift_lat, drift_lon)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.debug(f"Natural drift loop error: {e}")

    async def clear_location(self) -> None:
        """
        Stops location simulation and restores the device's real physical GPS.
        """
        if self._drift_task and not self._drift_task.done():
            self._drift_task.cancel()
            self._drift_task = None

        if self.loc_simulation:
            try:
                await self.loc_simulation.clear()
            except Exception as e:
                logger.warning(f"Error clearing DVT location simulation: {e}")
        elif self.legacy_loc_sim:
            try:
                await self.legacy_loc_sim.clear()
            except Exception as e:
                logger.warning(f"Error clearing legacy location simulation: {e}")

        self.is_spoofing = False
        self.current_coords = None
        logger.info("Simulated location cleared. Physical GPS restored.")

    async def emergency_kill(self) -> None:
        """Immediate failsafe kill switch: clears simulation, closes tunnels, restores physical GPS."""
        logger.warning("EMERGENCY KILL SWITCH TRIGGERED!")
        if self._drift_task and not self._drift_task.done():
            self._drift_task.cancel()
            self._drift_task = None
        if self.loc_simulation:
            try:
                await self.loc_simulation.clear()
            except Exception:
                pass
        if self.legacy_loc_sim:
            try:
                await self.legacy_loc_sim.clear()
            except Exception:
                pass
        await self.close_session()

    async def close_session(self) -> None:
        """Gracefully closes all channels and tunnels."""
        if self._drift_task and not self._drift_task.done():
            self._drift_task.cancel()
            self._drift_task = None

        if self.loc_simulation is not None:
            try:
                await self.loc_simulation.__aexit__(None, None, None)
            except Exception:
                pass
            self.loc_simulation = None

        if self.dvt_provider is not None:
            try:
                await self.dvt_provider.__aexit__(None, None, None)
            except Exception:
                pass
            self.dvt_provider = None

        if self.tunnel is not None:
            try:
                await self.tunnel.aclose()
            except Exception:
                pass
            self.tunnel = None
            self.rsd = None

        if self.lockdown is not None:
            try:
                await self.lockdown.close()
            except Exception:
                pass
            self.lockdown = None
            self.legacy_loc_sim = None

        self.active_udid = None
        self.is_spoofing = False
        logger.info("Location simulation session closed.")
