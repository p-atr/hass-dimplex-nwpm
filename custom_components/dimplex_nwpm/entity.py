"""Base entities for the Dimplex NWPM Touch integration."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import override

from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from pydimplex_nwpm import DatapointValue, canonical_name

from .coordinator import DimplexCoordinator, DimplexData, coil_key


@dataclass(frozen=True, kw_only=True)
class DimplexEntityDescription(EntityDescription):
    """Describes an entity backed by a gateway datapoint or Modbus coil.

    Exactly one of ``datapoint`` (MQTT) or ``coil`` (Modbus TCP) is set for
    value-backed entities. Entities deriving their state from several values
    leave both unset and provide ``available_fn``. ``condition`` names the
    equipment flag that has to be set for the entity to be created.
    """

    datapoint: str | None = None
    coil: int | None = None
    condition: str | None = None
    available_fn: Callable[[DimplexData], bool] | None = None

    @property
    def data_key(self) -> str | None:
        """Return the key of the backing value in the coordinator data."""
        if self.datapoint is not None:
            return canonical_name(self.datapoint)
        if self.coil is not None:
            return coil_key(self.coil)
        return None

    @property
    def uses_modbus(self) -> bool:
        """Return True if the entity needs the Modbus TCP connection."""
        return self.coil is not None

    def supported(self, coordinator: DimplexCoordinator) -> bool:
        """Return True if the installation provides this entity."""
        if self.uses_modbus and coordinator.modbus is None:
            return False
        return coordinator.data.condition(self.condition)


class DimplexEntity(CoordinatorEntity[DimplexCoordinator]):
    """Entity attached to the heat pump manager device."""

    _attr_has_entity_name = True
    entity_description: DimplexEntityDescription

    def __init__(
        self, coordinator: DimplexCoordinator, description: DimplexEntityDescription
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.serial}_{description.key}"
        self._attr_device_info = coordinator.appliance_device_info

    @property
    def raw_value(self) -> DatapointValue | None:
        """Return the backing value from the coordinator data."""
        if (key := self.entity_description.data_key) is None:
            return None
        return self.coordinator.data.values.get(key)

    @property
    @override
    def available(self) -> bool:
        """Return True if the backing value is known and the gateway is reachable."""
        if not super().available or not self.coordinator.connected:
            return False
        description = self.entity_description
        if description.uses_modbus and not self.coordinator.data.modbus_available:
            return False
        if description.data_key is not None and self.raw_value is None:
            return False
        if description.available_fn is not None:
            return description.available_fn(self.coordinator.data)
        return True


class DimplexGatewayEntity(DimplexEntity):
    """Entity attached to the NWPM Touch gateway device."""

    def __init__(
        self, coordinator: DimplexCoordinator, description: DimplexEntityDescription
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator, description)
        self._attr_device_info = coordinator.gateway_device_info
