"""Number platform for the R&T smart toilet."""

from __future__ import annotations

from typing import Any

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, NUMBERS
from .coordinator import RTToiletCoordinator
from .entity import RTToiletEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: RTToiletCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        RTToiletNumber(coordinator, mark, name, icon, minimum, maximum, step)
        for mark, name, icon, minimum, maximum, step in NUMBERS
    )


class RTToiletNumber(RTToiletEntity, NumberEntity):
    _attr_mode = NumberMode.SLIDER

    def __init__(
        self,
        coordinator: RTToiletCoordinator,
        mark: str,
        name: str,
        icon: str,
        minimum: float,
        maximum: float,
        step: float,
    ) -> None:
        super().__init__(coordinator, f"number_{mark}")
        self._mark = mark
        self._attr_name = name
        self._attr_icon = icon
        self._attr_native_min_value = minimum
        self._attr_native_max_value = maximum
        self._attr_native_step = step

    @property
    def native_value(self) -> float | None:
        value = self.coordinator.data.get("raw", {}).get(self._mark)
        return float(value) if isinstance(value, (int, float)) else None

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_send_command(
            self._mark, {self._mark: int(round(value))}
        )
