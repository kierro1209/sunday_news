"""Fetch candidate items from free, real sources.

Every fetcher returns a list of dicts with keys:
  title, url, source, published, snippet
Fetchers swallow their own errors and return [] so one dead feed
never blocks the paper.
"""

from __future__ import annotations

import html
import re
from typing import Callable

import feedparser
import httpx

UA = {"User-Agent": "MagnoliaTimes/1.0 (personal newsletter pipeline)"}
TIMEOUT = 20.0


def _clean(text: str, limit: int = 400) -> str:
    text = re.sub(r"<[^>]+>", " ", html.unescape(text or ""))
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


def _from_feed(url: str, source: str, limit: int) -> list[dict]:
    parsed = feedparser.parse(url, request_headers=UA)
    items = []
    for entry in parsed.entries[:limit]:
        items.append(
            {
                "title": _clean(entry.get("title", ""), 200),
                "url": entry.get("link", ""),
                "source": source,
                "published": entry.get("published", entry.get("updated", "")),
                "snippet": _clean(entry.get("summary", "")),
            }
        )
    return items


def _safe(fetch: Callable[[], list[dict]], label: str) -> list[dict]:
    try:
        items = fetch()
        print(f"  [sources] {label}: {len(items)} items")
        return items
    except Exception as exc:  # noqa: BLE001 - a dead feed must not kill the run
        print(f"  [sources] {label} FAILED: {exc}")
        return []


# --- ML / AI / data engineering -------------------------------------------

def fetch_arxiv(categories: str, limit: int = 15) -> list[dict]:
    url = (
        "https://export.arxiv.org/api/query"
        f"?search_query={categories}&sortBy=submittedDate&sortOrder=descending"
        f"&max_results={limit}"
    )
    return _from_feed(url, "arXiv", limit)


def fetch_hn_ml(limit: int = 20) -> list[dict]:
    query = (
        "https://hn.algolia.com/api/v1/search?query=machine%20learning%20OR%20LLM"
        "&tags=story&numericFilters=points%3E80&hitsPerPage=" + str(limit)
    )
    resp = httpx.get(query, headers=UA, timeout=TIMEOUT)
    resp.raise_for_status()
    return [
        {
            "title": _clean(hit.get("title", ""), 200),
            "url": hit.get("url") or f"https://news.ycombinator.com/item?id={hit['objectID']}",
            "source": "Hacker News",
            "published": hit.get("created_at", ""),
            "snippet": f"{hit.get('points', 0)} points on HN",
        }
        for hit in resp.json().get("hits", [])
    ]


# --- Finance ----------------------------------------------------------------

STOOQ_SYMBOLS = {
    "^spx": "S&P 500",
    "^ndq": "Nasdaq Composite",
    "^dji": "Dow Jones Industrial Average",
}


def fetch_market_snapshot() -> str:
    """Return a plain-text snapshot of major indices from stooq (free, no key)."""
    lines = []
    for symbol, name in STOOQ_SYMBOLS.items():
        try:
            resp = httpx.get(
                f"https://stooq.com/q/d/l/?s={symbol}&i=d", headers=UA, timeout=TIMEOUT
            )
            resp.raise_for_status()
            rows = [r.split(",") for r in resp.text.strip().splitlines()[1:]]
            if len(rows) < 2:
                continue
            prev_close, close = float(rows[-2][4]), float(rows[-1][4])
            pct = (close - prev_close) / prev_close * 100
            lines.append(f"{name}: {close:,.2f} ({pct:+.2f}% on {rows[-1][0]})")
        except Exception as exc:  # noqa: BLE001
            print(f"  [sources] stooq {symbol} FAILED: {exc}")
    return "\n".join(lines)


# --- Aggregate pull ----------------------------------------------------------

def gather_daily_candidates() -> dict[str, list[dict]]:
    """Pull all candidate pools for a daily edition, keyed by section id."""
    gnews = "https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"
    return {
        "ml_deep_dive": (
            _safe(lambda: fetch_arxiv("cat:cs.LG+OR+cat:cs.AI+OR+cat:cs.DC"), "arxiv-ml")
            + _safe(fetch_hn_ml, "hn-ml")
        ),
        "startup_biotech": (
            _safe(lambda: _from_feed("https://techcrunch.com/category/startups/feed/", "TechCrunch", 12), "techcrunch")
            + _safe(lambda: _from_feed("https://www.fiercebiotech.com/rss/xml", "Fierce Biotech", 12), "fiercebiotech")
            + _safe(lambda: _from_feed(gnews.format(q="biotech+startup+funding"), "Google News", 10), "gnews-biotech")
        ),
        "biology": (
            _safe(lambda: fetch_arxiv("cat:q-bio.BM+OR+cat:q-bio.MN+OR+cat:q-bio.GN", 12), "arxiv-qbio")
            + _safe(lambda: _from_feed("https://www.sciencedaily.com/rss/top/health.xml", "ScienceDaily", 10), "sciencedaily")
        ),
        "headlines": (
            _safe(lambda: _from_feed(gnews.format(q="San+Francisco"), "Google News SF", 10), "gnews-sf")
            + _safe(lambda: _from_feed(gnews.format(q="Los+Angeles"), "Google News LA", 10), "gnews-la")
        ),
        "spanish": (
            _safe(lambda: _from_feed("https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada", "El País", 12), "elpais")
            + _safe(lambda: _from_feed("https://www.bbc.com/mundo/index.xml", "BBC Mundo", 12), "bbc-mundo")
        ),
    }


def gather_weekly_candidates() -> dict[str, list[dict]]:
    return {
        "weekly_ai_paper": (
            _safe(lambda: fetch_arxiv("cat:cs.LG+OR+cat:cs.AI", 25), "arxiv-weekly")
            + _safe(fetch_hn_ml, "hn-weekly")
        ),
        "weekly_spanish": _safe(
            lambda: _from_feed("https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada", "El País", 15),
            "elpais-weekly",
        ),
    }
