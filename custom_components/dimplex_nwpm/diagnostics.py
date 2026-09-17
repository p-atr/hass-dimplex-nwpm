"""Diagnostics support for the Dimplex NWPM Touch integration."""

from dataclasses import asdict
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_MAC, CONF_PASSWORD
from homeassistant.core import HomeAssistant

from .coordinator import DimplexConfigEntry

TO_REDACT = {
    CONF_PASSWORD,
    CONF_MAC,
    "gatewayMac",
    "localIpAddressV6",
    "publicIpAddressV4",
    "publicIpAddressV6",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: DimplexConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data
    data = coordinator.data
    return async_redact_data(
        {
            "entry": dict(entry.data),
            "mqtt_connected": coordinator.connected,
            "modbus_enabled": coordinator.modbus is not None,
            "modbus_available": data.modbus_available,
            "twin_meta": data.twin.meta,
            "twin_telemetry": data.twin.raw_telemetry,
            "values": data.values,
            "error_history": [asdict(entry) for entry in data.error_history],
            "lock_history": [asdict(entry) for entry in data.lock_history],
        },
        TO_REDACT,
    )
