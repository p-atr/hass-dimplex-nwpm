"""Fixtures for the Dimplex NWPM Touch integration tests."""

from collections.abc import Callable, Generator
from typing import Any, Self
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

from homeassistant.const import CONF_HOST, CONF_MAC, CONF_PASSWORD, Platform
from homeassistant.core import HomeAssistant
from pydimplex_nwpm import DatapointValue, DimplexRequestError
from pydimplex_nwpm.models import (
    canonical_name,
    expand_range,
    format_value,
    parse_value,
)
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    load_json_object_fixture,
)
from pytest_homeassistant_custom_component.syrupy import (
    HomeAssistantSnapshotExtension,
)
from syrupy.assertion import SnapshotAssertion

from custom_components.dimplex_nwpm import PLATFORMS
from custom_components.dimplex_nwpm.const import CONF_USE_MODBUS, DOMAIN

SERIAL = "001535600010"
HOST = "127.0.0.127"
PASSWORD = "80B56598"
MAC = "00:0a:5c:12:34:56"

TOPIC_TWIN = "extern/broadcast/twin_reported_state"


class MockGateway:
    """Fake MQTT transport of the gateway answering from the fixtures."""

    def __init__(self, twin: dict[str, Any], values: dict[str, DatapointValue]) -> None:
        """Initialize the gateway."""
        self.twin = twin
        self.values = values
        self.connected = False
        self.authentication_failed = False
        self._on_message: Callable[[str, Any], None] | None = None
        self._on_connection: Callable[[], None] | None = None
        self.connect = AsyncMock(side_effect=self._connect)
        self.disconnect = AsyncMock()
        self.get_values = AsyncMock(side_effect=self._get_values)
        self.set_value = AsyncMock(side_effect=self._set_value)
        self.set_appliance_time = AsyncMock()

    def __call__(
        self,
        host: str,
        password: str,
        *,
        port: int,
        on_message: Callable[[str, Any], None],
        on_connection: Callable[[], None],
    ) -> Self:
        """Act as the transport class of the library."""
        self._on_message = on_message
        self._on_connection = on_connection
        return self

    def push(self, topic: str, payload: Any) -> None:
        """Deliver a broadcast from the gateway."""
        assert self._on_message is not None
        self._on_message(topic, payload)

    def push_values(self, values: dict[str, str]) -> None:
        """Deliver a changed_on broadcast."""
        self.push(
            "gateway/broadcast/changed_on/modbus/test",
            {
                "test": {
                    "value_batch": {
                        name: {"value": value} for name, value in values.items()
                    }
                }
            },
        )

    def set_connected(self, connected: bool) -> None:
        """Simulate a lost or restored connection."""
        assert self._on_connection is not None
        self.connected = connected
        self._on_connection()

    async def _connect(self) -> None:
        self.set_connected(True)
        self.push(TOPIC_TWIN, self.twin)
        self.push(
            "extern/broadcast/error_history_state",
            [
                {
                    "idx": 0,
                    "err_value": 25,
                    "time": "2025-12-19T08:15:00+01:00",
                    "err_rl": "24",
                }
            ],
        )
        self.push(
            "extern/broadcast/lock_history_state",
            [{"idx": 0, "lock_value": 15, "time": "2025-11-03T15:28:00+01:00"}],
        )
        self.push("extern/broadcast/appliance_time_state", {"utc_offset_minutes": 120})

    async def _get_values(self, name: str) -> dict[str, DatapointValue]:
        result: dict[str, DatapointValue] = {}
        for single in expand_range(name):
            if (key := canonical_name(single)) not in self.values:
                raise DimplexRequestError(1, f"Requested value not provided ({name})")
            result[key] = self.values[key]
        return result

    async def _set_value(self, name: str, value: float) -> None:
        self.values[canonical_name(name)] = parse_value(name, format_value(name, value))


@pytest.fixture(autouse=True)
def _custom_integrations(enable_custom_integrations: None) -> None:
    """Enable loading the integration from the test config directory."""


@pytest.fixture
def snapshot(snapshot: SnapshotAssertion) -> SnapshotAssertion:
    """Use the Home Assistant snapshot serializer."""
    return snapshot.use_extension(HomeAssistantSnapshotExtension)


@pytest.fixture
def entity_registry_enabled_by_default() -> Generator[None]:
    """Enable all entities, including those disabled by default."""
    with patch(
        "homeassistant.helpers.entity.Entity.entity_registry_enabled_default",
        new_callable=PropertyMock,
        return_value=True,
    ):
        yield


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Return the default mocked config entry."""
    return MockConfigEntry(
        title=f"Dimplex WPM {SERIAL}",
        domain=DOMAIN,
        data={
            CONF_HOST: HOST,
            CONF_PASSWORD: PASSWORD,
            CONF_USE_MODBUS: True,
            CONF_MAC: MAC,
        },
        unique_id=SERIAL,
    )


@pytest.fixture
def mock_setup_entry() -> Generator[None]:
    """Mock setting up a config entry."""
    with patch("custom_components.dimplex_nwpm.async_setup_entry", return_value=True):
        yield


@pytest.fixture
def mock_gateway() -> Generator[MockGateway]:
    """Replace the MQTT transport of the library with the fixture gateway."""
    gateway = MockGateway(
        load_json_object_fixture("twin.json", DOMAIN),
        dict(load_json_object_fixture("values.json", DOMAIN)),
    )
    with patch("pydimplex_nwpm.heat_pump.DimplexMqttClient", gateway):
        yield gateway


@pytest.fixture
def mock_modbus() -> Generator[MagicMock]:
    """Replace the Modbus TCP client with one reporting an open valve."""
    client = MagicMock(connected=True)
    client.read_coils = AsyncMock(
        return_value=MagicMock(bits=[True], isError=MagicMock(return_value=False))
    )
    with patch("pydimplex_nwpm.heat_pump.AsyncModbusTcpClient", return_value=client):
        yield client


@pytest.fixture
async def init_integration(
    hass: HomeAssistant,
    request: pytest.FixtureRequest,
    mock_config_entry: MockConfigEntry,
    mock_gateway: MockGateway,
    mock_modbus: MagicMock,
) -> MockConfigEntry:
    """Set up the integration, optionally limited to one platform."""
    platform: Platform | None = getattr(request, "param", None)
    mock_config_entry.add_to_hass(hass)
    with patch(
        "custom_components.dimplex_nwpm.PLATFORMS",
        [platform] if platform else PLATFORMS,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
    return mock_config_entry
