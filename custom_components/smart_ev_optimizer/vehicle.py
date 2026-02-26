"""Vehicle data model and state management."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .const import SOC_SOURCE_API, SOC_SOURCE_MANUAL, SOC_SOURCE_NONE


def classify_soc_source(entity_id: str | None) -> str:
    """Classify the SoC source type based on entity_id pattern."""
    if not entity_id:
        return SOC_SOURCE_NONE
    if entity_id.startswith("sensor."):
        return SOC_SOURCE_API
    if entity_id.startswith("input_number."):
        return SOC_SOURCE_MANUAL
    return SOC_SOURCE_NONE


@dataclass(frozen=True)
class VehicleConfig:
    """Immutable vehicle configuration from config entry."""

    vehicle_id: str
    name: str
    priority: int
    charger_entity_id: str
    soc_entity_id: str | None
    target_soc: int
    departure_entity_id: str | None


@dataclass
class VehicleState:
    """Mutable vehicle state for current decision cycle."""

    vehicle_id: str
    name: str
    priority: int
    target_soc: int
    current_soc: int | None
    departure_time: datetime | None
    is_connected: bool
    soc_source_type: str
    soc_entity_id: str | None
    charger_entity_id: str
    allocated_amps: int = 0
    allocated_phases: int = 1

    @property
    def needs_charge(self) -> bool:
        """Determine if the vehicle needs charging."""
        if not self.is_connected:
            return False
        if self.current_soc is None:
            return True
        return self.current_soc < self.target_soc


def build_vehicle_state(
    config: VehicleConfig,
    current_soc: int | None,
    is_connected: bool,
    departure_time: datetime | None,
) -> VehicleState:
    """Build a VehicleState from config and current readings."""
    return VehicleState(
        vehicle_id=config.vehicle_id,
        name=config.name,
        priority=config.priority,
        target_soc=config.target_soc,
        current_soc=current_soc,
        departure_time=departure_time,
        is_connected=is_connected,
        soc_source_type=classify_soc_source(config.soc_entity_id),
        soc_entity_id=config.soc_entity_id,
        charger_entity_id=config.charger_entity_id,
    )
