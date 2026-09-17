"""Tests for the Dimplex NWPM Touch water heater platform."""

from homeassistant.components.water_heater import (
    DOMAIN as WATER_HEATER_DOMAIN,
)
from homeassistant.components.water_heater import (
    SERVICE_SET_TEMPERATURE,
)
from homeassistant.const import ATTR_ENTITY_ID, ATTR_TEMPERATURE, Platform
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
    "init_integration", [Platform.WATER_HEATER], indirect=True
)

ENTITY_ID = "water_heater.dimplex_heat_pump_hot_water"


async def test_entities(
    hass: HomeAssistant,
    snapshot: SnapshotAssertion,
    entity_registry: er.EntityRegistry,
    init_integration: MockConfigEntry,
) -> None:
    """Test the water heater entity."""
    await snapshot_platform(hass, entity_registry, snapshot, init_integration.entry_id)


@pytest.mark.usefixtures("init_integration")
async def test_set_temperature(hass: HomeAssistant, mock_gateway: MockGateway) -> None:
    """Test setting the hot water setpoint."""
    await hass.services.async_call(
        WATER_HEATER_DOMAIN,
        SERVICE_SET_TEMPERATURE,
        {ATTR_ENTITY_ID: ENTITY_ID, ATTR_TEMPERATURE: 55},
        blocking=True,
    )
    mock_gateway.set_value.assert_awaited_once_with("1042u", 55)
    assert hass.states.get(ENTITY_ID).attributes[ATTR_TEMPERATURE] == 55


@pytest.mark.usefixtures("init_integration")
async def test_limits_fall_back_to_datapoint_range(
    hass: HomeAssistant, init_integration: MockConfigEntry, mock_gateway: MockGateway
) -> None:
    """Test the setpoint range defaults to the datapoint limits."""
    values = init_integration.runtime_data.heat_pump.values
    del values["1044i"], values["1045i"]
    mock_gateway.push_values({})
    await hass.async_block_till_done()
    state = hass.states.get(ENTITY_ID)
    assert state.attributes["min_temp"] == 10
    assert state.attributes["max_temp"] == 85
