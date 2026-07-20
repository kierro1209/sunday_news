"""The editor agent: turns candidate pools + reader context into an edition."""

from __future__ import annotations

import datetime as dt
import json
import uuid

from .config import Config
from .gemini import generate_json
from .sources import fetch_market_snapshot, gather_daily_candidates, gather_weekly_candidates

MOTTO = "All the signal that's fit to print"

ARTICLE_SHAPE = """Each article object must have exactly these keys:
- "headline": punchy newspaper headline
- "byline": source attribution, e.g. "arXiv · Chen et al." or "El País"
- "url": the real source url from the candidate list ("" only if the piece is generated, like a lesson or journal prompt)
- "summary": 1-2 sentence dek under the headline
- "body": the main piece in markdown (use short paragraphs; bold key terms)
- "difficulty": one of "intro", "intermediate", "advanced", or ""
- "tags": 2-4 lowercase topic tags
- "why_chosen": one sentence on why this was picked for this reader"""


def _candidates_block(items: list[dict], cap: int = 25) -> str:
    lines = []
    for i, item in enumerate(items[:cap]):
        lines.append(
            f"{i + 1}. [{item['source']}] {item['title']} — {item['snippet'][:200]} "
            f"(url: {item['url']}, published: {item['published']})"
        )
    return "\n".join(lines) if lines else "(no candidates fetched — generate from your own knowledge, url=\"\")"


def _reader_context(prefs: dict, feedback: list[dict]) -> str:
    fb_lines = [
        f"- [{'+1' if f['rating'] > 0 else '-1'}] \"{f['headline']}\" ({f['section_id']})"
        + (f" — reader said: {f['comment']}" if f.get("comment") else "")
        for f in feedback[:40]
    ]
    return f"""READER PROFILE
Data engineer building depth in ML/AI infrastructure; interested in biotech/pharma and
startups; learning Spanish (intermediate) and basic investing; lives between SF and LA.
Stated preferences (JSON): {json.dumps(prefs) if prefs else "(none yet)"}

RECENT FEEDBACK on past articles (steer toward +1 patterns, away from -1 patterns):
{chr(10).join(fb_lines) if fb_lines else "(none yet)"}"""


def _section_prompt(
    reader_context: str,
    date_str: str,
    kicker_instructions: str,
    candidates: str,
    n_articles: str,
) -> str:
    return f"""You are the editor of "The Magnolia Times", a personal newspaper, edition dated {date_str}.

{reader_context}

YOUR TASK
{kicker_instructions}

CANDIDATE SOURCES (pick real items from here whenever the task calls for real sources; never invent urls):
{candidates}

Return a JSON array of {n_articles} article object(s). {ARTICLE_SHAPE}"""


DAILY_SECTIONS: list[dict] = [
    {
        "id": "ml_deep_dive",
        "heading": "Machine Intelligence",
        "kicker": "Today's deep dive",
        "n": "1",
        "task": (
            "Pick ONE paper, blog post, or article on ML, AI, or data engineering. "
            "Favor recent innovations. Vary difficulty day to day (check the feedback for "
            "what landed). In the body, write a 300-450 word guided read: what it is, why it "
            "matters, the key technique explained plainly, and what a data/infra engineer "
            "should take away."
        ),
    },
    {
        "id": "startup_biotech",
        "heading": "Ventures & Vials",
        "kicker": "Startups and biotech",
        "n": "2 to 3",
        "task": (
            "Pick 2-3 startup and biotech stories (at least one biotech). For each, the body "
            "(150-250 words) must explain the TECHNICAL REASONING behind the move: the science, "
            "the platform bet, the market mechanics — not just what happened."
        ),
    },
    {
        "id": "biology",
        "heading": "The Bench",
        "kicker": "Biology for pharma intuition",
        "n": "1",
        "task": (
            "Pick ONE biological research paper or topic and turn it into a 250-400 word lesson "
            "that builds pharma intuition. Teach the underlying biology (mechanism, pathway, "
            "modality) at a level a strong engineer without a bio background can absorb. Define "
            "jargon inline."
        ),
    },
    {
        "id": "headlines",
        "heading": "The Wire",
        "kicker": "San Francisco & Los Angeles",
        "n": "4 to 6",
        "task": (
            "Pick 4-6 genuinely newsworthy SF and LA headlines (mix both cities). Body is a "
            "2-3 sentence brief. Skip celebrity fluff."
        ),
    },
    {
        "id": "finance",
        "heading": "Ledger & Tape",
        "kicker": "Markets and money",
        "n": "2",
        "task": (
            "Produce exactly 2 articles. (1) A finance-concept lesson (250-350 words) teaching one "
            "concept a beginner investor should learn — treat past feedback as a record of concepts "
            "already covered and progress logically (e.g. index funds -> expense ratios -> "
            "diversification -> valuation basics). url=\"\". (2) A market overview using the REAL "
            "index data provided in the candidates block; explain plainly what moved and one "
            "plausible driver. url=\"\"."
        ),
    },
    {
        "id": "spanish",
        "heading": "La Sección en Español",
        "kicker": "Para aprender",
        "n": "1",
        "task": (
            "Pick ONE Spanish-language article suited to an intermediate (B1) learner. In the body: "
            "first a 200-300 word retelling of the story IN SPANISH at B1 level (simplify from the "
            "source; keep it natural), then a \"**Vocabulario**\" list of 8-10 words with English "
            "translations, then \"**Preguntas**\" with 2 comprehension questions in Spanish."
        ),
    },
    {
        "id": "journal",
        "heading": "The Examined Life",
        "kicker": "Journal prompt",
        "n": "1",
        "task": (
            "Write ONE short journal prompt (2-4 sentences) about introspection and ambition. "
            "Make it specific and answerable in ten minutes, not generic. Vary the angle from "
            "recent days (see feedback). url=\"\", byline=\"The Editors\"."
        ),
    },
]

WEEKLY_SECTIONS: list[dict] = [
    {
        "id": "weekly_ai_paper",
        "heading": "The Sunday Paper",
        "kicker": "This week's AI research",
        "n": "1",
        "task": (
            "Pick ONE substantial, recent AI research paper worth an hour of study. Body is a "
            "600-900 word guided read: context, the core method with intuition, results and "
            "caveats, and how it connects to production ML/data infrastructure."
        ),
    },
    {
        "id": "weekly_finance",
        "heading": "The Week on the Tape",
        "kicker": "Finance debrief",
        "n": "1",
        "task": (
            "Write a 500-700 word weekly finance debrief using the REAL index data in the "
            "candidates block: what the week looked like, one concept explored in depth, and one "
            "thing to watch next week. Educational, not advice. url=\"\"."
        ),
    },
    {
        "id": "weekly_spanish",
        "heading": "Lectura del Domingo",
        "kicker": "Español extendido",
        "n": "1",
        "task": (
            "Pick ONE meaty Spanish article. Body: a 400-550 word B1-B2 retelling in Spanish, "
            "a \"**Vocabulario**\" list of 12-15 words with translations, and 3 comprehension "
            "questions plus 1 short writing prompt in Spanish."
        ),
    },
    {
        "id": "weekly_journal",
        "heading": "The Examined Life, Extended",
        "kicker": "Sunday journal",
        "n": "1",
        "task": (
            "Write ONE longer Sunday journal prompt (a short framing paragraph plus 3-4 linked "
            "questions) reviewing the week and pointing at ambition for the next. "
            "url=\"\", byline=\"The Editors\"."
        ),
    },
]


def _build_sections(
    cfg: Config,
    spec: list[dict],
    candidates: dict[str, list[dict]],
    reader_ctx: str,
    date_str: str,
    market_snapshot: str,
) -> list[dict]:
    sections = []
    for section in spec:
        pool = candidates.get(section["id"], [])
        block = _candidates_block(pool)
        if section["id"] in ("finance", "weekly_finance"):
            block = f"REAL MARKET DATA (latest closes):\n{market_snapshot or '(unavailable)'}\n\n{block}"
        prompt = _section_prompt(reader_ctx, date_str, section["task"], block, section["n"])
        try:
            articles = generate_json(cfg.gemini_api_key, cfg.gemini_model, prompt)
            if isinstance(articles, dict):
                articles = [articles]
            for article in articles:
                article["id"] = uuid.uuid4().hex[:8]
                article.setdefault("url", "")
                article.setdefault("difficulty", "")
                article.setdefault("tags", [])
                article.setdefault("why_chosen", "")
            sections.append(
                {
                    "id": section["id"],
                    "heading": section["heading"],
                    "kicker": section["kicker"],
                    "articles": articles,
                }
            )
            print(f"  [editor] {section['id']}: {len(articles)} article(s)")
        except Exception as exc:  # noqa: BLE001 - drop the section, keep the paper
            print(f"  [editor] {section['id']} FAILED, dropping section: {exc}")
    return sections


def build_edition(cfg: Config, kind: str, prefs: dict, feedback: list[dict]) -> dict:
    today = dt.date.today()
    date_str = today.isoformat()
    reader_ctx = _reader_context(prefs, feedback)
    market = fetch_market_snapshot()

    if kind == "daily":
        spec, candidates = DAILY_SECTIONS, gather_daily_candidates()
    else:
        spec, candidates = WEEKLY_SECTIONS, gather_weekly_candidates()

    sections = _build_sections(cfg, spec, candidates, reader_ctx, date_str, market)
    if not sections:
        raise RuntimeError("Every section failed; refusing to save an empty edition")

    day_of_year = today.timetuple().tm_yday
    return {
        "kind": kind,
        "date": date_str,
        "volume": f"Vol. {today.year - 2025}, No. {day_of_year}",
        "motto": MOTTO,
        "sections": sections,
    }
