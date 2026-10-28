"""Beer-game FIFO simulator from notebooks 03–05."""

import json
import math
from collections import deque

import numpy as np
import pandas as pd

from staffing_engine.decisions import (
    augment_capacity_state,
    capacity_guardrail,
    check_action,
)
from staffing_engine.rules import RULES, GameRules


def simulate_game(
    country,
    decision_fn,
    label,
    inputs: pd.DataFrame,
    rules: GameRules = RULES,
    enforce_capacity_guardrail: bool = True,
):
    part = inputs[inputs.Country == country].sort_values("Month").reset_index(drop=True)
    if len(part) != 12:
        raise ValueError("Country must have 12 rows")
    existing = int(part.Existing_Agent_Count.iloc[0])
    salary = float(part.Annual_Agent_Salary_USD.iloc[0])
    active = 0
    active_advertisers = 0
    active_monthly_revenue_usd = 0.0
    pending = {}
    fifo = deque()
    history = []
    rows = []
    audit = []
    for r in part.itertuples(index=False):
        month = int(r.Month)
        started = pending.pop(month, 0)
        active += started
        expired = 0
        while fifo and month - fifo[0][0] > rules.max_wait_months:
            expired += fifo.popleft()[1]
        backlog_start = sum(bucket[1] for bucket in fifo)
        observed = {
            "country": country,
            "month": month,
            "forecast_this_month": round(float(r.Forecast_Eligible_Signups), 2),
            "forecast_next_month": (
                round(float(part.loc[month, "Forecast_Eligible_Signups"]), 2)
                if month < 12
                else None
            ),
            "recent_history": history[-3:],
            "backlog_start": backlog_start,
            "abandoned_before_decision": expired,
            "existing_agents": existing,
            "existing_capacity_share": rules.existing_time_share,
            "cases_per_agent_month": rules.cases_per_agent_month,
            "active_flexible_agents": active,
            "pending_hires": {str(k): int(v) for k, v in pending.items()},
            "hire_lead_months": rules.hire_lead_months,
            "max_hires_per_month": rules.max_hires_per_month,
            "monthly_flexible_agent_salary_usd": round(salary / 12, 2),
            "one_time_hire_fee_usd": round(salary * rules.hire_fee_fraction, 2),
            "model_revenue_capture_rate": rules.revenue_capture_rate,
            "avg_advertiser_budget_usd": round(float(r.Avg_Budget), 2),
            "active_advertisers": active_advertisers,
        }
        observed = augment_capacity_state(observed, rules)
        source_name = label
        suggested = None
        guardrail_note = ""
        try:
            suggested = decision_fn(observed)
            numeric_checked = check_action(suggested, observed, rules)
            if enforce_capacity_guardrail:
                checked, guardrail_note = capacity_guardrail(numeric_checked, observed)
            else:
                checked, guardrail_note = numeric_checked, ""
            if guardrail_note:
                source_name = label + " [GUARDRAIL ADJUSTED]"
        except Exception as error:
            checked = {
                "hire": 0,
                "release": 0,
                "reason": (
                    f"Invalid decision / API error: {type(error).__name__}: {str(error)[:100]}"
                ),
            }
            source_name = "SAFE_FALLBACK_NOT_LLM"
        active -= checked["release"]
        if rules.hire_lead_months == 0:
            active += checked["hire"]
            started += checked["hire"]
        elif checked["hire"]:
            arrive_in = month + rules.hire_lead_months
            pending[arrive_in] = pending.get(arrive_in, 0) + checked["hire"]

        arrivals = int(math.floor(float(r.Forecast_Eligible_Signups) + 0.5))
        if arrivals:
            fifo.append([month, arrivals, float(r.Avg_Budget)])
        capacity = int(
            math.floor(
                (existing * rules.existing_time_share + active) * rules.cases_per_agent_month
                + 1e-9
            )
        )
        served = served_new = 0
        capacity_left = capacity
        while capacity_left > 0 and fifo:
            born, n, budget_per_advertiser = fifo[0]
            fulfilled = min(capacity_left, n)
            served += fulfilled
            served_new += fulfilled if born == month else 0
            active_monthly_revenue_usd += (
                fulfilled * budget_per_advertiser * rules.revenue_capture_rate / 12
            )
            capacity_left -= fulfilled
            if n == fulfilled:
                fifo.popleft()
            else:
                fifo[0][1] = n - fulfilled
        backlog_end = sum(bucket[1] for bucket in fifo)
        active_advertisers += served
        revenue_usd = active_monthly_revenue_usd
        baseline_allocation_usd = existing * rules.existing_time_share * salary / 12
        flexible_salary_usd = active * salary / 12
        hiring_fee_usd = started * salary * rules.hire_fee_fraction
        staffing_cost_usd = baseline_allocation_usd + flexible_salary_usd + hiring_fee_usd
        profit_usd = revenue_usd - staffing_cost_usd
        entry = {
            "Policy": label,
            "Country": country,
            "Month": month,
            "Forecast": float(r.Forecast_Eligible_Signups),
            "Arrivals": arrivals,
            "Hires_Ordered": checked["hire"],
            "Hires_Activated": started,
            "Releases": checked["release"],
            "Active_Flexible": active,
            "Pending_End": sum(pending.values()),
            "Existing_Agents": existing,
            "Capacity": capacity,
            "Served": served,
            "Served_Same_Month": served_new,
            "Abandoned": expired,
            "Backlog_Start": backlog_start,
            "Backlog_End": backlog_end,
            "Active_Advertisers": active_advertisers,
            "Modeled_Revenue_USD": revenue_usd,
            "Allocated_Existing_Salary_USD": baseline_allocation_usd,
            "Flexible_Salary_USD": flexible_salary_usd,
            "Hiring_Fee_USD": hiring_fee_usd,
            "Total_Staffing_Cost_USD": staffing_cost_usd,
            "Modeled_Profit_USD": profit_usd,
            "Action_Source": source_name,
            "Reason": checked["reason"],
            "Proposed_Hires": suggested.get("hire") if isinstance(suggested, dict) else None,
            "Proposed_Releases": suggested.get("release") if isinstance(suggested, dict) else None,
            "Guardrail_Note": guardrail_note,
        }
        rows.append(entry)
        audit.append(
            {
                "Policy": label,
                "Country": country,
                "Month": month,
                "Observed_State_JSON": json.dumps(observed, sort_keys=True),
                "Raw_LLM_Or_Policy_Action_JSON": json.dumps(suggested),
                "Applied_Action_JSON": json.dumps(checked),
                "Action_Source": source_name,
                "Guardrail_Note": guardrail_note,
            }
        )
        history.append(
            {
                "month": month,
                "actual_arrivals": arrivals,
                "served": served,
                "backlog_end": backlog_end,
                "hires_ordered": checked["hire"],
                "releases": checked["release"],
                "modeled_profit_usd": round(profit_usd, 2),
            }
        )
    out = pd.DataFrame(rows)
    assert (
        out.Arrivals.cumsum() == out.Served.cumsum() + out.Abandoned.cumsum() + out.Backlog_End
    ).all(), "Sign-up conservation failed"
    assert (out.Served <= out.Capacity).all(), "Service exceeded capacity"
    assert (
        out[["Active_Flexible", "Backlog_End", "Served", "Abandoned", "Hires_Activated"]] >= 0
    ).all().all()
    return out, pd.DataFrame(audit)


def summarize_runs(detail: pd.DataFrame) -> pd.DataFrame:
    if len(detail) == 0:
        return pd.DataFrame()
    grouped = detail.groupby(["Policy", "Country"], as_index=False).agg(
        Arrivals=("Arrivals", "sum"),
        Served=("Served", "sum"),
        Abandoned=("Abandoned", "sum"),
        Year_End_Backlog=("Backlog_End", "last"),
        Hires_Ordered=("Hires_Ordered", "sum"),
        Releases=("Releases", "sum"),
        Modeled_Revenue_USD=("Modeled_Revenue_USD", "sum"),
        Staffing_Cost_USD=("Total_Staffing_Cost_USD", "sum"),
        Modeled_Profit_USD=("Modeled_Profit_USD", "sum"),
    )
    grouped["Service_Rate"] = (
        grouped.Served / grouped.Arrivals.replace(0, np.nan)
    )
    return grouped
