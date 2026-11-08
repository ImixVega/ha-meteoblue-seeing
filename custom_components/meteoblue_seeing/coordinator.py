"""Download and coordinate the server-rendered meteoblue seeing table."""

from __future__ import annotations

from datetime import datetime, timedelta
import logging
from zoneinfo import ZoneInfo

from aiohttp import ClientError, ClientTimeout

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONF_TIMEZONE, DOMAIN, UPDATE_HOURS
from .parser import SeeingForecast, SeeingHour, SeeingParseError, parse_seeing_html

_LOGGER = logging.getLogger(__name__)


def seeing_url(latitude: float, longitude: float) -> str:
    """Build the same public page URL as meteoblue's location selector."""
    ns = "N" if latitude >= 0 else "S"
    ew = "E" if longitude >= 0 else "W"
    return (
        "https://www.meteoblue.com/pl/pogoda/outdoorsports/seeing/"
        f"{abs(latitude):.3f}{ns}{abs(longitude):.3f}{ew}"
    )


class MeteoblueSeeingCoordinator(DataUpdateCoordinator[SeeingForecast]):
    """One server request per update, shared by all entities."""

    def __init__(self, hass: HomeAssistant, entry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=entry,
            update_interval=timedelta(hours=UPDATE_HOURS),
        )
        self.entry = entry
        self.latitude = float(entry.data["latitude"])
        self.longitude = float(entry.data["longitude"])
        self.timezone = str(entry.data[CONF_TIMEZONE])
        self.zone = ZoneInfo(self.timezone)
        self.url = seeing_url(self.latitude, self.longitude)
        self.last_download: datetime | None = None

    async def _async_update_data(self) -> SeeingForecast:
        session = async_get_clientsession(self.hass)
        try:
            async with session.get(
                self.url,
                headers={
                    "User-Agent": "HomeAssistant-MeteoblueSeeing/0.1 (private noncommercial forecast viewer)",
                    "Accept": "text/html,application/xhtml+xml",
                    "Accept-Language": "pl,en;q=0.7",
                },
                timeout=ClientTimeout(total=30),
            ) as response:
                response.raise_for_status()
                html = await response.text()
            forecast = parse_seeing_html(html, self.timezone)
        except (ClientError, TimeoutError, UnicodeError, SeeingParseError) as err:
            raise UpdateFailed(f"Nie udało się pobrać prognozy meteoblue: {err}") from err
        self.last_download = datetime.now(tz=self.zone)
        return forecast

    def current_hour(self, now: datetime) -> SeeingHour | None:
        """Find the current local forecast hour; no network request."""
        if not self.data:
            return None
        now = now.astimezone(self.zone)
        for hour in self.data.hours:
            if hour.time <= now < hour.time + timedelta(hours=1):
                return hour
        return next((hour for hour in self.data.hours if hour.time > now), None)

    def day_hours(self, target_date, now: datetime) -> list[SeeingHour]:
        """Return only the remaining hours of a calendar day."""
        if not self.data:
            return []
        now = now.astimezone(self.zone)
        return [r for r in self.data.hours if r.time.date() == target_date and r.time + timedelta(hours=1) > now]
