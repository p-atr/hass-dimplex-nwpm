"""Tests for the Dimplex NWPM Touch config flow."""

from unittest.mock import MagicMock

from homeassistant.config_entries import SOURCE_DHCP, SOURCE_USER, ConfigEntryState
from homeassistant.const import CONF_HOST, CONF_MAC, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers.service_info.dhcp import DhcpServiceInfo
from pydimplex_nwpm import (
    DimplexAuthenticationError,
    DimplexConnectionError,
    DimplexTimeoutError,
    TwinState,
)
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.dimplex_nwpm.const import CONF_USE_MODBUS, DOMAIN

from .conftest import HOST, MAC, PASSWORD, SERIAL

pytestmark = pytest.mark.usefixtures(
    "mock_setup_entry", "mock_mqtt_client", "mock_modbus_client"
)

USER_INPUT = {CONF_HOST: HOST, CONF_PASSWORD: PASSWORD, CONF_USE_MODBUS: True}
ENTRY_DATA = {**USER_INPUT, CONF_MAC: MAC}


async def test_user_flow(hass: HomeAssistant) -> None:
    """Test the full happy path user flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=USER_INPUT
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == f"Dimplex WPM {SERIAL}"
    assert result["data"] == ENTRY_DATA
    assert result["result"].unique_id == SERIAL


async def test_user_flow_without_modbus(
    hass: HomeAssistant, mock_modbus_client: MagicMock
) -> None:
    """Test that Modbus TCP is not probed when it is disabled."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={**USER_INPUT, CONF_USE_MODBUS: False}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_USE_MODBUS] is False
    mock_modbus_client.read_software_version.assert_not_called()


@pytest.mark.parametrize(
    ("side_effect", "expected_error"),
    [
        pytest.param(DimplexConnectionError("boom"), "cannot_connect", id="connect"),
        pytest.param(DimplexTimeoutError("slow"), "cannot_connect", id="timeout"),
        pytest.param(DimplexAuthenticationError("no"), "invalid_auth", id="auth"),
    ],
)
async def test_user_flow_mqtt_errors(
    hass: HomeAssistant,
    mock_mqtt_client: MagicMock,
    side_effect: Exception,
    expected_error: str,
) -> None:
    """Test MQTT errors are shown and the flow can recover."""
    mock_mqtt_client.connect.side_effect = side_effect
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=USER_INPUT
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": expected_error}
    mock_mqtt_client.disconnect.assert_called()

    mock_mqtt_client.connect.side_effect = None
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=USER_INPUT
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_user_flow_modbus_error(
    hass: HomeAssistant, mock_modbus_client: MagicMock
) -> None:
    """Test an unreachable Modbus TCP server is reported."""
    mock_modbus_client.read_software_version.side_effect = DimplexConnectionError(
        "closed"
    )
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=USER_INPUT
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect_modbus"}
    mock_modbus_client.close.assert_called()

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={**USER_INPUT, CONF_USE_MODBUS: False}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_user_flow_no_serial(
    hass: HomeAssistant, mock_mqtt_client: MagicMock
) -> None:
    """Test a gateway without serial numbers cannot be configured."""
    mock_mqtt_client.wait_for_twin.return_value = TwinState.from_payload({})
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=USER_INPUT
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "no_serial"}


async def test_user_flow_already_configured(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test configuring the same heat pump again updates the host."""
    mock_config_entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={**USER_INPUT, CONF_HOST: "127.0.0.2"}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert mock_config_entry.data[CONF_HOST] == "127.0.0.2"


async def test_dhcp_flow(hass: HomeAssistant) -> None:
    """Test a gateway discovered via DHCP."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_DHCP},
        data=DhcpServiceInfo(
            ip=HOST, hostname="pcoweb123456", macaddress="000a5c123456"
        ),
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["data_schema"] is not None
    host_field = next(
        key for key in result["data_schema"].schema if key.schema == CONF_HOST
    )
    assert host_field.description == {"suggested_value": HOST}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=USER_INPUT
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == ENTRY_DATA


async def test_dhcp_flow_updates_host(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test DHCP discovery of a known gateway updates its IP address."""
    mock_config_entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_DHCP},
        data=DhcpServiceInfo(
            ip="127.0.0.2", hostname="pcoweb123456", macaddress="000a5c123456"
        ),
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert mock_config_entry.data[CONF_HOST] == "127.0.0.2"


async def test_dhcp_flow_known_host(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test DHCP discovery of an already configured host is ignored."""
    mock_config_entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_DHCP},
        data=DhcpServiceInfo(
            ip=HOST, hostname="pcoweb654321", macaddress="000a5c654321"
        ),
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert mock_config_entry.data[CONF_MAC] == MAC


async def test_reauth_flow(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_mqtt_client: MagicMock
) -> None:
    """Test re-authentication with a new password."""
    mock_config_entry.add_to_hass(hass)
    result = await mock_config_entry.start_reauth_flow(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    mock_mqtt_client.connect.side_effect = DimplexAuthenticationError("no")
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_PASSWORD: "wrong"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}

    mock_mqtt_client.connect.side_effect = None
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_PASSWORD: "NewPassword1"}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert mock_config_entry.data[CONF_PASSWORD] == "NewPassword1"


async def test_reauth_flow_other_device(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_mqtt_client: MagicMock
) -> None:
    """Test re-authentication against a different heat pump is rejected."""
    mock_config_entry.add_to_hass(hass)
    mock_mqtt_client.wait_for_twin.return_value = TwinState.from_payload(
        {"meta": {"applianceSerial": "other"}}
    )
    result = await mock_config_entry.start_reauth_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_PASSWORD: PASSWORD}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "unique_id_mismatch"


async def test_reconfigure_flow(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test reconfiguring host, password and Modbus usage."""
    mock_config_entry.add_to_hass(hass)
    result = await mock_config_entry.start_reconfigure_flow(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_HOST: "127.0.0.3",
            CONF_PASSWORD: "NewPassword1",
            CONF_USE_MODBUS: False,
        },
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert mock_config_entry.data == {
        CONF_HOST: "127.0.0.3",
        CONF_PASSWORD: "NewPassword1",
        CONF_USE_MODBUS: False,
        CONF_MAC: MAC,
    }
    assert mock_config_entry.state is ConfigEntryState.LOADED


async def test_reconfigure_flow_other_device(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_mqtt_client: MagicMock
) -> None:
    """Test reconfiguring to a different heat pump is rejected."""
    mock_config_entry.add_to_hass(hass)
    mock_mqtt_client.wait_for_twin.return_value = TwinState.from_payload(
        {"meta": {"applianceSerial": "other"}}
    )
    result = await mock_config_entry.start_reconfigure_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=USER_INPUT
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "unique_id_mismatch"
