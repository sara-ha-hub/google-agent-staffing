"""The staffing backend sends a supplied Gemini key to the Gemini API.

These tests use the real LangChain and google-genai clients. The HTTP call is
caught at the client boundary so the suite does not need a live key. Set
GEMINI_API_KEY to also call Gemini itself.
"""

import os
import unittest
import uuid
from contextlib import contextmanager
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient

from frontend.server import app
from genai.graph import ask

GEMINI_HOST = "generativelanguage.googleapis.com"
MODEL = "gemini-3.5-flash-lite"
REPLY = "Argentina in January 2026 has 70.8 eligible sign-ups."
GEMINI_BODY = {
    "candidates": [
        {
            "content": {"role": "model", "parts": [{"text": REPLY}]},
            "finishReason": "STOP",
        }
    ]
}


@contextmanager
def intercept_gemini():
    """Record calls to the Gemini host and return one generateContent reply."""
    calls = []
    original = httpx.Client.send

    def send(self, request, *args, **kwargs):
        if request.url.host == GEMINI_HOST:
            calls.append(request)
            return httpx.Response(200, json=GEMINI_BODY, request=request)
        return original(self, request, *args, **kwargs)

    with patch("httpx.Client.send", send):
        yield calls


def _request(api_key: str) -> dict:
    return {
        "message": "What is the January forecast for Argentina?",
        "thread_id": f"gemini-{uuid.uuid4()}",
        "llm": {"provider": "google", "model": MODEL, "api_key": api_key},
    }


class GeminiConnectionTests(unittest.TestCase):
    def test_missing_key_does_not_call_gemini(self):
        with intercept_gemini() as calls:
            with self.assertRaisesRegex(ValueError, "Paste a Gemini API key."):
                ask(_request("   "))
        self.assertEqual(calls, [])

    def test_ask_posts_the_supplied_key_to_gemini(self):
        api_key = "  test-gemini-key-do-not-leak  "
        with intercept_gemini() as calls:
            result = ask(_request(api_key))

        self.assertEqual(len(calls), 1)
        request = calls[0]
        self.assertEqual(request.method, "POST")
        self.assertEqual(request.url.host, GEMINI_HOST)
        self.assertIn(MODEL, request.url.path)
        self.assertIn("generateContent", request.url.path)
        self.assertEqual(request.headers["x-goog-api-key"], api_key.strip())
        body = request.content.decode()
        self.assertIn("What is the January forecast for Argentina?", body)
        self.assertNotIn(api_key, body)

        self.assertEqual(result.reply, REPLY)
        self.assertEqual(result.provider, "google")
        self.assertEqual(result.model, MODEL)
        dumped = result.model_dump_json()
        self.assertNotIn("api_key", dumped)
        self.assertNotIn(api_key.strip(), dumped)

    def test_chat_endpoint_forwards_the_key_to_gemini(self):
        api_key = "endpoint-gemini-key-do-not-leak"
        with intercept_gemini() as calls:
            response = TestClient(app).post("/api/chat", json=_request(api_key))

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0].headers["x-goog-api-key"], api_key)
        payload = response.json()
        self.assertEqual(payload["reply"], REPLY)
        self.assertNotIn("api_key", payload)
        self.assertNotIn(api_key, response.text)


@unittest.skipUnless(
    os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"),
    "Set GEMINI_API_KEY to call the live Gemini API.",
)
class LiveGeminiConnectionTests(unittest.TestCase):
    def test_live_key_receives_a_gemini_reply(self):
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ["GOOGLE_API_KEY"]
        result = ask(
            {
                "message": "Reply with the single word connected.",
                "thread_id": f"live-gemini-{uuid.uuid4()}",
                "llm": {"provider": "google", "model": MODEL, "api_key": api_key},
            }
        )
        self.assertIn("connected", result.reply.casefold())
        self.assertNotIn(api_key, result.model_dump_json())


if __name__ == "__main__":
    unittest.main()
