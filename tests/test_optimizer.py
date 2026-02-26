"""Tests for opportunity cost optimizer."""

from datetime import UTC, datetime

from custom_components.smart_ev_optimizer.optimizer import (
    evaluate_opportunity_cost,
    find_cheapest_night_price,
)


def test_find_cheapest_night_empty():
    assert find_cheapest_night_price([]) is None


def test_find_cheapest_night_single():
    prices = [(datetime(2026, 2, 26, 2, 0, tzinfo=UTC), 0.50)]
    assert find_cheapest_night_price(prices) == 0.50


def test_find_cheapest_night_multiple():
    prices = [
        (datetime(2026, 2, 26, 22, 0, tzinfo=UTC), 0.80),
        (datetime(2026, 2, 26, 2, 0, tzinfo=UTC), 0.30),
        (datetime(2026, 2, 26, 4, 0, tzinfo=UTC), 0.50),
    ]
    assert find_cheapest_night_price(prices) == 0.30


def test_opportunity_export_more_profitable():
    result = evaluate_opportunity_cost(
        current_export_price=1.50,
        cheapest_night_import_price=0.50,
        grid_fee_import=0.40,
        grid_fee_export=0.05,
        export_compensation=0.10,
        vat_rate=0.25,
    )
    assert result.should_charge_now is False
    assert result.export_revenue > result.night_charge_cost


def test_opportunity_charging_now_cheaper():
    result = evaluate_opportunity_cost(
        current_export_price=0.10,
        cheapest_night_import_price=1.50,
        grid_fee_import=0.40,
        grid_fee_export=0.05,
        export_compensation=0.10,
        vat_rate=0.25,
    )
    assert result.should_charge_now is True


def test_opportunity_no_night_price():
    result = evaluate_opportunity_cost(
        current_export_price=1.50,
        cheapest_night_import_price=None,
        grid_fee_import=0.40,
        grid_fee_export=0.05,
        export_compensation=0.10,
        vat_rate=0.25,
    )
    assert result.should_charge_now is True


def test_opportunity_cost_calculation():
    result = evaluate_opportunity_cost(
        current_export_price=1.00,
        cheapest_night_import_price=0.50,
        grid_fee_import=0.40,
        grid_fee_export=0.05,
        export_compensation=0.10,
        vat_rate=0.25,
    )
    # Export: 1.00 + 0.10 - 0.05 = 1.05
    assert abs(result.export_revenue - 1.05) < 0.001
    # Night: (0.50 + 0.40) * 1.25 = 1.125
    assert abs(result.night_charge_cost - 1.125) < 0.001
