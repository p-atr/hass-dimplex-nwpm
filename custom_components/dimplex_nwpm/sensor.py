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
from pydimplex_nwpm import DATAPOINTS, DimplexHeatPump, HistoryEntry

from .coordinator import DimplexConfigEntry
from .entity import DimplexEntity, DimplexEntityDescription

PARALLEL_UPDATES = 0

DIAGNOSTIC = EntityCategory.DIAGNOSTIC


@dataclass(frozen=True, kw_only=True)
class DimplexSensorEntityDescription(DimplexEntityDescription, SensorEntityDescription):
    """Describes a Dimplex sensor."""


def _sensor(
    key: str,
    device_class: SensorDeviceClass | None = None,
    unit: str | None = None,
    *,
    state_class: SensorStateClass | None = SensorStateClass.MEASUREMENT,
    precision: int | None = None,
    category: EntityCategory | None = None,
    enabled: bool = True,
) -> DimplexSensorEntityDescription:
    return DimplexSensorEntityDescription(
        key=key,
        translation_key=key,
        device_class=device_class,
        native_unit_of_measurement=unit,
        state_class=state_class,
        suggested_display_precision=precision,
        entity_category=category,
        entity_registry_enabled_default=enabled,
    )


def _temperature(
    key: str, category: EntityCategory | None = None, *, enabled: bool = True
) -> DimplexSensorEntityDescription:
    return _sensor(
        key,
        SensorDeviceClass.TEMPERATURE,
        UnitOfTemperature.CELSIUS,
        precision=1,
        category=category,
        enabled=enabled,
    )


def _enum(
    key: str, category: EntityCategory | None = None
) -> DimplexSensorEntityDescription:
    options = DATAPOINTS[key].options
    assert options is not None
    return DimplexSensorEntityDescription(
        key=key,
        translation_key=key,
        device_class=SensorDeviceClass.ENUM,
        options=sorted(set(options.values())),
        entity_category=category,
    )


def _total(
    key: str,
    device_class: SensorDeviceClass | None = None,
    unit: str | None = None,
    category: EntityCategory | None = None,
    *,
    enabled: bool = True,
) -> DimplexSensorEntityDescription:
    return _sensor(
        key,
        device_class,
        unit,
        state_class=SensorStateClass.TOTAL_INCREASING,
        category=category,
        enabled=enabled,
    )


def _runtime(key: str) -> DimplexSensorEntityDescription:
    return _total(
        key, SensorDeviceClass.DURATION, UnitOfTime.HOURS, DIAGNOSTIC, enabled=False
    )


def _starts(key: str) -> DimplexSensorEntityDescription:
    return _total(key, category=DIAGNOSTIC, enabled=False)


def _energy(
    key: str, category: EntityCategory | None = None
) -> DimplexSensorEntityDescription:
    return _total(key, SensorDeviceClass.ENERGY, UnitOfEnergy.KILO_WATT_HOUR, category)


def _last_time(
    key: str, history: Callable[[DimplexHeatPump], list[HistoryEntry]]
) -> DimplexSensorEntityDescription:
    def value_fn(heat_pump: DimplexHeatPump) -> datetime | None:
        entries = history(heat_pump)
        return entries[0].time if entries else None

    return DimplexSensorEntityDescription(
        key=key,
        translation_key=key,
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=DIAGNOSTIC,
        value_fn=value_fn,
    )


SENSORS: tuple[DimplexSensorEntityDescription, ...] = (
    _temperature("outdoor_temperature"),
    _temperature("flow_temperature"),
    _temperature("return_temperature"),
    _temperature("return_temperature_setpoint", DIAGNOSTIC),
    _temperature("heating_circuits_temperature", DIAGNOSTIC),
    _temperature("cooling_setpoint", DIAGNOSTIC),
    _temperature("cooling_circuits_temperature", DIAGNOSTIC),
    _temperature("heat_pump_flow_temperature", DIAGNOSTIC),
    _temperature("heat_pump_return_temperature", DIAGNOSTIC),
    _temperature("hot_water_temperature_setpoint", DIAGNOSTIC),
    _temperature("pool_temperature"),
    _temperature("pool_temperature_setpoint", DIAGNOSTIC),
    _temperature("regenerative_storage_temperature"),
    _temperature("heat_source_inlet_temperature", enabled=False),
    _temperature("heat_source_outlet_temperature"),
    _temperature("hot_gas_temperature", enabled=False),
    _temperature("evaporation_temperature", DIAGNOSTIC),
    _temperature("suction_gas_temperature", DIAGNOSTIC),
    _temperature("heating_circuit_1_temperature"),
    _temperature("heating_circuit_1_temperature_setpoint", DIAGNOSTIC),
    _temperature("heating_circuit_2_temperature"),
    _temperature("heating_circuit_2_temperature_setpoint", DIAGNOSTIC),
    _temperature("heating_circuit_3_temperature"),
    _temperature("heating_circuit_3_temperature_setpoint", DIAGNOSTIC),
    _temperature("room_temperature_1"),
    _temperature("room_temperature_2"),
    _temperature("room_temperature_3"),
    _temperature("room_temperature_setpoint_1", DIAGNOSTIC),
    _temperature("room_temperature_setpoint_2", DIAGNOSTIC),
    _temperature("room_temperature_setpoint_3", DIAGNOSTIC),
    _temperature("passive_cooling_flow_temperature"),
    _temperature("passive_cooling_return_temperature"),
    _temperature("primary_circuit_return_temperature"),
    _temperature("solar_collector_temperature"),
    _temperature("solar_storage_temperature"),
    _temperature("ventilation_outdoor_air_temperature"),
    _temperature("ventilation_supply_air_temperature"),
    _temperature("ventilation_exhaust_air_temperature"),
    _temperature("ventilation_extract_air_temperature"),
    _sensor(
        "flow_rate",
        SensorDeviceClass.VOLUME_FLOW_RATE,
        UnitOfVolumeFlowRate.LITERS_PER_HOUR,
    ),
    _sensor(
        "system_pressure", SensorDeviceClass.PRESSURE, UnitOfPressure.BAR, precision=1
    ),
    _sensor(
        "high_pressure", SensorDeviceClass.PRESSURE, UnitOfPressure.BAR, precision=1
    ),
    _sensor(
        "low_pressure", SensorDeviceClass.PRESSURE, UnitOfPressure.BAR, precision=1
    ),
    _sensor("inverter_frequency", SensorDeviceClass.FREQUENCY, UnitOfFrequency.HERTZ),
    _sensor("inverter_power", SensorDeviceClass.POWER, UnitOfPower.WATT),
    _sensor(
        "inverter_voltage",
        SensorDeviceClass.VOLTAGE,
        UnitOfElectricPotential.VOLT,
        category=DIAGNOSTIC,
    ),
    _sensor("power_stage_heating"),
    _sensor("power_stage_cooling"),
    _sensor(
        "superheat", unit=UnitOfTemperature.KELVIN, precision=1, category=DIAGNOSTIC
    ),
    _sensor("expansion_valve_position", unit=PERCENTAGE, category=DIAGNOSTIC),
    _sensor("room_humidity_1", SensorDeviceClass.HUMIDITY, PERCENTAGE, precision=1),
    _sensor("room_humidity_2", SensorDeviceClass.HUMIDITY, PERCENTAGE, precision=1),
    _sensor("room_humidity_3", SensorDeviceClass.HUMIDITY, PERCENTAGE, precision=1),
    _sensor("ventilation_supply_fan_speed", unit=REVOLUTIONS_PER_MINUTE),
    _sensor("ventilation_exhaust_fan_speed", unit=REVOLUTIONS_PER_MINUTE),
    _sensor("thermal_power", SensorDeviceClass.POWER, UnitOfPower.WATT),
    _sensor("cooling_power", SensorDeviceClass.POWER, UnitOfPower.WATT, enabled=False),
    _sensor("electrical_power", SensorDeviceClass.POWER, UnitOfPower.WATT),
    _enum("status"),
    _enum("lock"),
    _enum("fault"),
    _enum("sensor_fault"),
    _enum("heating_request"),
    _enum("cooling_request"),
    _enum("hot_water_request"),
    _enum("hot_water_status", DIAGNOSTIC),
    _enum("pool_request"),
    _enum("pool_status", DIAGNOSTIC),
    _enum("heating_circuit_1_status"),
    _enum("heating_circuit_2_status"),
    _enum("heating_circuit_3_status"),
    _runtime("compressor_1_runtime"),
    _runtime("compressor_2_runtime"),
    _runtime("primary_pump_runtime"),
    _runtime("second_heat_generator_runtime"),
    _runtime("heating_pump_runtime"),
    _runtime("hot_water_pump_runtime"),
    _runtime("flange_heater_runtime"),
    _runtime("pool_pump_runtime"),
    _runtime("cooling_runtime"),
    _runtime("additional_pump_runtime"),
    _starts("compressor_1_starts"),
    _starts("compressor_1_starts_heating"),
    _starts("compressor_1_starts_hot_water"),
    _starts("compressor_1_starts_pool"),
    _starts("compressor_1_starts_cooling"),
    _starts("compressor_2_starts"),
    _energy("heating_energy"),
    _energy("hot_water_energy"),
    _energy("pool_energy"),
    _energy("total_energy"),
    _energy("environmental_energy"),
    _energy("heating_energy_since_reset", DIAGNOSTIC),
    _energy("hot_water_energy_since_reset", DIAGNOSTIC),
    _energy("pool_energy_since_reset", DIAGNOSTIC),
    _energy("environmental_energy_since_reset", DIAGNOSTIC),
    _last_time("last_fault_time", lambda heat_pump: heat_pump.error_history),
    _last_time("last_lock_time", lambda heat_pump: heat_pump.lock_history),
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
        if description.supported(coordinator.heat_pump)
    )


class DimplexSensor(DimplexEntity, SensorEntity):
    """Representation of a Dimplex sensor."""

    entity_description: DimplexSensorEntityDescription

    @property
    @override
    def native_value(self) -> StateType | datetime:
        """Return the state of the sensor."""
        return self.current_value
