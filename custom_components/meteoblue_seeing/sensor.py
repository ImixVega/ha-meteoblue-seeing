"""Seeing and hourly forecast entities for Home Assistant."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfSpeed, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN, HOUR_TICK_SIGNAL
from .coordinator import MeteoblueSeeingCoordinator


@dataclass(frozen=True, kw_only=True)
class SeeingSensorDescription(SensorEntityDescription):
    """Sensor mapped to a field in the HTML hourly forecast."""


SENSOR_DESCRIPTIONS: tuple[SeeingSensorDescription, ...] = (
    SeeingSensorDescription(key="seeing_arcsec", name="Seeing (arcsec)", native_unit_of_measurement="arcsec", icon="mdi:telescope", suggested_display_precision=2),
    SeeingSensorDescription(key="seeing_1", name="Seeing Index 1", icon="mdi:star-four-points"),
    SeeingSensorDescription(key="seeing_2", name="Seeing Index 2", icon="mdi:star-four-points-outline"),
    SeeingSensorDescription(key="cloud_low", name="Chmury niskie", native_unit_of_measurement=PERCENTAGE, icon="mdi:cloud-outline"),
    SeeingSensorDescription(key="cloud_mid", name="Chmury średnie", native_unit_of_measurement=PERCENTAGE, icon="mdi:cloud"),
    SeeingSensorDescription(key="cloud_high", name="Chmury wysokie", native_unit_of_measurement=PERCENTAGE, icon="mdi:weather-cloudy"),
    SeeingSensorDescription(key="jetstream", name="Jet stream", native_unit_of_measurement=UnitOfSpeed.METERS_PER_SECOND, device_class=SensorDeviceClass.WIND_SPEED, icon="mdi:weather-windy"),
    SeeingSensorDescription(key="badlayer_bottom", name="Warstwa turbulencji dolna", native_unit_of_measurement="km", icon="mdi:arrow-collapse-down", suggested_display_precision=1),
    SeeingSensorDescription(key="badlayer_top", name="Warstwa turbulencji górna", native_unit_of_measurement="km", icon="mdi:arrow-collapse-up", suggested_display_precision=1),
    SeeingSensorDescription(key="badlayer_gradient", name="Gradient warstwy turbulencji", native_unit_of_measurement="K/100m", icon="mdi:chart-bell-curve", suggested_display_precision=1),
    SeeingSensorDescription(key="temperature", name="Temperatura przy gruncie", native_unit_of_measurement=UnitOfTemperature.CELSIUS, device_class=SensorDeviceClass.TEMPERATURE, icon="mdi:thermometer"),
    SeeingSensorDescription(key="humidity", name="Wilgotność przy gruncie", native_unit_of_measurement=PERCENTAGE, device_class=SensorDeviceClass.HUMIDITY, icon="mdi:water-percent"),
)


def _device_info(coordinator: MeteoblueSeeingCoordinator) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, coordinator.entry.entry_id)},
        name=coordinator.entry.title,
        manufacturer="meteoblue",
        model="Astronomy Seeing (web)",
        configuration_url=coordinator.url,
    )


class _BaseSeeingSensor(CoordinatorEntity[MeteoblueSeeingCoordinator], SensorEntity):
    """Shared device info and the hourly clock refresh signal."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: MeteoblueSeeingCoordinator, key: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.unique_id}_{key}"
        self._attr_device_info = _device_info(coordinator)

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                HOUR_TICK_SIGNAL.format(self.coordinator.entry.entry_id),
                self.async_write_ha_state,
            )
        )

    def _now(self) -> datetime:
        return dt_util.now().astimezone(self.coordinator.zone)


class MeteoblueCurrentSensor(_BaseSeeingSensor):
    """Value for the current hour (computed from the cached forecast)."""

    def __init__(self, coordinator: MeteoblueSeeingCoordinator, description: SeeingSensorDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self):
        hour = self.coordinator.current_hour(self._now())
        if hour is None:
            return None
        return getattr(hour, self.entity_description.key)

    @property
    def extra_state_attributes(self) -> dict:
        hour = self.coordinator.current_hour(self._now())
        return {"forecast_hour": hour.time.isoformat()} if hour is not None else {}


class MeteoblueDayForecastSensor(_BaseSeeingSensor):
    """Each entity exposes one day's remaining hourly data (well below 16 KB)."""

    _attr_icon = "mdi:calendar-clock"
    _attr_native_unit_of_measurement = "h"

    def __init__(self, coordinator: MeteoblueSeeingCoordinator, offset: int) -> None:
        super().__init__(coordinator, f"forecast_day_{offset}")
        self.offset = offset
        self._attr_name = ("Prognoza dzisiaj", "Prognoza jutro", "Prognoza pojutrze")[offset]

    def _target_date(self):
        return self._now().date() + timedelta(days=self.offset)

    @property
    def native_value(self) -> int:
        return len(self.coordinator.day_hours(self._target_date(), self._now()))

    @property
    def extra_state_attributes(self) -> dict:
        target = self._target_date()
        hours = self.coordinator.day_hours(target, self._now())
        return {
            "date": target.isoformat(),
            "source": "meteoblue Astronomy Seeing",
            "timezone": self.coordinator.timezone,
            **self.coordinator.data.days.get(target, {}),
            "forecast": [row.as_dict() for row in hours],
        }


class MeteoblueMoonSensor(_BaseSeeingSensor):
    """Moon illumination from the per-day astronomical header."""

    _attr_name = "Oświetlenie Księżyca"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_icon = "mdi:moon-waning-crescent"

    def __init__(self, coordinator: MeteoblueSeeingCoordinator) -> None:
        super().__init__(coordinator, "moon_illumination")

    @property
    def native_value(self) -> int | None:
        day = self._now().date()
        return self.coordinator.data.days.get(day, {}).get("moonphase")


class MeteoblueLastDownloadSensor(_BaseSeeingSensor):
    """Timestamp of the last successful HTML request and parse."""

    _attr_name = "Ostatnia aktualizacja"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:clock-check-outline"

    def __init__(self, coordinator: MeteoblueSeeingCoordinator) -> None:
        super().__init__(coordinator, "last_download")

    @property
    def native_value(self) -> datetime | None:
        return self.coordinator.last_download


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Add the location's sensors in a single device."""
    coordinator: MeteoblueSeeingCoordinator = entry.runtime_data
    async_add_entities(
        [MeteoblueCurrentSensor(coordinator, desc) for desc in SENSOR_DESCRIPTIONS]
        + [MeteoblueDayForecastSensor(coordinator, index) for index in range(3)]
        + [MeteoblueMoonSensor(coordinator), MeteoblueLastDownloadSensor(coordinator)]
    )
