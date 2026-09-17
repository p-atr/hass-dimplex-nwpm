"""Tests for the Dimplex NWPM Touch sensor platform."""

from homeassistant.const import STATE_UNAVAILABLE, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    snapshot_platform,
)
from syrupy.assertion import SnapshotAssertion

from .conftest import MockGateway

pytestmark = pytest.mark.parametrize(
    "init_integration", [Platform.SENSOR], indirect=True
)


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_entities(
    hass: HomeAssistant,
    snapshot: SnapshotAssertion,
    entity_registry: er.EntityRegistry,
    init_integration: MockConfigEntry,
) -> None:
    """Test the sensor entities."""
    await snapshot_platform(hass, entity_registry, snapshot, init_integration.entry_id)


@pytest.mark.usefixtures("init_integration")
async def test_unknown_message_code(
    hass: HomeAssistant, mock_gateway: MockGateway
) -> None:
    """Test an undocumented status code results in an unknown state."""
    assert hass.states.get("sensor.dimplex_heat_pump_status").state == "heating"
    mock_gateway.push_values({"530i": "99"})
    await hass.async_block_till_done()
    assert hass.states.get("sensor.dimplex_heat_pump_status").state == "unknown"


async def test_missing_value_is_unavailable(
    hass: HomeAssistant, init_integration: MockConfigEntry, mock_gateway: MockGateway
) -> None:
    """Test a sensor without a known value is unavailable."""
    init_integration.runtime_data.heat_pump.values.pop("1301a")
    mock_gateway.push_values({})
    await hass.async_block_till_done()
    state = hass.states.get("sensor.dimplex_heat_pump_outdoor_temperature")
    assert state.state == STATE_UNAVAILABLE
