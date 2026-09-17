"""Binary sensor platform for the Dimplex NWPM Touch integration."""

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

from .coordinator import DimplexConfigEntry
from .entity import DimplexEntity, DimplexEntityDescription

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class DimplexBinarySensorEntityDescription(
    DimplexEntityDescription, BinarySensorEntityDescription
):
    """Describes a Dimplex binary sensor."""


def _running(key: str) -> DimplexBinarySensorEntityDescription:
    """Describe an output driving a pump, compressor or heater."""
    return DimplexBinarySensorEntityDescription(
        key=key, translation_key=key, device_class=BinarySensorDeviceClass.RUNNING
    )


def _diagnostic(key: str) -> DimplexBinarySensorEntityDescription:
    """Describe an input, valve or mixer signal."""
    return DimplexBinarySensorEntityDescription(
        key=key,
        translation_key=key,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    )


BINARY_SENSORS: tuple[DimplexBinarySensorEntityDescription, ...] = (
    *(
        _running(key)
        for key in (
            "compressor_1",
            "compressor_2",
            "fan",
            "nozzle_ring_heater",
            "primary_pump",
            "boiler",
            "pipe_heater",
            "immersion_heater",
            "heating_pump",
            "hot_water_pump",
            "hot_water_circulation_pump",
            "additional_pump",
            "flange_heater",
            "heating_pump_2",
            "heating_pump_3",
            "pool_pump",
            "cooling_pump",
            "primary_pump_cooling",
            "second_cooling_generator",
            "solar_system",
            "room_thermostat_cooling",
        )
    ),
    *(
        _diagnostic(key)
        for key in (
            "smart_grid_input_1",
            "smart_grid_input_2",
            "utility_lock_input",
            "external_lock_input",
            "high_pressure_switch",
            "low_pressure_switch",
            "hot_gas_thermostat",
            "frost_protection_thermostat",
            "flow_switch_secondary",
            "compressor_motor_protection",
            "primary_motor_protection",
            "internal_four_way_valve",
            "external_four_way_valve",
            "passive_cooling_switch_valve",
            "solar_switch_valve",
            "mixer_1_open",
            "mixer_1_close",
            "mixer_2_open",
            "mixer_2_close",
            "mixer_3_open",
            "mixer_3_close",
            "mixer_bivalent_open",
            "mixer_bivalent_close",
            "mixer_regenerative_open",
            "mixer_regenerative_close",
        )
    ),
    DimplexBinarySensorEntityDescription(
        key="collective_fault",
        translation_key="collective_fault",
        device_class=BinarySensorDeviceClass.PROBLEM,
    ),
    DimplexBinarySensorEntityDescription(
        key="smart_rtc_valve",
        translation_key="smart_rtc_valve",
        device_class=BinarySensorDeviceClass.OPENING,
    ),
    DimplexBinarySensorEntityDescription(
        key="appliance_connection",
        translation_key="appliance_connection",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        gateway=True,
        value_fn=lambda heat_pump: (
            heat_pump.twin.appliance_connected if heat_pump.twin else None
        ),
    ),
    DimplexBinarySensorEntityDescription(
        key="cloud_connection",
        translation_key="cloud_connection",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        gateway=True,
        value_fn=lambda heat_pump: (
            heat_pump.twin.cloud_connected if heat_pump.twin else None
        ),
    ),
    DimplexBinarySensorEntityDescription(
        key="internet_connection",
        translation_key="internet_connection",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        gateway=True,
        value_fn=lambda heat_pump: (
            heat_pump.twin.internet_connected if heat_pump.twin else None
        ),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DimplexConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Dimplex binary sensors based on a config entry."""
    coordinator = entry.runtime_data
    async_add_entities(
        DimplexBinarySensor(coordinator, description)
        for description in BINARY_SENSORS
        if description.supported(coordinator.heat_pump)
    )


class DimplexBinarySensor(DimplexEntity, BinarySensorEntity):
    """Representation of a Dimplex binary sensor."""

    entity_description: DimplexBinarySensorEntityDescription

    @property
    @override
    def is_on(self) -> bool | None:
        """Return the state of the binary sensor."""
        return None if (value := self.current_value) is None else bool(value)
