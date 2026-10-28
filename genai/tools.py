"""LangChain tools. Core tools are always bound. Data tools are registered and optional."""

import json
from typing import Annotated

from langchain_core.messages import ToolMessage
from langchain_core.tools import InjectedToolCallId, tool
from langgraph.prebuilt import InjectedState
from langgraph.types import Command
from pydantic import BaseModel, ValidationError

from genai.contracts import SimulatorParams, StaffingParams
from genai.forecast_view import canonicalize
from genai.forecast_view import view_forecast as read_forecast
from genai.registry import register_data_tool
from genai.stubs import optimize_staffing as staffing_stub
from genai.stubs import run_simulator as simulator_stub
from genai.world_bank import gdp_growth


def _command(tool_call_id: str, payload: object, **state: object) -> Command:
    if isinstance(payload, str):
        content = payload
    else:
        content = json.dumps(payload)
    return Command(
        update={
            "messages": [ToolMessage(content=content, tool_call_id=tool_call_id)],
            **state,
        }
    )


def _merge(model_cls: type[BaseModel], state: dict | None, key: str, incoming: BaseModel | None) -> BaseModel:
    """Keep the request settings and overlay only fields this call set."""
    stored = dict((state or {}).get(key) or {})
    if incoming is not None:
        stored.update(incoming.model_dump(mode="json", include=incoming.model_fields_set))
    params = model_cls.model_validate(stored)
    countries = getattr(params, "countries", None)
    if not countries:
        return params
    return params.model_copy(update={"countries": [canonicalize(name) for name in countries]})


@tool
def view_forecast(country: str | None = None, month: int | None = None) -> str:
    """Read our 2026 eligible sign-up forecast.

    Pass a country to see each month. Pass a month from 1 to 12 to see every
    country in that month. Omit both for a country summary.
    """
    try:
        return json.dumps(read_forecast(country, month))
    except ValueError as exc:
        return str(exc)


@tool
def world_bank_gdp(country: str | None = None, year: int = 2026) -> str:
    """World Bank Global Economic Prospects real GDP growth, in percent.

    This is an outside projection, not our eligible sign-up forecast.
    Pass a project country, or omit it for every project country. year defaults to 2026.
    Some advanced economies have no country series. The result then names the World Bank
    group and that group rate is not the country's rate.
    """
    try:
        return json.dumps(gdp_growth(country, year))
    except ValueError as exc:
        return str(exc)


@tool
def run_simulator(
    tool_call_id: Annotated[str, InjectedToolCallId],
    params: SimulatorParams | None = None,
    state: Annotated[dict, InjectedState] = None,
) -> Command:
    """Run the live beer-game simulator under the user's demand scale.

    Call this when the manager asks about profit, cost, service rate, backlog,
    or which country is best or worst under keep_current_staff. demand_scale 1
    leaves the forecast unchanged. 0.8 is lower sign-ups and 1.2 is higher.
    Returns per-country profit and service metrics. Use only those numbers.
    """
    try:
        merged = _merge(SimulatorParams, state, "simulator", params)
        message = simulator_stub(merged)
    except (ValueError, ValidationError, RuntimeError) as exc:
        return _command(tool_call_id, str(exc))
    return _command(tool_call_id, message, simulator=merged.model_dump(mode="json"))


@tool
def optimize_staffing(
    tool_call_id: Annotated[str, InjectedToolCallId],
    params: StaffingParams | None = None,
    state: Annotated[dict, InjectedState] = None,
) -> Command:
    """Solve the live staffing MILP under the user's settings and demand scale.

    Call this when the manager asks for a hire/release plan or optimized staffing.
    Picks headcount actions per country and month for the highest modeled profit
    and compares against keep_current_staff. min_service_rate 0.98 adds the SLA
    floor. Use only the plan and profit numbers the tool returns.
    """
    try:
        merged = _merge(StaffingParams, state, "staffing", params)
        sim = SimulatorParams.model_validate((state or {}).get("simulator") or {})
        message = staffing_stub(merged, demand_scale=sim.demand_scale)
    except (ValueError, ValidationError, RuntimeError, AssertionError) as exc:
        return _command(tool_call_id, str(exc))
    return _command(tool_call_id, message, staffing=merged.model_dump(mode="json"))


CORE_TOOLS = [view_forecast, run_simulator, optimize_staffing]

register_data_tool(
    "world_bank_gdp",
    "World Bank Global Economic Prospects real GDP growth projection. Not the eligible sign-up forecast.",
    world_bank_gdp,
)
