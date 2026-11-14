"""Button platform (momentary actions) for the R&T smart toilet."""

from __future__ import annotations

from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import BUTTONS, DOMAIN
from .coordinator import RTToiletCoordinator
from .entity import RTToiletEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: RTToiletCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        RTToiletButton(coordinator, mark, name, icon)
        for mark, name, icon in BUTTONS
    )


class RTToiletButton(RTToiletEntity, ButtonEntity):
    def __init__(
        self, coordinator: RTToiletCoordinator, mark: str, name: str, icon: str
    ) -> None:
        super().__init__(coordinator, f"button_{mark}")
        self._mark = mark
        self._attr_name = name
        self._attr_icon = icon

    async def async_press(self, **kwargs: Any) -> None:
        await self.coordinator.async_send_command(self._mark)
