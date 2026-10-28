"""Live hooks for the simulator and the staffing plan.

Both call staffing_engine. Numbers come only from the beer-game simulator and
the SciPy MILP; nothing is invented here.
"""

from __future__ import annotations

import json
from typing import Any

import pandas as pd

from genai.contracts import SimulatorParams, StaffingParams
from genai.forecast_view import canonicalize
from staffing_engine import (
    apply_demand_scale,
    load_inputs,
    no_change_decider,
    simulate_game,
    simulate_optimized_plan,
    summarize_runs,
)


def _named(countries: list[str] | None) -> list[str] | None:
    if countries is None:
        return None
    return [canonicalize(name) for name in countries]


def _resolve_countries(names: list[str] | None, inputs: pd.DataFrame) -> list[str]:
    available = sorted(inputs.Country.unique().tolist())
    if names is None:
        return available
    missing = [name for name in names if name not in set(available)]
    if missing:
        raise ValueError(f"Unknown countries for the engine: {', '.join(missing)}")
    return names


def _round_money(value: float) -> float:
    return round(float(value), 2)


def _summary_records(detail: pd.DataFrame) -> list[dict[str, Any]]:
    summary = summarize_runs(detail)
    rows = []
    for row in summary.itertuples(index=False):
        arrivals = int(row.Arrivals)
        served = int(row.Served)
        rows.append(
            {
                "country": row.Country,
                "policy": row.Policy,
                "arrivals": arrivals,
                "served": served,
                "abandoned": int(row.Abandoned),
                "year_end_backlog": int(row.Year_End_Backlog),
                "hires_ordered": int(row.Hires_Ordered),
                "releases": int(row.Releases),
                "service_rate": None if arrivals == 0 else round(float(served / arrivals), 6),
                "modeled_revenue_usd": _round_money(row.Modeled_Revenue_USD),
                "staffing_cost_usd": _round_money(row.Staffing_Cost_USD),
                "modeled_profit_usd": _round_money(row.Modeled_Profit_USD),
            }
        )
    return rows


def _monthly_records(detail: pd.DataFrame) -> list[dict[str, Any]]:
    cols = [
        "Country",
        "Month",
        "Forecast",
        "Arrivals",
        "Hires_Ordered",
        "Hires_Activated",
        "Releases",
        "Active_Flexible",
        "Capacity",
        "Served",
        "Abandoned",
        "Backlog_End",
        "Modeled_Revenue_USD",
        "Total_Staffing_Cost_USD",
        "Modeled_Profit_USD",
    ]
    frame = detail[cols].copy()
    records = []
    for row in frame.itertuples(index=False):
        records.append(
            {
                "country": row.Country,
                "month": int(row.Month),
                "forecast": float(row.Forecast),
                "arrivals": int(row.Arrivals),
                "hires_ordered": int(row.Hires_Ordered),
                "hires_activated": int(row.Hires_Activated),
                "releases": int(row.Releases),
                "active_flexible": int(row.Active_Flexible),
                "capacity": int(row.Capacity),
                "served": int(row.Served),
                "abandoned": int(row.Abandoned),
                "backlog_end": int(row.Backlog_End),
                "modeled_revenue_usd": _round_money(row.Modeled_Revenue_USD),
                "total_staffing_cost_usd": _round_money(row.Total_Staffing_Cost_USD),
                "modeled_profit_usd": _round_money(row.Modeled_Profit_USD),
            }
        )
    return records


def run_simulator(params: SimulatorParams) -> str:
    """Scale demand and simulate keep_current_staff for the selected countries."""
    params = params.model_copy(update={"countries": _named(params.countries)})
    inputs = apply_demand_scale(load_inputs(), params.demand_scale)
    countries = _resolve_countries(params.countries, inputs)
    details = []
    for country in countries:
        detail, _ = simulate_game(
            country,
            no_change_decider,
            "Keep current staff",
            inputs,
            enforce_capacity_guardrail=False,
        )
        details.append(detail)
    detail = pd.concat(details, ignore_index=True)
    summary = _summary_records(detail)
    totals = {
        "arrivals": int(detail.Arrivals.sum()),
        "served": int(detail.Served.sum()),
        "abandoned": int(detail.Abandoned.sum()),
        "modeled_revenue_usd": _round_money(detail.Modeled_Revenue_USD.sum()),
        "staffing_cost_usd": _round_money(detail.Total_Staffing_Cost_USD.sum()),
        "modeled_profit_usd": _round_money(detail.Modeled_Profit_USD.sum()),
    }
    arrivals = totals["arrivals"]
    totals["service_rate"] = (
        None if arrivals == 0 else round(totals["served"] / arrivals, 6)
    )
    payload = {
        "demand_scale": params.demand_scale,
        "countries": countries,
        "policy": "Keep current staff",
        "summary": summary,
        "totals": totals,
        "monthly": _monthly_records(detail),
    }
    return json.dumps(payload)


def optimize_staffing(params: StaffingParams, demand_scale: float = 1.0) -> str:
    """Solve the staffing MILP under the current demand scale and compare to keep_current."""
    if demand_scale <= 0:
        raise ValueError("demand_scale must be greater than 0")
    params = params.model_copy(update={"countries": _named(params.countries)})
    inputs = apply_demand_scale(load_inputs(), demand_scale)
    countries = _resolve_countries(params.countries, inputs)
    results = []
    for country in countries:
        plan, detail, _, meta = simulate_optimized_plan(
            country,
            inputs,
            min_service_rate=params.min_service_rate,
            min_agents=params.min_agents,
            max_agents_vs_current=params.max_agents_vs_current,
        )
        baseline, _ = simulate_game(
            country,
            no_change_decider,
            "Keep current staff",
            inputs,
            enforce_capacity_guardrail=False,
        )
        baseline_profit = float(baseline.Modeled_Profit_USD.sum())
        optimized_profit = float(meta["Validated_Simulator_Profit_USD"])
        baseline_arrivals = int(baseline.Arrivals.sum())
        baseline_served = int(baseline.Served.sum())
        results.append(
            {
                "country": country,
                "min_service_rate": params.min_service_rate,
                "baseline": params.baseline,
                "solver": {
                    "country": meta["Country"],
                    "status": meta["Solver_Status"],
                    "message": meta["Solver_Message"],
                    "optimality_gap": meta["Optimality_Gap"],
                    "method": meta["Method"],
                    "forecast_signups": meta["Forecast_Signups"],
                    "optimized_profit_objective_usd": _round_money(
                        meta["Optimized_Profit_Objective_USD"]
                    ),
                    "validated_simulator_profit_usd": _round_money(optimized_profit),
                    "validated_service_rate": round(float(meta["Validated_Service_Rate"]), 6),
                    "min_agents": params.min_agents,
                    "max_agents_vs_current": params.max_agents_vs_current,
                },
                "plan_monthly": [
                    {
                        "country": row.Country,
                        "month": int(row.Month),
                        "new_hires": int(row.New_Hires),
                        "releases": int(row.Releases),
                        "projected_active_flexible": int(row.Projected_Active_Flexible),
                        "projected_arrivals": int(row.Projected_Arrivals),
                        "mode": row.Mode,
                    }
                    for row in plan.itertuples(index=False)
                ],
                "vs_baseline": {
                    "baseline_profit_usd": _round_money(baseline_profit),
                    "optimized_profit_usd": _round_money(optimized_profit),
                    "profit_improvement_usd": _round_money(optimized_profit - baseline_profit),
                    "baseline_service_rate": (
                        None
                        if baseline_arrivals == 0
                        else round(baseline_served / baseline_arrivals, 6)
                    ),
                    "optimized_service_rate": round(float(meta["Validated_Service_Rate"]), 6),
                },
                "summary": _summary_records(detail),
            }
        )
    payload = {
        "demand_scale": demand_scale,
        "min_service_rate": params.min_service_rate,
        "baseline": params.baseline,
        "countries": countries,
        "results": results,
        "note": (
            "Omitting countries runs every country; the MILP can take noticeable time."
            if params.countries is None
            else None
        ),
    }
    return json.dumps(payload)
