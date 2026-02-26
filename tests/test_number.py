"""Tests for number platform."""
from unittest.mock import AsyncMock, MagicMock

from custom_components.smart_ev_optimizer.const import SOC_SOURCE_API
from custom_components.smart_ev_optimizer.coordinator import SmartEVOptimizerData
from custom_components.smart_ev_optimizer.number import (
    SEOPowerLimitNumber,
    SEOVehicleTargetSOCNumber,
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
        allocated_amps=0,
        allocated_phases=1,
    )
    defaults.update(overrides)
    return VehicleState(**defaults)


def _make_coordinator_mock(data=None):
    coordinator = MagicMock()
    if data is None:
        data = SmartEVOptimizerData(power_limit_kw=11.0)
    coordinator.data = data
    coordinator.config_entry = MagicMock()
    coordinator.config_entry.entry_id = "test_entry"
    coordinator.async_request_refresh = AsyncMock()
    return coordinator


def test_power_limit_number_value():
    coord = _make_coordinator_mock()
    number = SEOPowerLimitNumber(coord)
    assert number.native_value == 11.0


def test_power_limit_unique_id():
    coord = _make_coordinator_mock()
    number = SEOPowerLimitNumber(coord)
    assert number._attr_unique_id == "test_entry_power_limit_kw"


async def test_power_limit_set_value():
    coord = _make_coordinator_mock()
    number = SEOPowerLimitNumber(coord)
    await number.async_set_native_value(15.0)
    assert coord.data.power_limit_kw == 15.0
    coord.async_request_refresh.assert_called_once()


def test_vehicle_target_soc_value():
    vehicle = _make_vehicle(target_soc=80)
    data = SmartEVOptimizerData(vehicles=[vehicle])
    coord = _make_coordinator_mock(data)
    number = SEOVehicleTargetSOCNumber(coord, "car_1", "Family Car")
    assert number.native_value == 80


def test_vehicle_target_soc_not_found():
    data = SmartEVOptimizerData(vehicles=[])
    coord = _make_coordinator_mock(data)
    number = SEOVehicleTargetSOCNumber(coord, "car_1", "Family Car")
    assert number.native_value is None


async def test_vehicle_target_soc_set_value():
    vehicle = _make_vehicle(target_soc=80)
    data = SmartEVOptimizerData(vehicles=[vehicle])
    coord = _make_coordinator_mock(data)
    number = SEOVehicleTargetSOCNumber(coord, "car_1", "Family Car")
    await number.async_set_native_value(90)
    assert vehicle.target_soc == 90
    coord.async_request_refresh.assert_called_once()


def test_vehicle_target_soc_unique_id():
    vehicle = _make_vehicle()
    data = SmartEVOptimizerData(vehicles=[vehicle])
    coord = _make_coordinator_mock(data)
    number = SEOVehicleTargetSOCNumber(coord, "car_1", "Family Car")
    assert number._attr_unique_id == "test_entry_car_1_target_soc"
