"""Tests for the Dimplex NWPM Touch binary sensor platform."""

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


@pytest.mark.parametrize("init_integration", [Platform.BINARY_SENSOR], indirect=True)
@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_entities(
    hass: HomeAssistant,
    snapshot: SnapshotAssertion,
    entity_registry: er.EntityRegistry,
    device_registry: dr.DeviceRegistry,
    init_integration: MockConfigEntry,
) -> None:
    """Test the binary sensor entities and their device assignment."""
    await snapshot_platform(hass, entity_registry, snapshot, init_integration.entry_id)

    gateway = device_registry.async_get_device_by_identifier(
        (DOMAIN, "A02216104"),
        init_integration.entry_id,
    )
    assert gateway is not None
    assert {
        entity_entry.entity_id
        for entity_entry in er.async_entries_for_device(entity_registry, gateway.id)
    } == {
        "binary_sensor.dimplex_nwpm_touch_heat_pump_connection",
        "binary_sensor.dimplex_nwpm_touch_cloud_connection",
        "binary_sensor.dimplex_nwpm_touch_internet_connection",
    }
