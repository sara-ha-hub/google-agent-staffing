"""Beer-game rules and optimizer defaults from notebooks 03–05."""

from dataclasses import dataclass

MIN_ANNUAL_SERVICE_RATE = 0.98
OPTIMIZER_TIME_LIMIT_SECONDS = 40
OPTIMIZER_MIP_REL_GAP = 1e-6


@dataclass(frozen=True)
class GameRules:
    cases_per_agent_month: float = 10.0
    existing_time_share: float = 0.20
    hire_lead_months: int = 1
    max_wait_months: int = 2
    hire_fee_fraction: float = 0.08
    revenue_capture_rate: float = 0.10
    max_hires_per_month: int = 150
    capacity_buffer: float = 0.10


RULES = GameRules()
