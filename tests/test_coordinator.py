"""Tests for the main coordinator decision pipeline."""
from datetime import datetime, timezone
from unittest.mock import patch

from custom_components.smart_ev_optimizer.const import SOC_SOURCE_API
from custom_components.smart_ev_optimizer.coordinator import (
    PipelineContext,
    build_initial_data,
    run_decision_pipeline,
)
from custom_components.smart_ev_optimizer.power_manager import CalendarHourTracker
from custom_components.smart_ev_optimizer.safety import OBCCooldownTracker
from custom_components.smart_ev_optimizer.vehicle import VehicleState


def _make_vehicle_state(**overrides) -> VehicleState:
    defaults = dict(
        vehicle_id="car_1", name="Test Car", priority=1, target_soc=80,
        current_soc=50, departure_time=None, is_connected=True,
        soc_source_type=SOC_SOURCE_API, soc_entity_id="sensor.car_soc",
        charger_entity_id="sensor.easee_charger", allocated_amps=0, allocated_phases=1,
    )
    defaults.update(overrides)
    return VehicleState(**defaults)


def _utc(year, month, day, hour, minute):
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)  # noqa: UP017


def test_build_initial_data():
    data = build_initial_data(power_limit_kw=11.0)
    assert data.grid_power_w == 0.0
    assert data.vehicles == []
    assert data.decision_reason == "initialized"
    assert data.power_limit_kw == 11.0


def test_pipeline_safety_blocks_charging():
    vehicles = [_make_vehicle_state()]
    ctx = PipelineContext(
        grid_power_w=5000.0, solar_power_w=3000.0,
        battery_power_w=-500.0, battery_soc=80,
        grid_rewards_active=True, grid_meter_available=True,
        current_export_price=1.50, current_import_price=1.00,
        night_prices=[(_utc(2026, 2, 27, 2, 0), 0.30)],
        grid_fee_import=0.40, grid_fee_export=0.05,
        export_compensation=0.10, vat_rate=0.25,
        power_limit_kw=11.0, vehicles=vehicles,
        obc_tracker=OBCCooldownTracker(),
        calendar_hour_tracker=CalendarHourTracker(),
        force_charge_vehicles=set(), last_commands={},
    )
    result = run_decision_pipeline(ctx)
    assert result.decision_reason == "grid_rewards_active_battery_exporting"
    assert all(v.allocated_amps == 0 for v in result.vehicles)


def test_pipeline_normal_charging():
    vehicles = [_make_vehicle_state()]
    tracker = CalendarHourTracker()
    now = _utc(2026, 2, 26, 10, 15)
    with patch("custom_components.smart_ev_optimizer.power_manager._utcnow", return_value=now):
        tracker.add_sample(5000.0)
    ctx = PipelineContext(
        grid_power_w=5000.0, solar_power_w=3000.0,
        battery_power_w=0.0, battery_soc=80,
        grid_rewards_active=False, grid_meter_available=True,
        current_export_price=0.10, current_import_price=0.50,
        night_prices=[(_utc(2026, 2, 27, 2, 0), 0.80)],
        grid_fee_import=0.40, grid_fee_export=0.05,
        export_compensation=0.10, vat_rate=0.25,
        power_limit_kw=11.0, vehicles=vehicles,
        obc_tracker=OBCCooldownTracker(),
        calendar_hour_tracker=tracker,
        force_charge_vehicles=set(), last_commands={},
    )
    result = run_decision_pipeline(ctx)
    assert result.vehicles[0].allocated_amps > 0


def test_pipeline_force_charge_overrides_optimization():
    vehicles = [_make_vehicle_state()]
    tracker = CalendarHourTracker()
    now = _utc(2026, 2, 26, 10, 15)
    with patch("custom_components.smart_ev_optimizer.power_manager._utcnow", return_value=now):
        tracker.add_sample(5000.0)
    ctx = PipelineContext(
        grid_power_w=5000.0, solar_power_w=3000.0,
        battery_power_w=0.0, battery_soc=80,
        grid_rewards_active=False, grid_meter_available=True,
        current_export_price=2.00, current_import_price=2.00,
        night_prices=[(_utc(2026, 2, 27, 2, 0), 0.10)],
        grid_fee_import=0.40, grid_fee_export=0.05,
        export_compensation=0.10, vat_rate=0.25,
        power_limit_kw=11.0, vehicles=vehicles,
        obc_tracker=OBCCooldownTracker(),
        calendar_hour_tracker=tracker,
        force_charge_vehicles={"car_1"}, last_commands={},
    )
    result = run_decision_pipeline(ctx)
    assert result.vehicles[0].allocated_amps > 0
    assert "force_charge" in result.decision_reason
