"""Shared entity base for the R&T smart toilet."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, MODEL
from .coordinator import RTToiletCoordinator


class RTToiletEntity(CoordinatorEntity[RTToiletCoordinator]):
    """Base class wiring an entity to the shared BLE coordinator."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: RTToiletCoordinator, key: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.address}_{key}"

    @property
    def available(self) -> bool:
        return self.coordinator.connected

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.address)},
            name=self.coordinator.device_name,
            manufacturer=MANUFACTURER,
            model=MODEL,
        )
