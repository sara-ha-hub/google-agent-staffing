"""Smoke tests for the extracted staffing engine and GenAI hooks."""

from __future__ import annotations

import json
import unittest

from genai.contracts import SimulatorParams, StaffingParams
from genai.stubs import optimize_staffing, run_simulator
from staffing_engine import (
    apply_demand_scale,
    load_inputs,
    maximize_staffing_profit,
    no_change_decider,
    simulate_game,
    simulate_optimized_plan,
)


class StaffingEngineTests(unittest.TestCase):
    def test_usa_keep_current_simulate(self) -> None:
        inputs = load_inputs()
        detail, _ = simulate_game(
            "USA",
            no_change_decider,
            "Keep current staff",
            inputs,
            enforce_capacity_guardrail=False,
        )
        self.assertEqual(len(detail), 12)
        profit = float(detail.Modeled_Profit_USD.sum())
        self.assertTrue(profit == profit)  # finite
        self.assertGreater(profit, 0)

    def test_demand_scale_changes_arrivals(self) -> None:
        inputs = load_inputs()
        base, _ = simulate_game(
            "USA",
            no_change_decider,
            "Keep current staff",
            inputs,
            enforce_capacity_guardrail=False,
        )
        scaled, _ = simulate_game(
            "USA",
            no_change_decider,
            "Keep current staff",
            apply_demand_scale(inputs, 0.8),
            enforce_capacity_guardrail=False,
        )
        self.assertLess(int(scaled.Arrivals.sum()), int(base.Arrivals.sum()))

    def test_usa_optimize_beats_keep_current(self) -> None:
        inputs = load_inputs()
        plan, meta = maximize_staffing_profit("USA", inputs)
        self.assertEqual(len(plan), 12)
        _, detail, _, validated = simulate_optimized_plan("USA", inputs)
        baseline, _ = simulate_game(
            "USA",
            no_change_decider,
            "Keep current staff",
            inputs,
            enforce_capacity_guardrail=False,
        )
        self.assertGreaterEqual(
            float(validated["Validated_Simulator_Profit_USD"]),
            float(baseline.Modeled_Profit_USD.sum()) - 0.05,
        )
        self.assertEqual(int(detail.Hires_Ordered.sum()), int(plan.New_Hires.sum()))
        self.assertEqual(meta["Country"], "USA")


class GenaiHookTests(unittest.TestCase):
    def test_run_simulator_json(self) -> None:
        raw = run_simulator(SimulatorParams(demand_scale=1.0, countries=["USA"]))
        self.assertNotIn("not implemented", raw.lower())
        payload = json.loads(raw)
        self.assertEqual(payload["demand_scale"], 1.0)
        self.assertEqual(payload["countries"], ["USA"])
        self.assertEqual(len(payload["summary"]), 1)
        self.assertIn("modeled_profit_usd", payload["summary"][0])

    def test_optimize_staffing_json(self) -> None:
        raw = optimize_staffing(
            StaffingParams(countries=["USA"]),
            demand_scale=1.0,
        )
        self.assertNotIn("not implemented", raw.lower())
        payload = json.loads(raw)
        self.assertEqual(payload["countries"], ["USA"])
        result = payload["results"][0]
        self.assertEqual(len(result["plan_monthly"]), 12)
        self.assertIn("profit_improvement_usd", result["vs_baseline"])


if __name__ == "__main__":
    unittest.main()
