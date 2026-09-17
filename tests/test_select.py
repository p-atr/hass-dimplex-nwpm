"""Tests for the Dimplex NWPM Touch select platform."""

from unittest.mock import MagicMock

from homeassistant.components.select import (
    ATTR_OPTION,
    SERVICE_SELECT_OPTION,
)
from homeassistant.components.select import (
    DOMAIN as SELECT_DOMAIN,
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
    "init_integration", [Platform.SELECT], indirect=True
)


async def test_entities(
    hass: HomeAssistant,
    snapshot: SnapshotAssertion,
    entity_registry: er.EntityRegistry,
    init_integration: MockConfigEntry,
) -> None:
    """Test the select entities."""
    await snapshot_platform(hass, entity_registry, snapshot, init_integration.entry_id)


@pytest.mark.usefixtures("init_integration")
@pytest.mark.parametrize(
    ("entity_id", "option", "datapoint", "code"),
    [
        pytest.param(
            "select.dimplex_heat_pump_operating_mode", "summer", "714u", 0, id="mode"
        ),
        pytest.param(
            "select.dimplex_heat_pump_smart_grid", "green", "2662u", 11, id="smart_grid"
        ),
        pytest.param(
            "select.dimplex_heat_pump_external_lock",
            "active",
            "2663i",
            11,
            id="external_lock",
        ),
    ],
)
async def test_select_option(
    hass: HomeAssistant,
    mock_mqtt_client: MagicMock,
    entity_id: str,
    option: str,
    datapoint: str,
    code: int,
) -> None:
    """Test selecting an option writes the matching code."""
    await hass.services.async_call(
        SELECT_DOMAIN,
        SERVICE_SELECT_OPTION,
        {ATTR_ENTITY_ID: entity_id, ATTR_OPTION: option},
        blocking=True,
    )
    mock_mqtt_client.set_value.assert_awaited_once_with(datapoint, code)


@pytest.mark.usefixtures("init_integration")
async def test_unknown_code(hass: HomeAssistant, mock_mqtt_client: MagicMock) -> None:
    """Test an undocumented mode code results in an unknown option."""
    for listener in mock_mqtt_client.listeners.values:
        listener({"714i": 42})
    await hass.async_block_till_done()
    assert hass.states.get("select.dimplex_heat_pump_operating_mode").state == "unknown"
