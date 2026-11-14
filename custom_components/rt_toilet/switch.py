"""Switch platform for the R&T smart toilet."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SWITCHES
from .coordinator import RTToiletCoordinator
from .entity import RTToiletEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: RTToiletCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        RTToiletSwitch(coordinator, mark, name, icon)
        for mark, name, icon in SWITCHES
    )


class RTToiletSwitch(RTToiletEntity, SwitchEntity):
    def __init__(
        self, coordinator: RTToiletCoordinator, mark: str, name: str, icon: str
    ) -> None:
        super().__init__(coordinator, f"switch_{mark}")
        self._mark = mark
        self._attr_name = name
        self._attr_icon = icon

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.data.get("raw", {}).get(self._mark))

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_send_command(self._mark, {self._mark: 1})

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_send_command(self._mark, {self._mark: 0})
