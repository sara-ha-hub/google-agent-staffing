"""Serves the staffing screen and forwards each turn to genai.ask.

The API key stays in the request body and is removed from any error text.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import ValidationError

from genai.forecast_view import known_countries
from genai.graph import ask
from genai.registry import list_data_tools

app = FastAPI(title="Agent staffing")
PAGE = Path(__file__).with_name("index.html")


def _scrub(exc: BaseException, api_key: str) -> str:
    text = str(exc)
    if api_key:
        text = text.replace(api_key, "[api key]")
    return text


@app.get("/")
def index() -> FileResponse:
    return FileResponse(PAGE)


@app.get("/api/tools")
def tools() -> list[dict[str, str]]:
    return list_data_tools()


@app.get("/api/countries")
def countries() -> list[str]:
    return known_countries()


@app.post("/api/chat")
async def chat(request: Request) -> dict:
    body = await request.json()
    api_key = ""
    llm = body.get("llm") if isinstance(body, dict) else None
    if isinstance(llm, dict) and isinstance(llm.get("api_key"), str):
        api_key = llm["api_key"]
    try:
        result = ask(body)
    except (ValidationError, ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=_scrub(exc, api_key)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=_scrub(exc, api_key)) from exc
    return result.model_dump(mode="json")


def main() -> None:
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8765)


if __name__ == "__main__":
    main()
