"""Opportunity cost engine: export solar vs charge now vs charge at night."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class OpportunityCostResult:
    should_charge_now: bool
    export_revenue: float
    night_charge_cost: float
    reason: str


def find_cheapest_night_price(prices: list[tuple[datetime, float]]) -> float | None:
    if not prices:
        return None
    return min(p for _, p in prices)


def evaluate_opportunity_cost(
    *,
    current_export_price: float,
    cheapest_night_import_price: float | None,
    grid_fee_import: float,
    grid_fee_export: float,
    export_compensation: float,
    vat_rate: float,
) -> OpportunityCostResult:
    export_revenue = current_export_price + export_compensation - grid_fee_export

    if cheapest_night_import_price is None:
        return OpportunityCostResult(
            should_charge_now=True,
            export_revenue=export_revenue,
            night_charge_cost=0.0,
            reason="no_night_prices_available",
        )

    night_charge_cost = (cheapest_night_import_price + grid_fee_import) * (
        1.0 + vat_rate
    )

    if export_revenue > night_charge_cost:
        return OpportunityCostResult(
            should_charge_now=False,
            export_revenue=export_revenue,
            night_charge_cost=night_charge_cost,
            reason="export_more_profitable",
        )

    return OpportunityCostResult(
        should_charge_now=True,
        export_revenue=export_revenue,
        night_charge_cost=night_charge_cost,
        reason="charging_now_cheaper",
    )
