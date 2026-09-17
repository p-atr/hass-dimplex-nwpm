"""Data update coordinator for the Dimplex NWPM Touch integration."""

import logging
from typing import override

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from pydimplex_nwpm import (
    DimplexAuthenticationError,
    DimplexConnectionError,
    DimplexHeatPump,
)

from .const import CONF_USE_MODBUS, DOMAIN, POLL_INTERVAL

_LOGGER = logging.getLogger(__name__)

MANUFACTURER = "Dimplex"

type DimplexConfigEntry = ConfigEntry[DimplexCoordinator]


class DimplexCoordinator(DataUpdateCoordinator[None]):
    """Poll the heat pump and forward its push updates to the entities."""

    config_entry: DimplexConfigEntry
    gateway_device_info: DeviceInfo
    heat_pump_device_info: DeviceInfo

    def __init__(self, hass: HomeAssistant, entry: DimplexConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=POLL_INTERVAL,
        )
        self.heat_pump = DimplexHeatPump(
            entry.data[CONF_HOST],
            entry.data[CONF_PASSWORD],
            use_modbus=entry.data[CONF_USE_MODBUS],
        )

    @override
    async def _async_setup(self) -> None:
        """Connect to the gateway."""
        try:
            twin = await self.heat_pump.connect()
        except DimplexAuthenticationError as err:
            raise ConfigEntryAuthFailed(
                translation_domain=DOMAIN, translation_key="invalid_auth"
            ) from err
        except DimplexConnectionError as err:
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="cannot_connect",
                translation_placeholders={"error": str(err)},
            ) from err
        serial = self.config_entry.unique_id
        assert serial is not None
        self.gateway_device_info = DeviceInfo(
            identifiers={(DOMAIN, twin.gateway_serial or f"gateway_{serial}")},
            manufacturer=MANUFACTURER,
            model="NWPM Touch",
            model_id=twin.gateway_model,
            translation_key="gateway",
            serial_number=twin.gateway_serial,
            sw_version=twin.gateway_firmware,
            configuration_url=f"https://{self.config_entry.data[CONF_HOST]}",
        )
        if twin.gateway_mac:
            self.gateway_device_info["connections"] = {
                (CONNECTION_NETWORK_MAC, twin.gateway_mac)
            }
        gateway = dr.async_get(self.hass).async_get_or_create(
            config_entry_id=self.config_entry.entry_id, **self.gateway_device_info
        )
        self.heat_pump_device_info = DeviceInfo(
            identifiers={(DOMAIN, serial)},
            manufacturer=MANUFACTURER,
            model=twin.appliance_type,
            model_id=twin.wpm_type,
            translation_key="heat_pump",
            serial_number=twin.appliance_serial,
            sw_version=twin.appliance_version,
            via_device_id=gateway.id,
        )
        # async_set_updated_data would postpone the poll on every push update.
        self.config_entry.async_on_unload(
            self.heat_pump.subscribe(self.async_update_listeners)
        )

    @override
    async def _async_update_data(self) -> None:
        """Poll the values that the gateway does not push."""
        if self.heat_pump.authentication_failed:
            raise ConfigEntryAuthFailed(
                translation_domain=DOMAIN, translation_key="invalid_auth"
            )
        try:
            await self.heat_pump.update()
        except DimplexConnectionError as err:
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="cannot_connect",
                translation_placeholders={"error": str(err)},
            ) from err

    @override
    async def async_shutdown(self) -> None:
        """Disconnect from the gateway."""
        await super().async_shutdown()
        await self.heat_pump.disconnect()
