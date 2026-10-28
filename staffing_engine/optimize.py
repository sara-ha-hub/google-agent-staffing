"""SciPy HiGHS staffing MILP from notebooks 03–05."""

import math

import numpy as np
import pandas as pd
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import lil_matrix

from staffing_engine.decisions import policy_from_plan
from staffing_engine.rules import (
    OPTIMIZER_MIP_REL_GAP,
    OPTIMIZER_TIME_LIMIT_SECONDS,
    RULES,
    GameRules,
)
from staffing_engine.simulate import simulate_game


def maximize_staffing_profit(
    country,
    inputs: pd.DataFrame,
    min_service_rate=None,
    rules: GameRules = RULES,
    min_agents: int | None = None,
    max_agents_vs_current: float | None = None,
):
    """Mixed-integer profit-maximization for one country and one 12-month horizon.

    Returns a plan and solver metadata. Objective is calendar-2026 cohort revenue
    minus active-flex salaries and hiring fees; existing allocated salary is
    constant across candidate plans.
    """
    if min_service_rate is not None and not 0 <= min_service_rate <= 1:
        raise ValueError("min_service_rate must be between 0 and 1, or None")
    if min_agents is not None and min_agents < 0:
        raise ValueError("min_agents must be >= 0")
    if max_agents_vs_current is not None and max_agents_vs_current <= 0:
        raise ValueError("max_agents_vs_current must be greater than 0")

    part = inputs.loc[inputs.Country == country].sort_values("Month").reset_index(drop=True)
    if len(part) != 12:
        raise ValueError(f"Expected 12 rows for {country}")
    horizon = len(part)
    salary = float(part.Annual_Agent_Salary_USD.iloc[0])
    annual_budget = part.Avg_Budget.to_numpy(dtype=float)
    if not np.allclose(annual_budget, annual_budget[0], rtol=0, atol=1e-5):
        raise ValueError(
            "This exact FIFO-equivalent optimizer requires a constant budget within each country"
        )
    arrivals = np.floor(part.Forecast_Eligible_Signups.to_numpy(dtype=float) + 0.5).astype(int)
    existing = int(part.Existing_Agent_Count.iloc[0])
    base_capacity = int(
        math.floor(existing * rules.existing_time_share * rules.cases_per_agent_month + 1e-9)
    )
    productivity = float(rules.cases_per_agent_month)
    if not productivity.is_integer():
        raise ValueError("Optimization requires integer cases_per_agent_month")
    lag = int(rules.hire_lead_months)
    if lag < 1 or lag > 11:
        raise ValueError("Optimizer supports 1-11 month hiring lead time")

    # Headcount = existing permanent agents + flexible A[t].
    min_flex = 0
    if min_agents is not None:
        min_flex = max(0, int(min_agents) - existing)
    max_flex = horizon * int(rules.max_hires_per_month)
    if max_agents_vs_current is not None:
        max_total = int(math.floor(existing * float(max_agents_vs_current) + 1e-9))
        max_flex = min(max_flex, max(0, max_total - existing))
        if min_agents is not None and min_agents > max_total:
            raise ValueError(
                f"min_agents ({min_agents}) exceeds max headcount "
                f"({max_total}) from max_agents_vs_current={max_agents_vs_current}"
            )

    H = list(range(0, horizon))
    R = list(range(horizon, horizon * 2))
    A = list(range(horizon * 2, horizon * 3))
    Z = list(range(horizon * 3, horizon * 4))
    served_index = {}
    next_col = horizon * 4
    for cohort in range(horizon):
        for month in range(cohort, min(horizon, cohort + rules.max_wait_months + 1)):
            served_index[cohort, month] = next_col
            next_col += 1

    num_vars = next_col
    c = np.zeros(num_vars, dtype=float)
    lower = np.zeros(num_vars)
    upper = np.full(num_vars, np.inf)
    integrality = np.ones(num_vars, dtype=int)
    upper[Z] = 1
    upper[H] = int(rules.max_hires_per_month)
    for month in range(horizon):
        if month + lag >= horizon:
            upper[H[month]] = 0
        c[A[month]] = salary / 12
        c[H[month]] = salary * rules.hire_fee_fraction
        lower[A[month]] = min_flex
        upper[A[month]] = max_flex
    max_active = horizon * int(rules.max_hires_per_month)
    upper[R] = max_active

    monthly_unit_revenue = float(annual_budget[0]) * rules.revenue_capture_rate / 12
    for (cohort, month), idx in served_index.items():
        c[idx] = -(horizon - month) * monthly_unit_revenue
        upper[idx] = int(arrivals[cohort])

    sparse_rows = []
    row_lower, row_upper = [], []

    def constrain(entries, lb=-np.inf, ub=np.inf):
        sparse_rows.append(entries)
        row_lower.append(lb)
        row_upper.append(ub)

    for month in range(horizon):
        e = {A[month]: 1, R[month]: 1}
        if month > 0:
            e[A[month - 1]] = -1
        if month - lag >= 0:
            e[H[month - lag]] = -1
        constrain(e, lb=0, ub=0)

        constrain({H[month]: 1, Z[month]: -rules.max_hires_per_month}, ub=0)
        constrain({R[month]: 1, Z[month]: max_active}, ub=max_active)

    for cohort in range(horizon):
        constrain(
            {idx: 1 for (i, t), idx in served_index.items() if i == cohort},
            ub=int(arrivals[cohort]),
        )
    for month in range(horizon):
        e = {A[month]: -productivity}
        e.update({idx: 1 for (i, t), idx in served_index.items() if t == month})
        constrain(e, ub=base_capacity)

    if min_service_rate is not None:
        min_served = int(math.ceil(arrivals.sum() * min_service_rate - 1e-10))
        constrain({idx: 1 for idx in served_index.values()}, lb=min_served)

    mat = lil_matrix((len(sparse_rows), num_vars), dtype=float)
    for row_no, entries in enumerate(sparse_rows):
        for col, coeff in entries.items():
            mat[row_no, col] = coeff
    lin = LinearConstraint(mat.tocsr(), np.array(row_lower), np.array(row_upper))
    res = milp(
        c=c,
        integrality=integrality,
        bounds=Bounds(lower, upper),
        constraints=lin,
        options={
            "time_limit": OPTIMIZER_TIME_LIMIT_SECONDS,
            "mip_rel_gap": OPTIMIZER_MIP_REL_GAP,
        },
    )
    if res.x is None:
        raise RuntimeError(f"MILP did not produce a feasible plan for {country}: {res.message}")
    if res.status not in (0, 1):
        raise RuntimeError(f"MILP ended with status {res.status}: {res.message}")
    hires = np.rint(res.x[H]).astype(int)
    releases = np.rint(res.x[R]).astype(int)
    agents = np.rint(res.x[A]).astype(int)
    plan = pd.DataFrame(
        {
            "Country": country,
            "Month": np.arange(1, horizon + 1),
            "New_Hires": hires,
            "Releases": releases,
            "Projected_Active_Flexible": agents,
            "Projected_Arrivals": arrivals,
        }
    )
    plan["Mode"] = (
        "Profit max (no service minimum)"
        if min_service_rate is None
        else f"Profit max ({min_service_rate:.0%} service minimum)"
    )
    meta = {
        "Country": country,
        "Solver_Status": int(res.status),
        "Solver_Message": str(res.message),
        "Optimality_Gap": float(getattr(res, "mip_gap", np.nan)),
        "Minimum_Service_Rate": min_service_rate,
        "Forecast_Signups": int(arrivals.sum()),
        "Optimized_Profit_Objective_USD": (
            -float(res.fun) - existing * rules.existing_time_share * salary
        ),
        "Method": "SciPy HiGHS mixed-integer linear programming",
        "Min_Agents": min_agents,
        "Max_Agents_Vs_Current": max_agents_vs_current,
    }
    return plan, meta


def simulate_optimized_plan(
    country,
    inputs: pd.DataFrame,
    min_service_rate=None,
    rules: GameRules = RULES,
    min_agents: int | None = None,
    max_agents_vs_current: float | None = None,
):
    plan, meta = maximize_staffing_profit(
        country,
        inputs,
        min_service_rate=min_service_rate,
        rules=rules,
        min_agents=min_agents,
        max_agents_vs_current=max_agents_vs_current,
    )
    detail, audit = simulate_game(
        country,
        policy_from_plan(plan),
        plan.Mode.iloc[0],
        inputs,
        rules,
        enforce_capacity_guardrail=False,
    )
    assert np.array_equal(detail.Hires_Ordered.to_numpy(), plan.New_Hires.to_numpy())
    assert np.array_equal(detail.Releases.to_numpy(), plan.Releases.to_numpy())
    simulated_profit = float(detail.Modeled_Profit_USD.sum())
    if not np.isclose(simulated_profit, meta["Optimized_Profit_Objective_USD"], atol=0.05):
        raise AssertionError(
            "Profit mismatch between optimizer and FIFO simulator: "
            f'{simulated_profit} versus {meta["Optimized_Profit_Objective_USD"]}'
        )
    if min_service_rate is not None:
        served_fraction = float(detail.Served.sum() / detail.Arrivals.sum())
        assert (
            served_fraction >= min_service_rate - 1e-12
        ), "Service rate dropped below solver requirement"
    meta["Validated_Simulator_Profit_USD"] = simulated_profit
    meta["Validated_Service_Rate"] = float(detail.Served.sum() / detail.Arrivals.sum())
    return plan, detail, audit, meta
