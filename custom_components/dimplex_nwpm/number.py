"""Number platform for the Dimplex NWPM Touch integration."""

from dataclasses import dataclass
from typing import override

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

from .const import (
    COND_COOLING,
    COND_HEATING_CIRCUIT_2,
    COND_HEATING_CIRCUIT_3,
    COND_HOT_WATER,
    COND_POOL,
    COND_SECOND_HEAT_GENERATOR,
    COND_THERMAL_DISINFECTION,
    COND_VENTILATION,
    DATAPOINT_PV_SURPLUS,
    POWER_SCALE,
)
from .coordinator import DimplexConfigEntry
from .entity import DimplexEntity, DimplexEntityDescription

PARALLEL_UPDATES = 1


@dataclass(frozen=True, kw_only=True)
class DimplexNumberEntityDescription(DimplexEntityDescription, NumberEntityDescription):
    """Describes a Dimplex number.

    The shown value is ``raw * scale + offset``; writes apply the inverse.
    """

    scale: float = 1
    offset: float = 0


def _setting(
    key: str,
    datapoint: str,
    *,
    min_value: float,
    max_value: float,
    step: float = 1,
    unit: str | None = None,
    device_class: NumberDeviceClass | None = None,
    offset: float = 0,
    condition: str | None = None,
    enabled: bool = True,
) -> DimplexNumberEntityDescription:
    return DimplexNumberEntityDescription(
        key=key,
        translation_key=key,
        datapoint=datapoint,
        device_class=device_class,
        native_unit_of_measurement=unit,
        native_min_value=min_value,
        native_max_value=max_value,
        native_step=step,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
        condition=condition,
        entity_registry_enabled_default=enabled,
        offset=offset,
    )


def _temperature_setting(
    key: str,
    datapoint: str,
    *,
    min_value: float,
    max_value: float,
    step: float = 1,
    condition: str | None = None,
    enabled: bool = True,
) -> DimplexNumberEntityDescription:
    return _setting(
        key,
        datapoint,
        min_value=min_value,
        max_value=max_value,
        step=step,
        unit=UnitOfTemperature.CELSIUS,
        device_class=NumberDeviceClass.TEMPERATURE,
        condition=condition,
        enabled=enabled,
    )


def _kelvin_setting(
    key: str,
    datapoint: str,
    *,
    min_value: float,
    max_value: float,
    step: float = 1,
    offset: float = 0,
    condition: str | None = None,
) -> DimplexNumberEntityDescription:
    return _setting(
        key,
        datapoint,
        min_value=min_value,
        max_value=max_value,
        step=step,
        unit=UnitOfTemperature.KELVIN,
        offset=offset,
        condition=condition,
    )


NUMBERS: tuple[DimplexNumberEntityDescription, ...] = (
    _setting("party_hours", "715u", min_value=0, max_value=72, unit=UnitOfTime.HOURS),
    _setting("holiday_days", "1108u", min_value=0, max_value=150, unit=UnitOfTime.DAYS),
    _setting(
        "ventilation_level",
        "1564u",
        min_value=0,
        max_value=5,
        condition=COND_VENTILATION,
    ),
    _setting(
        "shock_ventilation_time",
        "1565u",
        min_value=15,
        max_value=90,
        unit=UnitOfTime.MINUTES,
        condition=COND_VENTILATION,
    ),
    _kelvin_setting(
        "heating_curve_parallel_shift", "767u", min_value=-19, max_value=19, offset=-19
    ),
    _temperature_setting(
        "room_temperature_setpoint", "700a", min_value=15, max_value=30, step=0.5
    ),
    _temperature_setting("fixed_setpoint", "768u", min_value=18, max_value=60),
    _temperature_setting("heating_curve_endpoint", "766u", min_value=20, max_value=70),
    _kelvin_setting("heating_hysteresis", "701a", min_value=0.5, max_value=5, step=0.1),
    _temperature_setting(
        "cooling_setpoint_15",
        "773u",
        min_value=10,
        max_value=35,
        condition=COND_COOLING,
    ),
    _temperature_setting(
        "cooling_setpoint_35",
        "509u",
        min_value=10,
        max_value=35,
        condition=COND_COOLING,
    ),
    _temperature_setting(
        "heating_circuit_2_heating_curve_endpoint",
        "851u",
        min_value=20,
        max_value=70,
        condition=COND_HEATING_CIRCUIT_2,
    ),
    _temperature_setting(
        "heating_circuit_2_fixed_setpoint",
        "853u",
        min_value=20,
        max_value=60,
        condition=COND_HEATING_CIRCUIT_2,
    ),
    _kelvin_setting(
        "heating_circuit_2_parallel_shift",
        "852u",
        min_value=-19,
        max_value=19,
        offset=-19,
        condition=COND_HEATING_CIRCUIT_2,
    ),
    _temperature_setting(
        "heating_circuit_3_heating_curve_endpoint",
        "931u",
        min_value=20,
        max_value=70,
        condition=COND_HEATING_CIRCUIT_3,
    ),
    _temperature_setting(
        "heating_circuit_3_fixed_setpoint",
        "933u",
        min_value=20,
        max_value=60,
        condition=COND_HEATING_CIRCUIT_3,
    ),
    _kelvin_setting(
        "heating_circuit_3_parallel_shift",
        "932u",
        min_value=-19,
        max_value=19,
        offset=-19,
        condition=COND_HEATING_CIRCUIT_3,
    ),
    _temperature_setting(
        "hot_water_setpoint",
        "1042u",
        min_value=10,
        max_value=85,
        condition=COND_HOT_WATER,
    ),
    _kelvin_setting(
        "hot_water_hysteresis",
        "1043u",
        min_value=2,
        max_value=15,
        condition=COND_HOT_WATER,
    ),
    _temperature_setting(
        "hot_water_minimum_temperature",
        "1045u",
        min_value=10,
        max_value=85,
        condition=COND_HOT_WATER,
    ),
    _temperature_setting(
        "hot_water_maximum_temperature",
        "1044u",
        min_value=10,
        max_value=85,
        condition=COND_HOT_WATER,
    ),
    _temperature_setting(
        "thermal_disinfection_temperature",
        "1074u",
        min_value=60,
        max_value=85,
        condition=COND_THERMAL_DISINFECTION,
    ),
    _temperature_setting(
        "pool_setpoint", "1153u", min_value=5, max_value=60, condition=COND_POOL
    ),
    _kelvin_setting(
        "pool_hysteresis", "1150u", min_value=1, max_value=20, condition=COND_POOL
    ),
    _temperature_setting(
        "pool_minimum_temperature",
        "1481u",
        min_value=10,
        max_value=60,
        condition=COND_POOL,
    ),
    _temperature_setting(
        "pool_maximum_temperature",
        "1155u",
        min_value=10,
        max_value=60,
        condition=COND_POOL,
    ),
    _kelvin_setting(
        "second_heat_generator_mixer_hysteresis",
        "564a",
        min_value=0.5,
        max_value=2,
        step=0.1,
        condition=COND_SECOND_HEAT_GENERATOR,
    ),
    _temperature_setting(
        "bivalence_parallel_limit",
        "750i",
        min_value=-25,
        max_value=35,
        condition=COND_SECOND_HEAT_GENERATOR,
    ),
    _temperature_setting(
        "external_outdoor_temperature",
        "683a",
        min_value=-99.9,
        max_value=99.9,
        step=0.1,
        enabled=False,
    ),
    DimplexNumberEntityDescription(
        key="pv_surplus",
        translation_key="pv_surplus",
        datapoint=DATAPOINT_PV_SURPLUS,
        device_class=NumberDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        native_min_value=-327680,
        native_max_value=327670,
        native_step=POWER_SCALE,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
        scale=POWER_SCALE,
    ),
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
        if description.supported(coordinator)
    )


class DimplexNumber(DimplexEntity, NumberEntity):
    """Representation of a writable Dimplex setting."""

    entity_description: DimplexNumberEntityDescription

    @property
    @override
    def native_value(self) -> float | None:
        """Return the current value."""
        if (value := self.raw_value) is None:
            return None
        description = self.entity_description
        return float(value) * description.scale + description.offset

    @override
    async def async_set_native_value(self, value: float) -> None:
        """Write the new value to the heat pump manager."""
        description = self.entity_description
        assert description.datapoint is not None
        raw = (value - description.offset) / description.scale
        await self.coordinator.async_set_datapoint(description.datapoint, raw)
