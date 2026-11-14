"""BLE connection coordinator for the R&T C80Lite smart toilet."""

from __future__ import annotations

import asyncio
import logging

from bleak.exc import BleakError
from bleak_retry_connector import (
    BleakClientWithServiceCache,
    close_stale_connections_by_address,
    establish_connection,
)
from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from . import protocol
from .bluez import async_prepare_le, async_prime_le
from .discovery import is_supported
from .const import CONF_ADDRESS, CONNECT_RETRY_SECONDS, DOMAIN, KEEPALIVE_SECONDS

_LOGGER = logging.getLogger(__name__)


class RTToiletCoordinator(DataUpdateCoordinator[dict]):
    """Owns the BLE link, sends commands and decodes status frames."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=None)
        self.address: str = entry.data[CONF_ADDRESS]
        self.device_name: str = entry.title or self.address
        self._client: BleakClientWithServiceCache | None = None
        self._write_char: str | None = None
        self._notify_char: str | None = None
        self.connected = False
        self._stop = asyncio.Event()
        self._task: asyncio.Task | None = None
        self._cancel_rssi_callback = None
        self.data = {"raw": {}, "temp": {}, "text": {}, "rssi": None}

    # -- lifecycle --------------------------------------------------------
    async def async_start(self) -> None:
        self._start_rssi_listener()
        self._stop.clear()
        self._task = self.hass.loop.create_task(self._run())

    def _start_rssi_listener(self) -> None:
        if self._cancel_rssi_callback is not None:
            return

        def received(info):
            if info.address.upper() == self.address.upper():
                self.data = {**self.data, "rssi": info.rssi}
                self.async_set_updated_data(self.data)

        self._cancel_rssi_callback = bluetooth.async_register_advertisement_callback(
            self.hass, received, self.address
        )

    async def async_stop(self) -> None:
        self._stop.set()
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                pass
            self._task = None
        await self._disconnect()
        if self._cancel_rssi_callback is not None:
            self._cancel_rssi_callback()
            self._cancel_rssi_callback = None

    async def _disconnect(self) -> None:
        client, self._client = self._client, None
        self.connected = False
        if client is not None:
            try:
                await client.disconnect()
            except (BleakError, Exception):  # noqa: BLE001
                pass

    async def _run(self) -> None:
        """Maintain the connection, reconnecting forever."""
        while not self._stop.is_set():
            try:
                await self._connect()
                while (
                    self._client is not None
                    and self._client.is_connected
                    and not self._stop.is_set()
                ):
                    await asyncio.sleep(KEEPALIVE_SECONDS)
                    await self._send(protocol.build_handshake())
            except asyncio.CancelledError:
                raise
            except Exception as err:  # noqa: BLE001
                _LOGGER.debug("R&T toilet connect/keepalive failed: %s", err)
            self.connected = False
            self._client = None
            if self._stop.is_set():
                return
            try:
                await asyncio.sleep(CONNECT_RETRY_SECONDS)
            except asyncio.CancelledError:
                raise

    async def _async_wait_for_device(self):
        """Wait for a fresh matching advertisement instead of reusing history."""
        register_every = getattr(bluetooth, "async_register_advertisement_callback", None)
        request_sweep = getattr(bluetooth, "async_request_active_scan", None)
        if register_every is None or request_sweep is None:
            info = await bluetooth.async_process_advertisements(
                self.hass,
                is_supported,
                {"address": self.address, "connectable": True},
                bluetooth.BluetoothScanningMode.ACTIVE,
                CONNECT_RETRY_SECONDS,
            )
            return info.device

        fresh = asyncio.get_running_loop().create_future()

        def received(info):
            if info.address.upper() == self.address.upper() and is_supported(info) and not fresh.done():
                fresh.set_result(info.device)

        cancel = register_every(self.hass, received, self.address)
        sweep = self.hass.async_create_task(request_sweep(self.hass, CONNECT_RETRY_SECONDS))
        try:
            async with asyncio.timeout(CONNECT_RETRY_SECONDS):
                return await fresh
        finally:
            cancel()
            sweep.cancel()
            await asyncio.gather(sweep, return_exceptions=True)

    async def _connect(self) -> None:
        device = await self._async_wait_for_device()
        if device is None:
            raise BleakError("device is not currently advertised by a connectable R&T source")
        try:
            await close_stale_connections_by_address(self.address)
        except Exception:  # noqa: BLE001
            pass

        await async_prepare_le(device)

        try:
            client = await establish_connection(
                BleakClientWithServiceCache,
                device,
                self.device_name,
                disconnected_callback=self._on_disconnect,
                max_attempts=2,
            )
        except (BleakError, TimeoutError):
            if not await async_prime_le(device):
                raise
            device = await self._async_wait_for_device()
            client = await establish_connection(
                BleakClientWithServiceCache,
                device,
                self.device_name,
                disconnected_callback=self._on_disconnect,
                max_attempts=2,
            )
        self._client = client

        write_char, notify_char = self._find_characteristics(client)
        if write_char is None or notify_char is None:
            await client.disconnect()
            raise BleakError("FFE0/FFE1 characteristics not found")

        self._write_char = write_char
        self._notify_char = notify_char
        try:  # BlueZ negotiates automatically; Android needs an explicit request.
            if hasattr(client, "request_mtu"):
                await client.request_mtu(247)
        except Exception:  # noqa: BLE001
            pass
        await client.start_notify(notify_char, self._on_notify)
        self.connected = True
        _LOGGER.debug("Connected to R&T toilet %s", self.address)

        # Handshake exactly like the official app: connect -> featSel -> version.
        await self._send(protocol.build_handshake())
        await asyncio.sleep(0.2)
        await self._send(protocol.build_feat_sel())
        await asyncio.sleep(0.2)
        await self._send(protocol.build_version_query())
        self.async_set_updated_data(dict(self.data))

    def _find_characteristics(self, client: BleakClientWithServiceCache) -> tuple[str | None, str | None]:
        services = client.services
        # Preferred transparent-UART service FFE0 / FFE1.
        for service in services:
            if service.uuid.lower().startswith("0000ffe0"):
                for char in service.characteristics:
                    if char.uuid.lower().startswith("0000ffe1"):
                        return char.uuid, char.uuid
        # Fallback: FEE7 service with FEC8 (notify) / FEC7 (write).
        notify = write = None
        for service in services:
            if service.uuid.lower().startswith("0000fee7"):
                for char in service.characteristics:
                    uuid = char.uuid.lower()
                    if uuid.startswith("0000fec8"):
                        notify = char.uuid
                    elif uuid.startswith("0000fec7"):
                        write = char.uuid
        if notify and write:
            return write, notify
        return None, None

    # -- io ---------------------------------------------------------------
    async def _send(self, frame: bytes) -> None:
        client = self._client
        if client is None or self._write_char is None:
            return
        try:
            await client.write_gatt_char(self._write_char, frame, response=False)
        except (BleakError, Exception) as err:  # noqa: BLE001
            try:  # fall back to write-with-response for firmwares that require it
                await client.write_gatt_char(self._write_char, frame, response=True)
            except (BleakError, Exception) as err2:  # noqa: BLE001
                _LOGGER.debug("BLE write failed: %s / %s", err, err2)

    async def async_send_command(self, mark: str, overrides: dict | None = None) -> None:
        await self._send(protocol.build_command(mark, overrides))

    def _on_disconnect(self, _client: BleakClientWithServiceCache) -> None:
        self.connected = False
        _LOGGER.debug("R&T toilet %s disconnected", self.address)

    def _on_notify(self, _characteristic, data: bytearray) -> None:
        try:
            command_type, params = protocol.parse_packet(data)
        except ValueError as err:
            _LOGGER.debug("Ignoring invalid frame %s: %s", data.hex(), err)
            return

        if command_type in (
            protocol.RESP_UPDATE_STATUS,
            protocol.RESP_DISTRIBUTE,
        ):
            status = protocol.parse_status(params)
            merged = {
                **self.data,
                "raw": {**self.data.get("raw", {}), **status["raw"]},
                "temp": {**self.data.get("temp", {}), **status["temp"]},
                "text": {**self.data.get("text", {}), **status["text"]},
            }
            self.data = merged
            self.async_set_updated_data(merged)

        if command_type == protocol.RESP_UPDATE_STATUS:
            # The device expects an acknowledgement (command type 131).
            self.hass.async_create_task(self._send(protocol.build_ack(params)))
