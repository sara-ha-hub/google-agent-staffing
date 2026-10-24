"""Read the step 02 forecast and the January 2026 headcount. Does not write either file."""

import csv
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORECAST_PATH = ROOT / "data" / "clean" / "forecast_2026.csv"
COUNTRIES_PATH = ROOT / "data" / "clean" / "countries.csv"


@lru_cache(maxsize=1)
def _forecast() -> tuple[dict[str, str], ...]:
    with FORECAST_PATH.open(newline="") as handle:
        return tuple(csv.DictReader(handle))


@lru_cache(maxsize=1)
def _countries() -> tuple[dict[str, str], ...]:
    with COUNTRIES_PATH.open(newline="") as handle:
        return tuple(csv.DictReader(handle))


def known_countries() -> list[str]:
    return [row["Country"] for row in _countries()]


def canonicalize(name: str) -> str:
    lookup = {country.casefold(): country for country in known_countries()}
    found = lookup.get(name.casefold())
    if found is None:
        names = ", ".join(known_countries())
        raise ValueError(f"Unknown country {name!r}. Known countries: {names}")
    return found


def headcount() -> dict[str, int]:
    """January 2026 agents by country. keep_current_staff repeats this all year."""
    return {row["Country"]: int(row["Existing_Agent_Count"]) for row in _countries()}


def view_forecast(country: str | None = None, month: int | None = None) -> dict:
    """Return forecast rows, or a country summary when no filter is set."""
    if month is not None and not 1 <= month <= 12:
        raise ValueError("month must be from 1 to 12")
    selected = canonicalize(country) if country else None
    rows = []
    for row in _forecast():
        if selected is not None and row["Country"] != selected:
            continue
        if month is not None and int(row["Month"]) != month:
            continue
        rows.append(
            {
                "country": row["Country"],
                "month": int(row["Month"]),
                "eligible_signups": float(row["Forecast_Eligible_Signups"]),
                "avg_budget": float(row["Avg_Budget"]),
            }
        )
    if not rows:
        raise ValueError("No forecast rows match that filter")
    rows.sort(key=lambda item: (item["country"], item["month"]))
    if selected is None and month is None:
        by_country = []
        for name in known_countries():
            country_rows = [row for row in rows if row["country"] == name]
            by_country.append(
                {
                    "country": name,
                    "eligible_signups": round(sum(row["eligible_signups"] for row in country_rows), 1),
                    "avg_budget": country_rows[0]["avg_budget"],
                }
            )
        return {
            "source": "data/clean/forecast_2026.csv",
            "note": "Country totals. Pass a country or a month to see monthly rows.",
            "total_eligible_signups": round(sum(row["eligible_signups"] for row in rows), 1),
            "by_country": by_country,
        }
    return {
        "source": "data/clean/forecast_2026.csv",
        "country": selected,
        "month": month,
        "rows": rows,
    }
