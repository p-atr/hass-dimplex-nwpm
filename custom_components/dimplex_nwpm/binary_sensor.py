"""Binary sensor platform for the Dimplex NWPM Touch integration."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import override

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    COIL_SMART_RTC_VALVE,
    COND_ADDITIONAL_PUMP,
    COND_AIR_HEAT_PUMP,
    COND_BIVALENT,
    COND_COOLING,
    COND_FLOW_SENSOR,
    COND_HEATING_CIRCUIT_2,
    COND_HEATING_CIRCUIT_3,
    COND_HOT_GAS_THERMOSTAT,
    COND_HOT_WATER,
    COND_HOT_WATER_CIRCULATION,
    COND_IMMERSION_HEATER,
    COND_PASSIVE_COOLING,
    COND_PIPE_HEATER,
    COND_POOL,
    COND_SOLAR,
    COND_TWO_COMPRESSORS,
)
from .coordinator import DimplexConfigEntry, DimplexData
from .entity import DimplexEntity, DimplexEntityDescription, DimplexGatewayEntity

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class DimplexBinarySensorEntityDescription(
    DimplexEntityDescription, BinarySensorEntityDescription
):
    """Describes a Dimplex binary sensor."""

    is_on_fn: Callable[[DimplexData], bool | None] | None = None


def _input(
    key: str, datapoint: str, *, condition: str | None = None
) -> DimplexBinarySensorEntityDescription:
    return DimplexBinarySensorEntityDescription(
        key=key,
        translation_key=key,
        datapoint=datapoint,
        entity_category=EntityCategory.DIAGNOSTIC,
        condition=condition,
    )


def _output(
    key: str,
    datapoint: str,
    *,
    condition: str | None = None,
    device_class: BinarySensorDeviceClass | None = BinarySensorDeviceClass.RUNNING,
) -> DimplexBinarySensorEntityDescription:
    return DimplexBinarySensorEntityDescription(
        key=key,
        translation_key=key,
        datapoint=datapoint,
        device_class=device_class,
        condition=condition,
    )


def _mixer(
    key: str, datapoint: str, *, condition: str | None = None
) -> DimplexBinarySensorEntityDescription:
    return DimplexBinarySensorEntityDescription(
        key=key,
        translation_key=key,
        datapoint=datapoint,
        entity_category=EntityCategory.DIAGNOSTIC,
        condition=condition,
        entity_registry_enabled_default=False,
    )


def _twin_flag(key: str, meta_key: str) -> DimplexBinarySensorEntityDescription:
    return DimplexBinarySensorEntityDescription(
        key=key,
        translation_key=key,
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        is_on_fn=lambda data: data.twin.flag(meta_key),
        available_fn=lambda data: data.twin.flag(meta_key) is not None,
    )


APPLIANCE_BINARY_SENSORS: tuple[DimplexBinarySensorEntityDescription, ...] = (
    _input("smart_grid_input_1", "3d"),
    _input("smart_grid_input_2", "4d"),
    _input("utility_lock_input", "1402d"),
    _input("external_lock_input", "1245d"),
    _input("high_pressure_switch", "1415d"),
    _input("low_pressure_switch", "1416d"),
    _input("hot_gas_thermostat", "1413d", condition=COND_HOT_GAS_THERMOSTAT),
    _input("frost_protection_thermostat", "1406d"),
    _input("flow_switch_secondary", "1409d", condition=COND_FLOW_SENSOR),
    _input("compressor_motor_protection", "1249d"),
    _input("primary_motor_protection", "1250d"),
    _output("compressor_1", "1500d"),
    _output("compressor_2", "1501d", condition=COND_TWO_COMPRESSORS),
    _output("fan", "1502d", condition=COND_AIR_HEAT_PUMP),
    _output("nozzle_ring_heater", "1503d", condition=COND_AIR_HEAT_PUMP),
    _output("internal_four_way_valve", "1504d", device_class=None),
    _output("primary_pump", "1506d"),
    _output("boiler", "1507d", condition=COND_BIVALENT),
    _output("pipe_heater", "1508d", condition=COND_PIPE_HEATER),
    _output("immersion_heater", "1509d", condition=COND_IMMERSION_HEATER),
    _output("heating_pump", "1512d"),
    _output("hot_water_pump", "1517d", condition=COND_HOT_WATER),
    _output(
        "hot_water_circulation_pump", "1521d", condition=COND_HOT_WATER_CIRCULATION
    ),
    _output("additional_pump", "1516d", condition=COND_ADDITIONAL_PUMP),
    _output("flange_heater", "1510d", condition=COND_HOT_WATER),
    _output("heating_pump_2", "1514d", condition=COND_HEATING_CIRCUIT_2),
    _output("heating_pump_3", "1515d", condition=COND_HEATING_CIRCUIT_3),
    _output("pool_pump", "1518d", condition=COND_POOL),
    _output("cooling_pump", "1519d", condition=COND_COOLING),
    _output("primary_pump_cooling", "1522d", condition=COND_COOLING),
    _output("second_cooling_generator", "1511d", condition=COND_COOLING),
    _output(
        "external_four_way_valve", "1524d", condition=COND_COOLING, device_class=None
    ),
    _output(
        "passive_cooling_switch_valve",
        "1525d",
        condition=COND_PASSIVE_COOLING,
        device_class=None,
    ),
    _output("solar_system", "1520d", condition=COND_SOLAR),
    _output("solar_switch_valve", "1526d", condition=COND_SOLAR, device_class=None),
    _output("room_thermostat_cooling", "1527d", condition=COND_COOLING),
    _mixer("mixer_1_open", "698d"),
    _mixer("mixer_1_close", "699d"),
    _mixer("mixer_2_open", "1532d", condition=COND_HEATING_CIRCUIT_2),
    _mixer("mixer_2_close", "1533d", condition=COND_HEATING_CIRCUIT_2),
    _mixer("mixer_3_open", "1534d", condition=COND_HEATING_CIRCUIT_3),
    _mixer("mixer_3_close", "1535d", condition=COND_HEATING_CIRCUIT_3),
    _mixer("mixer_bivalent_open", "1528d"),
    _mixer("mixer_bivalent_close", "1529d"),
    _mixer("mixer_regenerative_open", "1530d"),
    _mixer("mixer_regenerative_close", "1531d"),
    DimplexBinarySensorEntityDescription(
        key="collective_fault",
        translation_key="collective_fault",
        datapoint="1523d",
        device_class=BinarySensorDeviceClass.PROBLEM,
    ),
    DimplexBinarySensorEntityDescription(
        key="smart_rtc_valve",
        translation_key="smart_rtc_valve",
        coil=COIL_SMART_RTC_VALVE,
        device_class=BinarySensorDeviceClass.OPENING,
    ),
)

GATEWAY_BINARY_SENSORS: tuple[DimplexBinarySensorEntityDescription, ...] = (
    _twin_flag("appliance_connection", "applianceConnectionState"),
    _twin_flag("cloud_connection", "cloudConnectionState"),
    _twin_flag("internet_connection", "internetConnectionState"),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DimplexConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Dimplex binary sensors based on a config entry."""
    coordinator = entry.runtime_data
    entities: list[DimplexBinarySensor] = [
        DimplexBinarySensor(coordinator, description)
        for description in APPLIANCE_BINARY_SENSORS
        if description.supported(coordinator)
    ]
    entities.extend(
        DimplexGatewayBinarySensor(coordinator, description)
        for description in GATEWAY_BINARY_SENSORS
    )
    async_add_entities(entities)


class DimplexBinarySensor(DimplexEntity, BinarySensorEntity):
    """Representation of a Dimplex binary sensor."""

    entity_description: DimplexBinarySensorEntityDescription

    @property
    @override
    def is_on(self) -> bool | None:
        """Return the state of the binary sensor."""
        if (is_on_fn := self.entity_description.is_on_fn) is not None:
            return is_on_fn(self.coordinator.data)
        if (value := self.raw_value) is None:
            return None
        return bool(value)


class DimplexGatewayBinarySensor(DimplexGatewayEntity, DimplexBinarySensor):
    """Binary sensor attached to the gateway device."""
