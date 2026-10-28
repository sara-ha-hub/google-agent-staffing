"""Load countries and the 2026 forecast into the simulator inputs table."""

from functools import lru_cache
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CLEAN = ROOT / "data" / "clean"
PATHS = [DEFAULT_CLEAN, Path("."), Path("data/clean"), Path("/content"), Path("/mnt/data")]


def locate(filename: str) -> Path:
    for folder in PATHS:
        path = folder / filename
        if path.is_file():
            return path
    raise FileNotFoundError(f"Could not find {filename}. Expected it under data/clean.")


def _validate(countries: pd.DataFrame, forecast: pd.DataFrame) -> None:
    required_a = {"Country", "Existing_Agent_Count", "Annual_Agent_Salary_USD"}
    required_b = {"Country", "Month", "Forecast_Eligible_Signups", "Avg_Budget"}
    if not required_a.issubset(countries):
        raise ValueError(f"countries.csv missing columns: {required_a - set(countries)}")
    if not required_b.issubset(forecast):
        raise ValueError(f"forecast_2026.csv missing columns: {required_b - set(forecast)}")
    if countries.Country.duplicated().any():
        raise ValueError("countries.csv has duplicate Country values")
    if forecast[["Country", "Month"]].duplicated().any():
        raise ValueError("forecast_2026.csv has duplicate Country/Month rows")
    if set(forecast.Country) != set(countries.Country):
        raise ValueError("Country sets in countries.csv and forecast_2026.csv differ")
    if len(forecast) != len(countries) * 12:
        raise ValueError("forecast_2026.csv must have 12 months per country")
    if not (forecast.groupby("Country").Month.nunique() == 12).all():
        raise ValueError("Each country must have months 1–12")
    if not (forecast[["Forecast_Eligible_Signups", "Avg_Budget"]] >= 0).all().all():
        raise ValueError("Forecast sign-ups and budgets must be non-negative")
    if not (countries[["Existing_Agent_Count", "Annual_Agent_Salary_USD"]] >= 0).all().all():
        raise ValueError("Existing agent counts and salaries must be non-negative")


@lru_cache(maxsize=1)
def load_inputs() -> pd.DataFrame:
    """Merged country-month frame used by simulate and optimize."""
    countries = pd.read_csv(locate("countries.csv"))
    forecast = pd.read_csv(locate("forecast_2026.csv"))
    _validate(countries, forecast)
    return (
        forecast.merge(
            countries[["Country", "Existing_Agent_Count", "Annual_Agent_Salary_USD"]],
            on="Country",
            validate="many_to_one",
        )
        .sort_values(["Country", "Month"])
        .reset_index(drop=True)
    )


def country_names(inputs: pd.DataFrame | None = None) -> list[str]:
    frame = load_inputs() if inputs is None else inputs
    return sorted(frame.Country.unique().tolist())
