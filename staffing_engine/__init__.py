"""Importable beer-game simulator and staffing MILP extracted from notebooks 03–05."""

from staffing_engine.data_io import country_names, load_inputs
from staffing_engine.decisions import no_change_decider, policy_from_plan
from staffing_engine.optimize import maximize_staffing_profit, simulate_optimized_plan
from staffing_engine.rules import MIN_ANNUAL_SERVICE_RATE, RULES, GameRules
from staffing_engine.scaling import apply_demand_scale
from staffing_engine.simulate import simulate_game, summarize_runs

__all__ = [
    "GameRules",
    "MIN_ANNUAL_SERVICE_RATE",
    "RULES",
    "apply_demand_scale",
    "country_names",
    "load_inputs",
    "maximize_staffing_profit",
    "no_change_decider",
    "policy_from_plan",
    "simulate_game",
    "simulate_optimized_plan",
    "summarize_runs",
]
