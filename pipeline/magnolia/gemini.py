"""Minimal Gemini REST client that returns parsed JSON."""

from __future__ import annotations

import json
import time

import httpx

API = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

# Tried in order after the configured model fails with quota/unavailability.
FALLBACK_MODELS = (
    "gemini-3-flash-preview",
    "gemini-flash-lite-latest",
)


def _parse_error(resp: httpx.Response) -> str:
    try:
        return resp.json().get("error", {}).get("message", resp.text[:200])
    except Exception:
        return resp.text[:200]


def _call_once(api_key: str, model: str, prompt: str) -> dict | list:
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.7,
            "maxOutputTokens": 8192,
        },
    }
    resp = httpx.post(
        API.format(model=model),
        params={"key": api_key},
        json=body,
        timeout=120.0,
    )
    if resp.status_code != 200:
        raise httpx.HTTPStatusError(
            f"{resp.status_code} on {model}: {_parse_error(resp)}",
            request=resp.request,
            response=resp,
        )
    text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
    return json.loads(text)


def generate_json(api_key: str, model: str, prompt: str, retries: int = 1) -> dict | list:
    """Call Gemini, retrying rate limits and falling back across models."""
    models = [model, *[m for m in FALLBACK_MODELS if m != model]]
    last_error: Exception | None = None

    for candidate in models:
        for attempt in range(retries):
            try:
                if candidate != model:
                    print(f"  [gemini] trying fallback model: {candidate}")
                return _call_once(api_key, candidate, prompt)
            except httpx.HTTPStatusError as exc:
                last_error = exc
                status = exc.response.status_code
                msg = str(exc)
                # Model gone or blocked for this account — try the next model immediately.
                if status == 404:
                    print(f"  [gemini] {candidate} unavailable ({msg[:120]})")
                    break
                # Quota / overload — short wait, then try fallback.
                if status in (429, 503):
                    wait = 5 * (attempt + 1)
                    print(f"  [gemini] {candidate} {status}, waiting {wait}s…")
                    time.sleep(wait)
                    continue
                raise RuntimeError(f"Gemini error on {candidate}: {msg}") from exc
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                time.sleep(5 * (attempt + 1))

    raise RuntimeError(
        f"Gemini call failed after trying {', '.join(models)}: {last_error}\n"
        "If you see quota errors, wait a few minutes or set GEMINI_MODEL=gemini-3-flash-preview "
        "in pipeline/.env (free tier often has separate limits per model)."
    )
