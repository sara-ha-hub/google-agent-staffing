"""LangGraph layer for the 2026 staffing conversation.

Call ask() with a TurnRequest. Optional data tools are listed by list_data_tools().
"""

from genai.graph import ask
from genai.registry import list_data_tools

__all__ = ["ask", "list_data_tools"]
