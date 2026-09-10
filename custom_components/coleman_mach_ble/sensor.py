"""Sensor entities for Coleman Mach BLE thermostat."""

from __future__ import annotations

import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.helpers.entity import EntityCategory
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
        ColemanMachPollFailureSensor(coordinator, entry),
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


class ColemanMachPollFailureSensor(_ColemanMachSensor):
    """Cumulative BLE poll failures.

    Tolerated blips no longer show up as entity unavailability, so this is what
    keeps the failure rate visible — in HA and in the recorder, not only in the
    capture file. It deliberately overrides `available`: a CoordinatorEntity
    would go unavailable exactly when the failures are happening, which is the
    one moment this needs to keep reporting.
    """

    _attr_name = "Poll Failures"
    _attr_icon = "mdi:bluetooth-off"
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: ColemanMachCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{coordinator.mac_address}_poll_failures"

    @property
    def available(self) -> bool:
        return True

    @property
    def native_value(self) -> int:
        return self.coordinator.failure_count

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        return {
            "consecutive_failures": self.coordinator._consecutive_failures,
            "last_failure": self.coordinator.last_failure,
            "last_error": self.coordinator.last_failure_error,
            # False means the capture file stopped being written — otherwise
            # that would fail silently and take the failure record with it.
            "capture_log_ok": self.coordinator.log_write_ok,
        }
