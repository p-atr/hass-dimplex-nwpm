"""Water heater platform for the Dimplex NWPM Touch integration."""

from dataclasses import dataclass
from typing import Any, override

from homeassistant.components.water_heater import (
    STATE_HEAT_PUMP,
    STATE_OFF,
    WaterHeaterEntity,
    WaterHeaterEntityDescription,
    WaterHeaterEntityFeature,
)
from homeassistant.const import ATTR_TEMPERATURE, PRECISION_WHOLE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from pydimplex_nwpm import canonical_name

from .const import (
    COND_HOT_WATER,
    DATAPOINT_HOT_WATER_MAX,
    DATAPOINT_HOT_WATER_MIN,
    DATAPOINT_HOT_WATER_SETPOINT,
    DATAPOINT_HOT_WATER_TEMPERATURE,
    DATAPOINT_STATUS,
    STATUS_HOT_WATER,
)
from .coordinator import DimplexConfigEntry
from .entity import DimplexEntity, DimplexEntityDescription

PARALLEL_UPDATES = 1

KEY_TEMPERATURE = canonical_name(DATAPOINT_HOT_WATER_TEMPERATURE)
KEY_MIN = canonical_name(DATAPOINT_HOT_WATER_MIN)
KEY_MAX = canonical_name(DATAPOINT_HOT_WATER_MAX)
KEY_STATUS = canonical_name(DATAPOINT_STATUS)

DEFAULT_MIN_TEMP = 10
DEFAULT_MAX_TEMP = 85


@dataclass(frozen=True, kw_only=True)
class DimplexWaterHeaterEntityDescription(
    DimplexEntityDescription, WaterHeaterEntityDescription
):
    """Describes the Dimplex hot water entity."""


HOT_WATER = DimplexWaterHeaterEntityDescription(
    key="hot_water",
    translation_key="hot_water",
    datapoint=DATAPOINT_HOT_WATER_SETPOINT,
    condition=COND_HOT_WATER,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DimplexConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Dimplex hot water entity based on a config entry."""
    coordinator = entry.runtime_data
    if HOT_WATER.supported(coordinator):
        async_add_entities([DimplexWaterHeater(coordinator, HOT_WATER)])


class DimplexWaterHeater(DimplexEntity, WaterHeaterEntity):
    """Domestic hot water preparation of the heat pump."""

    entity_description: DimplexWaterHeaterEntityDescription
    _attr_supported_features = WaterHeaterEntityFeature.TARGET_TEMPERATURE
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_precision = PRECISION_WHOLE
    _attr_target_temperature_step = PRECISION_WHOLE

    @property
    @override
    def current_operation(self) -> str:
        """Return whether the heat pump is currently heating water."""
        status = self.coordinator.data.values.get(KEY_STATUS)
        return STATE_HEAT_PUMP if status == STATUS_HOT_WATER else STATE_OFF

    @property
    @override
    def current_temperature(self) -> float | None:
        """Return the hot water temperature."""
        if (value := self.coordinator.data.values.get(KEY_TEMPERATURE)) is None:
            return None
        return float(value)

    @property
    @override
    def target_temperature(self) -> float | None:
        """Return the hot water setpoint."""
        if (value := self.raw_value) is None:
            return None
        return float(value)

    @property
    @override
    def min_temp(self) -> float:
        """Return the configured minimum hot water temperature."""
        return float(self.coordinator.data.values.get(KEY_MIN, DEFAULT_MIN_TEMP))

    @property
    @override
    def max_temp(self) -> float:
        """Return the configured maximum hot water temperature."""
        return float(self.coordinator.data.values.get(KEY_MAX, DEFAULT_MAX_TEMP))

    @override
    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set the hot water setpoint."""
        await self.coordinator.async_set_datapoint(
            DATAPOINT_HOT_WATER_SETPOINT, round(kwargs[ATTR_TEMPERATURE])
        )
