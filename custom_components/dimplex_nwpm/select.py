"""Select platform for the Dimplex NWPM Touch integration."""

from dataclasses import dataclass
from typing import override

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from pydimplex_nwpm import DATAPOINTS

from .coordinator import DimplexConfigEntry
from .entity import DimplexEntity, DimplexEntityDescription

PARALLEL_UPDATES = 1


@dataclass(frozen=True, kw_only=True)
class DimplexSelectEntityDescription(DimplexEntityDescription, SelectEntityDescription):
    """Describes a Dimplex selection."""


def _select(
    key: str, category: EntityCategory | None = None
) -> DimplexSelectEntityDescription:
    options = DATAPOINTS[key].options
    assert options is not None
    return DimplexSelectEntityDescription(
        key=key,
        translation_key=key,
        options=list(options.values()),
        entity_category=category,
    )


SELECTS: tuple[DimplexSelectEntityDescription, ...] = (
    _select("operating_mode"),
    _select("smart_grid", EntityCategory.CONFIG),
    _select("external_lock", EntityCategory.CONFIG),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DimplexConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Dimplex selects based on a config entry."""
    coordinator = entry.runtime_data
    async_add_entities(
        DimplexSelect(coordinator, description)
        for description in SELECTS
        if description.supported(coordinator.heat_pump)
    )


class DimplexSelect(DimplexEntity, SelectEntity):
    """Representation of a Dimplex mode selection."""

    entity_description: DimplexSelectEntityDescription

    @property
    @override
    def current_option(self) -> str | None:
        """Return the currently selected option."""
        return None if (value := self.current_value) is None else str(value)

    @override
    async def async_select_option(self, option: str) -> None:
        """Write the selected option to the heat pump manager."""
        await self.async_call(self.heat_pump.set(self.entity_description.key, option))
