"""Sensor platform for the R&T smart toilet."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, SIGNAL_STRENGTH_DECIBELS_MILLIWATT, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SENSORS
from .coordinator import RTToiletCoordinator
from .entity import RTToiletEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: RTToiletCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        RTToiletSensor(coordinator, mark, name, icon, kind)
        for mark, name, icon, kind in SENSORS
    )


class RTToiletSensor(RTToiletEntity, SensorEntity):
    def __init__(
        self,
        coordinator: RTToiletCoordinator,
        mark: str,
        name: str,
        icon: str,
        kind: str,
    ) -> None:
        super().__init__(coordinator, f"sensor_{mark}")
        self._mark = mark
        self._kind = kind
        self._attr_name = name
        self._attr_icon = icon
        if kind == "temp":
            self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
            self._attr_icon = icon
        elif kind == "rssi":
            self._attr_device_class = SensorDeviceClass.SIGNAL_STRENGTH
            self._attr_native_unit_of_measurement = SIGNAL_STRENGTH_DECIBELS_MILLIWATT
            self._attr_entity_category = EntityCategory.DIAGNOSTIC
        elif kind == "raw":
            self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def available(self) -> bool:
        if self._kind == "rssi":
            return self.coordinator.data.get("rssi") is not None
        return super().available

    @property
    def native_value(self) -> Any:
        if self._kind == "temp":
            return self.coordinator.data.get("temp", {}).get(self._mark)
        if self._kind == "rssi":
            return self.coordinator.data.get("rssi")
        if self._kind == "raw":
            return self.coordinator.data.get("raw", {}).get(self._mark)
        return self.coordinator.data.get("text", {}).get(self._mark)
