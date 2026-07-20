"""Minimal Gemini REST client that returns parsed JSON."""

from __future__ import annotations

import json
import time

import httpx

API = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def generate_json(api_key: str, model: str, prompt: str, retries: int = 3) -> dict | list:
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.7,
            "maxOutputTokens": 8192,
        },
    }
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            resp = httpx.post(
                API.format(model=model),
                params={"key": api_key},
                json=body,
                timeout=120.0,
            )
            if resp.status_code == 429:
                time.sleep(20 * (attempt + 1))
                continue
            resp.raise_for_status()
            text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
            return json.loads(text)
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"Gemini call failed after {retries} attempts: {last_error}")
