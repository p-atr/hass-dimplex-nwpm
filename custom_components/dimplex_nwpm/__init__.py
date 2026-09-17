"""The Dimplex NWPM Touch integration."""

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

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
    coordinator = DimplexCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: DimplexConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
