"""Base entity for the Dimplex NWPM Touch integration."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from typing import override

from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from pydimplex_nwpm import DATAPOINTS, DatapointValue, DimplexError, DimplexHeatPump

from .const import DOMAIN
from .coordinator import DimplexCoordinator

type EntityValue = DatapointValue | str | datetime | None


@dataclass(frozen=True, kw_only=True)
class DimplexEntityDescription(EntityDescription):
    """Describes a Dimplex entity.

    The key names the library datapoint, unless ``value_fn`` derives the state
    from other data of the heat pump.
    """

    value_fn: Callable[[DimplexHeatPump], EntityValue] | None = None
    gateway: bool = False

    def supported(self, heat_pump: DimplexHeatPump) -> bool:
        """Return True if the installation provides this entity."""
        return self.value_fn is not None or heat_pump.supports(self.key)


class DimplexEntity(CoordinatorEntity[DimplexCoordinator]):
    """Entity backed by a value of the heat pump or its gateway."""

    _attr_has_entity_name = True
    entity_description: DimplexEntityDescription

    def __init__(
        self, coordinator: DimplexCoordinator, description: DimplexEntityDescription
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.config_entry.unique_id}_{description.key}"
        self._attr_device_info = (
            coordinator.gateway_device_info
            if description.gateway
            else coordinator.heat_pump_device_info
        )

    @property
    def heat_pump(self) -> DimplexHeatPump:
        """Return the heat pump."""
        return self.coordinator.heat_pump

    @property
    def current_value(self) -> EntityValue:
        """Return the value backing the entity."""
        description = self.entity_description
        if description.value_fn is not None:
            return description.value_fn(self.heat_pump)
        return self.heat_pump.value(description.key)

    @property
    @override
    def available(self) -> bool:
        """Return True if the gateway is connected and the value is known."""
        if not super().available or not self.heat_pump.connected:
            return False
        key = self.entity_description.key
        if self.entity_description.value_fn is not None:
            return self.current_value is not None
        return key not in DATAPOINTS or self.heat_pump.available(key)

    async def async_call(self, action: Awaitable[None]) -> None:
        """Run a write to the heat pump and translate library errors."""
        try:
            await action
        except DimplexError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="write_failed",
                translation_placeholders={"error": str(err)},
            ) from err
