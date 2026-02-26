"""Safety checks for EV charging decisions."""

from __future__ import annotations

import time
from dataclasses import dataclass

from .const import OBC_COOLDOWN_SECONDS

SAFE_MODE_MAX_AMPS = 6


@dataclass(frozen=True)
class SafetyResult:
    """Result of a safety evaluation."""

    allow_charging: bool
    reason: str
    safe_mode: bool = False
    max_amps: int | None = None


class SafetyCheck:
    """Evaluates safety conditions for EV charging."""

    @staticmethod
    def evaluate(
        *,
        grid_rewards_active: bool,
        battery_power_w: float,
        grid_meter_available: bool,
        obc_cooldown_active: bool,
    ) -> SafetyResult:
        """Run safety checks and return a result.

        Priority order:
        1. Grid Rewards active + battery exporting -> block charging
        2. OBC cooldown active -> block charging
        3. Grid meter unavailable -> safe mode (allow at max 6A)
        4. All clear -> allow charging
        """
        if grid_rewards_active and battery_power_w < 0:
            return SafetyResult(
                allow_charging=False,
                reason="grid_rewards_active_battery_exporting",
            )

        if obc_cooldown_active:
            return SafetyResult(
                allow_charging=False,
                reason="obc_cooldown_active",
            )

        if not grid_meter_available:
            return SafetyResult(
                allow_charging=True,
                reason="grid_meter_unavailable_safe_mode",
                safe_mode=True,
                max_amps=SAFE_MODE_MAX_AMPS,
            )

        return SafetyResult(allow_charging=True, reason="all_clear")


class OBCCooldownTracker:
    """Tracks on-board charger cooldown periods after phase switches."""

    def __init__(self) -> None:
        self._cooldowns: dict[str, float] = {}

    def start_cooldown(self, charger_id: str) -> None:
        """Start a cooldown timer for a charger."""
        self._cooldowns[charger_id] = time.monotonic()

    def is_active(self, charger_id: str) -> bool:
        """Check if cooldown is still active for a charger."""
        start = self._cooldowns.get(charger_id)
        if start is None:
            return False
        return (time.monotonic() - start) < OBC_COOLDOWN_SECONDS

    def remaining_seconds(self, charger_id: str) -> float:
        """Return seconds remaining in cooldown, or 0.0 if expired."""
        start = self._cooldowns.get(charger_id)
        if start is None:
            return 0.0
        return max(0.0, OBC_COOLDOWN_SECONDS - (time.monotonic() - start))
