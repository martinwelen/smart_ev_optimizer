"""Tests for switch platform."""

from unittest.mock import AsyncMock, MagicMock

from custom_components.smart_ev_optimizer.coordinator import SmartEVOptimizerData
from custom_components.smart_ev_optimizer.switch import (
    SEOForceChargeSwitchEntity,
    SEOPauseAllSwitchEntity,
)


def _make_coordinator_mock(data=None):
    coordinator = MagicMock()
    if data is None:
        data = SmartEVOptimizerData()
    coordinator.data = data
    coordinator.config_entry = MagicMock()
    coordinator.config_entry.entry_id = "test_entry"
    coordinator._force_charge_vehicles = set()
    coordinator._pause_all = False
    coordinator.async_request_refresh = AsyncMock()
    return coordinator


def test_force_charge_switch_off_initially():
    coord = _make_coordinator_mock()
    switch = SEOForceChargeSwitchEntity(coord, "car_1", "Family Car")
    assert switch.is_on is False


def test_force_charge_switch_on():
    coord = _make_coordinator_mock()
    coord._force_charge_vehicles = {"car_1"}
    switch = SEOForceChargeSwitchEntity(coord, "car_1", "Family Car")
    assert switch.is_on is True


async def test_force_charge_turn_on():
    coord = _make_coordinator_mock()
    switch = SEOForceChargeSwitchEntity(coord, "car_1", "Family Car")
    await switch.async_turn_on()
    assert "car_1" in coord._force_charge_vehicles
    coord.async_request_refresh.assert_called_once()


async def test_force_charge_turn_off():
    coord = _make_coordinator_mock()
    coord._force_charge_vehicles = {"car_1"}
    switch = SEOForceChargeSwitchEntity(coord, "car_1", "Family Car")
    await switch.async_turn_off()
    assert "car_1" not in coord._force_charge_vehicles
    coord.async_request_refresh.assert_called_once()


def test_force_charge_unique_id():
    coord = _make_coordinator_mock()
    switch = SEOForceChargeSwitchEntity(coord, "car_1", "Family Car")
    assert switch._attr_unique_id == "test_entry_force_charge_car_1"


def test_pause_all_off_initially():
    coord = _make_coordinator_mock()
    switch = SEOPauseAllSwitchEntity(coord)
    assert switch.is_on is False


def test_pause_all_on():
    coord = _make_coordinator_mock()
    coord._pause_all = True
    switch = SEOPauseAllSwitchEntity(coord)
    assert switch.is_on is True


async def test_pause_all_turn_on():
    coord = _make_coordinator_mock()
    switch = SEOPauseAllSwitchEntity(coord)
    await switch.async_turn_on()
    assert coord._pause_all is True
    coord.async_request_refresh.assert_called_once()


async def test_pause_all_turn_off():
    coord = _make_coordinator_mock()
    coord._pause_all = True
    switch = SEOPauseAllSwitchEntity(coord)
    await switch.async_turn_off()
    assert coord._pause_all is False
    coord.async_request_refresh.assert_called_once()


def test_pause_all_unique_id():
    coord = _make_coordinator_mock()
    switch = SEOPauseAllSwitchEntity(coord)
    assert switch._attr_unique_id == "test_entry_pause_all"
