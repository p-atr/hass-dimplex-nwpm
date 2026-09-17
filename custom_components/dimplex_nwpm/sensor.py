"""Sensor platform for the Dimplex NWPM Touch integration."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import override

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    REVOLUTIONS_PER_MINUTE,
    EntityCategory,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfPressure,
    UnitOfTemperature,
    UnitOfTime,
    UnitOfVolumeFlowRate,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.typing import StateType
from pydimplex_nwpm import HistoryEntry, canonical_name

from .const import (
    CIRCUIT_STATES,
    COND_ADDITIONAL_PUMP,
    COND_COOLING,
    COND_FLOW_SENSOR,
    COND_HEAT_METER,
    COND_HEAT_METER_HOT_WATER,
    COND_HEAT_METER_POOL,
    COND_HEAT_METER_PRIMARY,
    COND_HEAT_METER_TOTAL,
    COND_HEATING,
    COND_HEATING_CIRCUIT_2,
    COND_HEATING_CIRCUIT_3,
    COND_HOT_WATER,
    COND_INVERTER,
    COND_PASSIVE_COOLING,
    COND_POOL,
    COND_REGENERATIVE,
    COND_REVERSIBLE,
    COND_ROOM_SENSOR_1,
    COND_ROOM_SENSOR_2,
    COND_ROOM_SENSOR_3,
    COND_SECOND_HEAT_GENERATOR,
    COND_SOLAR,
    COND_TWO_COMPRESSORS,
    COND_TWO_PRESSURE_SENSORS,
    COND_VENTILATION,
    DATAPOINT_COOLING_POWER,
    DATAPOINT_ELECTRICAL_POWER,
    DATAPOINT_FAULT,
    DATAPOINT_LOCK,
    DATAPOINT_SENSOR_FAULT,
    DATAPOINT_STATUS,
    DATAPOINT_THERMAL_POWER,
    ENERGY_ENVIRONMENTAL,
    ENERGY_ENVIRONMENTAL_RESET,
    ENERGY_HEATING,
    ENERGY_HEATING_RESET,
    ENERGY_HOT_WATER,
    ENERGY_HOT_WATER_RESET,
    ENERGY_POOL,
    ENERGY_POOL_RESET,
    ENERGY_TOTAL,
    FAULT_MESSAGES,
    HOT_WATER_STATES,
    LOCK_MESSAGES,
    POOL_STATES,
    POWER_SCALE,
    REQUEST_STATES,
    SENSOR_FAULT_MESSAGES,
    STATUS_MESSAGES,
    TEMPERATURE_SCALE,
)
from .coordinator import DimplexConfigEntry, DimplexData
from .entity import DimplexEntity, DimplexEntityDescription

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class DimplexSensorEntityDescription(DimplexEntityDescription, SensorEntityDescription):
    """Describes a Dimplex sensor.

    Plain numeric datapoints are multiplied by ``scale``; sensors deriving
    their state from several values provide ``value_fn`` instead.
    """

    scale: float = 1
    value_fn: Callable[[DimplexData], StateType | datetime] | None = None
    attributes_fn: Callable[[DimplexData], dict[str, StateType]] | None = None


def _measurement(
    key: str,
    datapoint: str,
    *,
    device_class: SensorDeviceClass | None = None,
    unit: str | None = None,
    precision: int | None = None,
    scale: float = 1,
    condition: str | None = None,
    category: EntityCategory | None = None,
    enabled: bool = True,
) -> DimplexSensorEntityDescription:
    return DimplexSensorEntityDescription(
        key=key,
        translation_key=key,
        datapoint=datapoint,
        device_class=device_class,
        native_unit_of_measurement=unit,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=precision,
        scale=scale,
        condition=condition,
        entity_category=category,
        entity_registry_enabled_default=enabled,
    )


def _temperature(
    key: str,
    datapoint: str,
    *,
    scale: float = 1,
    condition: str | None = None,
    category: EntityCategory | None = None,
    enabled: bool = True,
) -> DimplexSensorEntityDescription:
    return _measurement(
        key,
        datapoint,
        device_class=SensorDeviceClass.TEMPERATURE,
        unit=UnitOfTemperature.CELSIUS,
        precision=1,
        scale=scale,
        condition=condition,
        category=category,
        enabled=enabled,
    )


def _scaled_temperature(
    key: str,
    datapoint: str,
    *,
    condition: str | None = None,
    category: EntityCategory | None = None,
) -> DimplexSensorEntityDescription:
    """Describe an integer temperature delivered in 0.1 K steps."""
    return _temperature(
        key,
        datapoint,
        scale=TEMPERATURE_SCALE,
        condition=condition,
        category=category,
    )


def _pressure(
    key: str, datapoint: str, *, condition: str | None = None
) -> DimplexSensorEntityDescription:
    return _measurement(
        key,
        datapoint,
        device_class=SensorDeviceClass.PRESSURE,
        unit=UnitOfPressure.BAR,
        precision=1,
        condition=condition,
    )


def _power(
    key: str, datapoint: str, *, condition: str, enabled: bool = True
) -> DimplexSensorEntityDescription:
    return _measurement(
        key,
        datapoint,
        device_class=SensorDeviceClass.POWER,
        unit=UnitOfPower.WATT,
        scale=POWER_SCALE,
        condition=condition,
        enabled=enabled,
    )


def _runtime(
    key: str,
    datapoint: str,
    *,
    condition: str | None = None,
    enabled: bool = True,
) -> DimplexSensorEntityDescription:
    return DimplexSensorEntityDescription(
        key=key,
        translation_key=key,
        datapoint=datapoint,
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.HOURS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
        condition=condition,
        entity_registry_enabled_default=enabled,
    )


def _counter(
    key: str, datapoint: str, *, condition: str | None = None
) -> DimplexSensorEntityDescription:
    return DimplexSensorEntityDescription(
        key=key,
        translation_key=key,
        datapoint=datapoint,
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
        condition=condition,
    )


def _message_sensor(
    key: str,
    datapoint: str,
    messages: dict[int, str],
    *,
    condition: str | None = None,
    category: EntityCategory | None = None,
) -> DimplexSensorEntityDescription:
    """Describe an enum sensor mapping a WPM message code to a translation key."""
    data_key = canonical_name(datapoint)

    def value_fn(data: DimplexData) -> StateType:
        if (code := data.values.get(data_key)) is None:
            return None
        return messages.get(int(code))

    def attributes_fn(data: DimplexData) -> dict[str, StateType]:
        if (code := data.values.get(data_key)) is None:
            return {}
        return {"code": int(code)}

    return DimplexSensorEntityDescription(
        key=key,
        translation_key=key,
        datapoint=datapoint,
        device_class=SensorDeviceClass.ENUM,
        options=sorted(set(messages.values())),
        value_fn=value_fn,
        attributes_fn=attributes_fn,
        condition=condition,
        entity_category=category,
    )


def _composite_energy(names: tuple[str, str, str]) -> Callable[[DimplexData], int]:
    """Combine the three 4-digit decimal parts of an energy counter."""
    keys = tuple(canonical_name(name) for name in names)

    def value_fn(data: DimplexData) -> int:
        low, mid, high = (int(data.values[key]) for key in keys)
        return high * 100_000_000 + mid * 10_000 + low

    return value_fn


def _all_present(names: tuple[str, ...]) -> Callable[[DimplexData], bool]:
    keys = tuple(canonical_name(name) for name in names)
    return lambda data: all(key in data.values for key in keys)


def _energy_sensor(
    key: str,
    names: tuple[str, str, str],
    *,
    condition: str,
    category: EntityCategory | None = None,
) -> DimplexSensorEntityDescription:
    return DimplexSensorEntityDescription(
        key=key,
        translation_key=key,
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=_composite_energy(names),
        available_fn=_all_present(names),
        condition=condition,
        entity_category=category,
    )


def _cop(data: DimplexData) -> float | None:
    thermal = int(data.values[canonical_name(DATAPOINT_THERMAL_POWER)])
    electrical = int(data.values[canonical_name(DATAPOINT_ELECTRICAL_POWER)])
    if electrical <= 0 or thermal <= 0:
        return None
    return round(thermal / electrical, 2)


def _history_time(
    history: Callable[[DimplexData], list[HistoryEntry]],
) -> Callable[[DimplexData], datetime | None]:
    def value_fn(data: DimplexData) -> datetime | None:
        entries = history(data)
        return entries[0].time if entries else None

    return value_fn


def _history_attributes(
    history: Callable[[DimplexData], list[HistoryEntry]], messages: dict[int, str]
) -> Callable[[DimplexData], dict[str, StateType]]:
    def attributes_fn(data: DimplexData) -> dict[str, StateType]:
        if not (entries := history(data)):
            return {}
        entry = entries[0]
        return {
            "code": entry.value,
            "message": messages.get(entry.value),
            **entry.details,
        }

    return attributes_fn


SENSORS: tuple[DimplexSensorEntityDescription, ...] = (
    _temperature("outdoor_temperature", "1301a"),
    _temperature("flow_temperature", "1300a"),
    _temperature("return_temperature", "1294a"),
    _scaled_temperature(
        "return_temperature_setpoint",
        "1574i",
        condition=COND_HEATING,
        category=EntityCategory.DIAGNOSTIC,
    ),
    _scaled_temperature(
        "heating_circuits_temperature",
        "1575i",
        condition=COND_HEATING,
        category=EntityCategory.DIAGNOSTIC,
    ),
    _scaled_temperature(
        "cooling_setpoint",
        "1578i",
        condition=COND_COOLING,
        category=EntityCategory.DIAGNOSTIC,
    ),
    _scaled_temperature(
        "cooling_circuits_temperature",
        "1579i",
        condition=COND_COOLING,
        category=EntityCategory.DIAGNOSTIC,
    ),
    _temperature(
        "heat_pump_flow_temperature", "638a", category=EntityCategory.DIAGNOSTIC
    ),
    _temperature(
        "heat_pump_return_temperature", "637a", category=EntityCategory.DIAGNOSTIC
    ),
    _temperature("hot_water_temperature", "1305a", condition=COND_HOT_WATER),
    _scaled_temperature(
        "hot_water_temperature_setpoint",
        "1594i",
        condition=COND_HOT_WATER,
        category=EntityCategory.DIAGNOSTIC,
    ),
    _temperature("pool_temperature", "1297a", condition=COND_POOL),
    _scaled_temperature(
        "pool_temperature_setpoint",
        "1597i",
        condition=COND_POOL,
        category=EntityCategory.DIAGNOSTIC,
    ),
    _temperature(
        "regenerative_storage_temperature", "1292a", condition=COND_REGENERATIVE
    ),
    _temperature("heat_source_inlet_temperature", "1303a", enabled=False),
    _temperature("heat_source_outlet_temperature", "1302a"),
    _measurement(
        "flow_rate",
        "1472i",
        device_class=SensorDeviceClass.VOLUME_FLOW_RATE,
        unit=UnitOfVolumeFlowRate.LITERS_PER_HOUR,
        condition=COND_FLOW_SENSOR,
    ),
    _pressure("system_pressure", "556a"),
    _pressure("high_pressure", "1280a", condition=COND_TWO_PRESSURE_SENSORS),
    _pressure("low_pressure", "4865a"),
    _measurement(
        "inverter_frequency",
        "1550i",
        device_class=SensorDeviceClass.FREQUENCY,
        unit=UnitOfFrequency.HERTZ,
        condition=COND_INVERTER,
    ),
    _measurement(
        "inverter_power",
        "1556i",
        device_class=SensorDeviceClass.POWER,
        unit=UnitOfPower.WATT,
        condition=COND_INVERTER,
    ),
    _measurement(
        "inverter_voltage",
        "1557i",
        device_class=SensorDeviceClass.VOLTAGE,
        unit=UnitOfElectricPotential.VOLT,
        condition=COND_INVERTER,
        category=EntityCategory.DIAGNOSTIC,
    ),
    _measurement("power_stage_heating", "1260i", condition=COND_HEATING),
    _measurement("power_stage_cooling", "1261i", condition=COND_COOLING),
    _temperature("hot_gas_temperature", "1284a", enabled=False),
    _temperature("evaporation_temperature", "601a", category=EntityCategory.DIAGNOSTIC),
    _temperature(
        "suction_gas_temperature", "4866a", category=EntityCategory.DIAGNOSTIC
    ),
    _measurement(
        "superheat",
        "604a",
        unit=UnitOfTemperature.KELVIN,
        precision=1,
        category=EntityCategory.DIAGNOSTIC,
    ),
    _measurement(
        "expansion_valve_position",
        "1991i",
        unit=PERCENTAGE,
        category=EntityCategory.DIAGNOSTIC,
    ),
    _scaled_temperature("heating_circuit_1_temperature", "1621i"),
    _scaled_temperature(
        "heating_circuit_1_temperature_setpoint",
        "1620i",
        category=EntityCategory.DIAGNOSTIC,
    ),
    _scaled_temperature(
        "heating_circuit_2_temperature", "1582i", condition=COND_HEATING_CIRCUIT_2
    ),
    _scaled_temperature(
        "heating_circuit_2_temperature_setpoint",
        "1622i",
        condition=COND_HEATING_CIRCUIT_2,
        category=EntityCategory.DIAGNOSTIC,
    ),
    _scaled_temperature(
        "heating_circuit_3_temperature", "1583i", condition=COND_HEATING_CIRCUIT_3
    ),
    _scaled_temperature(
        "heating_circuit_3_temperature_setpoint",
        "1624i",
        condition=COND_HEATING_CIRCUIT_3,
        category=EntityCategory.DIAGNOSTIC,
    ),
    _scaled_temperature("room_temperature_1", "1632i", condition=COND_ROOM_SENSOR_1),
    _scaled_temperature("room_temperature_2", "1633i", condition=COND_ROOM_SENSOR_2),
    _scaled_temperature("room_temperature_3", "1634i", condition=COND_ROOM_SENSOR_3),
    _scaled_temperature(
        "room_temperature_setpoint_1",
        "1629i",
        condition=COND_ROOM_SENSOR_1,
        category=EntityCategory.DIAGNOSTIC,
    ),
    _scaled_temperature(
        "room_temperature_setpoint_2",
        "1630i",
        condition=COND_ROOM_SENSOR_2,
        category=EntityCategory.DIAGNOSTIC,
    ),
    _scaled_temperature(
        "room_temperature_setpoint_3",
        "1631i",
        condition=COND_ROOM_SENSOR_3,
        category=EntityCategory.DIAGNOSTIC,
    ),
    _measurement(
        "room_humidity_1",
        "1791i",
        device_class=SensorDeviceClass.HUMIDITY,
        unit=PERCENTAGE,
        precision=1,
        scale=TEMPERATURE_SCALE,
        condition=COND_ROOM_SENSOR_1,
    ),
    _measurement(
        "room_humidity_2",
        "1627i",
        device_class=SensorDeviceClass.HUMIDITY,
        unit=PERCENTAGE,
        precision=1,
        scale=TEMPERATURE_SCALE,
        condition=COND_ROOM_SENSOR_2,
    ),
    _measurement(
        "room_humidity_3",
        "1628i",
        device_class=SensorDeviceClass.HUMIDITY,
        unit=PERCENTAGE,
        precision=1,
        scale=TEMPERATURE_SCALE,
        condition=COND_ROOM_SENSOR_3,
    ),
    _temperature(
        "passive_cooling_flow_temperature", "1299a", condition=COND_PASSIVE_COOLING
    ),
    _temperature(
        "passive_cooling_return_temperature", "1298a", condition=COND_PASSIVE_COOLING
    ),
    _temperature("primary_circuit_return_temperature", "1296a", condition=COND_COOLING),
    _temperature("solar_collector_temperature", "1287a", condition=COND_SOLAR),
    _temperature("solar_storage_temperature", "1295a", condition=COND_SOLAR),
    _temperature(
        "ventilation_outdoor_air_temperature", "629a", condition=COND_VENTILATION
    ),
    _temperature(
        "ventilation_supply_air_temperature", "630a", condition=COND_VENTILATION
    ),
    _temperature(
        "ventilation_exhaust_air_temperature", "631a", condition=COND_VENTILATION
    ),
    _temperature(
        "ventilation_extract_air_temperature", "632a", condition=COND_VENTILATION
    ),
    _measurement(
        "ventilation_supply_fan_speed",
        "1559u",
        unit=REVOLUTIONS_PER_MINUTE,
        condition=COND_VENTILATION,
    ),
    _measurement(
        "ventilation_exhaust_fan_speed",
        "1560u",
        unit=REVOLUTIONS_PER_MINUTE,
        condition=COND_VENTILATION,
    ),
    _message_sensor("status", DATAPOINT_STATUS, STATUS_MESSAGES),
    _message_sensor("lock", DATAPOINT_LOCK, LOCK_MESSAGES),
    _message_sensor("fault", DATAPOINT_FAULT, FAULT_MESSAGES),
    _message_sensor("sensor_fault", DATAPOINT_SENSOR_FAULT, SENSOR_FAULT_MESSAGES),
    _message_sensor("heating_request", "1572i", REQUEST_STATES, condition=COND_HEATING),
    _message_sensor("cooling_request", "1604i", REQUEST_STATES, condition=COND_COOLING),
    _message_sensor(
        "hot_water_request", "1592i", REQUEST_STATES, condition=COND_HOT_WATER
    ),
    _message_sensor(
        "hot_water_status",
        "1593i",
        HOT_WATER_STATES,
        condition=COND_HOT_WATER,
        category=EntityCategory.DIAGNOSTIC,
    ),
    _message_sensor("pool_request", "1595i", REQUEST_STATES, condition=COND_POOL),
    _message_sensor(
        "pool_status",
        "1596i",
        POOL_STATES,
        condition=COND_POOL,
        category=EntityCategory.DIAGNOSTIC,
    ),
    _message_sensor("heating_circuit_1_status", "1581i", CIRCUIT_STATES),
    _message_sensor(
        "heating_circuit_2_status",
        "1585i",
        CIRCUIT_STATES,
        condition=COND_HEATING_CIRCUIT_2,
    ),
    _message_sensor(
        "heating_circuit_3_status",
        "1589i",
        CIRCUIT_STATES,
        condition=COND_HEATING_CIRCUIT_3,
    ),
    _runtime("compressor_1_runtime", "1380u"),
    _runtime("compressor_2_runtime", "1381u", condition=COND_TWO_COMPRESSORS),
    _runtime("primary_pump_runtime", "1384u"),
    _runtime(
        "second_heat_generator_runtime", "1382u", condition=COND_SECOND_HEAT_GENERATOR
    ),
    _runtime("heating_pump_runtime", "1385u"),
    _runtime("hot_water_pump_runtime", "1386u", condition=COND_HOT_WATER),
    _runtime("flange_heater_runtime", "1387u", condition=COND_HOT_WATER),
    _runtime("pool_pump_runtime", "1388u", condition=COND_POOL),
    _runtime("cooling_runtime", "1389u", condition=COND_REVERSIBLE),
    _runtime("additional_pump_runtime", "1390u", condition=COND_ADDITIONAL_PUMP),
    _counter("compressor_1_starts", "1491u"),
    _counter("compressor_1_starts_heating", "1492u"),
    _counter("compressor_1_starts_hot_water", "1493u", condition=COND_HOT_WATER),
    _counter("compressor_1_starts_pool", "1494u", condition=COND_POOL),
    _counter("compressor_1_starts_cooling", "1495u", condition=COND_COOLING),
    _counter("compressor_2_starts", "1496u", condition=COND_TWO_COMPRESSORS),
    _energy_sensor("heating_energy", ENERGY_HEATING, condition=COND_HEAT_METER),
    _energy_sensor(
        "hot_water_energy", ENERGY_HOT_WATER, condition=COND_HEAT_METER_HOT_WATER
    ),
    _energy_sensor("pool_energy", ENERGY_POOL, condition=COND_HEAT_METER_POOL),
    _energy_sensor("total_energy", ENERGY_TOTAL, condition=COND_HEAT_METER_TOTAL),
    _energy_sensor(
        "heating_energy_since_reset",
        ENERGY_HEATING_RESET,
        condition=COND_HEAT_METER,
        category=EntityCategory.DIAGNOSTIC,
    ),
    _energy_sensor(
        "hot_water_energy_since_reset",
        ENERGY_HOT_WATER_RESET,
        condition=COND_HEAT_METER_HOT_WATER,
        category=EntityCategory.DIAGNOSTIC,
    ),
    _energy_sensor(
        "pool_energy_since_reset",
        ENERGY_POOL_RESET,
        condition=COND_HEAT_METER_POOL,
        category=EntityCategory.DIAGNOSTIC,
    ),
    _energy_sensor(
        "environmental_energy_since_reset",
        ENERGY_ENVIRONMENTAL_RESET,
        condition=COND_HEAT_METER_PRIMARY,
        category=EntityCategory.DIAGNOSTIC,
    ),
    _energy_sensor(
        "environmental_energy",
        ENERGY_ENVIRONMENTAL,
        condition=COND_HEAT_METER_PRIMARY,
    ),
    _power("thermal_power", DATAPOINT_THERMAL_POWER, condition=COND_HEAT_METER),
    _power(
        "cooling_power",
        DATAPOINT_COOLING_POWER,
        condition=COND_HEAT_METER,
        enabled=False,
    ),
    _power("electrical_power", DATAPOINT_ELECTRICAL_POWER, condition=COND_HEAT_METER),
    DimplexSensorEntityDescription(
        key="coefficient_of_performance",
        translation_key="coefficient_of_performance",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=_cop,
        available_fn=_all_present(
            (DATAPOINT_THERMAL_POWER, DATAPOINT_ELECTRICAL_POWER)
        ),
        condition=COND_HEAT_METER,
    ),
    DimplexSensorEntityDescription(
        key="last_fault_time",
        translation_key="last_fault_time",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_history_time(lambda data: data.error_history),
        attributes_fn=_history_attributes(
            lambda data: data.error_history, FAULT_MESSAGES
        ),
        available_fn=lambda data: bool(data.error_history),
    ),
    DimplexSensorEntityDescription(
        key="last_lock_time",
        translation_key="last_lock_time",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_history_time(lambda data: data.lock_history),
        attributes_fn=_history_attributes(
            lambda data: data.lock_history, LOCK_MESSAGES
        ),
        available_fn=lambda data: bool(data.lock_history),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DimplexConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Dimplex sensors based on a config entry."""
    coordinator = entry.runtime_data
    async_add_entities(
        DimplexSensor(coordinator, description)
        for description in SENSORS
        if description.supported(coordinator)
    )


class DimplexSensor(DimplexEntity, SensorEntity):
    """Representation of a Dimplex sensor."""

    entity_description: DimplexSensorEntityDescription

    @property
    @override
    def native_value(self) -> StateType | datetime:
        """Return the state of the sensor."""
        description = self.entity_description
        if description.value_fn is not None:
            return description.value_fn(self.coordinator.data)
        value = self.raw_value
        if value is None or isinstance(value, bool):
            return value
        if description.scale != 1:
            return value * description.scale
        return value

    @property
    @override
    def extra_state_attributes(self) -> dict[str, StateType] | None:
        """Return additional details such as the raw message code."""
        if (attributes_fn := self.entity_description.attributes_fn) is None:
            return None
        return attributes_fn(self.coordinator.data)
