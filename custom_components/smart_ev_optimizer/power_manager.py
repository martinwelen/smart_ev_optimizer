"""Power management: calendar hour tracking and capacity allocation.

Swedish grid operators bill power tariffs (effekttaxa) based on average
consumption per calendar hour (xx:00:00 to xx:59:59). The CalendarHourTracker
matches this billing model by resetting all samples at each hour boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from .vehicle import VehicleState

MIN_CHARGING_AMPS = 6
NUM_PHASES = 3
VOLTAGE = 230


def _utcnow() -> datetime:
    """Get current UTC time. Extracted for testability."""
    return datetime.now(UTC)


@dataclass(frozen=True)
class PowerAllocation:
    """Result of power allocation for a single vehicle."""

    vehicle_id: str
    amps: int
    phases: int


class CalendarHourTracker:
    """Track average power consumption for the current calendar hour.

    Swedish grid operators calculate power tariffs based on average
    consumption per calendar hour. This tracker collects power samples
    within the current clock hour and resets when a new hour starts.
    """

    def __init__(self) -> None:
        self._samples: list[float] = []
        self._current_hour: int | None = None

    def add_sample(self, watts: float) -> None:
        """Add a power measurement sample in watts.

        If the current UTC hour has changed since the last sample,
        all previous samples are discarded before recording the new one.
        """
        now = _utcnow()
        current_hour = now.hour
        if self._current_hour is not None and current_hour != self._current_hour:
            self._samples.clear()
        self._current_hour = current_hour
        self._samples.append(watts)

    def average_kw(self) -> float:
        """Return the average power in kilowatts for the current hour."""
        if not self._samples:
            return 0.0
        return (sum(self._samples) / len(self._samples)) / 1000.0

    def available_capacity_kw(self, power_limit_kw: float) -> float:
        """Return remaining capacity in kW before hitting the power limit."""
        return max(0.0, power_limit_kw - self.average_kw())

    @property
    def current_hour(self) -> int | None:
        """Return the hour (0-23) of the most recent sample, or None."""
        return self._current_hour

    @property
    def sample_count(self) -> int:
        """Return the number of samples collected in the current hour."""
        return len(self._samples)


def allocate_power_to_vehicles(
    *,
    vehicles: list[VehicleState],
    available_capacity_kw: float,
    fuse_size: int = 20,
) -> list[PowerAllocation]:
    """Allocate available power capacity across vehicles by priority.

    Uses three-phase charging: I_per_phase = W / (230 * 3).
    The fuse_size parameter is an absolute cap per phase.

    Vehicles are sorted by priority (lower number = higher priority).
    Each vehicle that needs charging gets allocated as many amps as
    possible from the remaining capacity, subject to minimum amps
    and the fuse size limit.

    Args:
        vehicles: List of vehicle states to consider.
        available_capacity_kw: Total available power in kilowatts.
        fuse_size: Maximum amps per phase (fuse rating).

    Returns:
        A PowerAllocation for each vehicle, in the same order as sorted input.
    """
    sorted_vehicles = sorted(vehicles, key=lambda v: v.priority)
    remaining_kw = available_capacity_kw
    allocations: list[PowerAllocation] = []

    for vehicle in sorted_vehicles:
        if not vehicle.needs_charge or not vehicle.is_connected:
            allocations.append(PowerAllocation(vehicle.vehicle_id, amps=0, phases=NUM_PHASES))
            continue

        # Three-phase: I = W / (V * 3)
        max_amps_from_capacity = int(remaining_kw * 1000 / (VOLTAGE * NUM_PHASES))

        if max_amps_from_capacity < MIN_CHARGING_AMPS:
            allocations.append(PowerAllocation(vehicle.vehicle_id, amps=0, phases=NUM_PHASES))
            continue

        amps = min(max_amps_from_capacity, fuse_size)
        allocated_kw = (amps * VOLTAGE * NUM_PHASES) / 1000.0
        remaining_kw -= allocated_kw
        allocations.append(PowerAllocation(vehicle.vehicle_id, amps=amps, phases=NUM_PHASES))

    return allocations
