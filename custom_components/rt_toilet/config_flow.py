"""Config flow for the R&T C80Lite smart toilet."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_discovered_service_info,
)
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .const import CONF_ADDRESS, DOMAIN, NAME
from .discovery import is_supported

_LOGGER = logging.getLogger(__name__)


def _name_of(info: BluetoothServiceInfoBleak) -> str:
    return info.advertisement.local_name or info.name or info.address


def _is_supported(info: BluetoothServiceInfoBleak) -> bool:
    return is_supported(info)


class RTToiletConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle discovery and manual setup of an R&T toilet."""

    VERSION = 1

    def __init__(self) -> None:
        self._discovery: BluetoothServiceInfoBleak | None = None
        self._address: str | None = None

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> ConfigFlowResult:
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()

        if not _is_supported(discovery_info):
            return self.async_abort(reason="not_supported")

        self._discovery = discovery_info
        self._address = discovery_info.address
        self.context["title_placeholders"] = {"name": _name_of(discovery_info)}
        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        assert self._discovery is not None
        if user_input is not None:
            if not any(info.address == self._address and _is_supported(info)
                       for info in async_discovered_service_info(self.hass, connectable=True)):
                return self.async_abort(reason="not_supported")
            return self.async_create_entry(
                title=_name_of(self._discovery),
                data={CONF_ADDRESS: self._address},
            )
        self._set_confirm_only()
        return self.async_show_form(
            step_id="bluetooth_confirm",
            description_placeholders={"name": _name_of(self._discovery)},
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            address = user_input[CONF_ADDRESS].upper()
            if not any(info.address.upper() == address and _is_supported(info)
                       for info in async_discovered_service_info(self.hass, connectable=True)):
                return self.async_abort(reason="not_supported")
            await self.async_set_unique_id(address, raise_on_progress=False)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=user_input.get("name", address),
                data={CONF_ADDRESS: address},
            )

        current = self._async_current_ids()
        devices: dict[str, str] = {}
        for info in async_discovered_service_info(self.hass, connectable=True):
            if info.address in current or not _is_supported(info):
                continue
            devices[info.address] = f"{_name_of(info)} ({info.address})"

        if not devices:
            return self.async_abort(reason="no_devices_found")

        schema = vol.Schema(
            {
                vol.Required(CONF_ADDRESS): vol.In(devices),
                vol.Optional("name", default=NAME): str,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)
