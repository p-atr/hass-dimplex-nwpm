"""Tests for the Dimplex NWPM Touch diagnostics."""

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.components.diagnostics import (
    get_diagnostics_for_config_entry,
)
from pytest_homeassistant_custom_component.typing import ClientSessionGenerator
from syrupy.assertion import SnapshotAssertion


async def test_diagnostics(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
    init_integration: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the diagnostics output redacts secrets."""
    diagnostics = await get_diagnostics_for_config_entry(
        hass, hass_client, init_integration
    )
    assert diagnostics == snapshot
    assert diagnostics["entry"]["password"] == "**REDACTED**"
    assert diagnostics["twin_meta"]["gatewayMac"] == "**REDACTED**"
    assert diagnostics["twin_meta"]["applianceSerial"] == "**REDACTED**"
