"""Decision helpers used by the beer-game simulator."""

import math

from staffing_engine.rules import RULES, GameRules


def check_action(proposed, observed, rules: GameRules = RULES):
    if not isinstance(proposed, dict):
        raise ValueError("Decision must be a JSON object")
    hire, release = proposed.get("hire"), proposed.get("release")
    if type(hire) is not int or type(release) is not int:
        raise ValueError("hire and release must be integers")
    if min(hire, release) < 0:
        raise ValueError("No negative actions")
    if hire > rules.max_hires_per_month:
        raise ValueError("Hires exceed safe maximum")
    if release > observed["active_flexible_agents"]:
        raise ValueError("Releases exceed active flexible staff")
    if hire and release:
        raise ValueError("Cannot hire and release in same month")
    return {
        "hire": hire,
        "release": release,
        "reason": str(proposed.get("reason", ""))[:1500],
    }


def augment_capacity_state(observed, rules: GameRules = RULES):
    """Add derived capacity limits to the observable state."""
    state = dict(observed)
    current_agents = float(state["existing_agents"]) * rules.existing_time_share + int(
        state["active_flexible_agents"]
    )
    pending_next = int(state["pending_hires"].get(str(state["month"] + 1), 0))
    capacity_now = current_agents * rules.cases_per_agent_month
    capacity_next_before_new = (current_agents + pending_next) * rules.cases_per_agent_month
    forecast_next = state.get("forecast_next_month")
    backlog = int(state["backlog_start"])
    target_today = (float(state["forecast_this_month"]) + backlog) * (1 + rules.capacity_buffer)
    target_next = (
        (float(forecast_next) + backlog) * (1 + rules.capacity_buffer)
        if forecast_next is not None
        else 0.0
    )
    hires_shortfall = max(
        0, math.ceil((target_next - capacity_next_before_new) / rules.cases_per_agent_month - 1e-9)
    )
    if state["month"] + rules.hire_lead_months > 12:
        hires_shortfall = 0
    required_today_flex = max(
        0,
        math.ceil(
            (target_today / rules.cases_per_agent_month)
            - float(state["existing_agents"]) * rules.existing_time_share
            - 1e-9
        ),
    )
    required_next_flex = max(
        0,
        math.ceil(
            (target_next / rules.cases_per_agent_month)
            - float(state["existing_agents"]) * rules.existing_time_share
            - pending_next
            - 1e-9
        ),
    )
    max_safe_release = max(
        0, int(state["active_flexible_agents"]) - max(required_today_flex, required_next_flex)
    )
    state.update(
        {
            "current_capacity_cases": int(math.floor(capacity_now)),
            "projected_next_month_capacity_before_new_hires": int(
                math.floor(capacity_next_before_new)
            ),
            "next_month_target_with_buffer": round(target_next, 2)
            if forecast_next is not None
            else None,
            "max_justified_hires": min(rules.max_hires_per_month, int(hires_shortfall)),
            "max_safe_releases": int(max_safe_release),
            "capacity_buffer_fraction": rules.capacity_buffer,
            "financial_rule": (
                "Each hired active agent costs salary / 12 monthly, "
                "plus a one-time hiring fee at activation."
            ),
        }
    )
    return state


def capacity_guardrail(action, state):
    """Clip hire/release to capacity-derived limits and explain any change."""
    applied = dict(action)
    notes = []
    if applied["hire"] > state["max_justified_hires"]:
        notes.append(
            f"hire {applied['hire']} -> {state['max_justified_hires']} (no supported capacity shortfall)"
        )
        applied["hire"] = int(state["max_justified_hires"])
    if applied["release"] > state["max_safe_releases"]:
        notes.append(
            f"release {applied['release']} -> {state['max_safe_releases']} (protect service capacity)"
        )
        applied["release"] = int(state["max_safe_releases"])
    note = "; ".join(notes)
    if note:
        applied["reason"] = (
            f"[CAPACITY GUARDRAIL: {note}] Model reason: " + str(applied.get("reason", ""))
        )
    return applied, note


def no_change_decider(observed):
    return {"hire": 0, "release": 0, "reason": "Keep current team"}


def policy_from_plan(plan):
    action_by_month = {
        int(row.Month): (int(row.New_Hires), int(row.Releases))
        for row in plan.itertuples(index=False)
    }

    def decide(state):
        hire, release = action_by_month[int(state["month"])]
        return {
            "hire": hire,
            "release": release,
            "reason": (
                "MILP monthly action: maximize 2026 modeled profit under its stated constraints"
            ),
        }

    return decide
