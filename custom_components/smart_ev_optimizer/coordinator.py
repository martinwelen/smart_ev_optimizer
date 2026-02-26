"""Main DataUpdateCoordinator orchestrating the decision pipeline."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DEFAULT_SCAN_INTERVAL, DOMAIN
from .optimizer import evaluate_opportunity_cost, find_cheapest_night_price
from .power_manager import CalendarHourTracker, allocate_power_to_vehicles
from .safety import OBCCooldownTracker, SafetyCheck
from .vehicle import VehicleState

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


@dataclass
class SmartEVOptimizerData:
    grid_power_w: float = 0.0
    solar_power_w: float = 0.0
    battery_power_w: float = 0.0
    battery_soc: int = 0

    current_export_price: float = 0.0
    current_import_price: float = 0.0
    cheapest_night_price: float | None = None
    night_prices: list[tuple[datetime, float]] = field(default_factory=list)

    grid_fee_import: float = 0.0
    grid_fee_export: float = 0.0
    export_compensation: float = 0.0
    vat_rate: float = 0.25

    grid_rewards_active: bool = False
    grid_meter_available: bool = True

    calendar_hour_avg_kw: float = 0.0
    available_capacity_kw: float = 0.0
    power_limit_kw: float = 11.0

    vehicles: list[VehicleState] = field(default_factory=list)
    decision_reason: str = "initialized"
    last_commands: dict[str, dict] = field(default_factory=dict)

    opportunity_export_revenue: float = 0.0
    opportunity_night_cost: float = 0.0


def build_initial_data(power_limit_kw: float) -> SmartEVOptimizerData:
    return SmartEVOptimizerData(power_limit_kw=power_limit_kw)


@dataclass
class PipelineContext:
    grid_power_w: float
    solar_power_w: float
    battery_power_w: float
    battery_soc: int
    grid_rewards_active: bool
    grid_meter_available: bool
    current_export_price: float
    current_import_price: float
    night_prices: list[tuple[datetime, float]]
    grid_fee_import: float
    grid_fee_export: float
    export_compensation: float
    vat_rate: float
    power_limit_kw: float
    vehicles: list[VehicleState]
    obc_tracker: OBCCooldownTracker
    calendar_hour_tracker: CalendarHourTracker
    force_charge_vehicles: set[str]
    last_commands: dict[str, dict]


def run_decision_pipeline(ctx: PipelineContext) -> SmartEVOptimizerData:
    """Execute the 4-step decision pipeline."""
    cheapest_night = find_cheapest_night_price(ctx.night_prices)

    # Step 1: Safety
    any_obc_active = any(
        ctx.obc_tracker.is_active(v.charger_entity_id) for v in ctx.vehicles
    )
    safety = SafetyCheck.evaluate(
        grid_rewards_active=ctx.grid_rewards_active,
        battery_power_w=ctx.battery_power_w,
        grid_meter_available=ctx.grid_meter_available,
        obc_cooldown_active=any_obc_active,
    )
    _LOGGER.debug("Pipeline Step 1 (Safety): %s", safety.reason)

    if not safety.allow_charging:
        for v in ctx.vehicles:
            v.allocated_amps = 0
            v.allocated_phases = 1
        return _build_result(ctx, cheapest_night, safety.reason)

    # Step 2: Constraints
    ctx.calendar_hour_tracker.add_sample(ctx.grid_power_w)
    if safety.safe_mode:
        available_kw = (safety.max_amps * 230) / 1000.0
    else:
        available_kw = ctx.calendar_hour_tracker.available_capacity_kw(ctx.power_limit_kw)

    _LOGGER.debug(
        "Pipeline Step 2 (Constraints): avg=%.1fkW, available=%.1fkW",
        ctx.calendar_hour_tracker.average_kw(),
        available_kw,
    )

    # Step 3: User Intent
    force_vehicles = [v for v in ctx.vehicles if v.vehicle_id in ctx.force_charge_vehicles]
    normal_vehicles = [v for v in ctx.vehicles if v.vehicle_id not in ctx.force_charge_vehicles]
    reason_parts: list[str] = []

    if force_vehicles:
        force_alloc = allocate_power_to_vehicles(
            vehicles=force_vehicles, available_capacity_kw=available_kw
        )
        for alloc in force_alloc:
            for v in ctx.vehicles:
                if v.vehicle_id == alloc.vehicle_id:
                    v.allocated_amps = alloc.amps
                    v.allocated_phases = alloc.phases
            available_kw -= (alloc.amps * 230) / 1000.0
        reason_parts.append("force_charge")

    # Step 4: Optimization
    opp_result = evaluate_opportunity_cost(
        current_export_price=ctx.current_export_price,
        cheapest_night_import_price=cheapest_night,
        grid_fee_import=ctx.grid_fee_import,
        grid_fee_export=ctx.grid_fee_export,
        export_compensation=ctx.export_compensation,
        vat_rate=ctx.vat_rate,
    )
    _LOGGER.debug("Pipeline Step 4 (Optimization): %s", opp_result.reason)

    if opp_result.should_charge_now and normal_vehicles:
        remaining_kw = max(0.0, available_kw)
        normal_alloc = allocate_power_to_vehicles(
            vehicles=normal_vehicles, available_capacity_kw=remaining_kw
        )
        for alloc in normal_alloc:
            for v in ctx.vehicles:
                if v.vehicle_id == alloc.vehicle_id:
                    v.allocated_amps = alloc.amps
                    v.allocated_phases = alloc.phases
        reason_parts.append(opp_result.reason)
    elif normal_vehicles:
        for v in normal_vehicles:
            v.allocated_amps = 0
            v.allocated_phases = 1
        reason_parts.append(opp_result.reason)

    reason = " | ".join(reason_parts) if reason_parts else opp_result.reason
    data = _build_result(ctx, cheapest_night, reason)
    data.opportunity_export_revenue = opp_result.export_revenue
    data.opportunity_night_cost = opp_result.night_charge_cost
    return data


def _build_result(
    ctx: PipelineContext, cheapest_night: float | None, reason: str
) -> SmartEVOptimizerData:
    return SmartEVOptimizerData(
        grid_power_w=ctx.grid_power_w,
        solar_power_w=ctx.solar_power_w,
        battery_power_w=ctx.battery_power_w,
        battery_soc=ctx.battery_soc,
        current_export_price=ctx.current_export_price,
        current_import_price=ctx.current_import_price,
        cheapest_night_price=cheapest_night,
        night_prices=ctx.night_prices,
        grid_fee_import=ctx.grid_fee_import,
        grid_fee_export=ctx.grid_fee_export,
        export_compensation=ctx.export_compensation,
        vat_rate=ctx.vat_rate,
        grid_rewards_active=ctx.grid_rewards_active,
        grid_meter_available=ctx.grid_meter_available,
        calendar_hour_avg_kw=ctx.calendar_hour_tracker.average_kw(),
        available_capacity_kw=ctx.calendar_hour_tracker.available_capacity_kw(ctx.power_limit_kw),
        power_limit_kw=ctx.power_limit_kw,
        vehicles=ctx.vehicles,
        decision_reason=reason,
        last_commands=ctx.last_commands,
    )


class SmartEVOptimizerCoordinator(DataUpdateCoordinator[SmartEVOptimizerData]):
    def __init__(self, hass: HomeAssistant, config: dict[str, Any]) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self._config = config
        self._obc_tracker = OBCCooldownTracker()
        self._calendar_hour_tracker = CalendarHourTracker()
        self._force_charge_vehicles: set[str] = set()
        self._last_commands: dict[str, dict] = {}
        self.data = build_initial_data(power_limit_kw=config.get("power_limit_kw", 11.0))

    async def _async_update_data(self) -> SmartEVOptimizerData:
        return self.data
