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
    "applianceSerial",
    "gatewayMac",
    "gatewaySerial",
    "localIpAddressV4",
    "localIpAddressV6",
    "publicIpAddressV4",
    "publicIpAddressV6",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: DimplexConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    heat_pump = entry.runtime_data.heat_pump
    assert heat_pump.twin is not None
    return async_redact_data(
        {
            "entry": dict(entry.data),
            "connected": heat_pump.connected,
            "modbus_enabled": heat_pump.modbus_enabled,
            "twin_meta": heat_pump.twin.meta,
            "twin_telemetry": heat_pump.twin.telemetry,
            "values": heat_pump.values,
            "error_history": [asdict(item) for item in heat_pump.error_history],
            "lock_history": [asdict(item) for item in heat_pump.lock_history],
        },
        TO_REDACT,
    )
