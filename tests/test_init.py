"""Tests for the Dimplex NWPM Touch integration setup."""

from unittest.mock import MagicMock

from homeassistant.config_entries import SOURCE_REAUTH, ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from pydimplex_nwpm import (
    DimplexAuthenticationError,
    DimplexConnectionError,
    DimplexTimeoutError,
)
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.dimplex_nwpm.const import CONF_USE_MODBUS, DOMAIN

from .conftest import SERIAL


async def test_load_unload_config_entry(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_mqtt_client: MagicMock,
    mock_modbus_client: MagicMock,
) -> None:
    """Test the configuration entry loading and unloading."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.LOADED
    mock_mqtt_client.connect.assert_awaited_once()
    mock_mqtt_client.clear_cache.assert_awaited_once()
    mock_modbus_client.read_registers.assert_not_called()
    assert mock_modbus_client.read_coils.await_count == 1

    await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.NOT_LOADED
    mock_mqtt_client.disconnect.assert_awaited_once()
    mock_modbus_client.close.assert_awaited_once()
    assert not mock_mqtt_client.listeners.values


async def test_devices(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    device_registry: dr.DeviceRegistry,
) -> None:
    """Test the heat pump device is linked to the gateway device."""
    gateway = device_registry.async_get_device_by_identifier(
        (DOMAIN, "A02216104"), init_integration.entry_id
    )
    assert gateway is not None
    assert gateway.connections == {(dr.CONNECTION_NETWORK_MAC, "00:0a:5c:12:34:56")}
    assert gateway.sw_version == "10.0.1"
    heat_pump = device_registry.async_get_device_by_identifier(
        (DOMAIN, SERIAL), init_integration.entry_id
    )
    assert heat_pump is not None
    assert heat_pump.via_device_id == gateway.id
    assert heat_pump.sw_version == "M3.13"
    assert heat_pump.serial_number == SERIAL


@pytest.mark.usefixtures("mock_modbus_client")
@pytest.mark.parametrize(
    ("exception", "translation_key"),
    [
        pytest.param(DimplexConnectionError("refused"), "cannot_connect", id="refused"),
        pytest.param(DimplexTimeoutError("silent"), "cannot_connect", id="timeout"),
    ],
)
async def test_config_entry_not_ready(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_mqtt_client: MagicMock,
    exception: Exception,
    translation_key: str,
) -> None:
    """Test the entry retries when the gateway cannot be reached."""
    mock_mqtt_client.connect.side_effect = exception
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY
    assert mock_config_entry.error_reason_translation_key == translation_key
    mock_mqtt_client.disconnect.assert_awaited()


@pytest.mark.usefixtures("mock_modbus_client")
async def test_config_entry_twin_timeout(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_mqtt_client: MagicMock,
) -> None:
    """Test the entry retries when the gateway never publishes its twin."""
    mock_mqtt_client.wait_for_twin.side_effect = DimplexTimeoutError("no twin")
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY


@pytest.mark.usefixtures("mock_modbus_client")
async def test_config_entry_authentication_failed(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_mqtt_client: MagicMock,
) -> None:
    """Test a rejected password starts the reauth flow."""
    mock_mqtt_client.connect.side_effect = DimplexAuthenticationError("nope")
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.SETUP_ERROR
    flows = hass.config_entries.flow.async_progress()
    assert len(flows) == 1
    assert flows[0]["context"]["source"] == SOURCE_REAUTH
    assert flows[0]["context"]["entry_id"] == mock_config_entry.entry_id


@pytest.mark.usefixtures("mock_mqtt_client")
async def test_modbus_disabled(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_modbus_client: MagicMock,
) -> None:
    """Test no Modbus entities are created when Modbus TCP is disabled."""
    mock_config_entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(
        mock_config_entry, data={**mock_config_entry.data, CONF_USE_MODBUS: False}
    )
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.LOADED
    mock_modbus_client.read_coils.assert_not_called()
    assert hass.states.get("binary_sensor.dimplex_heat_pump_smart_rtc_valve") is None
    assert hass.states.get("sensor.dimplex_heat_pump_outdoor_temperature") is not None
