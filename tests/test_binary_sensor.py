"""Tests for binary_sensor platform."""
from unittest.mock import MagicMock

from custom_components.smart_ev_optimizer.binary_sensor import (
    SEOGridRewardsActiveSensor,
    SEOOBCCooldownActiveSensor,
    SEOVehicleChargingSensor,
)
from custom_components.smart_ev_optimizer.const import SOC_SOURCE_API
from custom_components.smart_ev_optimizer.coordinator import SmartEVOptimizerData
from custom_components.smart_ev_optimizer.vehicle import VehicleState


def _make_vehicle(**overrides) -> VehicleState:
    defaults = dict(
        vehicle_id="car_1",
        name="Family Car",
        priority=1,
        target_soc=80,
        current_soc=50,
        departure_time=None,
        is_connected=True,
        soc_source_type=SOC_SOURCE_API,
        soc_entity_id="sensor.car_soc",
        charger_entity_id="sensor.easee",
        allocated_amps=16,
        allocated_phases=1,
    )
    defaults.update(overrides)
    return VehicleState(**defaults)


def _make_coordinator_mock(data=None):
    coordinator = MagicMock()
    if data is None:
        data = SmartEVOptimizerData()
    coordinator.data = data
    coordinator.config_entry = MagicMock()
    coordinator.config_entry.entry_id = "test_entry"
    return coordinator


def test_grid_rewards_active_true():
    data = SmartEVOptimizerData(grid_rewards_active=True)
    coord = _make_coordinator_mock(data)
    sensor = SEOGridRewardsActiveSensor(coord)
    assert sensor.is_on is True


def test_grid_rewards_active_false():
    data = SmartEVOptimizerData(grid_rewards_active=False)
    coord = _make_coordinator_mock(data)
    sensor = SEOGridRewardsActiveSensor(coord)
    assert sensor.is_on is False


def test_grid_rewards_unique_id():
    coord = _make_coordinator_mock()
    sensor = SEOGridRewardsActiveSensor(coord)
    assert sensor._attr_unique_id == "test_entry_grid_rewards_active"


def test_vehicle_charging_true():
    vehicle = _make_vehicle(allocated_amps=16)
    data = SmartEVOptimizerData(vehicles=[vehicle])
    coord = _make_coordinator_mock(data)
    sensor = SEOVehicleChargingSensor(coord, "car_1", "Family Car")
    assert sensor.is_on is True


def test_vehicle_charging_false():
    vehicle = _make_vehicle(allocated_amps=0)
    data = SmartEVOptimizerData(vehicles=[vehicle])
    coord = _make_coordinator_mock(data)
    sensor = SEOVehicleChargingSensor(coord, "car_1", "Family Car")
    assert sensor.is_on is False


def test_vehicle_charging_not_found():
    data = SmartEVOptimizerData(vehicles=[])
    coord = _make_coordinator_mock(data)
    sensor = SEOVehicleChargingSensor(coord, "car_1", "Family Car")
    assert sensor.is_on is False


def test_obc_cooldown_active():
    data = SmartEVOptimizerData(
        decision_reason="obc_cooldown_active"
    )
    coord = _make_coordinator_mock(data)
    sensor = SEOOBCCooldownActiveSensor(coord)
    assert sensor.is_on is True


def test_obc_cooldown_inactive():
    data = SmartEVOptimizerData(decision_reason="all_clear")
    coord = _make_coordinator_mock(data)
    sensor = SEOOBCCooldownActiveSensor(coord)
    assert sensor.is_on is False
