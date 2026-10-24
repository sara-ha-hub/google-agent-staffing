"""Hooks for the simulator and the staffing plan.

Both accept the user settings and refuse to invent cost, revenue, profit, or headcount.
"""

from genai.contracts import SimulatorParams, StaffingParams
from genai.forecast_view import canonicalize, headcount


def _named(countries: list[str] | None) -> list[str] | None:
    if countries is None:
        return None
    return [canonicalize(name) for name in countries]


def run_simulator(params: SimulatorParams) -> str:
    """Echo the settings that would adjust model output. Step 03 is not built."""
    params = params.model_copy(update={"countries": _named(params.countries)})
    return (
        "The simulator (step 03) is not implemented yet. "
        "These settings would adjust the model output: "
        f"{params.model_dump_json()}. "
        "Do not invent cost, revenue, or profit."
    )


def optimize_staffing(params: StaffingParams) -> str:
    """Echo the headcount search settings. Step 04 is not built.

    keep_current_staff repeats January 2026 headcount for every month.
    The plan has to beat that baseline.
    """
    names = _named(params.countries)
    params = params.model_copy(update={"countries": names})
    counts = headcount()
    chosen = names if names is not None else list(counts)
    baseline = [
        {"country": name, "january_2026_agents": counts[name], "months": "1-12"}
        for name in chosen
    ]
    return (
        "The staffing plan (step 04) is not implemented yet. "
        "It must pick headcount per country and month for the highest profit "
        "and beat keep_current_staff. keep_current_staff repeats each country's "
        "January 2026 headcount for every month. "
        f"Requested settings: {params.model_dump_json()}. "
        f"Baseline headcount: {baseline}. "
        "Do not invent headcount or profit."
    )
