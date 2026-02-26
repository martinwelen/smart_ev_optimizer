"""Tests for the main coordinator decision pipeline."""

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from custom_components.smart_ev_optimizer.const import (
    CONF_BATTERY_POWER_SENSOR,
    CONF_BATTERY_SOC_SENSOR,
    CONF_EXPORT_COMPENSATION,
    CONF_GRID_FEE_EXPORT,
    CONF_GRID_FEE_IMPORT,
    CONF_GRID_SENSOR,
    CONF_NORDPOOL_SENSOR,
    CONF_SOLAR_SENSOR,
    CONF_VAT_RATE,
    CONF_VEHICLE_CHARGER_ENTITY,
    CONF_VEHICLE_NAME,
    CONF_VEHICLE_PRIORITY,
    CONF_VEHICLE_SOC_ENTITY,
    CONF_VEHICLE_TARGET_SOC,
    CONF_VEHICLES,
    SOC_SOURCE_API,
)
from custom_components.smart_ev_optimizer.coordinator import (
    PipelineContext,
    SmartEVOptimizerCoordinator,
    build_initial_data,
    run_decision_pipeline,
)
from custom_components.smart_ev_optimizer.power_manager import CalendarHourTracker
from custom_components.smart_ev_optimizer.safety import OBCCooldownTracker
from custom_components.smart_ev_optimizer.vehicle import VehicleState


def _make_vehicle_state(**overrides) -> VehicleState:
    defaults = dict(
        vehicle_id="car_1",
        name="Test Car",
        priority=1,
        target_soc=80,
        current_soc=50,
        departure_time=None,
        is_connected=True,
        soc_source_type=SOC_SOURCE_API,
        soc_entity_id="sensor.car_soc",
        charger_entity_id="sensor.easee_charger",
        allocated_amps=0,
        allocated_phases=1,
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
        grid_power_w=5000.0,
        solar_power_w=3000.0,
        battery_power_w=-500.0,
        battery_soc=80,
        grid_rewards_active=True,
        grid_meter_available=True,
        current_export_price=1.50,
        current_import_price=1.00,
        night_prices=[(_utc(2026, 2, 27, 2, 0), 0.30)],
        grid_fee_import=0.40,
        grid_fee_export=0.05,
        export_compensation=0.10,
        vat_rate=0.25,
        power_limit_kw=11.0,
        vehicles=vehicles,
        obc_tracker=OBCCooldownTracker(),
        calendar_hour_tracker=CalendarHourTracker(),
        force_charge_vehicles=set(),
        last_commands={},
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
        grid_power_w=5000.0,
        solar_power_w=3000.0,
        battery_power_w=0.0,
        battery_soc=80,
        grid_rewards_active=False,
        grid_meter_available=True,
        current_export_price=0.10,
        current_import_price=0.50,
        night_prices=[(_utc(2026, 2, 27, 2, 0), 0.80)],
        grid_fee_import=0.40,
        grid_fee_export=0.05,
        export_compensation=0.10,
        vat_rate=0.25,
        power_limit_kw=11.0,
        vehicles=vehicles,
        obc_tracker=OBCCooldownTracker(),
        calendar_hour_tracker=tracker,
        force_charge_vehicles=set(),
        last_commands={},
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
        grid_power_w=5000.0,
        solar_power_w=3000.0,
        battery_power_w=0.0,
        battery_soc=80,
        grid_rewards_active=False,
        grid_meter_available=True,
        current_export_price=2.00,
        current_import_price=2.00,
        night_prices=[(_utc(2026, 2, 27, 2, 0), 0.10)],
        grid_fee_import=0.40,
        grid_fee_export=0.05,
        export_compensation=0.10,
        vat_rate=0.25,
        power_limit_kw=11.0,
        vehicles=vehicles,
        obc_tracker=OBCCooldownTracker(),
        calendar_hour_tracker=tracker,
        force_charge_vehicles={"car_1"},
        last_commands={},
    )
    result = run_decision_pipeline(ctx)
    assert result.vehicles[0].allocated_amps > 0
    assert "force_charge" in result.decision_reason


# ---------------------------------------------------------------------------
# _async_update_data integration test
# ---------------------------------------------------------------------------


def _mock_state(state_value, attributes=None):
    """Create a mock HA state object."""
    s = SimpleNamespace()
    s.state = str(state_value)
    s.attributes = attributes or {}
    return s


def _make_config():
    """Build a minimal config dict for the coordinator."""
    return {
        CONF_GRID_SENSOR: "sensor.grid_power",
        CONF_SOLAR_SENSOR: "sensor.solar_power",
        CONF_BATTERY_POWER_SENSOR: "sensor.battery_power",
        CONF_BATTERY_SOC_SENSOR: "sensor.battery_soc",
        CONF_NORDPOOL_SENSOR: "sensor.nordpool",
        CONF_GRID_FEE_IMPORT: 0.40,
        CONF_GRID_FEE_EXPORT: 0.05,
        CONF_EXPORT_COMPENSATION: 0.10,
        CONF_VAT_RATE: 0.25,
        "power_limit_kw": 11.0,
        CONF_VEHICLES: [
            {
                CONF_VEHICLE_NAME: "Test Car",
                CONF_VEHICLE_PRIORITY: 1,
                CONF_VEHICLE_CHARGER_ENTITY: "sensor.easee_status",
                CONF_VEHICLE_SOC_ENTITY: "sensor.car_soc",
                CONF_VEHICLE_TARGET_SOC: 80,
            },
        ],
    }


@pytest.mark.asyncio
async def test_async_update_data_reads_sensors():
    """_async_update_data should read HA sensor states and run the pipeline."""
    nordpool_attrs = {
        "raw_today": [
            {
                "start": "2026-02-27T02:00:00+00:00",
                "end": "2026-02-27T03:00:00+00:00",
                "value": 0.30,
            },
            {
                "start": "2026-02-27T12:00:00+00:00",
                "end": "2026-02-27T13:00:00+00:00",
                "value": 1.50,
            },
        ],
        "raw_tomorrow": [],
    }

    states = {
        "sensor.grid_power": _mock_state(5000.0),
        "sensor.solar_power": _mock_state(3000.0),
        "sensor.battery_power": _mock_state(0.0),
        "sensor.battery_soc": _mock_state(80),
        "sensor.nordpool": _mock_state(1.20, nordpool_attrs),
        "sensor.easee_status": _mock_state("charging"),
        "sensor.car_soc": _mock_state(50),
    }

    hass = MagicMock()
    hass.states.get = lambda entity_id: states.get(entity_id)

    config = _make_config()
    coord = SmartEVOptimizerCoordinator(hass, config)

    now = _utc(2026, 2, 26, 10, 15)
    with patch("custom_components.smart_ev_optimizer.power_manager._utcnow", return_value=now):
        result = await coord._async_update_data()

    assert result.grid_power_w == 5000.0
    assert result.solar_power_w == 3000.0
    assert result.battery_power_w == 0.0
    assert result.battery_soc == 80
    assert result.current_export_price == 1.20
    assert result.grid_meter_available is True
    assert len(result.vehicles) == 1
    assert result.vehicles[0].name == "Test Car"
    assert result.vehicles[0].current_soc == 50
    assert result.vehicles[0].is_connected is True
    assert result.decision_reason != "initialized"


@pytest.mark.asyncio
async def test_async_update_data_unavailable_grid():
    """When grid sensor is unavailable, grid_meter_available should be False."""
    states = {
        "sensor.grid_power": _mock_state("unavailable"),
        "sensor.solar_power": _mock_state(0.0),
        "sensor.battery_power": _mock_state(0.0),
        "sensor.battery_soc": _mock_state(50),
        "sensor.nordpool": _mock_state(1.00),
        "sensor.easee_status": _mock_state("disconnected"),
        "sensor.car_soc": _mock_state(40),
    }

    hass = MagicMock()
    hass.states.get = lambda entity_id: states.get(entity_id)

    config = _make_config()
    coord = SmartEVOptimizerCoordinator(hass, config)

    result = await coord._async_update_data()

    assert result.grid_meter_available is False
