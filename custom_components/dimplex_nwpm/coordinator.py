"""Data update coordinator for the Dimplex NWPM Touch integration."""

from collections.abc import Callable
from dataclasses import dataclass, field
import logging
from typing import override

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from pydimplex_nwpm import (
    DatapointValue,
    DimplexAuthenticationError,
    DimplexConnectionError,
    DimplexError,
    DimplexModbusClient,
    DimplexMqttClient,
    DimplexRequestError,
    HistoryEntry,
    TwinState,
    canonical_name,
)

from .const import (
    CONDITION_RANGES,
    DOMAIN,
    MANUFACTURER,
    MODBUS_COIL_BLOCKS,
    POLL_INTERVAL,
    POLL_RANGES,
)

_LOGGER = logging.getLogger(__name__)

type DimplexConfigEntry = ConfigEntry[DimplexCoordinator]


def coil_key(address: int) -> str:
    """Return the data key of a Modbus coil."""
    return f"co{address}"


@dataclass(frozen=True, kw_only=True)
class DimplexData:
    """Snapshot of all known values of the heat pump."""

    values: dict[str, DatapointValue]
    twin: TwinState
    error_history: list[HistoryEntry] = field(default_factory=list)
    lock_history: list[HistoryEntry] = field(default_factory=list)
    modbus_available: bool = False

    def condition(self, name: str | None) -> bool:
        """Return whether an equipment condition flag is set.

        Flags unknown to the connected software version are treated as set so
        the related entities are still offered.
        """
        if name is None:
            return True
        if (flag := self.values.get(canonical_name(name))) is None:
            return True
        return bool(flag)


class DimplexCoordinator(DataUpdateCoordinator[DimplexData]):
    """Merge MQTT push updates with periodic MQTT and Modbus polling."""

    config_entry: DimplexConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: DimplexConfigEntry,
        mqtt_client: DimplexMqttClient,
        modbus_client: DimplexModbusClient | None,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=POLL_INTERVAL,
        )
        self.mqtt = mqtt_client
        self.modbus = modbus_client
        self._values: dict[str, DatapointValue] = {}
        self._modbus_available = False
        self.gateway_device_id: str | None = None
        self._unsubscribe: list[Callable[[], None]] = []

    @property
    def connected(self) -> bool:
        """Return True while the MQTT connection to the gateway is up."""
        return self.mqtt.connected

    @property
    def twin(self) -> TwinState:
        """Return the last received device twin."""
        assert self.mqtt.twin is not None
        return self.mqtt.twin

    @property
    def gateway_device_info(self) -> DeviceInfo:
        """Return the device info of the NWPM Touch gateway."""
        twin = self.twin
        identifiers = {(DOMAIN, twin.gateway_serial or f"gateway_{self.serial}")}
        info = DeviceInfo(
            identifiers=identifiers,
            manufacturer=MANUFACTURER,
            model="NWPM Touch",
            model_id=twin.gateway_model,
            name="Dimplex NWPM Touch",
            serial_number=twin.gateway_serial,
            sw_version=twin.plugin_version,
            hw_version=twin.gateway_firmware,
            configuration_url=f"https://{self.config_entry.data[CONF_HOST]}",
        )
        if twin.gateway_mac:
            info["connections"] = {(CONNECTION_NETWORK_MAC, twin.gateway_mac)}
        return info

    @property
    def serial(self) -> str:
        """Return the serial number used as unique id."""
        assert self.config_entry.unique_id is not None
        return self.config_entry.unique_id

    @property
    def appliance_device_info(self) -> DeviceInfo:
        """Return the device info of the heat pump manager."""
        twin = self.twin
        info = DeviceInfo(
            identifiers={(DOMAIN, self.serial)},
            manufacturer=MANUFACTURER,
            model=f"Heat pump manager {twin.appliance_type or 'WPM'}",
            model_id=twin.wpm_type,
            name="Dimplex heat pump",
            serial_number=twin.appliance_serial,
            sw_version=twin.appliance_version,
        )
        if self.gateway_device_id is not None:
            info["via_device_id"] = self.gateway_device_id
        return info

    @override
    async def _async_setup(self) -> None:
        """Connect to the gateway and subscribe to push updates."""
        try:
            await self.mqtt.connect()
            twin = await self.mqtt.wait_for_twin()
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
        self._values.update(twin.telemetry)
        await self._async_poll_ranges(CONDITION_RANGES)
        self._unsubscribe.extend(
            (
                self.mqtt.add_values_listener(self._handle_values),
                self.mqtt.add_twin_listener(self._handle_twin),
                self.mqtt.add_error_history_listener(self._handle_history),
                self.mqtt.add_lock_history_listener(self._handle_history),
                self.mqtt.add_connection_listener(self._handle_connection),
            )
        )
        # Ask the gateway to re-send its cached telemetry so the push channel
        # delivers a complete snapshot right away.
        try:
            await self.mqtt.clear_cache()
        except DimplexError as err:
            _LOGGER.debug("Clearing the gateway value cache failed: %s", err)

    @override
    async def async_shutdown(self) -> None:
        """Disconnect from the gateway."""
        await super().async_shutdown()
        for unsubscribe in self._unsubscribe:
            unsubscribe()
        self._unsubscribe.clear()
        await self.mqtt.disconnect()
        if self.modbus is not None:
            await self.modbus.close()

    @override
    async def _async_update_data(self) -> DimplexData:
        """Poll the datapoints that are not pushed by the gateway."""
        if self.mqtt.authentication_failed:
            raise ConfigEntryAuthFailed(
                translation_domain=DOMAIN, translation_key="invalid_auth"
            )
        if not self.mqtt.connected:
            raise UpdateFailed(
                translation_domain=DOMAIN, translation_key="not_connected"
            )
        await self._async_poll_ranges(POLL_RANGES)
        if self.modbus is not None:
            await self._async_poll_modbus()
        return self._snapshot()

    async def _async_poll_ranges(self, ranges: tuple[str, ...]) -> None:
        for name in ranges:
            try:
                self._values.update(await self.mqtt.get_values(name))
            except DimplexRequestError as err:
                _LOGGER.debug("Datapoint range %s not available: %s", name, err)
            except DimplexConnectionError as err:
                raise UpdateFailed(
                    translation_domain=DOMAIN,
                    translation_key="cannot_connect",
                    translation_placeholders={"error": str(err)},
                ) from err

    async def _async_poll_modbus(self) -> None:
        assert self.modbus is not None
        try:
            for address, count in MODBUS_COIL_BLOCKS:
                coils = await self.modbus.read_coils(address, count)
                for offset, state in enumerate(coils):
                    self._values[coil_key(address + offset)] = state
        except DimplexError as err:
            if self._modbus_available:
                _LOGGER.warning(
                    "Modbus TCP connection to %s lost: %s",
                    self.config_entry.data[CONF_HOST],
                    err,
                )
            self._modbus_available = False
            return
        if not self._modbus_available and self.data is not None:
            _LOGGER.info(
                "Modbus TCP connection to %s restored",
                self.config_entry.data[CONF_HOST],
            )
        self._modbus_available = True

    def _snapshot(self) -> DimplexData:
        return DimplexData(
            values=dict(self._values),
            twin=self.twin,
            error_history=list(self.mqtt.error_history),
            lock_history=list(self.mqtt.lock_history),
            modbus_available=self._modbus_available,
        )

    @callback
    def _handle_values(self, changed: dict[str, DatapointValue]) -> None:
        self._values.update(changed)
        self.async_set_updated_data(self._snapshot())

    @callback
    def _handle_twin(self, twin: TwinState) -> None:
        self._values.update(twin.telemetry)
        self.async_set_updated_data(self._snapshot())

    @callback
    def _handle_history(self, _: list[HistoryEntry]) -> None:
        self.async_set_updated_data(self._snapshot())

    @callback
    def _handle_connection(self, connected: bool) -> None:
        if connected:
            _LOGGER.info(
                "Connection to gateway %s restored", self.config_entry.data[CONF_HOST]
            )
            self.config_entry.async_create_task(self.hass, self._async_resync())
        else:
            _LOGGER.warning(
                "Connection to gateway %s lost", self.config_entry.data[CONF_HOST]
            )
        self.async_update_listeners()

    async def _async_resync(self) -> None:
        """Fetch everything again after the connection was re-established."""
        try:
            await self.mqtt.clear_cache()
        except DimplexError as err:
            _LOGGER.debug("Clearing the gateway value cache failed: %s", err)
        await self.async_request_refresh()

    async def async_set_datapoint(self, name: str, value: DatapointValue) -> None:
        """Write a datapoint over MQTT and read the resulting value back."""
        try:
            await self.mqtt.set_value(name, value)
            self._values.update(await self.mqtt.get_values(name))
        except DimplexError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="write_failed",
                translation_placeholders={"datapoint": name, "error": str(err)},
            ) from err
        self.async_set_updated_data(self._snapshot())
