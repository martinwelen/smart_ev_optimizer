"""Sensor platform for Smart EV Optimizer."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
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
    """Set up sensor entities from a config entry."""
    coordinator: SmartEVOptimizerCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[SensorEntity] = [
        SEODecisionReasonSensor(coordinator),
        SEOCalendarHourAvgSensor(coordinator),
        SEOAvailableCapacitySensor(coordinator),
        SEOOpportunityCostSensor(coordinator),
    ]

    vehicles = entry.data.get(CONF_VEHICLES, [])
    for vehicle_cfg in vehicles:
        vid = vehicle_cfg.get("vehicle_id", vehicle_cfg.get(CONF_VEHICLE_NAME, ""))
        name = vehicle_cfg.get(CONF_VEHICLE_NAME, vid)
        entities.append(SEOVehicleAllocatedAmpsSensor(coordinator, vid, name))
        entities.append(SEOVehicleAllocatedPhasesSensor(coordinator, vid, name))

    async_add_entities(entities)


class SEODecisionReasonSensor(CoordinatorEntity, SensorEntity):
    """Sensor that shows why the current charging decision was made."""

    def __init__(self, coordinator: SmartEVOptimizerCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_decision_reason"
        self._attr_name = "SEO Decision Reason"
        self._attr_icon = "mdi:information-outline"

    @property
    def native_value(self) -> str | None:
        return self.coordinator.data.decision_reason


class SEOCalendarHourAvgSensor(CoordinatorEntity, SensorEntity):
    """Sensor showing calendar hour average power consumption."""

    def __init__(self, coordinator: SmartEVOptimizerCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_calendar_hour_avg_kw"
        self._attr_name = "SEO Calendar Hour Avg kW"
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = "kW"

    @property
    def native_value(self) -> float | None:
        return self.coordinator.data.calendar_hour_avg_kw


class SEOAvailableCapacitySensor(CoordinatorEntity, SensorEntity):
    """Sensor showing headroom to power limit."""

    def __init__(self, coordinator: SmartEVOptimizerCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_available_capacity_kw"
        self._attr_name = "SEO Available Capacity kW"
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = "kW"

    @property
    def native_value(self) -> float | None:
        return self.coordinator.data.available_capacity_kw


class SEOOpportunityCostSensor(CoordinatorEntity, SensorEntity):
    """Sensor showing export revenue minus night charging cost."""

    def __init__(self, coordinator: SmartEVOptimizerCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_opportunity_cost"
        self._attr_name = "SEO Opportunity Cost"
        self._attr_device_class = SensorDeviceClass.MONETARY
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = "SEK/kWh"
        self._attr_icon = "mdi:currency-usd"

    @property
    def native_value(self) -> float | None:
        data = self.coordinator.data
        return data.opportunity_export_revenue - data.opportunity_night_cost


class SEOVehicleAllocatedAmpsSensor(CoordinatorEntity, SensorEntity):
    """Sensor showing per-vehicle allocated amps."""

    def __init__(
        self,
        coordinator: SmartEVOptimizerCoordinator,
        vehicle_id: str,
        vehicle_name: str,
    ) -> None:
        super().__init__(coordinator)
        self._vehicle_id = vehicle_id
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{vehicle_id}_allocated_amps"
        self._attr_name = f"SEO {vehicle_name} Allocated Amps"
        self._attr_device_class = SensorDeviceClass.CURRENT
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = "A"

    @property
    def native_value(self) -> int | None:
        for vehicle in self.coordinator.data.vehicles:
            if vehicle.vehicle_id == self._vehicle_id:
                return vehicle.allocated_amps
        return None


class SEOVehicleAllocatedPhasesSensor(CoordinatorEntity, SensorEntity):
    """Sensor showing per-vehicle allocated phases."""

    def __init__(
        self,
        coordinator: SmartEVOptimizerCoordinator,
        vehicle_id: str,
        vehicle_name: str,
    ) -> None:
        super().__init__(coordinator)
        self._vehicle_id = vehicle_id
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_{vehicle_id}_allocated_phases"
        )
        self._attr_name = f"SEO {vehicle_name} Allocated Phases"
        self._attr_icon = "mdi:sine-wave"

    @property
    def native_value(self) -> int | None:
        for vehicle in self.coordinator.data.vehicles:
            if vehicle.vehicle_id == self._vehicle_id:
                return vehicle.allocated_phases
        return None
