"""Water heater platform for the Dimplex NWPM Touch integration."""

from dataclasses import dataclass
from typing import Any, overload, override

from homeassistant.components.water_heater import (
    STATE_HEAT_PUMP,
    WaterHeaterEntity,
    WaterHeaterEntityDescription,
    WaterHeaterEntityFeature,
)
from homeassistant.const import ATTR_TEMPERATURE, PRECISION_WHOLE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from pydimplex_nwpm import DATAPOINTS

from .coordinator import DimplexConfigEntry
from .entity import DimplexEntity, DimplexEntityDescription

PARALLEL_UPDATES = 1

SETPOINT = "hot_water_setpoint"
MIN_TEMP = DATAPOINTS[SETPOINT].minimum or 0
MAX_TEMP = DATAPOINTS[SETPOINT].maximum or 0


@dataclass(frozen=True, kw_only=True)
class DimplexWaterHeaterEntityDescription(
    DimplexEntityDescription, WaterHeaterEntityDescription
):
    """Describes the Dimplex hot water entity."""


HOT_WATER = DimplexWaterHeaterEntityDescription(
    key="hot_water",
    translation_key="hot_water",
    value_fn=lambda heat_pump: heat_pump.value(SETPOINT),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DimplexConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Dimplex hot water entity based on a config entry."""
    coordinator = entry.runtime_data
    if coordinator.heat_pump.supports(SETPOINT):
        async_add_entities([DimplexWaterHeater(coordinator, HOT_WATER)])


class DimplexWaterHeater(DimplexEntity, WaterHeaterEntity):
    """Domestic hot water prepared by the heat pump."""

    entity_description: DimplexWaterHeaterEntityDescription

    _attr_current_operation = STATE_HEAT_PUMP
    _attr_supported_features = WaterHeaterEntityFeature.TARGET_TEMPERATURE
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_precision = PRECISION_WHOLE
    _attr_target_temperature_step = PRECISION_WHOLE

    @property
    @override
    def current_temperature(self) -> float | None:
        """Return the hot water temperature."""
        return self._float("hot_water_temperature")

    @property
    @override
    def target_temperature(self) -> float | None:
        """Return the hot water setpoint."""
        return self._float(SETPOINT)

    @property
    @override
    def min_temp(self) -> float:
        """Return the configured minimum hot water temperature."""
        return self._float("hot_water_minimum_temperature", MIN_TEMP)

    @property
    @override
    def max_temp(self) -> float:
        """Return the configured maximum hot water temperature."""
        return self._float("hot_water_maximum_temperature", MAX_TEMP)

    @override
    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set the hot water setpoint."""
        await self.async_call(self.heat_pump.set(SETPOINT, kwargs[ATTR_TEMPERATURE]))

    @overload
    def _float(self, key: str) -> float | None: ...
    @overload
    def _float(self, key: str, default: float) -> float: ...
    def _float(self, key: str, default: float | None = None) -> float | None:
        value = self.heat_pump.value(key)
        return default if value is None else float(value)
