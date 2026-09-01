"""Depreciation calculation engine.

Supports straight-line and declining-balance methods, and can generate
a full year-by-year schedule for an asset or compute the next single
period's entry (used when posting depreciation).
"""
from dataclasses import dataclass
from datetime import date


@dataclass
class DepreciationPeriod:
    period_date: date
    depreciation_amount: float
    accumulated_depreciation: float
    book_value: float


def straight_line_schedule(
    purchase_cost: float,
    salvage_value: float,
    useful_life_years: float,
    purchase_date: date,
) -> list[DepreciationPeriod]:
    """Equal depreciation each year until salvage value is reached."""
    depreciable_base = max(purchase_cost - salvage_value, 0)
    years = max(int(round(useful_life_years)), 1)
    annual_amount = depreciable_base / years

    schedule = []
    accumulated = 0.0
    for year in range(1, years + 1):
        accumulated = min(accumulated + annual_amount, depreciable_base)
        book_value = purchase_cost - accumulated
        period_date = date(purchase_date.year + year, purchase_date.month, purchase_date.day) \
            if _safe_date(purchase_date, year) else _year_end(purchase_date.year + year)
        schedule.append(DepreciationPeriod(
            period_date=period_date,
            depreciation_amount=round(annual_amount if accumulated < depreciable_base or year < years
                                       else depreciable_base - (accumulated - annual_amount), 2),
            accumulated_depreciation=round(accumulated, 2),
            book_value=round(book_value, 2),
        ))
    return schedule


def declining_balance_schedule(
    purchase_cost: float,
    salvage_value: float,
    useful_life_years: float,
    purchase_date: date,
    rate: float = 0.4,
) -> list[DepreciationPeriod]:
    """
    Declining-balance method: each year, depreciate `rate` of the current
    book value. Depreciation stops once book value hits salvage value.
    """
    years = max(int(round(useful_life_years)), 1)
    book_value = purchase_cost
    accumulated = 0.0
    schedule = []

    for year in range(1, years + 1):
        depreciation = book_value * rate
        # Don't depreciate below salvage value
        if book_value - depreciation < salvage_value:
            depreciation = max(book_value - salvage_value, 0)
        book_value -= depreciation
        accumulated += depreciation
        period_date = date(purchase_date.year + year, purchase_date.month, purchase_date.day) \
            if _safe_date(purchase_date, year) else _year_end(purchase_date.year + year)
        schedule.append(DepreciationPeriod(
            period_date=period_date,
            depreciation_amount=round(depreciation, 2),
            accumulated_depreciation=round(accumulated, 2),
            book_value=round(book_value, 2),
        ))
        if book_value <= salvage_value:
            break

    return schedule


def get_schedule(
    method: str,
    purchase_cost: float,
    salvage_value: float,
    useful_life_years: float,
    purchase_date: date,
    declining_balance_rate: float = 0.4,
) -> list[DepreciationPeriod]:
    if method == "declining_balance":
        return declining_balance_schedule(
            purchase_cost, salvage_value, useful_life_years, purchase_date, declining_balance_rate
        )
    return straight_line_schedule(purchase_cost, salvage_value, useful_life_years, purchase_date)


def _safe_date(d: date, years_to_add: int) -> bool:
    """Check Feb-29-safe date shift is valid; else caller falls back to year-end."""
    try:
        date(d.year + years_to_add, d.month, d.day)
        return True
    except ValueError:
        return False


def _year_end(year: int) -> date:
    return date(year, 12, 31)
