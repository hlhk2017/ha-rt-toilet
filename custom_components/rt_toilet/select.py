"""Select platform (temperature levels) for the R&T smart toilet."""

from __future__ import annotations

from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    SELECTS,
    TEMPERATURE_LEVELS,
    TEMPERATURE_MIN,
    TEMPERATURE_STEP,
)
from .coordinator import RTToiletCoordinator
from .entity import RTToiletEntity

_OPTIONS = [
    f"{TEMPERATURE_MIN + TEMPERATURE_STEP * i}℃" for i in range(TEMPERATURE_LEVELS)
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: RTToiletCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        RTToiletTemperatureSelect(coordinator, mark, name, icon)
        for mark, name, icon in SELECTS
    )


class RTToiletTemperatureSelect(RTToiletEntity, SelectEntity):
    _attr_options = _OPTIONS

    def __init__(
        self, coordinator: RTToiletCoordinator, mark: str, name: str, icon: str
    ) -> None:
        super().__init__(coordinator, f"select_{mark}")
        self._mark = mark
        self._attr_name = name
        self._attr_icon = icon

    @property
    def current_option(self) -> str | None:
        value = self.coordinator.data.get("raw", {}).get(self._mark)
        if isinstance(value, int) and 0 <= value < len(_OPTIONS):
            return _OPTIONS[value]
        return None

    async def async_select_option(self, option: str) -> None:
        if option not in _OPTIONS:
            return
        await self.coordinator.async_send_command(
            self._mark, {self._mark: _OPTIONS.index(option)}
        )
