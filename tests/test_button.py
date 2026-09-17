"""Tests for the Dimplex NWPM Touch button platform."""

from datetime import datetime

from homeassistant.components.button import DOMAIN as BUTTON_DOMAIN
from homeassistant.components.button import SERVICE_PRESS
from homeassistant.const import ATTR_ENTITY_ID, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from pydimplex_nwpm import DimplexConnectionError
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    snapshot_platform,
)
from syrupy.assertion import SnapshotAssertion

from .conftest import MockGateway

pytestmark = [
    pytest.mark.parametrize("init_integration", [Platform.BUTTON], indirect=True),
    pytest.mark.freeze_time("2026-09-17 10:00:00+00:00"),
]

ENTITY_ID = "button.dimplex_heat_pump_synchronize_time"


async def test_entities(
    hass: HomeAssistant,
    snapshot: SnapshotAssertion,
    entity_registry: er.EntityRegistry,
    init_integration: MockConfigEntry,
) -> None:
    """Test the button entity."""
    await snapshot_platform(hass, entity_registry, snapshot, init_integration.entry_id)


async def _press(hass: HomeAssistant) -> None:
    await hass.services.async_call(
        BUTTON_DOMAIN, SERVICE_PRESS, {ATTR_ENTITY_ID: ENTITY_ID}, blocking=True
    )


@pytest.mark.usefixtures("init_integration")
async def test_sync_time_uses_appliance_timezone(
    hass: HomeAssistant, mock_gateway: MockGateway
) -> None:
    """Test the appliance clock is set in the appliance's own time zone."""
    await _press(hass)
    written = mock_gateway.set_appliance_time.await_args.args[0]
    assert written.replace(tzinfo=None) == datetime(2026, 9, 17, 12, 0, 0)


@pytest.mark.usefixtures("init_integration")
async def test_sync_time_falls_back_to_local_timezone(
    hass: HomeAssistant, init_integration: MockConfigEntry, mock_gateway: MockGateway
) -> None:
    """Test Home Assistant's time zone is used when the gateway reported none."""
    init_integration.runtime_data.heat_pump.utc_offset_minutes = None
    await hass.config.async_set_time_zone("America/New_York")
    await _press(hass)
    written = mock_gateway.set_appliance_time.await_args.args[0]
    assert written.replace(tzinfo=None) == datetime(2026, 9, 17, 6, 0, 0)


@pytest.mark.usefixtures("init_integration")
async def test_sync_time_error(hass: HomeAssistant, mock_gateway: MockGateway) -> None:
    """Test a failed time write raises a translated error."""
    mock_gateway.set_appliance_time.side_effect = DimplexConnectionError("gone")
    with pytest.raises(HomeAssistantError) as excinfo:
        await _press(hass)
    assert excinfo.value.translation_key == "write_failed"
