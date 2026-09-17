"""The Dimplex NWPM Touch integration."""

from homeassistant.const import CONF_HOST, CONF_PASSWORD, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from pydimplex_nwpm import DimplexModbusClient, DimplexMqttClient

from .const import CONF_USE_MODBUS
from .coordinator import DimplexConfigEntry, DimplexCoordinator

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.WATER_HEATER,
]


async def async_setup_entry(hass: HomeAssistant, entry: DimplexConfigEntry) -> bool:
    """Set up Dimplex NWPM Touch from a config entry."""
    host: str = entry.data[CONF_HOST]
    mqtt_client = DimplexMqttClient(host, entry.data[CONF_PASSWORD])
    modbus_client = (
        DimplexModbusClient(host) if entry.data.get(CONF_USE_MODBUS, False) else None
    )
    coordinator = DimplexCoordinator(hass, entry, mqtt_client, modbus_client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    # The gateway device is the parent of the heat pump device, so it has to
    # exist before the platforms create their entities.
    gateway = dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id, **coordinator.gateway_device_info
    )
    coordinator.gateway_device_id = gateway.id

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: DimplexConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
