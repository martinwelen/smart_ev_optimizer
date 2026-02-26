"""Abstract charger control layer with Easee implementation.

The EaseeChargerHandler maintains "master control" over the charger,
overriding external cloud schedules (e.g., Tibber Smart Charging) to
protect the main fuse and maximize economic optimization.
"""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

_BLOCKING_STATES = {"awaiting_smart_charging", "standby"}
_WAKEUP_STATES = {"awaiting_smart_charging", "standby"}
_VERIFY_MAX_RETRIES = 3
_VERIFY_RETRY_DELAY_S = 2.0


class EaseeChargerStatus:
    """Status helper for Easee charger states."""

    @staticmethod
    def needs_wakeup(status: str) -> bool:
        """Return True if charger is in a cloud-controlled state requiring wake."""
        return status.lower() in _WAKEUP_STATES

    @staticmethod
    def is_blocking(status: str) -> bool:
        """Return True if charger is in a state that blocks local control."""
        return status.lower() in _BLOCKING_STATES


@dataclass(frozen=True)
class ChargerCommand:
    """Immutable command representing a desired charger state.

    Used for deduplication to avoid spamming the Easee Cloud API
    with identical commands.
    """

    amps: int
    phases: int
    paused: bool

    def differs_from(self, other: ChargerCommand | None) -> bool:
        """Return True if this command differs from another (or if other is None)."""
        if other is None:
            return True
        return self != other


class ChargerActionHandler(ABC):
    """Abstract base class for charger control implementations."""

    @abstractmethod
    async def set_charging_current(self, amps: int) -> bool:
        """Set the dynamic charging current limit in amps."""
        ...

    @abstractmethod
    async def set_phases(self, phases: int) -> bool:
        """Set the number of active phases (1 or 3)."""
        ...

    @abstractmethod
    async def pause_charging(self) -> bool:
        """Pause the charger."""
        ...

    @abstractmethod
    async def resume_charging(self) -> bool:
        """Resume charging from a paused or cloud-controlled state."""
        ...

    @abstractmethod
    async def verify_state(
        self, expected: dict[str, Any], timeout_s: float = 5.0
    ) -> bool:
        """Verify the charger reached the expected state."""
        ...

    @abstractmethod
    def get_current_status(self) -> str | None:
        """Return the current charger status string, or None if unknown."""
        ...


class EaseeChargerHandler(ChargerActionHandler):
    """Control Easee chargers via HA services with master control.

    Requires the Easee HACS integration (nordicopen/easee_hacs).
    """

    def __init__(
        self, hass: HomeAssistant, charger_id: str, circuit_id: str
    ) -> None:
        self._hass = hass
        self._charger_id = charger_id
        self._circuit_id = circuit_id

    def get_current_status(self) -> str | None:
        """Read charger status from HA state machine."""
        state = self._hass.states.get(
            f"sensor.easee_{self._charger_id}_status"
        )
        return state.state if state else None

    async def _ensure_ready(self) -> bool:
        """Wake charger from cloud-controlled states before sending commands.

        If the charger is in 'awaiting_smart_charging' or 'standby',
        an external service (e.g., Tibber) has taken control. We send
        a resume command first to reclaim master control.
        """
        status = self.get_current_status()
        if status and EaseeChargerStatus.needs_wakeup(status):
            _LOGGER.info(
                "Charger %s in '%s', sending resume to take control",
                self._charger_id,
                status,
            )
            await self._hass.services.async_call(
                "easee",
                "action_command",
                {
                    "charger_id": self._charger_id,
                    "action_command": "resume",
                },
                blocking=True,
            )
            await asyncio.sleep(1.0)
        return True

    async def set_charging_current(self, amps: int) -> bool:
        """Set dynamic current limit on the circuit."""
        try:
            await self._ensure_ready()
            await self._hass.services.async_call(
                "easee",
                "set_circuit_dynamic_limit",
                {
                    "circuit_id": self._circuit_id,
                    "currentP1": amps,
                    "currentP2": amps,
                    "currentP3": amps,
                },
                blocking=True,
            )
            _LOGGER.info(
                "Set Easee circuit %s dynamic limit to %dA",
                self._circuit_id,
                amps,
            )
            return True
        except Exception:
            _LOGGER.exception(
                "Failed to set charging current on %s", self._circuit_id
            )
            return False

    async def set_phases(self, phases: int) -> bool:
        """Set active phases via static circuit limit."""
        try:
            await self._ensure_ready()
            await self._hass.services.async_call(
                "easee",
                "set_charger_circuit_static_limit",
                {
                    "charger_id": self._charger_id,
                    "currentP1": 32 if phases >= 1 else 0,
                    "currentP2": 32 if phases >= 2 else 0,
                    "currentP3": 32 if phases >= 3 else 0,
                },
                blocking=True,
            )
            _LOGGER.info(
                "Set Easee charger %s to %d phase(s)",
                self._charger_id,
                phases,
            )
            return True
        except Exception:
            _LOGGER.exception(
                "Failed to set phases on %s", self._charger_id
            )
            return False

    async def pause_charging(self) -> bool:
        """Pause the charger via action command."""
        try:
            await self._hass.services.async_call(
                "easee",
                "action_command",
                {
                    "charger_id": self._charger_id,
                    "action_command": "pause",
                },
                blocking=True,
            )
            _LOGGER.info("Paused charging on %s", self._charger_id)
            return True
        except Exception:
            _LOGGER.exception(
                "Failed to pause charging on %s", self._charger_id
            )
            return False

    async def resume_charging(self) -> bool:
        """Resume the charger via action command."""
        try:
            await self._hass.services.async_call(
                "easee",
                "action_command",
                {
                    "charger_id": self._charger_id,
                    "action_command": "resume",
                },
                blocking=True,
            )
            _LOGGER.info("Resumed charging on %s", self._charger_id)
            return True
        except Exception:
            _LOGGER.exception(
                "Failed to resume charging on %s", self._charger_id
            )
            return False

    async def verify_state(
        self, expected: dict[str, Any], timeout_s: float = 5.0
    ) -> bool:
        """Verify charger reached expected state with retry logic.

        After max retries, logs a warning about possible external conflict
        (e.g., Easee cloud schedule overriding local control).
        """
        for attempt in range(_VERIFY_MAX_RETRIES):
            await asyncio.sleep(
                timeout_s if attempt == 0 else _VERIFY_RETRY_DELAY_S
            )
            state = self._hass.states.get(
                f"sensor.easee_{self._charger_id}_status"
            )
            if state is None:
                _LOGGER.warning(
                    "Could not read state for charger %s", self._charger_id
                )
                return False

            if EaseeChargerStatus.is_blocking(state.state):
                _LOGGER.debug(
                    "Charger %s still blocking '%s' (attempt %d/%d)",
                    self._charger_id,
                    state.state,
                    attempt + 1,
                    _VERIFY_MAX_RETRIES,
                )
                continue

            all_match = True
            for key, value in expected.items():
                actual = state.attributes.get(
                    key, state.state if key == "status" else None
                )
                if actual != value:
                    all_match = False
                    break
            if all_match:
                return True

        _LOGGER.warning(
            "Charger %s did not reach expected state after %d attempts. "
            "An external service may be overriding charger settings. "
            "Check the Easee app for conflicting schedules.",
            self._charger_id,
            _VERIFY_MAX_RETRIES,
        )
        return False
