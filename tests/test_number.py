"""Tests for the Dimplex NWPM Touch number platform."""

from unittest.mock import MagicMock

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
            21.0,
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
            "number.dimplex_heat_pump_hot_water_setpoint", 55, "1042u", 55.0, id="plain"
        ),
        pytest.param(
            "number.dimplex_heat_pump_bivalence_parallel_limit_temperature",
            -10,
            "750i",
            -10.0,
            id="signed",
        ),
    ],
)
async def test_set_value(
    hass: HomeAssistant,
    mock_mqtt_client: MagicMock,
    entity_id: str,
    value: float,
    datapoint: str,
    written: float,
) -> None:
    """Test writing a setting over MQTT."""
    await hass.services.async_call(
        NUMBER_DOMAIN,
        SERVICE_SET_VALUE,
        {ATTR_ENTITY_ID: entity_id, ATTR_VALUE: value},
        blocking=True,
    )
    mock_mqtt_client.set_value.assert_awaited_once_with(datapoint, written)
    mock_mqtt_client.get_values.assert_any_await(datapoint)


@pytest.mark.usefixtures("entity_registry_enabled_by_default", "init_integration")
async def test_set_scaled_value(
    hass: HomeAssistant, mock_mqtt_client: MagicMock
) -> None:
    """Test the PV surplus is written in units of 10 W."""
    assert hass.states.get("number.dimplex_heat_pump_pv_surplus").state == "0.0"
    await hass.services.async_call(
        NUMBER_DOMAIN,
        SERVICE_SET_VALUE,
        {ATTR_ENTITY_ID: "number.dimplex_heat_pump_pv_surplus", ATTR_VALUE: 1500},
        blocking=True,
    )
    mock_mqtt_client.set_value.assert_awaited_once_with("2670i", 150.0)


@pytest.mark.usefixtures("entity_registry_enabled_by_default", "init_integration")
@pytest.mark.parametrize(
    "exception",
    [
        pytest.param(DimplexConnectionError("gone"), id="connection"),
        pytest.param(DimplexRequestError(1, "rejected"), id="request"),
    ],
)
async def test_set_value_error(
    hass: HomeAssistant, mock_mqtt_client: MagicMock, exception: Exception
) -> None:
    """Test a failed write raises a translated error."""
    mock_mqtt_client.set_value.side_effect = exception
    with pytest.raises(HomeAssistantError) as excinfo:
        await hass.services.async_call(
            NUMBER_DOMAIN,
            SERVICE_SET_VALUE,
            {
                ATTR_ENTITY_ID: "number.dimplex_heat_pump_party_hours",
                ATTR_VALUE: 4,
            },
            blocking=True,
        )
    assert excinfo.value.translation_key == "write_failed"
    assert excinfo.value.translation_placeholders["datapoint"] == "715u"
