"""Tests for the Dimplex NWPM Touch water heater platform."""

from unittest.mock import MagicMock

from homeassistant.components.water_heater import (
    ATTR_TEMPERATURE,
    SERVICE_SET_TEMPERATURE,
    STATE_HEAT_PUMP,
)
from homeassistant.components.water_heater import (
    DOMAIN as WATER_HEATER_DOMAIN,
)
from homeassistant.const import ATTR_ENTITY_ID, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    snapshot_platform,
)
from syrupy.assertion import SnapshotAssertion

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
async def test_set_temperature(
    hass: HomeAssistant, mock_mqtt_client: MagicMock
) -> None:
    """Test setting the hot water setpoint."""
    await hass.services.async_call(
        WATER_HEATER_DOMAIN,
        SERVICE_SET_TEMPERATURE,
        {ATTR_ENTITY_ID: ENTITY_ID, ATTR_TEMPERATURE: 55},
        blocking=True,
    )
    mock_mqtt_client.set_value.assert_awaited_once_with("1042u", 55)


@pytest.mark.usefixtures("init_integration")
async def test_operation_follows_status(
    hass: HomeAssistant, mock_mqtt_client: MagicMock
) -> None:
    """Test the operation state reflects hot water preparation."""
    assert hass.states.get(ENTITY_ID).state == "off"
    for listener in mock_mqtt_client.listeners.values:
        listener({"530i": 4})
    await hass.async_block_till_done()
    assert hass.states.get(ENTITY_ID).state == STATE_HEAT_PUMP
