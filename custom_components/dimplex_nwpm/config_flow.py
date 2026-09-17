"""Config flow for the Dimplex NWPM Touch integration."""

from collections.abc import Mapping
import logging
from typing import Any, override

try:
    import probatio
except ImportError:  # Home Assistant < 2026.10 ships voluptuous instead
    import voluptuous as probatio  # type: ignore[no-redef]
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_MAC, CONF_PASSWORD
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.selector import (
    BooleanSelector,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)
from homeassistant.helpers.service_info.dhcp import DhcpServiceInfo
from pydimplex_nwpm import (
    DimplexAuthenticationError,
    DimplexConnectionError,
    DimplexError,
    DimplexModbusClient,
    DimplexMqttClient,
    TwinState,
)

from .const import CONF_USE_MODBUS, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_SCHEMA = probatio.Schema(
    {
        probatio.Required(CONF_HOST): TextSelector(
            TextSelectorConfig(type=TextSelectorType.TEXT, autocomplete="off")
        ),
        probatio.Required(CONF_PASSWORD): TextSelector(
            TextSelectorConfig(
                type=TextSelectorType.PASSWORD, autocomplete="current-password"
            )
        ),
        probatio.Required(CONF_USE_MODBUS, default=False): BooleanSelector(),
    }
)

STEP_REAUTH_SCHEMA = probatio.Schema(
    {
        probatio.Required(CONF_PASSWORD): TextSelector(
            TextSelectorConfig(
                type=TextSelectorType.PASSWORD, autocomplete="current-password"
            )
        ),
    }
)


async def async_validate_connection(
    host: str, password: str, use_modbus: bool
) -> tuple[TwinState | None, dict[str, str]]:
    """Connect to the gateway with the given settings and return its twin."""
    errors: dict[str, str] = {}
    twin: TwinState | None = None
    client = DimplexMqttClient(host, password)
    try:
        await client.connect()
        twin = await client.wait_for_twin()
    except DimplexAuthenticationError:
        errors["base"] = "invalid_auth"
    except DimplexConnectionError as err:
        _LOGGER.debug("Unable to connect to %s: %s", host, err)
        errors["base"] = "cannot_connect"
    finally:
        await client.disconnect()
    if twin is not None and not (twin.appliance_serial or twin.gateway_serial):
        errors["base"] = "no_serial"
    if not errors and use_modbus:
        modbus = DimplexModbusClient(host)
        try:
            await modbus.read_software_version()
        except DimplexError as err:
            _LOGGER.debug("Modbus TCP check for %s failed: %s", host, err)
            errors["base"] = "cannot_connect_modbus"
        finally:
            await modbus.close()
    return twin, errors


class DimplexConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the config flow for a Dimplex NWPM Touch gateway."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the flow."""
        self._discovered_host: str | None = None
        self._discovered_mac: str | None = None

    @override
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            twin, errors = await async_validate_connection(
                user_input[CONF_HOST],
                user_input[CONF_PASSWORD],
                user_input[CONF_USE_MODBUS],
            )
            if not errors:
                assert twin is not None
                serial = twin.appliance_serial or twin.gateway_serial
                await self.async_set_unique_id(serial)
                self._abort_if_unique_id_configured(
                    updates={CONF_HOST: user_input[CONF_HOST]}
                )
                return self.async_create_entry(
                    title=f"Dimplex {twin.appliance_type or 'WPM'} {serial}",
                    data={
                        **user_input,
                        CONF_MAC: _format_mac(twin.gateway_mac) or self._discovered_mac,
                    },
                )
        suggested = user_input or {CONF_HOST: self._discovered_host}
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                STEP_USER_SCHEMA, suggested
            ),
            errors=errors,
        )

    @override
    async def async_step_dhcp(
        self, discovery_info: DhcpServiceInfo
    ) -> ConfigFlowResult:
        """Handle a gateway discovered via DHCP."""
        mac = dr.format_mac(discovery_info.macaddress)
        for entry in self._async_current_entries(include_ignore=False):
            if entry.data.get(CONF_MAC) != mac:
                continue
            if entry.data[CONF_HOST] != discovery_info.ip:
                self.hass.config_entries.async_update_entry(
                    entry, data={**entry.data, CONF_HOST: discovery_info.ip}
                )
                self.hass.config_entries.async_schedule_reload(entry.entry_id)
            return self.async_abort(reason="already_configured")
        self._async_abort_entries_match({CONF_HOST: discovery_info.ip})
        self._discovered_host = discovery_info.ip
        self._discovered_mac = mac
        self.context["title_placeholders"] = {"name": discovery_info.hostname}
        return await self.async_step_user()

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Handle re-authentication after the gateway password changed."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for the new password."""
        errors: dict[str, str] = {}
        entry = self._get_reauth_entry()
        if user_input is not None:
            twin, errors = await async_validate_connection(
                entry.data[CONF_HOST], user_input[CONF_PASSWORD], False
            )
            if not errors:
                assert twin is not None
                await self.async_set_unique_id(
                    twin.appliance_serial or twin.gateway_serial
                )
                self._abort_if_unique_id_mismatch()
                return self.async_update_reload_and_abort(
                    entry, data_updates={CONF_PASSWORD: user_input[CONF_PASSWORD]}
                )
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=STEP_REAUTH_SCHEMA,
            errors=errors,
            description_placeholders={CONF_HOST: entry.data[CONF_HOST]},
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Allow changing host, password and Modbus usage."""
        errors: dict[str, str] = {}
        entry = self._get_reconfigure_entry()
        if user_input is not None:
            twin, errors = await async_validate_connection(
                user_input[CONF_HOST],
                user_input[CONF_PASSWORD],
                user_input[CONF_USE_MODBUS],
            )
            if not errors:
                assert twin is not None
                await self.async_set_unique_id(
                    twin.appliance_serial or twin.gateway_serial
                )
                self._abort_if_unique_id_mismatch()
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates={
                        **user_input,
                        CONF_MAC: _format_mac(twin.gateway_mac)
                        or entry.data.get(CONF_MAC),
                    },
                )
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(
                STEP_USER_SCHEMA, user_input or entry.data
            ),
            errors=errors,
        )


def _format_mac(mac: str | None) -> str | None:
    """Normalise a MAC address reported by the gateway."""
    return dr.format_mac(mac) if mac else None
