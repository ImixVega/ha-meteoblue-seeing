"""UI setup for the custom Meteoblue Seeing integration."""

from __future__ import annotations

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE, CONF_NAME
from homeassistant.data_entry_flow import FlowResult

from .const import CONF_TIMEZONE, DEFAULT_NAME, DOMAIN


class MeteoblueSeeingConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Configure location and forecast timezone from the HA UI."""

    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                ZoneInfo(user_input[CONF_TIMEZONE])
            except (ZoneInfoNotFoundError, ValueError, KeyError):
                errors[CONF_TIMEZONE] = "invalid_timezone"
            else:
                lat = round(float(user_input[CONF_LATITUDE]), 3)
                lon = round(float(user_input[CONF_LONGITUDE]), 3)
                await self.async_set_unique_id(f"{DOMAIN}_{lat:.3f}_{lon:.3f}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=user_input[CONF_NAME].strip() or DEFAULT_NAME,
                    data={
                        CONF_NAME: user_input[CONF_NAME].strip() or DEFAULT_NAME,
                        CONF_LATITUDE: lat,
                        CONF_LONGITUDE: lon,
                        CONF_TIMEZONE: user_input[CONF_TIMEZONE],
                    },
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
                vol.Required(CONF_LATITUDE, default=round(self.hass.config.latitude, 3)): vol.All(
                    vol.Coerce(float), vol.Range(min=-90, max=90)
                ),
                vol.Required(CONF_LONGITUDE, default=round(self.hass.config.longitude, 3)): vol.All(
                    vol.Coerce(float), vol.Range(min=-180, max=180)
                ),
                vol.Required(CONF_TIMEZONE, default=self.hass.config.time_zone): str,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
