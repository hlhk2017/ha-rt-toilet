"""Binary sensor platform for the R&T smart toilet."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import BINARY_SENSORS, DOMAIN
from .coordinator import RTToiletCoordinator
from .entity import RTToiletEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: RTToiletCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        RTToiletBinarySensor(coordinator, mark, name, icon)
        for mark, name, icon in BINARY_SENSORS
    )


class RTToiletBinarySensor(RTToiletEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.OCCUPANCY

    def __init__(
        self, coordinator: RTToiletCoordinator, mark: str, name: str, icon: str
    ) -> None:
        super().__init__(coordinator, f"binary_{mark}")
        self._mark = mark
        self._attr_name = name
        self._attr_icon = icon

    @property
    def is_on(self) -> bool:
        return self.coordinator.data.get("raw", {}).get(self._mark) == 1
