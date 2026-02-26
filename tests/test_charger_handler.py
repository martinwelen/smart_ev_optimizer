"""Tests for charger action handler."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.smart_ev_optimizer.charger_handler import (
    ChargerCommand,
    EaseeChargerHandler,
    EaseeChargerStatus,
)


def test_charger_command_equality():
    cmd1 = ChargerCommand(amps=16, phases=1, paused=False)
    cmd2 = ChargerCommand(amps=16, phases=1, paused=False)
    assert cmd1 == cmd2


def test_charger_command_inequality():
    cmd1 = ChargerCommand(amps=16, phases=1, paused=False)
    cmd2 = ChargerCommand(amps=10, phases=1, paused=False)
    assert cmd1 != cmd2


def test_command_dedup_same():
    cmd = ChargerCommand(amps=16, phases=1, paused=False)
    assert cmd.differs_from(cmd) is False


def test_command_dedup_different():
    cmd1 = ChargerCommand(amps=16, phases=1, paused=False)
    cmd2 = ChargerCommand(amps=10, phases=3, paused=False)
    assert cmd1.differs_from(cmd2) is True


def test_command_dedup_none():
    cmd = ChargerCommand(amps=16, phases=1, paused=False)
    assert cmd.differs_from(None) is True


def test_charger_status_needs_wakeup():
    assert EaseeChargerStatus.needs_wakeup("awaiting_smart_charging") is True
    assert EaseeChargerStatus.needs_wakeup("standby") is True
    assert EaseeChargerStatus.needs_wakeup("charging") is False
    assert EaseeChargerStatus.needs_wakeup("ready_to_charge") is False


def test_charger_status_is_blocking():
    assert EaseeChargerStatus.is_blocking("awaiting_smart_charging") is True
    assert EaseeChargerStatus.is_blocking("standby") is True
    assert EaseeChargerStatus.is_blocking("charging") is False


def _make_hass_mock(charger_status="charging"):
    hass = MagicMock()
    hass.services = MagicMock()
    hass.services.async_call = AsyncMock()
    state_obj = MagicMock()
    state_obj.state = charger_status
    state_obj.attributes = {"status": charger_status}
    hass.states.get = MagicMock(return_value=state_obj)
    return hass


@pytest.mark.asyncio
async def test_easee_set_current_normal():
    hass = _make_hass_mock("charging")
    handler = EaseeChargerHandler(hass=hass, charger_id="EH123456", circuit_id="EC789")
    result = await handler.set_charging_current(16)
    assert result is True


@pytest.mark.asyncio
async def test_easee_set_current_wakes_from_smart_charging():
    hass = _make_hass_mock("awaiting_smart_charging")
    handler = EaseeChargerHandler(hass=hass, charger_id="EH123456", circuit_id="EC789")
    result = await handler.set_charging_current(16)
    assert result is True
    calls = hass.services.async_call.call_args_list
    assert len(calls) >= 2
    # First call should be resume
    first_call = calls[0]
    assert first_call[0][0] == "easee"
    assert first_call[0][1] == "action_command"


@pytest.mark.asyncio
async def test_easee_pause():
    hass = _make_hass_mock("charging")
    handler = EaseeChargerHandler(hass=hass, charger_id="EH123456", circuit_id="EC789")
    result = await handler.pause_charging()
    assert result is True


@pytest.mark.asyncio
async def test_easee_resume():
    hass = _make_hass_mock("standby")
    handler = EaseeChargerHandler(hass=hass, charger_id="EH123456", circuit_id="EC789")
    result = await handler.resume_charging()
    assert result is True


@pytest.mark.asyncio
async def test_verify_state_confirms_no_blocking():
    hass = _make_hass_mock("charging")
    handler = EaseeChargerHandler(hass=hass, charger_id="EH123456", circuit_id="EC789")
    result = await handler.verify_state({"status": "charging"}, timeout_s=0.01)
    assert result is True


@pytest.mark.asyncio
async def test_verify_state_detects_still_blocked():
    hass = _make_hass_mock("awaiting_smart_charging")
    handler = EaseeChargerHandler(hass=hass, charger_id="EH123456", circuit_id="EC789")
    result = await handler.verify_state({"status": "charging"}, timeout_s=0.01)
    assert result is False
