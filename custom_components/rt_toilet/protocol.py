"""R&T (瑞尔特) C80Lite smart-toilet BLE protocol.

Reverse engineered from the official WeChat mini-program "R&T智控"
(appid ``wxd88d18786f43971e``).

Transport
---------
The toilet exposes a transparent BLE-UART bridge:

* Service ``0000FFE0-0000-1000-8000-00805F9B34FB``
* Characteristic ``0000FFE1-0000-1000-8000-00805F9B34FB`` (write + notify)

Every frame is::

    55 AA  <len>  <deviceType>  <cmdType> <paramLen> <params...> <deviceModel hi lo> <checksum>

``len`` is the number of bytes that follow it (deviceType..checksum), and
``checksum`` is ``sum(everything after the 55 AA header except checksum) & 0xFF``.
Command parameters are always ``[0xA1, code, b0..b7]`` where the eight bytes
are a little bit-field array addressed by ``(position, bit-range)``.
"""

from __future__ import annotations

import logging
from typing import Any

from .protocol_data import FUNCTION_OPERATION_LIST, FUNCTION_PARAM_CODE_LIST

_LOGGER = logging.getLogger(__name__)

# --- transport constants -------------------------------------------------
DATA_HEADER = (0x55, 0xAA)
DEFAULT_DEVICE_TYPE = (0x01,)
DEFAULT_DEVICE_MODEL = (0x00, 0x00)
COMMAND_HEADER = 0xA1
PARAM_BYTES = 8

SERVICE_UUID = "0000ffe0-0000-1000-8000-00805f9b34fb"
CHARACTERISTIC_UUID = "0000ffe1-0000-1000-8000-00805f9b34fb"

# Alternative (UID / one-key-direct) transport seen in some firmwares.
UID_SERVICE_UUID = "0000fee7-0000-1000-8000-00805f9b34fb"
UID_NOTIFY_CHAR_UUID = "0000fec8-0000-1000-8000-00805f9b34fb"
UID_WRITE_CHAR_UUID = "0000fec7-0000-1000-8000-00805f9b34fb"

# --- command types -------------------------------------------------------
CMD_TYPE_CONTROL = 2
CMD_TYPE_VERSION_QUERY = 4
CMD_TYPE_FEAT_SEL = 13
CMD_TYPE_NOTIFY_ACK = 131

RESP_DISTRIBUTE = 130
RESP_UPDATE_STATUS = 3
RESP_VERSION_QUERY = 132
RESP_OTA = 139
RESP_FEAT_SEL = 141
RESP_ALLOWED = frozenset(
    {RESP_DISTRIBUTE, RESP_UPDATE_STATUS, RESP_VERSION_QUERY, RESP_OTA, RESP_FEAT_SEL}
)


def _checksum(values: Any) -> int:
    return sum(values) & 0xFF


def build_packet(
    command_type: int,
    params: Any,
    device_type: tuple[int, ...] | list[int] = DEFAULT_DEVICE_TYPE,
    device_model: tuple[int, ...] | list[int] = DEFAULT_DEVICE_MODEL,
) -> bytes:
    """Assemble a complete frame."""
    params = list(params)
    length = 3 + len(params) + 2 + 1
    body = list(device_type) + [command_type, len(params)] + params + list(device_model)
    chk = _checksum([length] + body)
    return bytes(list(DATA_HEADER) + [length] + body + [chk])


def _combine(
    children: list[dict[str, Any]],
    bits: list[str],
    overrides: dict[str, Any],
    feat_sels: dict[str, Any],
) -> None:
    for child in children:
        if child.get("children"):
            _combine(child["children"], bits, overrides, feat_sels)
            continue
        position = child.get("position")
        if position is None or position < 0:
            continue
        while len(bits) <= position:  # some operations use a 9th+ parameter byte
            bits.append("00000000")
        high, low = (int(x) for x in str(child["bit"]).split("-"))
        current = bits[position] or "00000000"
        value = child.get("value")
        if value is None:
            if child.get("type") == "featSels":
                mark = child.get("mark")
                if isinstance(mark, list):
                    value = 1 if (mark and all(feat_sels.get(m) for m in mark)) else 0
                else:
                    value = feat_sels.get(mark, 0) if feat_sels else 0
            elif child.get("mark") in overrides:
                value = overrides[child["mark"]]
        if value is None:
            value = 0
        replace = child.get("valueReplace")
        if isinstance(replace, list) and 0 <= int(value) < len(replace):
            value = replace[int(value)]
        width = high - low + 1
        vbin = format(int(value), "b").zfill(width)[-width:]
        head = current[: 7 - high] + vbin
        bits[position] = head + current[len(head) :]


def create_command_params(op: dict[str, Any], overrides: dict[str, Any] | None = None) -> list[int]:
    """Build the ``[0xA1, code, b0..b7]`` parameter block for an operation."""
    overrides = overrides or {}
    params: list[int] = [COMMAND_HEADER, int(op.get("code", 0))]
    bits = ["00000000"] * PARAM_BYTES
    param_code = op.get("paramCode")
    if param_code:
        _combine(param_code, bits, overrides, op.get("featSels") or {})
    params.extend(int(b, 2) for b in bits)
    return params


def build_command(mark: str | dict[str, Any], overrides: dict[str, Any] | None = None) -> bytes:
    """Build a frame for an operation (by mark or by operation dict)."""
    op = FUNCTION_OPERATION_LIST[mark] if isinstance(mark, str) else mark
    return build_packet(op["commandType"], create_command_params(op, overrides))


def build_handshake() -> bytes:
    return build_command("null")


def build_feat_sel() -> bytes:
    return build_command("featSel")


def build_version_query() -> bytes:
    return build_command("versionCheck")


def build_ack(params: list[int]) -> bytes:
    """ACK a received status frame (command type 131, echo parameters)."""
    return build_packet(CMD_TYPE_NOTIFY_ACK, params)


def parse_packet(data: bytes | bytearray) -> tuple[int, list[int]]:
    """Validate and split an inbound frame into ``(command_type, params)``."""
    values = list(data)
    if len(values) < 9:
        raise ValueError("frame too short")
    if tuple(values[:2]) != DATA_HEADER:
        raise ValueError("bad header")
    command_type = values[4]
    if command_type not in RESP_ALLOWED:
        raise ValueError(f"unexpected command type {command_type}")
    params = values[6:-3]
    if values[5] != len(params):
        raise ValueError("param length mismatch")
    expected = build_packet(
        command_type, params, device_type=values[3:4], device_model=values[-3:-1]
    )
    if len(expected) != len(values) or any(a != b for a, b in zip(expected, values)):
        raise ValueError("checksum mismatch")
    return command_type, params


def _status_name(spec: dict[str, Any], value: int) -> str | None:
    parse = spec.get("parse")
    if not parse or parse.get("type") != "status":
        return None
    enum = parse.get("statusEnum")
    entry = None
    if isinstance(enum, dict):
        entry = enum.get(str(value))
    elif isinstance(enum, list) and 0 <= value < len(enum):
        entry = enum[value]
    if isinstance(entry, dict):
        return entry.get("name")
    return None


def parse_status(params: list[int]) -> dict[str, dict[str, Any]]:
    """Decode a status/parameter block using ``FUNCTION_PARAM_CODE_LIST``.

    Returns ``{"raw": {...}, "temp": {...}, "text": {...}}``.
    """
    raw: dict[str, Any] = {}
    temp: dict[str, Any] = {}
    text: dict[str, Any] = {}

    for mark, spec in FUNCTION_PARAM_CODE_LIST.items():
        position = spec.get("position", 0)
        index = int(position) + 2
        if index < 0 or index >= len(params):
            continue
        byte = params[index]
        high, low = (int(x) for x in str(spec["bit"]).split("-"))
        width = high - low + 1
        value = (byte >> low) & ((1 << width) - 1)
        raw[mark] = value

        parse = spec.get("parse")
        if parse:
            if parse.get("type") == "temperature":
                temp[mark] = int(parse.get("min", 0)) + int(parse.get("step", 1)) * value
            elif parse.get("type") == "status":
                name = _status_name(spec, value)
                if name is not None:
                    text[mark] = name

        assoc = spec.get("assocParse")
        if isinstance(assoc, dict):
            for item in assoc.get(str(value)) or []:
                if isinstance(item, dict) and item.get("mark"):
                    raw[item["mark"]] = item.get("value")
        elif isinstance(assoc, list) and 0 <= value < len(assoc):
            for item in assoc[value] or []:
                if isinstance(item, dict) and item.get("mark"):
                    raw[item["mark"]] = item.get("value")

    # The app promotes a running "healthy" programme into the device status
    # (values 121..127) when healthyVitalityPopup is active.
    healthy = raw.get("healthyVitalityPopup")
    if isinstance(healthy, int) and 1 <= healthy <= 7:
        raw["deviceStatus"] = 120 + healthy
        name = _status_name(FUNCTION_PARAM_CODE_LIST["deviceStatus"], 120 + healthy)
        if name:
            text["deviceStatus"] = name

    return {"raw": raw, "temp": temp, "text": text}
