"""Coleman Mach BLE Thermostat integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, DATA_COORDINATOR, DEFAULT_POLL_INTERVAL
from .coordinator import ColemanMachCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["climate", "sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Coleman Mach BLE from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    mac_address = entry.data["mac_address"]
    poll_interval = entry.data.get("poll_interval", DEFAULT_POLL_INTERVAL)

    coordinator = ColemanMachCoordinator(hass, mac_address, poll_interval)

    hass.data[DOMAIN][entry.entry_id] = {
        DATA_COORDINATOR: coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Fetch initial data in the background so HA boot isn't blocked
    entry.async_create_background_task(
        hass,
        coordinator.async_refresh(),
        f"coleman_mach_ble_first_refresh_{entry.entry_id}",
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
