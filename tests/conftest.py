"""Fixtures for the Dimplex NWPM Touch integration tests."""

from collections.abc import Callable, Generator
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, PropertyMock, patch

from homeassistant.const import CONF_HOST, CONF_MAC, CONF_PASSWORD, Platform
from homeassistant.core import HomeAssistant
from pydimplex_nwpm import (
    ApplianceTimeState,
    DatapointValue,
    DimplexRequestError,
    HistoryEntry,
    TwinState,
    canonical_name,
    expand_range,
)
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_load_json_object_fixture,
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

MODBUS_COILS: dict[int, list[bool]] = {177: [True]}


@dataclass
class MqttListeners:
    """Callbacks the coordinator registered on the mocked MQTT client."""

    values: list[Callable[[dict[str, DatapointValue]], None]] = field(
        default_factory=list
    )
    twin: list[Callable[[TwinState], None]] = field(default_factory=list)
    error_history: list[Callable[[list[HistoryEntry]], None]] = field(
        default_factory=list
    )
    lock_history: list[Callable[[list[HistoryEntry]], None]] = field(
        default_factory=list
    )
    connection: list[Callable[[bool], None]] = field(default_factory=list)


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
def twin() -> TwinState:
    """Return the device twin reported by the gateway."""
    return TwinState.from_payload(load_json_object_fixture("twin.json", DOMAIN))


@pytest.fixture
def values() -> dict[str, DatapointValue]:
    """Return the datapoint values the gateway answers with."""
    return dict(load_json_object_fixture("values.json", DOMAIN))


@pytest.fixture
def mock_mqtt_client(
    twin: TwinState, values: dict[str, DatapointValue]
) -> Generator[MagicMock]:
    """Return a mocked MQTT client that answers from the fixtures."""

    async def get_values(name: str) -> dict[str, DatapointValue]:
        result: dict[str, DatapointValue] = {}
        for single in expand_range(name):
            key = canonical_name(single)
            if key not in values:
                raise DimplexRequestError(1, f"Requested value not provided ({name})")
            result[key] = values[key]
        return result

    with (
        patch(
            "custom_components.dimplex_nwpm.DimplexMqttClient", autospec=True
        ) as mock_class,
        patch(
            "custom_components.dimplex_nwpm.config_flow.DimplexMqttClient",
            new=mock_class,
        ),
    ):
        client: MagicMock = mock_class.return_value
        client.host = HOST
        client.client_id = "ha_dimplex_test"
        client.connected = True
        client.authentication_failed = False
        client.twin = twin
        client.error_history = [
            HistoryEntry(
                index=0,
                value=25,
                time=datetime(2025, 12, 19, 8, 15, tzinfo=timezone(timedelta(hours=1))),
                details={"err_rl": "24", "err_vl": "21"},
            )
        ]
        client.lock_history = [
            HistoryEntry(
                index=0,
                value=15,
                time=datetime(2025, 11, 3, 15, 28, tzinfo=timezone(timedelta(hours=1))),
                details={"lock_rl": "22"},
            )
        ]
        client.appliance_time_state = ApplianceTimeState(
            timezone_name="Europe/Zurich", utc_offset_minutes=120
        )
        client.wait_for_twin.return_value = twin
        client.get_values.side_effect = get_values
        client.get_appliance_time.return_value = datetime(2026, 9, 17, 12, 0, 0)
        listeners = MqttListeners()
        client.listeners = listeners

        def register(
            target: list[Callable[..., None]],
        ) -> Callable[..., Callable[[], None]]:
            def add(listener: Callable[..., None]) -> Callable[[], None]:
                target.append(listener)
                return lambda: target.remove(listener)

            return add

        client.add_values_listener.side_effect = register(listeners.values)
        client.add_twin_listener.side_effect = register(listeners.twin)
        client.add_error_history_listener.side_effect = register(
            listeners.error_history
        )
        client.add_lock_history_listener.side_effect = register(listeners.lock_history)
        client.add_connection_listener.side_effect = register(listeners.connection)
        yield client


@pytest.fixture
def mock_modbus_client() -> Generator[MagicMock]:
    """Return a mocked Modbus TCP client that answers from the fixtures."""

    async def read_coils(address: int, count: int = 1) -> list[bool]:
        return MODBUS_COILS[address][:count]

    with (
        patch(
            "custom_components.dimplex_nwpm.DimplexModbusClient", autospec=True
        ) as mock_class,
        patch(
            "custom_components.dimplex_nwpm.config_flow.DimplexModbusClient",
            new=mock_class,
        ),
    ):
        client: MagicMock = mock_class.return_value
        client.connected = True
        client.read_coils.side_effect = read_coils
        client.read_software_version.return_value = "M3.13"
        yield client


@pytest.fixture
async def init_integration(
    hass: HomeAssistant,
    request: pytest.FixtureRequest,
    mock_config_entry: MockConfigEntry,
    mock_mqtt_client: MagicMock,
    mock_modbus_client: MagicMock,
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


async def load_twin(hass: HomeAssistant) -> TwinState:
    """Load the twin fixture without blocking the event loop."""
    return TwinState.from_payload(
        await async_load_json_object_fixture(hass, "twin.json", DOMAIN)
    )
