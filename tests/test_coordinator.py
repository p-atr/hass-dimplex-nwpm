"""Tests for push updates, polling and availability handling."""

from datetime import timedelta
from unittest.mock import MagicMock

from freezegun.api import FrozenDateTimeFactory
from homeassistant.config_entries import SOURCE_REAUTH, ConfigEntryState
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from pydimplex_nwpm import DimplexConnectionError
from pymodbus.exceptions import ConnectionException
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.dimplex_nwpm.const import POLL_INTERVAL

from .conftest import TOPIC_TWIN, MockGateway

OUTDOOR = "sensor.dimplex_heat_pump_outdoor_temperature"
PARTY_HOURS = "number.dimplex_heat_pump_party_hours"
HEATING_ENERGY = "sensor.dimplex_heat_pump_heating_energy"
VALVE = "binary_sensor.dimplex_heat_pump_smart_rtc_valve"
LAST_FAULT = "sensor.dimplex_heat_pump_last_fault"
CLOUD = "binary_sensor.dimplex_nwpm_touch_cloud_connection"

pytestmark = pytest.mark.usefixtures("init_integration")


async def _poll(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> None:
    freezer.tick(POLL_INTERVAL + timedelta(seconds=1))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()


async def test_push_values(hass: HomeAssistant, mock_gateway: MockGateway) -> None:
    """Test a changed_on broadcast updates entities immediately."""
    assert hass.states.get(OUTDOOR).state == "13.6"
    mock_gateway.push_values({"1301a": "-2.5", "1500d": "0"})
    await hass.async_block_till_done()
    assert hass.states.get(OUTDOOR).state == "-2.5"
    assert (
        hass.states.get("binary_sensor.dimplex_heat_pump_compressor_1").state == "off"
    )


async def test_push_does_not_postpone_poll(
    hass: HomeAssistant,
    mock_gateway: MockGateway,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test settings are still polled while push updates keep arriving."""
    mock_gateway.values["715i"] = 5
    for _ in range(3):
        freezer.tick(POLL_INTERVAL / 2)
        mock_gateway.push_values({"1301a": "1.0"})
        async_fire_time_changed(hass)
        await hass.async_block_till_done()
    assert hass.states.get(PARTY_HOURS).state == "5.0"


async def test_push_energy_parts_ignored(
    hass: HomeAssistant, mock_gateway: MockGateway, freezer: FrozenDateTimeFactory
) -> None:
    """Test energy counters only change atomically with a poll."""
    before = hass.states.get(HEATING_ENERGY).state
    mock_gateway.push_values({"1300i": "0"})
    await hass.async_block_till_done()
    assert hass.states.get(HEATING_ENERGY).state == before

    mock_gateway.values.update({"1300i": 0, "1301i": 0, "1302i": 1})
    await _poll(hass, freezer)
    assert hass.states.get(HEATING_ENERGY).state == "100000000"


async def test_push_twin_and_history(
    hass: HomeAssistant, mock_gateway: MockGateway
) -> None:
    """Test twin and history broadcasts update the gateway and history sensors."""
    assert hass.states.get(CLOUD).state == "on"
    assert hass.states.get(LAST_FAULT).state == "2025-12-19T07:15:00+00:00"
    meta = {**mock_gateway.twin["meta"], "cloudConnectionState": "0"}
    mock_gateway.push(TOPIC_TWIN, {"meta": meta, "telemetry": {"1301a": "7.5"}})
    mock_gateway.push("extern/broadcast/error_history_state", [])
    await hass.async_block_till_done()
    assert hass.states.get(CLOUD).state == "off"
    assert hass.states.get(OUTDOOR).state == "7.5"
    assert hass.states.get(LAST_FAULT).state == STATE_UNAVAILABLE


async def test_connection_lost_and_restored(
    hass: HomeAssistant, mock_gateway: MockGateway
) -> None:
    """Test entities follow the connection state of the gateway."""
    mock_gateway.set_connected(False)
    await hass.async_block_till_done()
    assert hass.states.get(OUTDOOR).state == STATE_UNAVAILABLE

    mock_gateway.set_connected(True)
    await hass.async_block_till_done()
    assert hass.states.get(OUTDOOR).state == "13.6"


async def test_poll_connection_error(
    hass: HomeAssistant, mock_gateway: MockGateway, freezer: FrozenDateTimeFactory
) -> None:
    """Test a failing poll marks the entities unavailable until it recovers."""
    mock_gateway.get_values.side_effect = DimplexConnectionError("gone")
    await _poll(hass, freezer)
    assert hass.states.get(OUTDOOR).state == STATE_UNAVAILABLE

    mock_gateway.get_values.side_effect = mock_gateway._get_values
    await _poll(hass, freezer)
    assert hass.states.get(OUTDOOR).state == "13.6"


async def test_poll_authentication_failed(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    mock_gateway: MockGateway,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test a rejected reconnect starts the reauth flow."""
    mock_gateway.authentication_failed = True
    await _poll(hass, freezer)
    flows = hass.config_entries.flow.async_progress()
    assert len(flows) == 1
    assert flows[0]["context"]["source"] == SOURCE_REAUTH
    assert init_integration.state is ConfigEntryState.LOADED


async def test_poll_range_not_available(
    hass: HomeAssistant, mock_gateway: MockGateway, freezer: FrozenDateTimeFactory
) -> None:
    """Test a range rejected by the gateway only affects its own entities."""
    del mock_gateway.values["1301a"]
    mock_gateway.values["715i"] = 7
    await _poll(hass, freezer)
    assert hass.states.get(OUTDOOR).state == "13.6"
    assert hass.states.get(PARTY_HOURS).state == "7.0"


async def test_modbus_lost_and_restored(
    hass: HomeAssistant, mock_modbus: MagicMock, freezer: FrozenDateTimeFactory
) -> None:
    """Test only Modbus entities become unavailable when Modbus TCP fails."""
    assert hass.states.get(VALVE).state == "on"
    mock_modbus.read_coils.side_effect = ConnectionException("closed")
    await _poll(hass, freezer)
    assert hass.states.get(VALVE).state == STATE_UNAVAILABLE
    assert hass.states.get(OUTDOOR).state == "13.6"

    mock_modbus.read_coils.side_effect = None
    mock_modbus.read_coils.return_value.bits = [False]
    await _poll(hass, freezer)
    assert hass.states.get(VALVE).state == "off"
