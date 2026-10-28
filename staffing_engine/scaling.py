"""Demand scaling for step 05-style scenario runs."""

import pandas as pd


def apply_demand_scale(inputs: pd.DataFrame, scale: float) -> pd.DataFrame:
    """Return a copy with Forecast_Eligible_Signups multiplied by scale.

    Budgets, salaries, and existing headcount are unchanged.
    """
    if scale <= 0:
        raise ValueError("demand_scale must be greater than 0")
    out = inputs.copy(deep=True)
    out["Forecast_Eligible_Signups"] = out.Forecast_Eligible_Signups * float(scale)
    return out
