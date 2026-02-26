"""Tests for vehicle data model."""

from custom_components.smart_ev_optimizer.const import (
    SOC_SOURCE_API,
    SOC_SOURCE_MANUAL,
    SOC_SOURCE_NONE,
)
from custom_components.smart_ev_optimizer.vehicle import (
    VehicleConfig,
    VehicleState,
    build_vehicle_state,
    classify_soc_source,
)


def test_classify_soc_source_sensor():
    assert classify_soc_source("sensor.car_soc") == SOC_SOURCE_API


def test_classify_soc_source_input_number():
    assert classify_soc_source("input_number.manual_soc") == SOC_SOURCE_MANUAL


def test_classify_soc_source_none():
    assert classify_soc_source(None) == SOC_SOURCE_NONE


def test_classify_soc_source_empty():
    assert classify_soc_source("") == SOC_SOURCE_NONE


def test_vehicle_config_creation():
    cfg = VehicleConfig(
        vehicle_id="car_1",
        name="Family Car",
        priority=1,
        charger_entity_id="sensor.easee_status",
        soc_entity_id="sensor.car_soc",
        target_soc=80,
        departure_entity_id=None,
    )
    assert cfg.vehicle_id == "car_1"
    assert cfg.priority == 1


def test_vehicle_state_needs_charge():
    state = VehicleState(
        vehicle_id="car_1",
        name="Family Car",
        priority=1,
        target_soc=80,
        current_soc=50,
        departure_time=None,
        is_connected=True,
        soc_source_type=SOC_SOURCE_API,
        soc_entity_id="sensor.car_soc",
        charger_entity_id="sensor.easee_status",
        allocated_amps=0,
        allocated_phases=1,
    )
    assert state.needs_charge is True


def test_vehicle_state_no_charge_needed():
    state = VehicleState(
        vehicle_id="car_1",
        name="Family Car",
        priority=1,
        target_soc=80,
        current_soc=85,
        departure_time=None,
        is_connected=True,
        soc_source_type=SOC_SOURCE_API,
        soc_entity_id="sensor.car_soc",
        charger_entity_id="sensor.easee_status",
        allocated_amps=0,
        allocated_phases=1,
    )
    assert state.needs_charge is False


def test_vehicle_state_needs_charge_soc_unknown():
    state = VehicleState(
        vehicle_id="car_1",
        name="Family Car",
        priority=1,
        target_soc=80,
        current_soc=None,
        departure_time=None,
        is_connected=True,
        soc_source_type=SOC_SOURCE_NONE,
        soc_entity_id=None,
        charger_entity_id="sensor.easee_status",
        allocated_amps=0,
        allocated_phases=1,
    )
    assert state.needs_charge is True


def test_vehicle_state_disconnected_no_charge():
    state = VehicleState(
        vehicle_id="car_1",
        name="Family Car",
        priority=1,
        target_soc=80,
        current_soc=50,
        departure_time=None,
        is_connected=False,
        soc_source_type=SOC_SOURCE_API,
        soc_entity_id="sensor.car_soc",
        charger_entity_id="sensor.easee_status",
        allocated_amps=0,
        allocated_phases=1,
    )
    assert state.needs_charge is False


def test_build_vehicle_state():
    cfg = VehicleConfig(
        vehicle_id="car_1",
        name="Family Car",
        priority=1,
        charger_entity_id="sensor.easee_status",
        soc_entity_id="sensor.car_soc",
        target_soc=80,
        departure_entity_id=None,
    )
    state = build_vehicle_state(config=cfg, current_soc=65, is_connected=True, departure_time=None)
    assert state.vehicle_id == "car_1"
    assert state.current_soc == 65
    assert state.soc_source_type == SOC_SOURCE_API
    assert state.needs_charge is True
    assert state.allocated_amps == 0
    assert state.allocated_phases == 1
