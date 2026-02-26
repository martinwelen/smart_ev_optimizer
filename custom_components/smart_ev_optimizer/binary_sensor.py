"""Binary sensor platform for Smart EV Optimizer."""
from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
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
    """Set up binary sensor entities from a config entry."""
    coordinator: SmartEVOptimizerCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[BinarySensorEntity] = [
        SEOGridRewardsActiveSensor(coordinator),
        SEOOBCCooldownActiveSensor(coordinator),
    ]

    vehicles = entry.data.get(CONF_VEHICLES, [])
    for vehicle_cfg in vehicles:
        vid = vehicle_cfg.get("vehicle_id", vehicle_cfg.get(CONF_VEHICLE_NAME, ""))
        name = vehicle_cfg.get(CONF_VEHICLE_NAME, vid)
        entities.append(SEOVehicleChargingSensor(coordinator, vid, name))

    async_add_entities(entities)


class SEOGridRewardsActiveSensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor indicating Grid Rewards status."""

    def __init__(self, coordinator: SmartEVOptimizerCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_grid_rewards_active"
        self._attr_name = "SEO Grid Rewards Active"
        self._attr_device_class = BinarySensorDeviceClass.POWER
        self._attr_icon = "mdi:transmission-tower"

    @property
    def is_on(self) -> bool:
        return self.coordinator.data.grid_rewards_active


class SEOVehicleChargingSensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor indicating whether a vehicle is currently charging."""

    def __init__(
        self,
        coordinator: SmartEVOptimizerCoordinator,
        vehicle_id: str,
        vehicle_name: str,
    ) -> None:
        super().__init__(coordinator)
        self._vehicle_id = vehicle_id
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{vehicle_id}_charging"
        self._attr_name = f"SEO {vehicle_name} Charging"
        self._attr_device_class = BinarySensorDeviceClass.BATTERY_CHARGING

    @property
    def is_on(self) -> bool:
        for vehicle in self.coordinator.data.vehicles:
            if vehicle.vehicle_id == self._vehicle_id:
                return vehicle.allocated_amps > 0
        return False


class SEOOBCCooldownActiveSensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor indicating whether the OBC phase-switch cooldown is active."""

    def __init__(self, coordinator: SmartEVOptimizerCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_obc_cooldown_active"
        self._attr_name = "SEO OBC Cooldown Active"
        self._attr_icon = "mdi:timer-sand"

    @property
    def is_on(self) -> bool:
        return "obc_cooldown" in self.coordinator.data.decision_reason
