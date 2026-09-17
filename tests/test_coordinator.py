"""Tests for push updates, polling and availability handling."""

from datetime import timedelta
from unittest.mock import MagicMock

from freezegun.api import FrozenDateTimeFactory
from homeassistant.config_entries import SOURCE_REAUTH, ConfigEntryState
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from pydimplex_nwpm import (
    DimplexAuthenticationError,
    DimplexConnectionError,
    DimplexRequestError,
    HistoryEntry,
    TwinState,
)
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.dimplex_nwpm.const import POLL_INTERVAL

from .conftest import load_twin

OUTDOOR = "sensor.dimplex_heat_pump_outdoor_temperature"
THERMAL_POWER = "sensor.dimplex_heat_pump_thermal_power"
VALVE = "binary_sensor.dimplex_heat_pump_smart_rtc_valve"
LAST_FAULT = "sensor.dimplex_heat_pump_last_fault"
COMPRESSOR = "binary_sensor.dimplex_heat_pump_compressor_1"
CLOUD = "binary_sensor.dimplex_nwpm_touch_cloud_connection"

pytestmark = pytest.mark.usefixtures("init_integration")


async def test_push_values(hass: HomeAssistant, mock_mqtt_client: MagicMock) -> None:
    """Test a changed_on broadcast updates entities immediately."""
    assert hass.states.get(OUTDOOR).state == "13.6"
    assert hass.states.get(COMPRESSOR).state == "on"

    for listener in mock_mqtt_client.listeners.values:
        listener({"1301a": -2.5, "1500d": False})
    await hass.async_block_till_done()

    assert hass.states.get(OUTDOOR).state == "-2.5"
    assert hass.states.get(COMPRESSOR).state == "off"


async def test_push_twin(hass: HomeAssistant, mock_mqtt_client: MagicMock) -> None:
    """Test a device twin broadcast updates telemetry and gateway state."""
    assert hass.states.get(CLOUD).state == "on"
    twin = await load_twin(hass)
    updated = TwinState.from_payload(
        {
            "meta": {**twin.meta, "cloudConnectionState": "0"},
            "telemetry": {"1301a": "7.5"},
        }
    )
    mock_mqtt_client.twin = updated
    for listener in mock_mqtt_client.listeners.twin:
        listener(updated)
    await hass.async_block_till_done()

    assert hass.states.get(CLOUD).state == "off"
    assert hass.states.get(OUTDOOR).state == "7.5"


async def test_push_history(hass: HomeAssistant, mock_mqtt_client: MagicMock) -> None:
    """Test a fault history broadcast updates the last fault sensor."""
    assert hass.states.get(LAST_FAULT).state == "2025-12-19T07:15:00+00:00"
    mock_mqtt_client.error_history = []
    for listener in mock_mqtt_client.listeners.error_history:
        listener([])
    await hass.async_block_till_done()
    assert hass.states.get(LAST_FAULT).state == STATE_UNAVAILABLE


async def test_connection_lost_and_restored(
    hass: HomeAssistant, mock_mqtt_client: MagicMock
) -> None:
    """Test entities become unavailable while the gateway is disconnected."""
    mock_mqtt_client.connected = False
    for listener in mock_mqtt_client.listeners.connection:
        listener(False)
    await hass.async_block_till_done()
    assert hass.states.get(OUTDOOR).state == STATE_UNAVAILABLE

    mock_mqtt_client.connected = True
    mock_mqtt_client.clear_cache.reset_mock()
    for listener in mock_mqtt_client.listeners.connection:
        listener(True)
    await hass.async_block_till_done()
    assert hass.states.get(OUTDOOR).state == "13.6"
    mock_mqtt_client.clear_cache.assert_awaited_once()


async def test_poll_connection_error(
    hass: HomeAssistant,
    mock_mqtt_client: MagicMock,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test a failing poll marks all entities unavailable."""
    mock_mqtt_client.get_values.side_effect = DimplexConnectionError("gone")
    freezer.tick(POLL_INTERVAL + timedelta(seconds=1))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert hass.states.get(OUTDOOR).state == STATE_UNAVAILABLE


async def test_poll_disconnected(
    hass: HomeAssistant,
    mock_mqtt_client: MagicMock,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test polling while disconnected marks all entities unavailable."""
    mock_mqtt_client.connected = False
    mock_mqtt_client.get_values.reset_mock()
    freezer.tick(POLL_INTERVAL + timedelta(seconds=1))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert hass.states.get(OUTDOOR).state == STATE_UNAVAILABLE
    mock_mqtt_client.get_values.assert_not_called()


async def test_poll_authentication_failed(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    mock_mqtt_client: MagicMock,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test a rejected reconnect starts the reauth flow."""
    mock_mqtt_client.connected = False
    mock_mqtt_client.authentication_failed = True
    freezer.tick(POLL_INTERVAL + timedelta(seconds=1))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    flows = hass.config_entries.flow.async_progress()
    assert len(flows) == 1
    assert flows[0]["context"]["source"] == SOURCE_REAUTH
    assert init_integration.state is ConfigEntryState.LOADED


async def test_poll_range_not_available(
    hass: HomeAssistant,
    mock_mqtt_client: MagicMock,
    freezer: FrozenDateTimeFactory,
    values: dict[str, float],
) -> None:
    """Test a datapoint range rejected by the gateway only affects its entities."""
    original = mock_mqtt_client.get_values.side_effect

    async def get_values(name: str) -> dict[str, float]:
        if name == "1285-1305a":
            raise DimplexRequestError(1, "Requested value not provided")
        return await original(name)

    mock_mqtt_client.get_values.side_effect = get_values
    for listener in mock_mqtt_client.listeners.values:
        listener({"1301a": 9.9})
    await hass.async_block_till_done()
    freezer.tick(POLL_INTERVAL + timedelta(seconds=1))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    # last pushed value survives, other polled values are refreshed
    assert hass.states.get(OUTDOOR).state == "9.9"
    assert hass.states.get(THERMAL_POWER).state == "12500"


async def test_modbus_lost_and_restored(
    hass: HomeAssistant,
    mock_modbus_client: MagicMock,
    freezer: FrozenDateTimeFactory,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test only Modbus entities become unavailable when Modbus TCP fails."""
    assert hass.states.get(VALVE).state == "on"
    mock_modbus_client.read_coils.side_effect = DimplexConnectionError("closed")
    freezer.tick(POLL_INTERVAL + timedelta(seconds=1))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    assert hass.states.get(VALVE).state == STATE_UNAVAILABLE
    assert hass.states.get(OUTDOOR).state == "13.6"
    assert "Modbus TCP connection to 127.0.0.127 lost" in caplog.text

    async def read_coils(address: int, count: int = 1) -> list[bool]:
        return [False]

    mock_modbus_client.read_coils.side_effect = read_coils
    freezer.tick(POLL_INTERVAL + timedelta(seconds=1))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    assert hass.states.get(VALVE).state == "off"
    assert "Modbus TCP connection to 127.0.0.127 restored" in caplog.text


async def test_history_entries_are_models(mock_mqtt_client: MagicMock) -> None:
    """Sanity check the fixture history entries."""
    assert isinstance(mock_mqtt_client.error_history[0], HistoryEntry)


async def test_authentication_error_is_connection_error() -> None:
    """The reauth path relies on the exception hierarchy."""
    assert issubclass(DimplexAuthenticationError, DimplexConnectionError)
