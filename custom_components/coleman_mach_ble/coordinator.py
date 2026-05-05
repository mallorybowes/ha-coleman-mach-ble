"""Data coordinator for Coleman Mach BLE thermostat."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import timedelta

from bleak import BleakClient
from bleak_retry_connector import establish_connection, BleakNotFoundError

from homeassistant.components import bluetooth
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

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


@dataclass
class ColemanMachData:
    room_temperature: float | None = None
    set_point: int | None = None
    mode_operation: str | None = None
    available_modes: int | None = None
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
        d.unit_id = _parse_string(v, 3)

    if (v := raw_data.get(CHAR_AVAILABLE_MODE)) and len(v) >= 1:
        d.available_modes = v[0]

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


async def write_set_point(hass: HomeAssistant, mac_address: str, value: int) -> None:
    device = _get_ble_device(hass, mac_address)
    try:
        client = await establish_connection(BleakClient, device, mac_address)
    except BleakNotFoundError as err:
        raise UpdateFailed(f"Device {mac_address} not found: {err}") from err
    except Exception as err:
        raise UpdateFailed(f"BLE connection failed: {err}") from err

    try:
        await client.write_gatt_char(CHAR_SET_POINT, bytes([value]))
        _LOGGER.debug("Wrote set_point=%d to %s", value, mac_address)
    finally:
        await client.disconnect()


async def write_mode(hass: HomeAssistant, mac_address: str, mode: str) -> None:
    device = _get_ble_device(hass, mac_address)
    try:
        client = await establish_connection(BleakClient, device, mac_address)
    except BleakNotFoundError as err:
        raise UpdateFailed(f"Device {mac_address} not found: {err}") from err
    except Exception as err:
        raise UpdateFailed(f"BLE connection failed: {err}") from err

    try:
        await client.write_gatt_char(CHAR_MODE_OPERATION, mode.encode("ascii"))
        _LOGGER.debug("Wrote mode=%r to %s", mode, mac_address)
    finally:
        await client.disconnect()


class ColemanMachCoordinator(DataUpdateCoordinator[ColemanMachData]):
    """Coordinator that polls the Coleman Mach BLE thermostat."""

    def __init__(self, hass: HomeAssistant, mac_address: str, interval: int) -> None:
        self.mac_address = mac_address
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{mac_address}",
            update_interval=timedelta(seconds=interval),
        )

    async def _async_update_data(self) -> ColemanMachData:
        return await _read_device(self.hass, self.mac_address)
