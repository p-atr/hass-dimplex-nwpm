"""Select platform for the Dimplex NWPM Touch integration."""

from dataclasses import dataclass
from typing import override

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    DATAPOINT_OPERATING_MODE,
    EXTERNAL_LOCK_STATES,
    OPERATING_MODES,
    SMART_GRID_STATES,
)
from .coordinator import DimplexConfigEntry
from .entity import DimplexEntity, DimplexEntityDescription

PARALLEL_UPDATES = 1


@dataclass(frozen=True, kw_only=True)
class DimplexSelectEntityDescription(DimplexEntityDescription, SelectEntityDescription):
    """Describes a Dimplex select mapping datapoint codes to options."""

    states: dict[int, str]


SELECTS: tuple[DimplexSelectEntityDescription, ...] = (
    DimplexSelectEntityDescription(
        key="operating_mode",
        translation_key="operating_mode",
        datapoint=DATAPOINT_OPERATING_MODE,
        options=list(OPERATING_MODES.values()),
        states=OPERATING_MODES,
    ),
    DimplexSelectEntityDescription(
        key="smart_grid",
        translation_key="smart_grid",
        datapoint="2662u",
        options=list(SMART_GRID_STATES.values()),
        states=SMART_GRID_STATES,
        entity_category=EntityCategory.CONFIG,
    ),
    DimplexSelectEntityDescription(
        key="external_lock",
        translation_key="external_lock",
        datapoint="2663i",
        options=list(EXTERNAL_LOCK_STATES.values()),
        states=EXTERNAL_LOCK_STATES,
        entity_category=EntityCategory.CONFIG,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DimplexConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Dimplex selects based on a config entry."""
    async_add_entities(
        DimplexSelect(entry.runtime_data, description) for description in SELECTS
    )


class DimplexSelect(DimplexEntity, SelectEntity):
    """Representation of a Dimplex mode selection."""

    entity_description: DimplexSelectEntityDescription

    @property
    @override
    def current_option(self) -> str | None:
        """Return the currently selected option."""
        if (value := self.raw_value) is None:
            return None
        return self.entity_description.states.get(int(value))

    @override
    async def async_select_option(self, option: str) -> None:
        """Write the selected option to the heat pump manager."""
        description = self.entity_description
        assert description.datapoint is not None
        code = next(key for key, name in description.states.items() if name == option)
        await self.coordinator.async_set_datapoint(description.datapoint, code)
