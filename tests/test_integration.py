"""End-to-end integration tests for the full decision pipeline."""
from datetime import UTC, datetime
from unittest.mock import patch

from custom_components.smart_ev_optimizer.const import SOC_SOURCE_API, SOC_SOURCE_NONE
from custom_components.smart_ev_optimizer.coordinator import (
    PipelineContext,
    run_decision_pipeline,
)
from custom_components.smart_ev_optimizer.power_manager import CalendarHourTracker
from custom_components.smart_ev_optimizer.safety import OBCCooldownTracker
from custom_components.smart_ev_optimizer.vehicle import (
    VehicleConfig,
    VehicleState,
    build_vehicle_state,
)

_FIXED_NOW = datetime(2026, 2, 26, 14, 30, tzinfo=UTC)
_UTCNOW_PATH = "custom_components.smart_ev_optimizer.power_manager._utcnow"


def _utc(year, month, day, hour, minute):
    return datetime(year, month, day, hour, minute, tzinfo=UTC)


def _make_vehicle(vehicle_id, priority=1, current_soc=50, target_soc=80,
                  is_connected=True, soc_source_type=SOC_SOURCE_API):
    return VehicleState(
        vehicle_id=vehicle_id, name=f"Car {vehicle_id}", priority=priority,
        target_soc=target_soc, current_soc=current_soc, departure_time=None,
        is_connected=is_connected, soc_source_type=soc_source_type,
        soc_entity_id=f"sensor.{vehicle_id}_soc" if soc_source_type == SOC_SOURCE_API else None,
        charger_entity_id=f"sensor.{vehicle_id}_charger",
    )


def _make_context(vehicles, grid_power_w=5000, solar_power_w=3000,
                  battery_power_w=0, grid_rewards_active=False,
                  current_export_price=0.50, night_price=0.30,
                  power_limit_kw=11.0, force_charge=None,
                  tracker_samples=None):
    tracker = CalendarHourTracker()
    with patch(_UTCNOW_PATH, return_value=_FIXED_NOW):
        if tracker_samples:
            for s in tracker_samples:
                tracker.add_sample(s)
        else:
            tracker.add_sample(grid_power_w)

    return PipelineContext(
        grid_power_w=grid_power_w, solar_power_w=solar_power_w,
        battery_power_w=battery_power_w, battery_soc=80,
        grid_rewards_active=grid_rewards_active, grid_meter_available=True,
        current_export_price=current_export_price, current_import_price=0.50,
        night_prices=[(_utc(2026, 2, 27, 3, 0), night_price)],
        grid_fee_import=0.40, grid_fee_export=0.05,
        export_compensation=0.10, vat_rate=0.25,
        power_limit_kw=power_limit_kw, vehicles=vehicles,
        obc_tracker=OBCCooldownTracker(),
        calendar_hour_tracker=tracker,
        force_charge_vehicles=force_charge or set(),
        last_commands={},
    )


class TestFullPipeline:
    """End-to-end tests exercising the complete decision pipeline."""

    def test_single_vehicle_normal_charging(self):
        """Normal conditions: single vehicle charges with available capacity."""
        v = _make_vehicle("car_1", current_soc=50)
        ctx = _make_context([v], grid_power_w=5000, power_limit_kw=11.0,
                            current_export_price=0.10, night_price=0.80)
        with patch(_UTCNOW_PATH, return_value=_FIXED_NOW):
            result = run_decision_pipeline(ctx)
        assert result.vehicles[0].allocated_amps > 0
        assert "charging_now_cheaper" in result.decision_reason

    def test_single_vehicle_export_profitable(self):
        """High export price: vehicle should NOT charge, solar should be sold."""
        v = _make_vehicle("car_1", current_soc=50)
        ctx = _make_context([v], grid_power_w=3000, power_limit_kw=11.0,
                            current_export_price=2.00, night_price=0.20)
        with patch(_UTCNOW_PATH, return_value=_FIXED_NOW):
            result = run_decision_pipeline(ctx)
        assert result.vehicles[0].allocated_amps == 0
        assert "export_more_profitable" in result.decision_reason

    def test_grid_rewards_blocks_all(self):
        """Grid Rewards active + battery exporting: all charging blocked."""
        v = _make_vehicle("car_1", current_soc=50)
        ctx = _make_context([v], battery_power_w=-500, grid_rewards_active=True)
        with patch(_UTCNOW_PATH, return_value=_FIXED_NOW):
            result = run_decision_pipeline(ctx)
        assert result.vehicles[0].allocated_amps == 0
        assert "grid_rewards" in result.decision_reason

    def test_grid_rewards_not_exporting_allows_charging(self):
        """Grid Rewards active but battery NOT exporting: charging allowed."""
        v = _make_vehicle("car_1", current_soc=50)
        ctx = _make_context([v], battery_power_w=500, grid_rewards_active=True,
                            current_export_price=0.10, night_price=0.80)
        with patch(_UTCNOW_PATH, return_value=_FIXED_NOW):
            result = run_decision_pipeline(ctx)
        assert result.vehicles[0].allocated_amps > 0

    def test_two_vehicles_priority_allocation(self):
        """Two vehicles: higher priority gets power first."""
        v1 = _make_vehicle("car_1", priority=1, current_soc=50)
        v2 = _make_vehicle("car_2", priority=2, current_soc=50)
        ctx = _make_context([v2, v1], grid_power_w=8000, power_limit_kw=11.0,
                            current_export_price=0.10, night_price=0.80)
        with patch(_UTCNOW_PATH, return_value=_FIXED_NOW):
            result = run_decision_pipeline(ctx)
        car_1 = next(v for v in result.vehicles if v.vehicle_id == "car_1")
        assert car_1.allocated_amps > 0
        # car_2 may or may not get amps depending on remaining capacity

    def test_vehicle_at_target_soc_skipped(self):
        """Vehicle already at target SoC gets no allocation."""
        v = _make_vehicle("car_1", current_soc=90, target_soc=80)
        ctx = _make_context([v], current_export_price=0.10, night_price=0.80)
        with patch(_UTCNOW_PATH, return_value=_FIXED_NOW):
            result = run_decision_pipeline(ctx)
        assert result.vehicles[0].allocated_amps == 0

    def test_disconnected_vehicle_skipped(self):
        """Disconnected vehicle gets no allocation."""
        v = _make_vehicle("car_1", is_connected=False)
        ctx = _make_context([v], current_export_price=0.10, night_price=0.80)
        with patch(_UTCNOW_PATH, return_value=_FIXED_NOW):
            result = run_decision_pipeline(ctx)
        assert result.vehicles[0].allocated_amps == 0

    def test_force_charge_overrides_export_decision(self):
        """Force charge allocates power even when export is more profitable."""
        v = _make_vehicle("car_1", current_soc=50)
        ctx = _make_context([v], grid_power_w=3000, power_limit_kw=11.0,
                            current_export_price=2.00, night_price=0.10,
                            force_charge={"car_1"})
        with patch(_UTCNOW_PATH, return_value=_FIXED_NOW):
            result = run_decision_pipeline(ctx)
        assert result.vehicles[0].allocated_amps > 0
        assert "force_charge" in result.decision_reason

    def test_power_limit_constrains_allocation(self):
        """High grid usage leaves little room for charging."""
        v = _make_vehicle("car_1", current_soc=50)
        ctx = _make_context([v], grid_power_w=10500, power_limit_kw=11.0,
                            current_export_price=0.10, night_price=0.80)
        with patch(_UTCNOW_PATH, return_value=_FIXED_NOW):
            result = run_decision_pipeline(ctx)
        # Only 0.5kW headroom = ~2.2A, below 6A minimum
        assert result.vehicles[0].allocated_amps == 0

    def test_offline_vehicle_unknown_soc_charges(self):
        """Offline vehicle (no SoC) connected: assumes needs charge."""
        v = _make_vehicle("car_1", current_soc=None, soc_source_type=SOC_SOURCE_NONE)
        ctx = _make_context([v], grid_power_w=5000, power_limit_kw=11.0,
                            current_export_price=0.10, night_price=0.80)
        with patch(_UTCNOW_PATH, return_value=_FIXED_NOW):
            result = run_decision_pipeline(ctx)
        assert result.vehicles[0].allocated_amps > 0

    def test_build_vehicle_state_integration(self):
        """Test VehicleConfig -> build_vehicle_state -> pipeline integration."""
        cfg = VehicleConfig(
            vehicle_id="car_1", name="Family Car", priority=1,
            charger_entity_id="sensor.easee", soc_entity_id="sensor.car_soc",
            target_soc=80, departure_entity_id=None,
        )
        state = build_vehicle_state(
            config=cfg, current_soc=60, is_connected=True, departure_time=None,
        )
        ctx = _make_context([state], grid_power_w=5000, power_limit_kw=11.0,
                            current_export_price=0.10, night_price=0.80)
        with patch(_UTCNOW_PATH, return_value=_FIXED_NOW):
            result = run_decision_pipeline(ctx)
        assert result.vehicles[0].allocated_amps > 0
        assert result.vehicles[0].soc_source_type == SOC_SOURCE_API

    def test_data_output_completeness(self):
        """Verify SmartEVOptimizerData has all expected fields populated."""
        v = _make_vehicle("car_1", current_soc=50)
        ctx = _make_context([v], grid_power_w=5000, power_limit_kw=11.0,
                            current_export_price=0.50, night_price=0.30)
        with patch(_UTCNOW_PATH, return_value=_FIXED_NOW):
            result = run_decision_pipeline(ctx)
        assert result.grid_power_w == 5000.0
        assert result.power_limit_kw == 11.0
        assert result.calendar_hour_avg_kw > 0
        assert result.available_capacity_kw >= 0
        assert isinstance(result.decision_reason, str)
        assert len(result.vehicles) == 1
        assert result.vat_rate == 0.25
