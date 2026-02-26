"""Select platform for Smart EV Optimizer."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import SmartEVOptimizerCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities,
) -> None:
    """Set up select entities from a config entry."""
    coordinator: SmartEVOptimizerCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[SelectEntity] = [
        SEOConnectedVehicleSelect(coordinator),
    ]

    async_add_entities(entities)


class SEOConnectedVehicleSelect(CoordinatorEntity, SelectEntity):
    """Select entity for manually overriding vehicle-charger assignment."""

    def __init__(self, coordinator: SmartEVOptimizerCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_connected_vehicle"
        self._attr_name = "SEO Connected Vehicle"
        self._attr_icon = "mdi:car-connected"

    @property
    def options(self) -> list[str]:
        return self.coordinator._vehicle_names

    @property
    def current_option(self) -> str | None:
        return self.coordinator._connected_vehicle

    async def async_select_option(self, option: str) -> None:
        self.coordinator._connected_vehicle = option
        await self.coordinator.async_request_refresh()
