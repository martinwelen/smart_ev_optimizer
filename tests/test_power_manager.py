"""Tests for power manager module."""

from datetime import UTC, datetime
from unittest.mock import patch

from custom_components.smart_ev_optimizer.const import SOC_SOURCE_API
from custom_components.smart_ev_optimizer.power_manager import (
    CalendarHourTracker,
    allocate_power_to_vehicles,
)
from custom_components.smart_ev_optimizer.vehicle import VehicleState


def _make_vehicle(vehicle_id, priority, is_connected=True, current_soc=50, target_soc=80):
    return VehicleState(
        vehicle_id=vehicle_id,
        name=f"Car {vehicle_id}",
        priority=priority,
        target_soc=target_soc,
        current_soc=current_soc,
        departure_time=None,
        is_connected=is_connected,
        soc_source_type=SOC_SOURCE_API,
        soc_entity_id=f"sensor.{vehicle_id}_soc",
        charger_entity_id=f"sensor.{vehicle_id}_charger",
    )


def _utc(year, month, day, hour, minute, second=0):
    return datetime(year, month, day, hour, minute, second, tzinfo=UTC)


_UTCNOW = "custom_components.smart_ev_optimizer.power_manager._utcnow"


class TestCalendarHourTracker:
    def test_empty_tracker(self):
        tracker = CalendarHourTracker()
        assert tracker.average_kw() == 0.0

    def test_single_sample(self):
        now = _utc(2026, 2, 26, 10, 15)
        tracker = CalendarHourTracker()
        with patch(_UTCNOW, return_value=now):
            tracker.add_sample(5000.0)
            assert tracker.average_kw() == 5.0

    def test_multiple_samples_same_hour(self):
        tracker = CalendarHourTracker()
        t1 = _utc(2026, 2, 26, 10, 10)
        t2 = _utc(2026, 2, 26, 10, 20)
        t3 = _utc(2026, 2, 26, 10, 30)
        with patch(_UTCNOW, return_value=t1):
            tracker.add_sample(4000.0)
        with patch(_UTCNOW, return_value=t2):
            tracker.add_sample(6000.0)
        with patch(_UTCNOW, return_value=t3):
            tracker.add_sample(5000.0)
            assert tracker.average_kw() == 5.0

    def test_reset_at_hour_boundary(self):
        tracker = CalendarHourTracker()
        t1 = _utc(2026, 2, 26, 10, 55)
        with patch(_UTCNOW, return_value=t1):
            tracker.add_sample(10000.0)
            assert tracker.average_kw() == 10.0
        t2 = _utc(2026, 2, 26, 11, 0)
        with patch(_UTCNOW, return_value=t2):
            tracker.add_sample(2000.0)
            assert tracker.average_kw() == 2.0

    def test_available_capacity(self):
        tracker = CalendarHourTracker()
        now = _utc(2026, 2, 26, 10, 15)
        with patch(_UTCNOW, return_value=now):
            tracker.add_sample(7000.0)
            assert tracker.available_capacity_kw(power_limit_kw=11.0) == 4.0

    def test_available_capacity_over_limit(self):
        tracker = CalendarHourTracker()
        now = _utc(2026, 2, 26, 10, 15)
        with patch(_UTCNOW, return_value=now):
            tracker.add_sample(12000.0)
            assert tracker.available_capacity_kw(power_limit_kw=11.0) == 0.0

    def test_current_hour_property(self):
        tracker = CalendarHourTracker()
        now = _utc(2026, 2, 26, 14, 30)
        with patch(_UTCNOW, return_value=now):
            tracker.add_sample(1000.0)
            assert tracker.current_hour == 14

    def test_sample_count(self):
        tracker = CalendarHourTracker()
        now = _utc(2026, 2, 26, 10, 15)
        with patch(_UTCNOW, return_value=now):
            tracker.add_sample(1000.0)
            tracker.add_sample(2000.0)
            tracker.add_sample(3000.0)
            assert tracker.sample_count == 3


class TestPowerAllocation:
    def test_allocate_single_vehicle(self):
        vehicles = [_make_vehicle("car_1", priority=1)]
        result = allocate_power_to_vehicles(
            vehicles=vehicles, available_capacity_kw=7.36, voltage=230
        )
        assert len(result) == 1
        assert result[0].amps > 0

    def test_allocate_priority_order(self):
        v1 = _make_vehicle("car_1", priority=1)
        v2 = _make_vehicle("car_2", priority=2)
        result = allocate_power_to_vehicles(
            vehicles=[v2, v1], available_capacity_kw=3.68, voltage=230
        )
        car_1_alloc = next(r for r in result if r.vehicle_id == "car_1")
        car_2_alloc = next(r for r in result if r.vehicle_id == "car_2")
        assert car_1_alloc.amps > 0
        assert car_2_alloc.amps == 0

    def test_allocate_disconnected_gets_nothing(self):
        v1 = _make_vehicle("car_1", priority=1, is_connected=False)
        result = allocate_power_to_vehicles(vehicles=[v1], available_capacity_kw=11.0, voltage=230)
        assert result[0].amps == 0

    def test_allocate_at_target_soc_gets_nothing(self):
        v1 = _make_vehicle("car_1", priority=1, current_soc=90, target_soc=80)
        result = allocate_power_to_vehicles(vehicles=[v1], available_capacity_kw=11.0, voltage=230)
        assert result[0].amps == 0

    def test_allocate_respects_min_amps(self):
        vehicles = [_make_vehicle("car_1", priority=1)]
        result = allocate_power_to_vehicles(
            vehicles=vehicles, available_capacity_kw=1.0, voltage=230
        )
        assert result[0].amps == 0
