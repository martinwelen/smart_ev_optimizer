"""Switch platform for Smart EV Optimizer."""
from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_VEHICLE_NAME, CONF_VEHICLES, DOMAIN
from .coordinator import SmartEVOptimizerCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities,
) -> None:
    """Set up switch entities from a config entry."""
    coordinator: SmartEVOptimizerCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[SwitchEntity] = [
        SEOPauseAllSwitchEntity(coordinator),
    ]

    vehicles = entry.data.get(CONF_VEHICLES, [])
    for vehicle_cfg in vehicles:
        vid = vehicle_cfg.get("vehicle_id", vehicle_cfg.get(CONF_VEHICLE_NAME, ""))
        name = vehicle_cfg.get(CONF_VEHICLE_NAME, vid)
        entities.append(SEOForceChargeSwitchEntity(coordinator, vid, name))

    async_add_entities(entities)


class SEOForceChargeSwitchEntity(CoordinatorEntity, SwitchEntity):
    """Switch to force-charge a specific vehicle."""

    def __init__(
        self,
        coordinator: SmartEVOptimizerCoordinator,
        vehicle_id: str,
        vehicle_name: str,
    ) -> None:
        super().__init__(coordinator)
        self._vehicle_id = vehicle_id
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_force_charge_{vehicle_id}"
        self._attr_name = f"SEO Force Charge {vehicle_name}"
        self._attr_icon = "mdi:ev-station"

    @property
    def is_on(self) -> bool:
        return self._vehicle_id in self.coordinator._force_charge_vehicles

    async def async_turn_on(self, **kwargs) -> None:
        self.coordinator._force_charge_vehicles.add(self._vehicle_id)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        self.coordinator._force_charge_vehicles.discard(self._vehicle_id)
        await self.coordinator.async_request_refresh()


class SEOPauseAllSwitchEntity(CoordinatorEntity, SwitchEntity):
    """Switch to pause all EV charging (emergency stop)."""

    def __init__(self, coordinator: SmartEVOptimizerCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_pause_all"
        self._attr_name = "SEO Pause All Charging"
        self._attr_icon = "mdi:stop-circle"

    @property
    def is_on(self) -> bool:
        return self.coordinator._pause_all

    async def async_turn_on(self, **kwargs) -> None:
        self.coordinator._pause_all = True
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        self.coordinator._pause_all = False
        await self.coordinator.async_request_refresh()
