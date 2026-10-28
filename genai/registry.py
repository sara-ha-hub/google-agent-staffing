"""Optional data tools. A new source is one register_data_tool call."""

from typing import Any

_TOOLS: dict[str, dict[str, Any]] = {}


def register_data_tool(name: str, description: str, tool: Any) -> None:
    _TOOLS[name] = {"name": name, "description": description, "tool": tool}


def _load() -> None:
    import genai.tools  # noqa: F401  registers the tools


def list_data_tools() -> list[dict[str, str]]:
    """Names and descriptions for a tool checkbox list."""
    _load()
    return [{"name": item["name"], "description": item["description"]} for item in _TOOLS.values()]


def tools_for(enabled: list[str]) -> list[Any]:
    """Return the tool objects the user turned on, in that order."""
    _load()
    unknown = [name for name in enabled if name not in _TOOLS]
    if unknown:
        known = ", ".join(_TOOLS) or "(none)"
        raise ValueError(f"Unknown data tool(s): {', '.join(unknown)}. Known tools: {known}")
    selected = []
    seen: set[str] = set()
    for name in enabled:
        if name in seen:
            continue
        seen.add(name)
        selected.append(_TOOLS[name]["tool"])
    return selected
