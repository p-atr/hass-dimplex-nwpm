"""Tests for the Dimplex NWPM Touch sensor platform."""

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    snapshot_platform,
)
from syrupy.assertion import SnapshotAssertion

from custom_components.dimplex_nwpm.const import DOMAIN

from .conftest import SERIAL


@pytest.mark.parametrize("init_integration", [Platform.SENSOR], indirect=True)
@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_entities(
    hass: HomeAssistant,
    snapshot: SnapshotAssertion,
    entity_registry: er.EntityRegistry,
    device_registry: dr.DeviceRegistry,
    init_integration: MockConfigEntry,
) -> None:
    """Test the sensor entities."""
    await snapshot_platform(hass, entity_registry, snapshot, init_integration.entry_id)

    heat_pump = device_registry.async_get_device_by_identifier(
        (DOMAIN, SERIAL), init_integration.entry_id
    )
    assert heat_pump is not None
    for entity_entry in er.async_entries_for_config_entry(
        entity_registry, init_integration.entry_id
    ):
        assert entity_entry.device_id == heat_pump.id


@pytest.mark.parametrize("init_integration", [Platform.SENSOR], indirect=True)
@pytest.mark.usefixtures("init_integration")
async def test_unknown_message_code(
    hass: HomeAssistant, mock_mqtt_client: object
) -> None:
    """Test an undocumented status code results in an unknown state."""
    assert hass.states.get("sensor.dimplex_heat_pump_status").state == "heating"
    for listener in mock_mqtt_client.listeners.values:  # type: ignore[attr-defined]
        listener({"530i": 99})
    await hass.async_block_till_done()
    state = hass.states.get("sensor.dimplex_heat_pump_status")
    assert state.state == "unknown"
    assert state.attributes["code"] == 99


@pytest.mark.parametrize("init_integration", [Platform.SENSOR], indirect=True)
@pytest.mark.usefixtures("entity_registry_enabled_by_default", "init_integration")
async def test_unsupported_equipment_has_no_entities(hass: HomeAssistant) -> None:
    """Test entities of equipment the installation lacks are not created."""
    assert hass.states.get("sensor.dimplex_heat_pump_flow_rate").state == "576"
    assert hass.states.get("sensor.dimplex_heat_pump_system_pressure").state == "1.8"
    assert hass.states.get("sensor.dimplex_heat_pump_thermal_power").state == "12500"
    assert hass.states.get("sensor.dimplex_heat_pump_environmental_energy").state == (
        "29032"
    )
    assert (
        hass.states.get("sensor.dimplex_heat_pump_solar_collector_temperature") is None
    )
    assert hass.states.get("sensor.dimplex_heat_pump_pool_energy") is None
