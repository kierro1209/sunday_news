"""Supabase access via PostgREST using the service-role key."""

from __future__ import annotations

import httpx

from .config import Config


def _headers(cfg: Config) -> dict:
    # PostgREST needs both: apikey identifies the project, Authorization carries
    # the JWT that determines the role for RLS. Service-role key doubles as both.
    return {
        "apikey": cfg.supabase_service_role_key,
        "Authorization": f"Bearer {cfg.supabase_service_role_key}",
        "Content-Type": "application/json",
    }


def _raise_with_body(resp: httpx.Response) -> None:
    """PostgREST/GoTrue put the actual reason in the JSON body (e.g. "JWT
    expired", "Invalid API key", "role ... does not exist") — surface it
    instead of just the generic '401 Unauthorized'."""
    if resp.is_success:
        return
    try:
        detail = resp.json()
    except Exception:
        detail = resp.text[:300]
    print(f"[store] {resp.status_code} from {resp.request.method} {resp.request.url.path}: {detail}")
    resp.raise_for_status()


def save_edition(cfg: Config, edition: dict) -> str:
    """Upsert the edition (idempotent re-runs) and return its id."""
    resp = httpx.post(
        f"{cfg.supabase_url}/rest/v1/editions",
        headers={
            **_headers(cfg),
            "Prefer": "resolution=merge-duplicates,return=representation",
        },
        params={"on_conflict": "kind,edition_date"},
        json={
            "kind": edition["kind"],
            "edition_date": edition["date"],
            "content": edition,
        },
        timeout=30.0,
    )
    _raise_with_body(resp)
    return resp.json()[0]["id"]


def load_preferences(cfg: Config) -> dict:
    """Single-reader paper: merge all preference rows (normally one)."""
    resp = httpx.get(
        f"{cfg.supabase_url}/rest/v1/preferences",
        headers=_headers(cfg),
        params={"select": "prefs"},
        timeout=30.0,
    )
    _raise_with_body(resp)
    merged: dict = {}
    for row in resp.json():
        merged.update(row.get("prefs") or {})
    return merged


def load_recent_history(cfg: Config, editions: int = 16) -> list[dict]:
    """Flatten recent editions into one row per published article, for the
    editor-in-chief's anti-repetition context."""
    resp = httpx.get(
        f"{cfg.supabase_url}/rest/v1/editions",
        headers=_headers(cfg),
        params={
            "select": "kind,edition_date,content",
            "order": "edition_date.desc",
            "limit": str(editions),
        },
        timeout=30.0,
    )
    _raise_with_body(resp)
    history = []
    for row in resp.json():
        for section in (row.get("content") or {}).get("sections", []):
            for article in section.get("articles", []):
                history.append(
                    {
                        "date": row["edition_date"],
                        "kind": row["kind"],
                        "section_id": section.get("id", ""),
                        "headline": article.get("headline", ""),
                        "url": article.get("url", ""),
                        "tags": article.get("tags", []),
                        "difficulty": article.get("difficulty", ""),
                    }
                )
    return history


def load_recent_feedback(cfg: Config, limit: int = 40) -> list[dict]:
    resp = httpx.get(
        f"{cfg.supabase_url}/rest/v1/feedback",
        headers=_headers(cfg),
        params={
            "select": "section_id,headline,rating,comment,created_at",
            "order": "created_at.desc",
            "limit": str(limit),
        },
        timeout=30.0,
    )
    _raise_with_body(resp)
    return resp.json()
