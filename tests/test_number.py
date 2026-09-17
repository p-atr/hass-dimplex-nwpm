"""Tests for the Dimplex NWPM Touch number platform."""

from homeassistant.components.number import (
    ATTR_VALUE,
    SERVICE_SET_VALUE,
)
from homeassistant.components.number import (
    DOMAIN as NUMBER_DOMAIN,
)
from homeassistant.const import ATTR_ENTITY_ID, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from pydimplex_nwpm import DimplexConnectionError, DimplexRequestError
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    snapshot_platform,
)
from syrupy.assertion import SnapshotAssertion

from .conftest import MockGateway

pytestmark = pytest.mark.parametrize(
    "init_integration", [Platform.NUMBER], indirect=True
)


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_entities(
    hass: HomeAssistant,
    snapshot: SnapshotAssertion,
    entity_registry: er.EntityRegistry,
    init_integration: MockConfigEntry,
) -> None:
    """Test the number entities."""
    await snapshot_platform(hass, entity_registry, snapshot, init_integration.entry_id)


@pytest.mark.usefixtures("entity_registry_enabled_by_default", "init_integration")
@pytest.mark.parametrize(
    ("entity_id", "value", "datapoint", "written"),
    [
        pytest.param(
            "number.dimplex_heat_pump_heating_curve_parallel_shift",
            2,
            "767u",
            21,
            id="offset",
        ),
        pytest.param(
            "number.dimplex_heat_pump_room_temperature_setpoint",
            21.5,
            "700a",
            21.5,
            id="analog",
        ),
        pytest.param(
            "number.dimplex_heat_pump_bivalence_parallel_limit_temperature",
            -10,
            "750i",
            -10,
            id="signed",
        ),
        pytest.param(
            "number.dimplex_heat_pump_pv_surplus", 1500, "2670i", 150, id="scaled"
        ),
    ],
)
async def test_set_value(
    hass: HomeAssistant,
    mock_gateway: MockGateway,
    entity_id: str,
    value: float,
    datapoint: str,
    written: float,
) -> None:
    """Test writing a setting and reading it back."""
    await hass.services.async_call(
        NUMBER_DOMAIN,
        SERVICE_SET_VALUE,
        {ATTR_ENTITY_ID: entity_id, ATTR_VALUE: value},
        blocking=True,
    )
    mock_gateway.set_value.assert_awaited_once_with(datapoint, written)
    mock_gateway.get_values.assert_awaited_with(datapoint)
    assert float(hass.states.get(entity_id).state) == value


@pytest.mark.usefixtures("init_integration")
@pytest.mark.parametrize(
    "exception",
    [
        pytest.param(DimplexConnectionError("gone"), id="connection"),
        pytest.param(DimplexRequestError(1, "rejected"), id="request"),
    ],
)
async def test_set_value_error(
    hass: HomeAssistant, mock_gateway: MockGateway, exception: Exception
) -> None:
    """Test a failed write raises a translated error."""
    mock_gateway.set_value.side_effect = exception
    with pytest.raises(HomeAssistantError) as excinfo:
        await hass.services.async_call(
            NUMBER_DOMAIN,
            SERVICE_SET_VALUE,
            {ATTR_ENTITY_ID: "number.dimplex_heat_pump_party_hours", ATTR_VALUE: 4},
            blocking=True,
        )
    assert excinfo.value.translation_key == "write_failed"
