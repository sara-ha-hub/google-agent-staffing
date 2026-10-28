"""LangGraph agent. ask() is the entry point a later screen can call."""

import json
from typing import Annotated, Any

from langchain.chat_models import init_chat_model
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from typing_extensions import NotRequired, TypedDict

from genai.contracts import LLMChoice, SimulatorParams, StaffingParams, TurnRequest, TurnResult
from genai.registry import tools_for
from genai.tools import CORE_TOOLS

_CHECKPOINTER = MemorySaver()

SYSTEM = """You are an analyst for Google's 2026 agent staffing plan. A manager asks a question. You use the tools and explain the result in plain words.

Rules:
- Use only numbers the tools return. Do not invent eligible sign-ups, GDP growth, cost, revenue, profit, or headcount.
- The simulator and staffing optimizer are implemented. Never say they are missing, stubbed, or not built. If you need those numbers, call the tools.
- view_forecast is our 2026 eligible sign-up forecast. Call it for sign-up questions.
- For profit, cost, service rate, backlog, or “which country is best/worst,” call run_simulator. It scales demand and runs keep_current_staff. Compare the country summary rows the tool returns.
- For a hire/release staffing plan, call optimize_staffing. It solves for highest modeled profit (optional min_service_rate for SLA) under the current demand scale and compares to keep_current_staff.
- world_bank_gdp is a World Bank GDP growth projection. It is not our sign-up forecast. Call it only when it is listed under enabled extra tools.
"""


class AgentState(TypedDict):
    messages: Annotated[list[Any], add_messages]
    simulator: NotRequired[dict | None]
    staffing: NotRequired[dict | None]
    enabled_tools: NotRequired[list[str]]


def _system(state: AgentState) -> str:
    enabled = state.get("enabled_tools") or []
    extra = ", ".join(enabled) if enabled else "(none)"
    return (
        SYSTEM
        + "\nEnabled extra tools: "
        + extra
        + "\nCurrent simulator settings:\n"
        + json.dumps(state.get("simulator") or {})
        + "\nCurrent staffing settings:\n"
        + json.dumps(state.get("staffing") or {})
    )


def build_llm(choice: LLMChoice):
    """Build the chat model. The Gemini key is passed only to the client constructor."""
    if choice.provider == "google":
        if not choice.api_key or not choice.api_key.strip():
            raise ValueError("Paste a Gemini API key.")
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
        except ImportError as exc:
            raise RuntimeError("Install langchain-google-genai to use the Gemini provider.") from exc
        return ChatGoogleGenerativeAI(model=choice.model, google_api_key=choice.api_key.strip())
    kwargs = {"model_provider": choice.provider}
    if choice.api_key:
        kwargs["api_key"] = choice.api_key.strip()
    return init_chat_model(choice.model, **kwargs)


def _compile(model: Any, tools: list[Any]):
    bound = model.bind_tools(tools)

    def agent(state: AgentState) -> dict:
        response = bound.invoke([SystemMessage(content=_system(state)), *state["messages"]])
        return {"messages": [response]}

    graph = StateGraph(AgentState)
    graph.add_node("agent", agent)
    graph.add_node("tools", ToolNode(tools))
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", tools_condition)
    graph.add_edge("tools", "agent")
    return graph.compile(checkpointer=_CHECKPOINTER)


def _reply_text(messages: list[Any]) -> str:
    for message in reversed(messages):
        if isinstance(message, AIMessage) and not message.tool_calls:
            content = message.content
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                parts = []
                for block in content:
                    if isinstance(block, str):
                        parts.append(block)
                    elif isinstance(block, dict) and "text" in block:
                        parts.append(str(block["text"]))
                return "".join(parts)
            return str(content)
    return ""


def ask(request: TurnRequest | dict) -> TurnResult:
    """Answer one message. Follow-ups with the same thread_id keep the conversation.

    The request's simulator and staffing settings are the base for the turn.
    A tool call that omits a field keeps that base. The result reports the
    settings in effect after the turn, without the API key.
    """
    incoming = TurnRequest.model_validate(request)
    optional = tools_for(incoming.enabled_tools)
    model = build_llm(incoming.llm)
    graph = _compile(model, [*CORE_TOOLS, *optional])
    config = {"configurable": {"thread_id": incoming.thread_id}}
    graph.invoke(
        {
            "messages": [HumanMessage(content=incoming.message)],
            "simulator": incoming.simulator.model_dump(mode="json"),
            "staffing": incoming.staffing.model_dump(mode="json"),
            "enabled_tools": list(dict.fromkeys(incoming.enabled_tools)),
        },
        config,
    )
    state = graph.get_state(config).values
    enabled = list(dict.fromkeys(incoming.enabled_tools))
    return TurnResult(
        reply=_reply_text(state["messages"]),
        thread_id=incoming.thread_id,
        provider=incoming.llm.provider,
        model=incoming.llm.model,
        enabled_tools=enabled,
        simulator=SimulatorParams.model_validate(state.get("simulator") or {}),
        staffing=StaffingParams.model_validate(state.get("staffing") or {}),
    )
