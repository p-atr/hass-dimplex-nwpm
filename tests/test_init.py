"""Tests for the Dimplex NWPM Touch integration setup."""

from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.config_entries import SOURCE_REAUTH, ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from pydimplex_nwpm import DimplexAuthenticationError, DimplexConnectionError
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.dimplex_nwpm.const import CONF_USE_MODBUS, DOMAIN

from .conftest import SERIAL, MockGateway


async def test_load_unload_config_entry(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    mock_gateway: MockGateway,
    mock_modbus: MagicMock,
) -> None:
    """Test the configuration entry loading and unloading."""
    assert init_integration.state is ConfigEntryState.LOADED
    mock_gateway.connect.assert_awaited_once()
    mock_modbus.read_coils.assert_awaited_once_with(177)

    await hass.config_entries.async_unload(init_integration.entry_id)
    await hass.async_block_till_done()

    assert init_integration.state is ConfigEntryState.NOT_LOADED
    mock_gateway.disconnect.assert_awaited_once()
    mock_modbus.close.assert_called_once()


async def test_devices(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    device_registry: dr.DeviceRegistry,
) -> None:
    """Test the heat pump device is linked to the gateway device."""
    gateway = device_registry.async_get_device_by_identifier(
        (DOMAIN, "A02216104"),
        init_integration.entry_id,
    )
    assert gateway is not None
    assert gateway.name == "Dimplex NWPM Touch"
    assert gateway.connections == {(dr.CONNECTION_NETWORK_MAC, "00:0a:5c:12:34:56")}
    assert gateway.sw_version == "A2.1.7-B2.1.7"
    assert gateway.hw_version is None
    heat_pump = device_registry.async_get_device_by_identifier(
        (DOMAIN, SERIAL),
        init_integration.entry_id,
    )
    assert heat_pump is not None
    assert heat_pump.name == "Dimplex heat pump"
    assert heat_pump.model == "WPM"
    assert heat_pump.via_device_id == gateway.id
    assert heat_pump.sw_version == "M3.13"


@pytest.mark.usefixtures("mock_modbus")
async def test_setup_retry_on_connection_error(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_gateway: MockGateway,
) -> None:
    """Test the entry retries when the gateway cannot be reached."""
    mock_gateway.connect.side_effect = DimplexConnectionError("refused")
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY
    assert mock_config_entry.error_reason_translation_key == "cannot_connect"
    mock_gateway.disconnect.assert_awaited()


@pytest.mark.usefixtures("mock_modbus")
async def test_setup_retry_without_twin(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_gateway: MockGateway,
) -> None:
    """Test the entry retries when the gateway never publishes its twin."""
    mock_gateway.connect.side_effect = None
    mock_config_entry.add_to_hass(hass)
    with patch("pydimplex_nwpm.heat_pump.DEFAULT_TIMEOUT", 0):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY


@pytest.mark.usefixtures("mock_modbus")
async def test_setup_authentication_failed(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_gateway: MockGateway,
) -> None:
    """Test a rejected password starts the reauth flow."""
    mock_gateway.connect.side_effect = DimplexAuthenticationError("nope")
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.SETUP_ERROR
    flows = hass.config_entries.flow.async_progress()
    assert len(flows) == 1
    assert flows[0]["context"]["source"] == SOURCE_REAUTH


@pytest.mark.usefixtures("mock_gateway")
async def test_modbus_disabled(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test no Modbus client and entities exist when Modbus TCP is disabled."""
    mock_config_entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(
        mock_config_entry, data={**mock_config_entry.data, CONF_USE_MODBUS: False}
    )
    modbus = AsyncMock()
    with patch("pydimplex_nwpm.heat_pump.AsyncModbusTcpClient", modbus):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.LOADED
    modbus.assert_not_called()
    assert hass.states.get("binary_sensor.dimplex_heat_pump_smart_rtc_valve") is None
    assert hass.states.get("sensor.dimplex_heat_pump_outdoor_temperature") is not None
