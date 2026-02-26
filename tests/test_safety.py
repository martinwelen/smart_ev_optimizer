"""Tests for safety module."""

import time

from custom_components.smart_ev_optimizer.const import OBC_COOLDOWN_SECONDS
from custom_components.smart_ev_optimizer.safety import (
    OBCCooldownTracker,
    SafetyCheck,
)


def test_safety_all_clear():
    result = SafetyCheck.evaluate(
        grid_rewards_active=False,
        battery_power_w=500.0,
        grid_meter_available=True,
        obc_cooldown_active=False,
    )
    assert result.allow_charging is True
    assert result.reason == "all_clear"


def test_safety_grid_rewards_exporting():
    result = SafetyCheck.evaluate(
        grid_rewards_active=True,
        battery_power_w=-500.0,
        grid_meter_available=True,
        obc_cooldown_active=False,
    )
    assert result.allow_charging is False
    assert "grid_rewards" in result.reason


def test_safety_grid_rewards_not_exporting():
    result = SafetyCheck.evaluate(
        grid_rewards_active=True,
        battery_power_w=500.0,
        grid_meter_available=True,
        obc_cooldown_active=False,
    )
    assert result.allow_charging is True


def test_safety_grid_meter_unavailable():
    result = SafetyCheck.evaluate(
        grid_rewards_active=False,
        battery_power_w=0.0,
        grid_meter_available=False,
        obc_cooldown_active=False,
    )
    assert result.allow_charging is True
    assert result.safe_mode is True
    assert result.max_amps == 6


def test_safety_obc_cooldown():
    result = SafetyCheck.evaluate(
        grid_rewards_active=False,
        battery_power_w=0.0,
        grid_meter_available=True,
        obc_cooldown_active=True,
    )
    assert result.allow_charging is False
    assert "obc_cooldown" in result.reason


def test_obc_tracker_start_and_check():
    tracker = OBCCooldownTracker()
    assert tracker.is_active("charger_1") is False
    tracker.start_cooldown("charger_1")
    assert tracker.is_active("charger_1") is True


def test_obc_tracker_expired():
    tracker = OBCCooldownTracker()
    tracker._cooldowns["charger_1"] = time.monotonic() - OBC_COOLDOWN_SECONDS - 1
    assert tracker.is_active("charger_1") is False


def test_obc_tracker_remaining():
    tracker = OBCCooldownTracker()
    tracker.start_cooldown("charger_1")
    remaining = tracker.remaining_seconds("charger_1")
    assert 0 < remaining <= OBC_COOLDOWN_SECONDS
