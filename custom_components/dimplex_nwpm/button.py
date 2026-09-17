"""Button platform for the Dimplex NWPM Touch integration."""

from dataclasses import dataclass
from typing import override

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .coordinator import DimplexConfigEntry
from .entity import DimplexEntity, DimplexEntityDescription

PARALLEL_UPDATES = 1


@dataclass(frozen=True, kw_only=True)
class DimplexButtonEntityDescription(DimplexEntityDescription, ButtonEntityDescription):
    """Describes a Dimplex button."""


SYNC_TIME = DimplexButtonEntityDescription(
    key="sync_time",
    translation_key="sync_time",
    entity_category=EntityCategory.CONFIG,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DimplexConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Dimplex buttons based on a config entry."""
    async_add_entities([DimplexSyncTimeButton(entry.runtime_data, SYNC_TIME)])


class DimplexSyncTimeButton(DimplexEntity, ButtonEntity):
    """Button that sets the heat pump manager clock to the current time."""

    entity_description: DimplexButtonEntityDescription

    @override
    async def async_press(self) -> None:
        """Set the appliance clock to the current time."""
        await self.async_call(self.heat_pump.set_time(dt_util.now()))
