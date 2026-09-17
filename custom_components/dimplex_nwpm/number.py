"""Number platform for the Dimplex NWPM Touch integration."""

from dataclasses import dataclass
from typing import cast, override

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.const import (
    EntityCategory,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from pydimplex_nwpm import DATAPOINTS

from .coordinator import DimplexConfigEntry
from .entity import DimplexEntity, DimplexEntityDescription

PARALLEL_UPDATES = 1


@dataclass(frozen=True, kw_only=True)
class DimplexNumberEntityDescription(DimplexEntityDescription, NumberEntityDescription):
    """Describes a Dimplex setting."""


def _number(
    key: str,
    unit: str | None = None,
    device_class: NumberDeviceClass | None = None,
    *,
    category: EntityCategory | None = EntityCategory.CONFIG,
    enabled: bool = True,
) -> DimplexNumberEntityDescription:
    datapoint = DATAPOINTS[key]
    assert datapoint.minimum is not None and datapoint.maximum is not None
    return DimplexNumberEntityDescription(
        key=key,
        translation_key=key,
        device_class=device_class,
        native_unit_of_measurement=unit,
        native_min_value=datapoint.minimum,
        native_max_value=datapoint.maximum,
        native_step=datapoint.step,
        mode=NumberMode.BOX,
        entity_category=category,
        entity_registry_enabled_default=enabled,
    )


def _celsius(key: str) -> DimplexNumberEntityDescription:
    return _number(key, UnitOfTemperature.CELSIUS, NumberDeviceClass.TEMPERATURE)


def _kelvin(key: str) -> DimplexNumberEntityDescription:
    return _number(key, UnitOfTemperature.KELVIN)


NUMBERS: tuple[DimplexNumberEntityDescription, ...] = (
    _number("party_hours", UnitOfTime.HOURS),
    _number("holiday_days", UnitOfTime.DAYS),
    _number("ventilation_level"),
    _number("shock_ventilation_time", UnitOfTime.MINUTES),
    _kelvin("heating_curve_parallel_shift"),
    _celsius("room_temperature_setpoint"),
    _celsius("fixed_setpoint"),
    _celsius("heating_curve_endpoint"),
    _kelvin("heating_hysteresis"),
    _celsius("cooling_setpoint_15"),
    _celsius("cooling_setpoint_35"),
    _celsius("heating_circuit_2_heating_curve_endpoint"),
    _celsius("heating_circuit_2_fixed_setpoint"),
    _kelvin("heating_circuit_2_parallel_shift"),
    _celsius("heating_circuit_3_heating_curve_endpoint"),
    _celsius("heating_circuit_3_fixed_setpoint"),
    _kelvin("heating_circuit_3_parallel_shift"),
    _kelvin("hot_water_hysteresis"),
    _celsius("hot_water_minimum_temperature"),
    _celsius("hot_water_maximum_temperature"),
    _celsius("thermal_disinfection_temperature"),
    _celsius("pool_setpoint"),
    _kelvin("pool_hysteresis"),
    _celsius("pool_minimum_temperature"),
    _celsius("pool_maximum_temperature"),
    _kelvin("second_heat_generator_mixer_hysteresis"),
    _celsius("bivalence_parallel_limit"),
    # Inputs meant to be fed by automations rather than configured once.
    _number(
        "external_outdoor_temperature",
        UnitOfTemperature.CELSIUS,
        NumberDeviceClass.TEMPERATURE,
        category=None,
        enabled=False,
    ),
    _number("pv_surplus", UnitOfPower.WATT, NumberDeviceClass.POWER, category=None),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DimplexConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Dimplex numbers based on a config entry."""
    coordinator = entry.runtime_data
    async_add_entities(
        DimplexNumber(coordinator, description)
        for description in NUMBERS
        if description.supported(coordinator.heat_pump)
    )


class DimplexNumber(DimplexEntity, NumberEntity):
    """Representation of a writable Dimplex setting."""

    entity_description: DimplexNumberEntityDescription

    @property
    @override
    def native_value(self) -> float | None:
        """Return the current value."""
        return (
            None if (value := self.current_value) is None else float(cast(float, value))
        )

    @override
    async def async_set_native_value(self, value: float) -> None:
        """Write the new value to the heat pump manager."""
        await self.async_call(self.heat_pump.set(self.entity_description.key, value))
