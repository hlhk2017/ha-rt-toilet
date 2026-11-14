"""Translate the mini-program's search page and DeviceBluetooth.discovery."""
from .protocol import SERVICE_UUID


def is_supported(info) -> bool:
    # pages/IOT/index scans commonInfo.serviceId (FFE0), then the callback
    # requires localName.includes("R&T"). FEE7 is a connection transport,
    # not an alternative automatic-discovery identifier.
    local_name = getattr(getattr(info, "advertisement", None), "local_name", None) or ""
    return (
        info.connectable
        and "R&T" in local_name
        and SERVICE_UUID in {uuid.lower() for uuid in info.service_uuids}
    )
