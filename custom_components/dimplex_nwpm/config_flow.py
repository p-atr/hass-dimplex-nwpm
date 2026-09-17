"""Config flow for the Dimplex NWPM Touch integration."""

from collections.abc import Mapping
import logging
from typing import Any, Self, override

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_MAC, CONF_PASSWORD
from homeassistant.helpers.device_registry import format_mac
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
    DimplexHeatPump,
    DimplexModbusError,
    TwinState,
)
import voluptuous as vol

from .const import CONF_USE_MODBUS, DOMAIN

_LOGGER = logging.getLogger(__name__)

PASSWORD_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_PASSWORD): TextSelector(
            TextSelectorConfig(
                type=TextSelectorType.PASSWORD, autocomplete="current-password"
            )
        ),
    }
)
CONNECTION_SCHEMA = PASSWORD_SCHEMA.extend(
    {vol.Required(CONF_USE_MODBUS, default=False): BooleanSelector()}
)
USER_SCHEMA = vol.Schema({vol.Required(CONF_HOST): TextSelector()}).extend(
    CONNECTION_SCHEMA.schema
)


async def _async_validate(
    host: str, user_input: Mapping[str, Any]
) -> tuple[TwinState | None, dict[str, str]]:
    """Connect with the given settings and return the device twin."""
    heat_pump = DimplexHeatPump(
        host,
        user_input[CONF_PASSWORD],
        use_modbus=user_input.get(CONF_USE_MODBUS, False),
    )
    try:
        twin = await heat_pump.connect()
        if heat_pump.modbus_enabled:
            await heat_pump.read_modbus()
    except DimplexAuthenticationError:
        return None, {"base": "invalid_auth"}
    except DimplexModbusError:
        return None, {"base": "cannot_connect_modbus"}
    except DimplexConnectionError:
        return None, {"base": "cannot_connect"}
    except Exception:
        _LOGGER.exception("Unexpected exception")
        return None, {"base": "unknown"}
    finally:
        await heat_pump.disconnect()
    if twin.appliance_serial is None:
        return None, {"base": "no_serial"}
    return twin, {}


def _mac(twin: TwinState, fallback: str | None) -> str | None:
    return format_mac(twin.gateway_mac) if twin.gateway_mac else fallback


class DimplexConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the config flow for a Dimplex NWPM Touch gateway."""

    VERSION = 1

    _host: str | None = None
    _mac: str | None = None

    @override
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            twin, errors = await _async_validate(user_input[CONF_HOST], user_input)
            if twin is not None:
                return await self._async_create_entry(user_input, twin)
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(USER_SCHEMA, user_input),
            errors=errors,
        )

    @override
    async def async_step_dhcp(
        self, discovery_info: DhcpServiceInfo
    ) -> ConfigFlowResult:
        """Handle a gateway discovered via DHCP."""
        mac = format_mac(discovery_info.macaddress)
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
        self._host = discovery_info.ip
        self._mac = mac
        if self.hass.config_entries.flow.async_has_matching_flow(self):
            return self.async_abort(reason="already_in_progress")
        self.context["title_placeholders"] = {"name": discovery_info.hostname}
        return await self.async_step_dhcp_confirm()

    @override
    def is_matching(self, other_flow: Self) -> bool:
        """Return True if the other flow discovered the same gateway."""
        return other_flow._host == self._host

    async def async_step_dhcp_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for the password of a discovered gateway."""
        assert self._host is not None
        errors: dict[str, str] = {}
        if user_input is not None:
            twin, errors = await _async_validate(self._host, user_input)
            if twin is not None:
                return await self._async_create_entry(
                    {CONF_HOST: self._host, **user_input}, twin
                )
        return self.async_show_form(
            step_id="dhcp_confirm",
            data_schema=CONNECTION_SCHEMA,
            errors=errors,
            description_placeholders={CONF_HOST: self._host},
        )

    async def _async_create_entry(
        self, data: dict[str, Any], twin: TwinState
    ) -> ConfigFlowResult:
        await self.async_set_unique_id(twin.appliance_serial)
        self._abort_if_unique_id_configured(updates={CONF_HOST: data[CONF_HOST]})
        return self.async_create_entry(
            title=f"Dimplex {twin.appliance_type or 'WPM'} {twin.appliance_serial}",
            data={**data, CONF_MAC: _mac(twin, self._mac)},
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Handle re-authentication after the gateway password changed."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for the new password."""
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            twin, errors = await _async_validate(entry.data[CONF_HOST], user_input)
            if twin is not None:
                await self.async_set_unique_id(twin.appliance_serial)
                self._abort_if_unique_id_mismatch()
                return self.async_update_reload_and_abort(
                    entry, data_updates=user_input
                )
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=PASSWORD_SCHEMA,
            errors=errors,
            description_placeholders={CONF_HOST: entry.data[CONF_HOST]},
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Allow changing host, password and Modbus usage."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            twin, errors = await _async_validate(user_input[CONF_HOST], user_input)
            if twin is not None:
                await self.async_set_unique_id(twin.appliance_serial)
                self._abort_if_unique_id_mismatch()
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates={
                        **user_input,
                        CONF_MAC: _mac(twin, entry.data.get(CONF_MAC)),
                    },
                )
        suggested = {
            key: value
            for key, value in (user_input or entry.data).items()
            if key != CONF_PASSWORD
        }
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(USER_SCHEMA, suggested),
            errors=errors,
        )
