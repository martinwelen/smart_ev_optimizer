"""Main DataUpdateCoordinator orchestrating the decision pipeline."""

from __future__ import annotations

import contextlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    CONF_BATTERY_POWER_SENSOR,
    CONF_BATTERY_SOC_SENSOR,
    CONF_EXPORT_COMPENSATION,
    CONF_GRID_FEE_EXPORT,
    CONF_GRID_FEE_IMPORT,
    CONF_GRID_REWARDS_ENTITY,
    CONF_GRID_SENSOR,
    CONF_NORDPOOL_SENSOR,
    CONF_SOLAR_SENSOR,
    CONF_VAT_RATE,
    CONF_VEHICLE_CHARGER_ENTITY,
    CONF_VEHICLE_DEPARTURE_ENTITY,
    CONF_VEHICLE_NAME,
    CONF_VEHICLE_PRIORITY,
    CONF_VEHICLE_SOC_ENTITY,
    CONF_VEHICLE_TARGET_SOC,
    CONF_VEHICLES,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TARGET_SOC,
    DEFAULT_VAT_RATE,
    DOMAIN,
)
from .optimizer import evaluate_opportunity_cost, find_cheapest_night_price
from .power_manager import CalendarHourTracker, allocate_power_to_vehicles
from .safety import OBCCooldownTracker, SafetyCheck
from .vehicle import VehicleConfig, VehicleState, build_vehicle_state

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
    any_obc_active = any(ctx.obc_tracker.is_active(v.charger_entity_id) for v in ctx.vehicles)
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
        self._pause_all: bool = False
        self._connected_vehicle: str | None = None
        self._last_commands: dict[str, dict] = {}

        vehicles_cfg = config.get("vehicles", [])
        self._vehicle_names: list[str] = [v.get("name", "") for v in vehicles_cfg]

        self.data = build_initial_data(power_limit_kw=config.get("power_limit_kw", 11.0))

    # ------------------------------------------------------------------
    # Sensor helpers
    # ------------------------------------------------------------------

    def _read_float(self, entity_id: str | None, default: float = 0.0) -> float:
        """Safely read a float from an entity state."""
        if not entity_id:
            return default
        state = self.hass.states.get(entity_id)
        if state is None or state.state in ("unavailable", "unknown", ""):
            return default
        try:
            return float(state.state)
        except (ValueError, TypeError):
            _LOGGER.warning("Cannot convert %s state '%s' to float", entity_id, state.state)
            return default

    def _read_int(self, entity_id: str | None, default: int = 0) -> int:
        """Safely read an int from an entity state."""
        return int(self._read_float(entity_id, float(default)))

    def _parse_nordpool_prices(
        self, entity_id: str | None
    ) -> tuple[float, list[tuple[datetime, float]]]:
        """Extract current price and night prices from a Nordpool sensor.

        Returns (current_price, night_prices) where night_prices is a list of
        (start_dt, price) tuples filtered to hours 21:00-05:00 UTC
        (approximately 22:00-06:00 CET).
        """
        if not entity_id:
            return 0.0, []

        state = self.hass.states.get(entity_id)
        if state is None or state.state in ("unavailable", "unknown", ""):
            return 0.0, []

        try:
            current_price = float(state.state)
        except (ValueError, TypeError):
            _LOGGER.warning("Cannot parse Nordpool current price from %s", entity_id)
            current_price = 0.0

        night_prices: list[tuple[datetime, float]] = []
        attrs = state.attributes if hasattr(state, "attributes") else {}
        for key in ("raw_today", "raw_tomorrow"):
            raw = attrs.get(key) or []
            for entry in raw:
                try:
                    start = entry.get("start") if isinstance(entry, dict) else None
                    value = entry.get("value") if isinstance(entry, dict) else None
                    if start is None or value is None:
                        continue
                    dt = datetime.fromisoformat(start) if isinstance(start, str) else start
                    hour_utc = dt.hour if dt.tzinfo is None else dt.utctimetuple().tm_hour
                    if hour_utc >= 21 or hour_utc < 5:
                        night_prices.append((dt, float(value)))
                except (ValueError, TypeError, AttributeError):
                    continue

        return current_price, night_prices

    # ------------------------------------------------------------------
    # Main update
    # ------------------------------------------------------------------

    async def _async_update_data(self) -> SmartEVOptimizerData:
        """Read HA sensors and run the decision pipeline."""
        cfg = self._config

        # Power sensors
        grid_power = self._read_float(cfg.get(CONF_GRID_SENSOR))
        solar_power = self._read_float(cfg.get(CONF_SOLAR_SENSOR))
        battery_power = self._read_float(cfg.get(CONF_BATTERY_POWER_SENSOR))
        battery_soc = self._read_int(cfg.get(CONF_BATTERY_SOC_SENSOR))

        # Grid meter availability
        grid_entity_id = cfg.get(CONF_GRID_SENSOR)
        grid_state = self.hass.states.get(grid_entity_id) if grid_entity_id else None
        grid_meter_available = grid_state is not None and grid_state.state not in (
            "unavailable",
            "unknown",
            "",
        )
        if not grid_meter_available:
            _LOGGER.warning("Grid meter %s unavailable — entering safe mode", grid_entity_id)

        # Nordpool
        current_price, night_prices = self._parse_nordpool_prices(cfg.get(CONF_NORDPOOL_SENSOR))

        # Grid Rewards
        grid_rewards_active = False
        gr_entity_id = cfg.get(CONF_GRID_REWARDS_ENTITY)
        if gr_entity_id:
            gr_state = self.hass.states.get(gr_entity_id)
            if gr_state is not None:
                grid_rewards_active = gr_state.state.lower() in ("on", "true", "1", "active")

        # Economics from config
        grid_fee_import = float(cfg.get(CONF_GRID_FEE_IMPORT, 0.0))
        grid_fee_export = float(cfg.get(CONF_GRID_FEE_EXPORT, 0.0))
        export_compensation = float(cfg.get(CONF_EXPORT_COMPENSATION, 0.0))
        vat_rate = float(cfg.get(CONF_VAT_RATE, DEFAULT_VAT_RATE))
        power_limit_kw = float(cfg.get("power_limit_kw", 11.0))

        # Build vehicle states
        vehicles: list[VehicleState] = []
        for vcfg in cfg.get(CONF_VEHICLES, []):
            v_config = VehicleConfig(
                vehicle_id=vcfg.get("vehicle_id", vcfg.get(CONF_VEHICLE_NAME, "")),
                name=vcfg.get(CONF_VEHICLE_NAME, ""),
                priority=int(vcfg.get(CONF_VEHICLE_PRIORITY, 1)),
                charger_entity_id=vcfg.get(CONF_VEHICLE_CHARGER_ENTITY, ""),
                soc_entity_id=vcfg.get(CONF_VEHICLE_SOC_ENTITY),
                target_soc=int(vcfg.get(CONF_VEHICLE_TARGET_SOC, DEFAULT_TARGET_SOC)),
                departure_entity_id=vcfg.get(CONF_VEHICLE_DEPARTURE_ENTITY),
            )
            current_soc: int | None = None
            if v_config.soc_entity_id:
                soc_val = self._read_float(v_config.soc_entity_id, -1.0)
                current_soc = int(soc_val) if soc_val >= 0 else None

            charger_state = self.hass.states.get(v_config.charger_entity_id)
            _not_connected = ("unavailable", "unknown", "disconnected", "")
            is_connected = (
                charger_state is not None and charger_state.state.lower() not in _not_connected
            )

            departure_time: datetime | None = None
            if v_config.departure_entity_id:
                dep_state = self.hass.states.get(v_config.departure_entity_id)
                if dep_state and dep_state.state not in ("unavailable", "unknown", ""):
                    with contextlib.suppress(ValueError, TypeError):
                        departure_time = datetime.fromisoformat(dep_state.state)

            vehicles.append(
                build_vehicle_state(v_config, current_soc, is_connected, departure_time)
            )

        # Build context and run pipeline
        ctx = PipelineContext(
            grid_power_w=grid_power,
            solar_power_w=solar_power,
            battery_power_w=battery_power,
            battery_soc=battery_soc,
            grid_rewards_active=grid_rewards_active,
            grid_meter_available=grid_meter_available,
            current_export_price=current_price,
            current_import_price=current_price,
            night_prices=night_prices,
            grid_fee_import=grid_fee_import,
            grid_fee_export=grid_fee_export,
            export_compensation=export_compensation,
            vat_rate=vat_rate,
            power_limit_kw=power_limit_kw,
            vehicles=vehicles,
            obc_tracker=self._obc_tracker,
            calendar_hour_tracker=self._calendar_hour_tracker,
            force_charge_vehicles=self._force_charge_vehicles,
            last_commands=self._last_commands,
        )

        return run_decision_pipeline(ctx)
