"""Custom Meteoblue Astronomy Seeing integration for Home Assistant."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_time_change

from .const import HOUR_TICK_SIGNAL
from .coordinator import MeteoblueSeeingCoordinator

PLATFORMS = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up all entities after the first download."""
    coordinator = MeteoblueSeeingCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Re-evaluate the already-downloaded forecast at each new local hour,
    # even though the web request happens only once every three hours.
    entry.async_on_unload(
        async_track_time_change(
            hass,
            lambda _now: async_dispatcher_send(
                hass, HOUR_TICK_SIGNAL.format(entry.entry_id)
            ),
            minute=0,
            second=5,
        )
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload cleanly."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
