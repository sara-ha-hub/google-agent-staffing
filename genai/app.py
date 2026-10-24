"""Streamlit screen for the 2026 forecast assistant.

Run from the repository root:

    streamlit run genai/app.py
"""

import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

from genai.forecast_view import known_countries
from genai.graph import ask
from genai.registry import list_data_tools

PROVIDERS = {
    "google": "Google Gemini",
    "openai": "OpenAI",
    "other": "Other",
}


def _sync_model() -> None:
    provider = st.session_state.provider
    model = st.session_state.get("model", "")
    if provider == "openai" and model.startswith("gemini"):
        st.session_state.model = "gpt-4.1-mini"
    elif provider == "google" and model.startswith("gpt"):
        st.session_state.model = "gemini-3.5-flash-lite"


def _apply_pending() -> None:
    pending = st.session_state.pop("pending_settings", None)
    if not pending:
        return
    for key, value in pending.items():
        st.session_state[key] = value


def _init() -> None:
    st.session_state.setdefault("thread_id", str(uuid.uuid4()))
    st.session_state.setdefault("messages", [])
    st.session_state.setdefault("provider", "google")
    st.session_state.setdefault("other_provider", "")
    st.session_state.setdefault("model", "gemini-3.5-flash-lite")
    st.session_state.setdefault("api_key", "")
    st.session_state.setdefault("demand_scale", 1.0)
    st.session_state.setdefault("sim_countries", [])
    st.session_state.setdefault("staff_countries", [])
    st.session_state.setdefault("min_agents", "")
    st.session_state.setdefault("max_agents", "")
    _apply_pending()


def _new_conversation() -> None:
    st.session_state.thread_id = str(uuid.uuid4())
    st.session_state.messages = []


def _optional_number(raw: str, label: str, whole: bool) -> int | float | None:
    text = raw.strip()
    if not text:
        return None
    try:
        return int(text) if whole else float(text)
    except ValueError as exc:
        raise ValueError(f"{label} must be a number.") from exc


def _scrub(exc: BaseException, api_key: str) -> str:
    text = str(exc)
    cleaned = api_key.strip()
    if cleaned:
        text = text.replace(cleaned, "[api key]")
    return text


def _settings_note(result) -> str:
    countries = result.simulator.countries
    where = ", ".join(countries) if countries else "every country"
    tools = ", ".join(result.enabled_tools) if result.enabled_tools else "no extra tools"
    return f"Demand scale {result.simulator.demand_scale} for {where}. {tools}. Model {result.model}."


def _pending_from_result(result) -> dict:
    pending = {
        "model": result.model,
        "demand_scale": result.simulator.demand_scale,
        "sim_countries": list(result.simulator.countries or []),
        "staff_countries": list(result.staffing.countries or []),
        "min_agents": "" if result.staffing.min_agents is None else str(result.staffing.min_agents),
        "max_agents": (
            ""
            if result.staffing.max_agents_vs_current is None
            else str(result.staffing.max_agents_vs_current)
        ),
    }
    if result.provider in PROVIDERS and result.provider != "other":
        pending["provider"] = result.provider
    else:
        pending["provider"] = "other"
        pending["other_provider"] = result.provider
    return pending


def _turn(message: str) -> dict:
    provider = st.session_state.provider
    if provider == "other":
        provider = st.session_state.other_provider.strip()
    api_key = st.session_state.api_key
    enabled = [
        tool["name"]
        for tool in list_data_tools()
        if st.session_state.get(f"tool_{tool['name']}")
    ]
    staffing = {
        "countries": st.session_state.staff_countries or None,
        "objective": "max_profit",
        "baseline": "keep_current_staff",
    }
    min_agents = _optional_number(st.session_state.min_agents, "Minimum agents", whole=True)
    max_agents = _optional_number(
        st.session_state.max_agents,
        "Maximum multiple of current staff",
        whole=False,
    )
    if min_agents is not None:
        staffing["min_agents"] = min_agents
    if max_agents is not None:
        staffing["max_agents_vs_current"] = max_agents
    try:
        result = ask(
            {
                "message": message,
                "thread_id": st.session_state.thread_id,
                "llm": {
                    "provider": provider,
                    "model": st.session_state.model.strip(),
                    "api_key": api_key,
                },
                "enabled_tools": enabled,
                "simulator": {
                    "demand_scale": st.session_state.demand_scale,
                    "countries": st.session_state.sim_countries or None,
                },
                "staffing": staffing,
            }
        )
    except Exception as exc:
        return {"role": "assistant", "content": _scrub(exc, api_key), "error": True}
    return {
        "role": "assistant",
        "content": result.reply or "No reply.",
        "meta": _settings_note(result),
        "pending": _pending_from_result(result),
    }


def _draw_message(message: dict) -> None:
    with st.chat_message(message["role"]):
        if message.get("error"):
            st.error(message["content"])
        else:
            st.markdown(message["content"])
        if message.get("meta"):
            st.caption(message["meta"])


def _options() -> None:
    with st.sidebar:
        st.header("Options")
        st.selectbox(
            "Provider",
            list(PROVIDERS),
            format_func=lambda key: PROVIDERS[key],
            key="provider",
            on_change=_sync_model,
        )
        if st.session_state.provider == "other":
            st.text_input("Provider id", key="other_provider", placeholder="anthropic")
        st.text_input("Model", key="model")
        st.text_input("API key", type="password", key="api_key", placeholder="Paste your key")
        st.caption("The key stays in this session and is not written to a file.")

        st.subheader("Extra tools")
        for tool in list_data_tools():
            st.checkbox(tool["description"], key=f"tool_{tool['name']}")

        st.subheader("Simulator")
        st.number_input("Demand scale", min_value=0.1, step=0.1, key="demand_scale")
        st.caption("1 keeps the forecast. 0.8 is lower sign-ups. 1.2 is higher sign-ups.")
        st.multiselect(
            "Countries",
            known_countries(),
            key="sim_countries",
            placeholder="Every country",
        )

        st.subheader("Staffing plan")
        st.caption("The plan has to beat keeping January 2026 headcount all year.")
        st.multiselect(
            "Countries to restaff",
            known_countries(),
            key="staff_countries",
            placeholder="Keep current staff",
        )
        st.text_input("Minimum agents", key="min_agents", placeholder="No minimum")
        st.text_input(
            "Maximum multiple of current staff",
            key="max_agents",
            placeholder="No maximum",
        )
        st.button("New conversation", on_click=_new_conversation)


def main() -> None:
    st.set_page_config(page_title="2026 forecast assistant", layout="centered")
    _init()
    _options()
    st.title("2026 forecast assistant")
    st.caption("Ask about eligible sign-ups by country and month.")
    if not st.session_state.messages:
        st.info("Ask the assistant about a country, a month, or a change in sign-ups.")
    for message in st.session_state.messages:
        _draw_message(message)
    prompt = st.chat_input("What is the January forecast for Argentina?")
    if not prompt:
        return
    user = {"role": "user", "content": prompt}
    st.session_state.messages.append(user)
    _draw_message(user)
    with st.spinner("Checking the forecast..."):
        reply = _turn(prompt)
    pending = reply.pop("pending", None)
    st.session_state.messages.append(reply)
    if pending:
        st.session_state.pending_settings = pending
    st.rerun()


main()
