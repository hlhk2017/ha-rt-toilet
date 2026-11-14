"""BlueZ connection preparation for dual-mode toilet radios."""

from __future__ import annotations

import asyncio
import logging

from bleak.backends.bluezdbus.utils import get_dbus_authenticator
from dbus_fast import BusType, Message, MessageType, Variant
from dbus_fast.aio import MessageBus

_LOGGER = logging.getLogger(__name__)


def _path(device) -> str | None:
    details = getattr(device, "details", None)
    path = details.get("path") if isinstance(details, dict) else None
    return path if isinstance(path, str) and path.startswith("/org/bluez/") else None


async def _call(bus, path: str, interface: str, member: str, signature: str = "", body=None):
    reply = await bus.call(Message(
        destination="org.bluez", path=path, interface=interface,
        member=member, signature=signature, body=body or [],
    ))
    if reply.message_type == MessageType.ERROR:
        raise RuntimeError(f"{reply.error_name}: {reply.body}")
    return reply


async def async_prepare_le(device) -> None:
    """Prefer LE before Bleak connects; ignore unsupported BlueZ properties."""
    path = _path(device)
    if path is None:
        return
    bus = None
    try:
        async with asyncio.timeout(6):
            bus = await MessageBus(
                bus_type=BusType.SYSTEM, auth=get_dbus_authenticator()
            ).connect()
            props = "org.freedesktop.DBus.Properties"
            current = await _call(bus, path, props, "Get", "ss",
                                  ["org.bluez.Device1", "PreferredBearer"])
            if current.body[0].value != "le":
                await _call(bus, path, props, "Set", "ssv", [
                    "org.bluez.Device1", "PreferredBearer", Variant("s", "le"),
                ])
                _LOGGER.debug("Set LE bearer for %s", device.address)
    except Exception as err:  # noqa: BLE001
        _LOGGER.debug("Could not set LE bearer for %s: %s", device.address, err)
    finally:
        if bus is not None:
            bus.disconnect()


async def async_prime_le(device) -> bool:
    """Reproduce BlueZ connect/disconnect after a failed Bleak connection."""
    path = _path(device)
    if path is None:
        return False
    bus = None
    connected = False
    try:
        async with asyncio.timeout(20):
            bus = await MessageBus(
                bus_type=BusType.SYSTEM, auth=get_dbus_authenticator()
            ).connect()
            status = await _call(bus, path, "org.freedesktop.DBus.Properties", "Get", "ss",
                                 ["org.bluez.Device1", "Connected"])
            if status.body[0].value:
                return False
            await _call(bus, path, "org.bluez.Device1", "Connect")
            connected = True
            await _call(bus, path, "org.bluez.Device1", "Disconnect")
            connected = False
            return True
    except Exception as err:  # noqa: BLE001
        _LOGGER.debug("BlueZ LE connection prime failed for %s: %s", device.address, err)
        return False
    finally:
        if bus is not None:
            if connected:
                try:
                    async with asyncio.timeout(5):
                        await _call(bus, path, "org.bluez.Device1", "Disconnect")
                except Exception:  # noqa: BLE001
                    _LOGGER.debug("BlueZ LE prime cleanup failed for %s", device.address)
            bus.disconnect()
