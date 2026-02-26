"""Number platform for Smart EV Optimizer."""
from __future__ import annotations

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberMode
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
    """Set up number entities from a config entry."""
    coordinator: SmartEVOptimizerCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[NumberEntity] = [
        SEOPowerLimitNumber(coordinator),
    ]

    vehicles = entry.data.get(CONF_VEHICLES, [])
    for vehicle_cfg in vehicles:
        vid = vehicle_cfg.get("vehicle_id", vehicle_cfg.get(CONF_VEHICLE_NAME, ""))
        name = vehicle_cfg.get(CONF_VEHICLE_NAME, vid)
        entities.append(SEOVehicleTargetSOCNumber(coordinator, vid, name))

    async_add_entities(entities)


class SEOPowerLimitNumber(CoordinatorEntity, NumberEntity):
    """Number entity for the site power ceiling in kW."""

    def __init__(self, coordinator: SmartEVOptimizerCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_power_limit_kw"
        self._attr_name = "SEO Power Limit kW"
        self._attr_device_class = NumberDeviceClass.POWER
        self._attr_native_unit_of_measurement = "kW"
        self._attr_native_min_value = 0.0
        self._attr_native_max_value = 50.0
        self._attr_native_step = 0.5
        self._attr_mode = NumberMode.BOX
        self._attr_icon = "mdi:flash-alert"

    @property
    def native_value(self) -> float | None:
        return self.coordinator.data.power_limit_kw

    async def async_set_native_value(self, value: float) -> None:
        self.coordinator.data.power_limit_kw = value
        await self.coordinator.async_request_refresh()


class SEOVehicleTargetSOCNumber(CoordinatorEntity, NumberEntity):
    """Number entity for per-vehicle target state of charge."""

    def __init__(
        self,
        coordinator: SmartEVOptimizerCoordinator,
        vehicle_id: str,
        vehicle_name: str,
    ) -> None:
        super().__init__(coordinator)
        self._vehicle_id = vehicle_id
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{vehicle_id}_target_soc"
        self._attr_name = f"SEO {vehicle_name} Target SoC"
        self._attr_device_class = NumberDeviceClass.BATTERY
        self._attr_native_unit_of_measurement = "%"
        self._attr_native_min_value = 0
        self._attr_native_max_value = 100
        self._attr_native_step = 5
        self._attr_mode = NumberMode.SLIDER
        self._attr_icon = "mdi:battery-charging"

    @property
    def native_value(self) -> int | None:
        for vehicle in self.coordinator.data.vehicles:
            if vehicle.vehicle_id == self._vehicle_id:
                return vehicle.target_soc
        return None

    async def async_set_native_value(self, value: float) -> None:
        for vehicle in self.coordinator.data.vehicles:
            if vehicle.vehicle_id == self._vehicle_id:
                vehicle.target_soc = int(value)
                break
        await self.coordinator.async_request_refresh()
