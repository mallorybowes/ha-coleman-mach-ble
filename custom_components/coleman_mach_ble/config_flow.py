"""Config flow for Coleman Mach BLE integration."""

from __future__ import annotations

import re
import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN, DEFAULT_POLL_INTERVAL

_LOGGER = logging.getLogger(__name__)

MAC_REGEX = re.compile(r"^([0-9A-Fa-f]{2}[:\-]){5}[0-9A-Fa-f]{2}$")

STEP_USER_SCHEMA = vol.Schema({
    vol.Required("mac_address"): str,
    vol.Required("name", default="Coleman Mach AC"): str,
    vol.Required("poll_interval", default=DEFAULT_POLL_INTERVAL): vol.All(
        int, vol.Range(min=10, max=300)
    ),
})


class ColemanMachConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Coleman Mach BLE."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            mac = user_input["mac_address"].upper().replace("-", ":")
            if not MAC_REGEX.match(mac):
                errors["mac_address"] = "invalid_mac"
            else:
                await self.async_set_unique_id(mac)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=user_input["name"],
                    data={
                        "mac_address": mac,
                        "poll_interval": user_input["poll_interval"],
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_SCHEMA,
            errors=errors,
        )
