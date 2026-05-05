"""Sensor entities for Coleman Mach BLE thermostat."""

from __future__ import annotations

import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.config_entries import ConfigEntry

from .const import DOMAIN, DATA_COORDINATOR
from .coordinator import ColemanMachCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: ColemanMachCoordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    async_add_entities([
        ColemanMachZoneSensor(coordinator, entry),
        ColemanMachUnitIDSensor(coordinator, entry),
    ])


class _ColemanMachSensor(CoordinatorEntity[ColemanMachCoordinator], SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator: ColemanMachCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.mac_address)},
        }


class ColemanMachZoneSensor(_ColemanMachSensor):
    _attr_name = "Zone"
    _attr_icon = "mdi:map-marker"

    def __init__(self, coordinator: ColemanMachCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{coordinator.mac_address}_zone"

    @property
    def native_value(self) -> str | None:
        if not self.coordinator.data:
            return None
        return self.coordinator.data.zone_name or None


class ColemanMachUnitIDSensor(_ColemanMachSensor):
    _attr_name = "Unit ID"
    _attr_icon = "mdi:identifier"

    def __init__(self, coordinator: ColemanMachCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{coordinator.mac_address}_unit_id"

    @property
    def native_value(self) -> str | None:
        if not self.coordinator.data:
            return None
        return self.coordinator.data.unit_id or None
