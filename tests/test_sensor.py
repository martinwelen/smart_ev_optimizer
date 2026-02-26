"""Tests for sensor platform."""
from unittest.mock import MagicMock

from custom_components.smart_ev_optimizer.const import SOC_SOURCE_API
from custom_components.smart_ev_optimizer.coordinator import SmartEVOptimizerData
from custom_components.smart_ev_optimizer.sensor import (
    SEOAvailableCapacitySensor,
    SEOCalendarHourAvgSensor,
    SEODecisionReasonSensor,
    SEOOpportunityCostSensor,
    SEOVehicleAllocatedAmpsSensor,
    SEOVehicleAllocatedPhasesSensor,
)
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
        data = SmartEVOptimizerData(
            decision_reason="all_clear",
            calendar_hour_avg_kw=5.5,
            available_capacity_kw=5.5,
            opportunity_export_revenue=1.05,
            opportunity_night_cost=1.125,
        )
    coordinator.data = data
    coordinator.config_entry = MagicMock()
    coordinator.config_entry.entry_id = "test_entry"
    return coordinator


def test_decision_reason_sensor():
    coord = _make_coordinator_mock()
    sensor = SEODecisionReasonSensor(coord)
    assert sensor.native_value == "all_clear"


def test_decision_reason_sensor_unique_id():
    coord = _make_coordinator_mock()
    sensor = SEODecisionReasonSensor(coord)
    assert sensor._attr_unique_id == "test_entry_decision_reason"


def test_calendar_hour_avg_sensor():
    coord = _make_coordinator_mock()
    sensor = SEOCalendarHourAvgSensor(coord)
    assert sensor.native_value == 5.5


def test_available_capacity_sensor():
    coord = _make_coordinator_mock()
    sensor = SEOAvailableCapacitySensor(coord)
    assert sensor.native_value == 5.5


def test_opportunity_cost_sensor():
    coord = _make_coordinator_mock()
    sensor = SEOOpportunityCostSensor(coord)
    # Export revenue (1.05) - night cost (1.125) = -0.075
    assert abs(sensor.native_value - (-0.075)) < 0.001


def test_opportunity_cost_sensor_positive():
    data = SmartEVOptimizerData(
        opportunity_export_revenue=2.0,
        opportunity_night_cost=1.0,
    )
    coord = _make_coordinator_mock(data)
    sensor = SEOOpportunityCostSensor(coord)
    assert abs(sensor.native_value - 1.0) < 0.001


def test_vehicle_allocated_amps_sensor():
    vehicle = _make_vehicle()
    data = SmartEVOptimizerData(vehicles=[vehicle])
    coord = _make_coordinator_mock(data)
    sensor = SEOVehicleAllocatedAmpsSensor(coord, "car_1", "Family Car")
    assert sensor.native_value == 16


def test_vehicle_allocated_amps_sensor_not_found():
    data = SmartEVOptimizerData(vehicles=[])
    coord = _make_coordinator_mock(data)
    sensor = SEOVehicleAllocatedAmpsSensor(coord, "car_1", "Family Car")
    assert sensor.native_value is None


def test_vehicle_allocated_phases_sensor():
    vehicle = _make_vehicle(allocated_phases=3)
    data = SmartEVOptimizerData(vehicles=[vehicle])
    coord = _make_coordinator_mock(data)
    sensor = SEOVehicleAllocatedPhasesSensor(coord, "car_1", "Family Car")
    assert sensor.native_value == 3


def test_vehicle_allocated_amps_unique_id():
    vehicle = _make_vehicle()
    data = SmartEVOptimizerData(vehicles=[vehicle])
    coord = _make_coordinator_mock(data)
    sensor = SEOVehicleAllocatedAmpsSensor(coord, "car_1", "Family Car")
    assert sensor._attr_unique_id == "test_entry_car_1_allocated_amps"
