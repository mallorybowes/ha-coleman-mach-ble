"""Data coordinator for Coleman Mach BLE thermostat."""

from __future__ import annotations

import asyncio
import logging
import os
import traceback
from dataclasses import dataclass
from datetime import timedelta

from bleak import BleakClient
from bleak_retry_connector import establish_connection, BleakNotFoundError

from homeassistant.components import bluetooth
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    CHAR_ROOM_TEMPERATURE,
    CHAR_ZONE_ID,
    CHAR_MODE_OPERATION,
    CHAR_AVAILABLE_MODE,
    CHAR_SET_POINT,
    CHAR_CELSIUS,
    CHAR_UNIT_ID,
    READ_ORDER,
)

_LOGGER = logging.getLogger(__name__)

BLE_READ_TIMEOUT = 10.0  # seconds

# The AC's BLE module intermittently refuses a connection for a single poll.
# Ride out short blips instead of flipping the entity to unavailable on the
# first miss; a real outage still surfaces after MAX_CONSECUTIVE_FAILURES polls.
# Measured: 34 failures over 16h, every one an isolated single, never back to
# back. 2 is enough to absorb that, and keeps time-to-unavailable at ~4 min on
# the 120s poll cycle rather than the ~6 min a threshold of 3 would give.
MAX_CONSECUTIVE_FAILURES = 2

# Failures are rare (~1/hour) and HA keeps no log file here, so each one is
# appended to this file in the config dir with BLE context for later diagnosis.
FAILURE_LOG_NAME = "coleman_mach_ble_failures.log"

# A sustained outage keeps polling and failing every ~33s, so the file must be
# bounded: rotate once at 1 MB, giving a hard ceiling of ~2 MB across both.
FAILURE_LOG_MAX_BYTES = 1_000_000


def _append_failure_log(path: str, text: str) -> bool:
    """Append a failure record. Runs in the executor — never on the event loop."""
    try:
        if os.path.exists(path) and os.path.getsize(path) + len(text) > FAILURE_LOG_MAX_BYTES:
            os.replace(path, f"{path}.1")
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(text)
        return True
    except OSError as err:  # diagnostics must never break the poll
        _LOGGER.warning("Could not write %s: %s", path, err)
        return False


@dataclass
class ColemanMachData:
    room_temperature: float | None = None
    set_point: int | None = None
    mode_operation: str | None = None
    available_modes: bytes | None = None
    is_celsius: bool = False
    zone_name: str | None = None
    unit_id: str | None = None


def _parse_string(raw: bytes, max_len: int) -> str:
    try:
        return raw[:max_len].rstrip(b"\x00").decode("ascii", errors="replace").strip()
    except Exception:
        return ""


def _parse_data(raw_data: dict[str, bytes]) -> ColemanMachData:
    d = ColemanMachData()

    if (v := raw_data.get(CHAR_CELSIUS)) and len(v) >= 1:
        d.is_celsius = (v[0] == 1)

    if (v := raw_data.get(CHAR_SET_POINT)) and len(v) >= 1:
        d.set_point = v[0]

    if (v := raw_data.get(CHAR_ROOM_TEMPERATURE)) and len(v) >= 1:
        d.room_temperature = float(v[0])

    if (v := raw_data.get(CHAR_MODE_OPERATION)):
        d.mode_operation = _parse_string(v, 14)

    if (v := raw_data.get(CHAR_ZONE_ID)):
        d.zone_name = _parse_string(v, 7)

    if (v := raw_data.get(CHAR_UNIT_ID)):
        # UNIT_ID is opaque binary, not ASCII (unlike ZONE_ID / MODE_OPERATION).
        # On the test unit the 3 bytes 60 58 2A ASCII-decode to garbage ("`X*");
        # uppercase hex displays them losslessly. The field's true semantics and
        # length are unconfirmed across hardware — this only renders the bytes
        # faithfully, it does not assert meaning. (Width 3 mirrors the original
        # read; widen if other units return longer identifiers.)
        d.unit_id = v[:3].hex().upper()

    if (v := raw_data.get(CHAR_AVAILABLE_MODE)):
        # Keep the full positional array; see modes.py for interpretation.
        # (Previously only v[0] was stored, discarding capability data.)
        d.available_modes = bytes(v)

    return d


def _get_ble_device(hass: HomeAssistant, mac_address: str):
    device = bluetooth.async_ble_device_from_address(hass, mac_address, connectable=True)
    if device is None:
        raise UpdateFailed(
            f"Device {mac_address} not found in BLE scan — is the AC powered on and in range?"
        )
    return device


async def _read_device(hass: HomeAssistant, mac_address: str) -> ColemanMachData:
    device = _get_ble_device(hass, mac_address)
    _LOGGER.info("Connecting to %s (rssi=%s)", mac_address, getattr(device, 'rssi', 'unknown'))
    raw_data: dict[str, bytes] = {}

    try:
        client = await establish_connection(BleakClient, device, mac_address)
    except BleakNotFoundError as err:
        raise UpdateFailed(f"Device {mac_address} not found: {err}") from err
    except Exception as err:
        raise UpdateFailed(f"BLE connection failed: {err}") from err
    _LOGGER.info("Connected to %s", mac_address)

    try:
        for char_uuid in READ_ORDER:
            try:
                value = await asyncio.wait_for(
                    client.read_gatt_char(char_uuid),
                    timeout=BLE_READ_TIMEOUT,
                )
                raw_data[char_uuid] = bytes(value)
                _LOGGER.debug("Read %s: %s", char_uuid, bytes(value).hex())
            except asyncio.TimeoutError:
                _LOGGER.warning("Timeout reading characteristic %s", char_uuid)
            except Exception as err:
                _LOGGER.warning("Error reading characteristic %s: %s", char_uuid, err)
    finally:
        await client.disconnect()

    if not raw_data:
        raise UpdateFailed("No data received from device")

    return _parse_data(raw_data)


class ColemanMachCoordinator(DataUpdateCoordinator[ColemanMachData]):
    """Coordinator that polls the Coleman Mach BLE thermostat."""

    def __init__(self, hass: HomeAssistant, mac_address: str, interval: int) -> None:
        self.mac_address = mac_address
        self._ble_lock = asyncio.Lock()
        self._consecutive_failures = 0
        self._failure_log_path = hass.config.path(FAILURE_LOG_NAME)
        # Surfaced by the diagnostic sensor so the failure rate stays visible in
        # HA (and the recorder) even though tolerated blips no longer show up as
        # entity unavailability.
        self.failure_count = 0
        self.last_failure: str | None = None
        self.last_failure_error: str | None = None
        self.log_write_ok = True
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{mac_address}",
            update_interval=timedelta(seconds=interval),
        )

    async def _async_update_data(self) -> ColemanMachData:
        async with self._ble_lock:
            try:
                data = await _read_device(self.hass, self.mac_address)
            except Exception as err:
                self._consecutive_failures += 1
                await self._record_failure(err)
                if self.data is not None and self._consecutive_failures < MAX_CONSECUTIVE_FAILURES:
                    _LOGGER.warning(
                        "Poll %d/%d failed for %s (%s) — keeping last known data",
                        self._consecutive_failures,
                        MAX_CONSECUTIVE_FAILURES,
                        self.mac_address,
                        err,
                    )
                    return self.data
                raise

        if self._consecutive_failures:
            _LOGGER.warning(
                "Recovered after %d consecutive failure(s) for %s",
                self._consecutive_failures,
                self.mac_address,
            )
            self._consecutive_failures = 0
        return data

    async def _record_failure(self, err: Exception) -> None:
        """Record the real exception plus BLE context for later diagnosis."""
        try:
            self.failure_count += 1
            self.last_failure = dt_util.utcnow().isoformat()
            self.last_failure_error = f"{type(err).__name__}: {err}"

            service_info = bluetooth.async_last_service_info(
                self.hass, self.mac_address, connectable=True
            )
            in_scan = (
                bluetooth.async_ble_device_from_address(
                    self.hass, self.mac_address, connectable=True
                )
                is not None
            )
            header = (
                f"{self.last_failure} "
                f"attempt={self._consecutive_failures}/{MAX_CONSECUTIVE_FAILURES} "
                f"total={self.failure_count} "
                f"in_scan={in_scan} "
                f"rssi={getattr(service_info, 'rssi', None)} "
                f"advertised={getattr(service_info, 'time', None)}\n"
                f"  {self.last_failure_error}\n"
            )
            # Full traceback only for the first failure of a streak. During a
            # sustained outage the rest are the same exception every ~33s, and
            # repeating the traceback would bury the interesting first record.
            if self._consecutive_failures == 1:
                tb = traceback.format_exception(type(err), err, err.__traceback__)
                record = header + "".join(
                    f"  {line}\n" for line in "".join(tb).rstrip().splitlines()
                ) + "\n"
                _LOGGER.warning("BLE poll failure for %s:\n%s", self.mac_address, record)
            else:
                record = header
                _LOGGER.warning(
                    "BLE poll failure %d for %s: %s",
                    self._consecutive_failures,
                    self.mac_address,
                    self.last_failure_error,
                )

            self.log_write_ok = await self.hass.async_add_executor_job(
                _append_failure_log, self._failure_log_path, record
            )
        except Exception:  # diagnostics must never mask the original failure
            self.log_write_ok = False
            _LOGGER.exception("Could not record BLE failure diagnostics")

    async def write_set_point(self, value: int) -> None:
        async with self._ble_lock:
            device = _get_ble_device(self.hass, self.mac_address)
            try:
                client = await establish_connection(BleakClient, device, self.mac_address)
            except BleakNotFoundError as err:
                raise UpdateFailed(f"Device {self.mac_address} not found: {err}") from err
            except Exception as err:
                raise UpdateFailed(f"BLE connection failed: {err}") from err
            try:
                await client.write_gatt_char(CHAR_SET_POINT, bytes([value]))
                _LOGGER.debug("Wrote set_point=%d to %s", value, self.mac_address)
            finally:
                await client.disconnect()

    async def write_mode(self, mode: str) -> None:
        async with self._ble_lock:
            device = _get_ble_device(self.hass, self.mac_address)
            try:
                client = await establish_connection(BleakClient, device, self.mac_address)
            except BleakNotFoundError as err:
                raise UpdateFailed(f"Device {self.mac_address} not found: {err}") from err
            except Exception as err:
                raise UpdateFailed(f"BLE connection failed: {err}") from err
            try:
                await client.write_gatt_char(CHAR_MODE_OPERATION, mode.encode("ascii"))
                _LOGGER.debug("Wrote mode=%r to %s", mode, self.mac_address)
            finally:
                await client.disconnect()
