"""Climate entity for Coleman Mach BLE thermostat."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
    HVACAction,
)
from homeassistant.const import UnitOfTemperature, ATTR_TEMPERATURE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.config_entries import ConfigEntry

from .const import (
    DOMAIN,
    DATA_COORDINATOR,
    COOL_MODES,
    FAN_MODES,
    HEAT_MODES,
    OPTION_EXCLUDED_MODES,
)
from .coordinator import ColemanMachCoordinator
from .modes import resolve_preset_modes, choose_write_mode

_LOGGER = logging.getLogger(__name__)


def _mode_to_hvac(mode: str | None) -> HVACMode:
    if not mode or mode == "OFF":
        return HVACMode.OFF
    if mode in COOL_MODES:
        return HVACMode.COOL
    if mode in HEAT_MODES:
        return HVACMode.HEAT
    if mode in FAN_MODES:
        return HVACMode.FAN_ONLY
    return HVACMode.OFF


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: ColemanMachCoordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    async_add_entities([ColemanMachClimate(coordinator, entry)])


class ColemanMachClimate(CoordinatorEntity[ColemanMachCoordinator], ClimateEntity):
    """Coleman Mach BLE thermostat climate entity."""

    _attr_has_entity_name = True
    _attr_name = None  # use device name

    # Supported features
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.PRESET_MODE
    )

    _attr_target_temperature_step = 1.0
    _attr_min_temp = 60.0   # °F or °C — will be overridden by unit
    _attr_max_temp = 90.0

    def __init__(
        self,
        coordinator: ColemanMachCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{coordinator.mac_address}_climate"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.mac_address)},
            "name": entry.title,
            "manufacturer": "Coleman Mach / ICM Controls",
            "model": "9430-720 BLE Control Assembly",
        }

    def _excluded_modes(self) -> set[str]:
        return set(self._entry.options.get(OPTION_EXCLUDED_MODES, []))

    @property
    def preset_modes(self) -> list[str]:
        available = (
            self.coordinator.data.available_modes if self.coordinator.data else None
        )
        return resolve_preset_modes(available, self._excluded_modes())

    @property
    def hvac_modes(self) -> list[HVACMode]:
        presets = self.preset_modes
        modes = [HVACMode.OFF]
        if any(m in COOL_MODES for m in presets):
            modes.append(HVACMode.COOL)
        if any(m in HEAT_MODES for m in presets):
            modes.append(HVACMode.HEAT)
        if any(m in FAN_MODES for m in presets):
            modes.append(HVACMode.FAN_ONLY)
        return modes

    @property
    def temperature_unit(self) -> str:
        if self.coordinator.data and self.coordinator.data.is_celsius:
            return UnitOfTemperature.CELSIUS
        return UnitOfTemperature.FAHRENHEIT

    @property
    def current_temperature(self) -> float | None:
        if not self.coordinator.data:
            return None
        return self.coordinator.data.room_temperature

    @property
    def target_temperature(self) -> float | None:
        if not self.coordinator.data:
            return None
        return float(self.coordinator.data.set_point) if self.coordinator.data.set_point is not None else None

    @property
    def hvac_mode(self) -> HVACMode:
        if not self.coordinator.data:
            return HVACMode.OFF
        return _mode_to_hvac(self.coordinator.data.mode_operation)

    @property
    def hvac_action(self) -> HVACAction | None:
        mode = self.hvac_mode
        if mode == HVACMode.COOL:
            return HVACAction.COOLING
        if mode == HVACMode.HEAT:
            return HVACAction.HEATING
        if mode == HVACMode.FAN_ONLY:
            return HVACAction.FAN
        return HVACAction.IDLE

    @property
    def preset_mode(self) -> str | None:
        if not self.coordinator.data:
            return None
        return self.coordinator.data.mode_operation

    @property
    def min_temp(self) -> float:
        if self.coordinator.data and self.coordinator.data.is_celsius:
            return 16.0
        return 60.0

    @property
    def max_temp(self) -> float:
        if self.coordinator.data and self.coordinator.data.is_celsius:
            return 32.0
        return 90.0

    async def async_set_temperature(self, **kwargs: Any) -> None:
        temp = kwargs.get(ATTR_TEMPERATURE)
        if temp is None:
            return
        raw_value = int(round(temp))
        await self.coordinator.write_set_point(raw_value)
        await self.coordinator.async_request_refresh()

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        if hvac_mode == HVACMode.OFF:
            await self.coordinator.write_mode("OFF")
            await self.coordinator.async_request_refresh()
            return

        category = {
            HVACMode.COOL: COOL_MODES,
            HVACMode.HEAT: HEAT_MODES,
            HVACMode.FAN_ONLY: FAN_MODES,
        }.get(hvac_mode)
        if category is None:
            return

        new_mode = choose_write_mode(category, self.preset_modes, self.preset_mode)
        if new_mode is None:
            _LOGGER.warning("No available mode for HVAC mode %s", hvac_mode)
            return

        await self.coordinator.write_mode(new_mode)
        await self.coordinator.async_request_refresh()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        if preset_mode not in self.preset_modes:
            _LOGGER.warning("Unavailable preset mode: %s", preset_mode)
            return
        await self.coordinator.write_mode(preset_mode)
        await self.coordinator.async_request_refresh()
