"""Tests for select platform."""

from unittest.mock import AsyncMock, MagicMock

from custom_components.smart_ev_optimizer.const import SOC_SOURCE_API
from custom_components.smart_ev_optimizer.coordinator import SmartEVOptimizerData
from custom_components.smart_ev_optimizer.select import SEOConnectedVehicleSelect
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


def _make_coordinator_mock(data=None, vehicle_names=None):
    coordinator = MagicMock()
    if data is None:
        data = SmartEVOptimizerData()
    coordinator.data = data
    coordinator.config_entry = MagicMock()
    coordinator.config_entry.entry_id = "test_entry"
    coordinator._connected_vehicle = None
    coordinator._vehicle_names = vehicle_names or ["Family Car", "Work Car"]
    coordinator.async_request_refresh = AsyncMock()
    return coordinator


def test_connected_vehicle_options():
    coord = _make_coordinator_mock()
    select = SEOConnectedVehicleSelect(coord)
    assert select.options == ["Family Car", "Work Car"]


def test_connected_vehicle_current_none():
    coord = _make_coordinator_mock()
    select = SEOConnectedVehicleSelect(coord)
    assert select.current_option is None


def test_connected_vehicle_current_set():
    coord = _make_coordinator_mock()
    coord._connected_vehicle = "Family Car"
    select = SEOConnectedVehicleSelect(coord)
    assert select.current_option == "Family Car"


async def test_connected_vehicle_select_option():
    coord = _make_coordinator_mock()
    select = SEOConnectedVehicleSelect(coord)
    await select.async_select_option("Work Car")
    assert coord._connected_vehicle == "Work Car"
    coord.async_request_refresh.assert_called_once()


def test_connected_vehicle_unique_id():
    coord = _make_coordinator_mock()
    select = SEOConnectedVehicleSelect(coord)
    assert select._attr_unique_id == "test_entry_connected_vehicle"
