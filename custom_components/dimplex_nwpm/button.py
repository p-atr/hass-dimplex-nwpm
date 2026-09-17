"""Button platform for the Dimplex NWPM Touch integration."""

from dataclasses import dataclass
from datetime import timedelta
from typing import override

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util
from pydimplex_nwpm import DimplexError

from .const import DOMAIN
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
    """Button that writes the current time to the heat pump manager."""

    entity_description: DimplexButtonEntityDescription

    @override
    async def async_press(self) -> None:
        """Set the appliance clock to the current time."""
        now = dt_util.utcnow()
        # The appliance keeps a naive local clock; use its own time zone when
        # the gateway reported one, otherwise fall back to Home Assistant's.
        if (time_state := self.coordinator.mqtt.appliance_time_state) and (
            offset := time_state.utc_offset_minutes
        ) is not None:
            local = now + timedelta(minutes=offset)
        else:
            local = dt_util.as_local(now)
        try:
            await self.coordinator.mqtt.set_appliance_time(local.replace(tzinfo=None))
        except DimplexError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="write_failed",
                translation_placeholders={
                    "datapoint": "appliance_time",
                    "error": str(err),
                },
            ) from err
