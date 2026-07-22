"""Two-stage editorial desk.

Stage 1 (editor-in-chief): one Gemini call that sees every candidate pool, the
reader profile, feedback, and what already ran in past editions. It assigns
exactly ONE story per section, a target difficulty, and a directive — balancing
novelty against repetition and saving heavier picks for the Sunday weekly.

Stage 2 (section writers): one Gemini call per section writes the single
assigned article. If the chief call fails, writers fall back to choosing from
their own candidate pool so the paper still ships.
"""

from __future__ import annotations

import datetime as dt
import json
import uuid

from .config import Config
from .gemini import generate_json
from .sources import (
    fetch_article_text,
    fetch_market_snapshot,
    gather_daily_candidates,
    gather_weekly_candidates,
)

MOTTO = "All the signal that's fit to print"
CANDIDATE_CAP = 20

ARTICLE_SHAPE = """The article object must have exactly these keys:
- "headline": punchy newspaper headline
- "byline": short printed attribution, e.g. "Chen et al. \u00b7 arXiv" or "The Editors"
- "authors": array of {"name": "...", "url": "..."} objects. Use ONLY author names and
  profile urls that appear in the source data; url "" if unknown. [] for in-house pieces.
  NEVER invent a profile url.
- "publication": the venue/outlet name (e.g. "arXiv", "El Pa\u00eds", "TechCrunch");
  "The Magnolia Times" for in-house pieces
- "published": the publication date string exactly as given in the source data ("" if in-house)
- "url": the real source url from the source data ("" for in-house pieces); never invent urls
- "summary": 1-2 sentence dek under the headline
- "body": the piece in markdown (short paragraphs; bold key terms; [text](url) links allowed).
  When the assignment below asks for a two-part structure, keep the two parts clearly separate
  under their own markdown headings — never blend your own analysis into the factual recap part.
- "difficulty": one of "intro", "intermediate", "advanced", or ""
- "tags": 2-4 lowercase topic tags
- "why_chosen": one sentence on why this was picked for this reader today"""

SOURCE_REPORTING_RULES = """SOURCE REPORTING RULES for externally sourced pieces:
- Report only claims supported by FULL ARTICLE TEXT (or by the snippet when full text is unavailable).
- Preserve names, numbers, dates, qualifications, uncertainty, and chronology accurately.
- Do not add facts, opinions, motives, or causal claims to the source-reporting portion.
- Do not reproduce the entire source article verbatim. Write a close, faithful recap in your
  own words; a short quotation is allowed only when the exact wording is materially important.
- Put all interpretation and reader-specific context at the very bottom under the exact
  markdown heading "**Relevance / Importance**". Never blend it into the factual recap."""


# --- prompt building blocks --------------------------------------------------

def _candidate_line(num: int, item: dict) -> str:
    authors = ", ".join(
        a["name"] + (f" ({a['url']})" if a.get("url") else "")
        for a in item.get("authors", [])
    )
    return (
        f"{num}. [{item['source']}] {item['title']}\n"
        f"   snippet: {item['snippet'][:200]}\n"
        f"   url: {item['url']}\n"
        f"   authors: {authors or 'unknown'} | published: {item['published'] or 'unknown'}"
    )


def _candidates_block(items: list[dict]) -> str:
    lines = [_candidate_line(i + 1, item) for i, item in enumerate(items)]
    return "\n".join(lines) if lines else "(no candidates fetched)"


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


def _history_block(history: list[dict], section_ids: set[str] | None = None, cap: int = 50) -> str:
    rows = [h for h in history if section_ids is None or h["section_id"] in section_ids]
    if not rows:
        return "(nothing has run yet)"
    lines = []
    for h in rows[:cap]:
        line = f"- {h['date']} [{h['section_id']}] \"{h['headline']}\""
        if h.get("difficulty"):
            line += f" (difficulty: {h['difficulty']})"
        if h.get("tags"):
            line += f" tags: {', '.join(h['tags'])}"
        lines.append(line)
    return "\n".join(lines)


# --- section specs ------------------------------------------------------------
# mode: "pick"     — chief assigns one candidate from the pool
#       "pool"     — writer sees the whole pool (digest-style sections)
#       "generate" — written in-house, no external candidates

DAILY_SECTIONS: list[dict] = [
    {
        "id": "ml_deep_dive",
        "heading": "Machine Intelligence",
        "kicker": "Today's deep dive",
        "mode": "pick",
        "brief": "One ML/AI/data-engineering paper, blog post, or article. Favor recent innovations; rotate difficulty across days.",
        "task": (
            "Write a two-part guided read of the assigned item. First, under a \"**The "
            "Source**\" heading, faithfully and thoroughly recap what the article/paper "
            "actually says — the problem, method, and results — drawing ONLY from the "
            "article text in MATERIAL below, in 350-500 words. Then, at the bottom under "
            "\"**Relevance / Importance**\", add your own explanation of the key technique in plain "
            "terms and what a data/infra engineer should take away, in 100-200 words. Keep "
            "the two parts clearly separate — no outside claims or speculation in the first."
        ),
    },
    {
        "id": "startup_biotech",
        "heading": "Ventures & Vials",
        "kicker": "Startups and biotech",
        "mode": "pick",
        "brief": "One startup OR biotech story. Alternate between startup and biotech across days (check history).",
        "task": (
            "Cover the assigned story in two parts. First, under \"**The Story**\", "
            "faithfully report what the article actually says happened, drawing ONLY from "
            "the article text in MATERIAL below, in 150-250 words. Then, at the bottom under "
            "\"**Relevance / Importance**\", add the TECHNICAL REASONING behind the move — the science, the "
            "platform bet, or the market mechanics — in 100-175 words. Keep the two parts "
            "clearly separate — no outside claims or speculation in the first."
        ),
    },
    {
        "id": "biology",
        "heading": "The Bench",
        "kicker": "Biology for pharma intuition",
        "mode": "pick",
        "brief": "One biological research paper or topic that builds pharma intuition; should not repeat mechanisms already taught.",
        "task": (
            "Turn the assigned item into a two-part piece. First, under \"**The Research**\", "
            "faithfully summarize what the article/paper actually reports, drawing ONLY from "
            "the article text in MATERIAL below, in 200-300 words. Then, at the bottom under "
            "\"**Relevance / Importance**\", build pharma intuition by teaching the underlying biology "
            "(mechanism, pathway, modality) at a level a strong engineer without a bio "
            "background can absorb, defining jargon inline, in 125-225 words. Keep the two "
            "parts clearly separate — no outside claims or speculation in the first."
        ),
    },
    {
        "id": "politics",
        "heading": "Statecraft",
        "kicker": "Politics, foreign affairs & the economy",
        "mode": "pick",
        "brief": (
            "One politics, foreign-affairs, economic-policy, or political-theory story or "
            "analysis piece — pull from any one of these or a mix; rotate the angle across days."
        ),
        "task": (
            "Cover the assigned story in two parts. First, under \"**The Story**\", "
            "faithfully report what the article actually says, drawing ONLY from the "
            "article text in MATERIAL below, in 200-300 words. Then, at the bottom under "
            "\"**Relevance / Importance**\", add the underlying context — the political dynamics, policy "
            "tradeoffs, economic mechanics, or theoretical framework at play — in 125-200 "
            "words. Keep the two parts clearly separate — no outside claims or speculation "
            "in the first."
        ),
    },
    {
        "id": "headlines",
        "heading": "The Wire",
        "kicker": "San Francisco & Los Angeles",
        "mode": "pool",
        "brief": "A single wire digest of 4-6 genuinely newsworthy SF and LA briefs.",
        "task": (
            "Write ONE wire-digest article. headline like \"The Wire: <short theme of the day>\"; "
            "byline \"Wire Desk\"; publication \"The Magnolia Times\"; url \"\". The body is a "
            "markdown bullet list of 4-6 briefs mixing both cities, each formatted as "
            "\"**<City> — <mini headline>:** one-two sentence brief ([source](url))\" using the "
            "real url of that candidate. Skip celebrity fluff."
        ),
    },
    {
        "id": "finance",
        "heading": "Ledger & Tape",
        "kicker": "Markets and money",
        "mode": "generate",
        "brief": "One combined piece: a progressive finance-concept lesson plus today's market overview from real index data.",
        "task": (
            "Write ONE combined piece, url \"\", byline \"Ledger Desk\", publication "
            "\"The Magnolia Times\". Part 1 (200-300 words): a finance-concept lesson — treat "
            "the section history as concepts already covered and progress logically (e.g. index "
            "funds -> expense ratios -> diversification -> valuation basics). Part 2, under a "
            "\"**Market overview**\" heading: explain the REAL index data provided — what moved "
            "and one plausible driver. Educational, not advice."
        ),
    },
    {
        "id": "spanish",
        "heading": "La Sección en Español",
        "kicker": "Para aprender",
        "mode": "pick",
        "brief": "One Spanish-language article from Spain, Colombia, or Southern California (SoCal).",
        "task": (
            "Using the article text in MATERIAL below, write a faithful 200-300 word recap "
            "IN SPANISH under \"**El artículo**\". Preserve the source's facts, names, dates, "
            "numbers, nuance, and level of language; do not invent details or simplify it into "
            "an in-house lesson. Then add \"**Vocabulario**\" with 8-10 words from the source "
            "and English translations, followed by \"**Preguntas**\" with 2-3 comprehension "
            "questions based strictly on the recap. Finish at the bottom with "
            "\"**Relevance / Importance**\" and 2-3 concise sentences explaining why the "
            "reported story matters, clearly separate from what the outlet reported."
        ),
    },
    {
        "id": "journal",
        "heading": "The Examined Life",
        "kicker": "Journal prompt",
        "mode": "generate",
        "brief": "One short emotional-introspection journal prompt; vary the angle from recent days.",
        "task": (
            "Write ONE short journal prompt (2-4 sentences) centered on emotional introspection: "
            "feelings being avoided, unmet needs, recurring reactions, relationships, self-trust, "
            "grief, joy, shame, vulnerability, or inner conflict. Make it gentle, specific, and "
            "answerable in ten minutes. Do not make career, productivity, achievement, or ambition "
            "the main subject. Vary the emotional angle from what already ran. url \"\", byline "
            "\"The Editors\", publication \"The Magnolia Times\"."
        ),
    },
]

WEEKLY_SECTIONS: list[dict] = [
    {
        "id": "weekly_ai_paper",
        "heading": "The Sunday Paper",
        "kicker": "This week's AI research",
        "mode": "pick",
        "brief": "One substantial, recent AI research paper worth an hour of study — heavier than the weekday deep dives, and not one already covered this week.",
        "task": (
            "Write a two-part guided read of the assigned paper. First, under \"**The "
            "Paper**\", faithfully and thoroughly recap the context, method, and results, "
            "drawing ONLY from the article text in MATERIAL below, in 450-600 words. Then, "
            "at the bottom under \"**Relevance / Importance**\", add your own explanation of the core method with "
            "intuition, caveats, and how it connects to production ML/data infrastructure, "
            "in 150-300 words. Keep the two parts clearly separate — no outside claims or "
            "speculation in the first."
        ),
    },
    {
        "id": "weekly_politics",
        "heading": "The Week in Statecraft",
        "kicker": "Politics, foreign affairs & the economy",
        "mode": "pick",
        "brief": (
            "One substantial politics, foreign-affairs, economic-policy, or "
            "political-theory story or analysis from the week worth deeper treatment — "
            "heavier than the weekday piece, and not one already covered this week."
        ),
        "task": (
            "Write a two-part piece on the assigned story. First, under \"**The Story**\", "
            "faithfully and thoroughly recap what the article actually reports, drawing "
            "ONLY from the article text in MATERIAL below, in 350-500 words. Then, at the bottom under "
            "\"**Relevance / Importance**\", add deeper context — the political dynamics, policy "
            "tradeoffs, economic mechanics, or theoretical framework at play, and how it "
            "connects to the broader week's events — in 200-300 words. Keep the two parts "
            "clearly separate — no outside claims or speculation in the first."
        ),
    },
    {
        "id": "weekly_finance",
        "heading": "The Week on the Tape",
        "kicker": "Finance debrief",
        "mode": "generate",
        "brief": "A longer week-in-review market debrief plus one concept treated in depth.",
        "task": (
            "Write a 500-700 word weekly finance debrief using the REAL index data provided: "
            "what the week looked like, one concept explored in depth (progressing from concepts "
            "already covered — see history), and one thing to watch next week. Educational, not "
            "advice. url \"\", byline \"Ledger Desk\", publication \"The Magnolia Times\"."
        ),
    },
    {
        "id": "weekly_spanish",
        "heading": "Lectura del Domingo",
        "kicker": "Español extendido",
        "mode": "pick",
        "brief": "One meaty Spanish article from Spain, Colombia, or Southern California (SoCal) for a longer Sunday read.",
        "task": (
            "Using the article text in MATERIAL below, write a faithful 400-550 word recap "
            "IN SPANISH under \"**El artículo**\". Preserve the source's facts, names, dates, "
            "numbers, nuance, and level of language; do not invent details or simplify it into "
            "an in-house lesson. Then add \"**Vocabulario**\" with 12-15 words from the source "
            "and English translations, followed by 3 comprehension questions and 1 short "
            "writing prompt in Spanish based strictly on the recap. Finish at the bottom with "
            "\"**Relevance / Importance**\" and a concise paragraph explaining why the "
            "reported story matters, clearly separate from what the outlet reported."
        ),
    },
    {
        "id": "weekly_journal",
        "heading": "The Examined Life, Extended",
        "kicker": "Sunday journal",
        "mode": "generate",
        "brief": "One longer Sunday prompt for emotional reflection and self-understanding.",
        "task": (
            "Write ONE longer Sunday journal prompt centered on emotional introspection: a "
            "gentle framing paragraph plus 3-4 linked questions exploring the week's feelings, "
            "needs, relationships, avoided emotions, moments of aliveness, or recurring inner "
            "patterns. End with one compassionate intention for the coming week. Do not center "
            "career, productivity, achievement, or ambition. url \"\", byline \"The Editors\", "
            "publication \"The Magnolia Times\"."
        ),
    },
]

# Weekly sections should also avoid repeating their weekday counterparts.
RELATED_SECTIONS: dict[str, set[str]] = {
    "weekly_ai_paper": {"weekly_ai_paper", "ml_deep_dive"},
    "weekly_politics": {"weekly_politics", "politics"},
    "weekly_finance": {"weekly_finance", "finance"},
    "weekly_spanish": {"weekly_spanish", "spanish"},
    "weekly_journal": {"weekly_journal", "journal"},
}


# --- stage 1: editor-in-chief ---------------------------------------------------

def plan_edition(
    cfg: Config,
    kind: str,
    spec: list[dict],
    candidates: dict[str, list[dict]],
    reader_ctx: str,
    history: list[dict],
    date_str: str,
) -> dict[str, dict]:
    pools = []
    for section in spec:
        pool = candidates.get(section["id"], [])[:CANDIDATE_CAP]
        header = f"SECTION {section['id']} — {section['brief']}"
        if section["mode"] == "pick":
            pools.append(f"{header}\n{_candidates_block(pool)}")
        elif section["mode"] == "pool":
            pools.append(f"{header}\n(writer will digest the pool; give a directive on what to feature)\n{_candidates_block(pool)}")
        else:
            pools.append(f"{header}\n(written in-house; no candidates — give a directive)")

    weekly_note = (
        "This is the SUNDAY WEEKLY edition. Prefer the most substantial, heavyweight items — "
        "pieces worth a long Sunday read — and never repeat anything the weekday editions "
        "already covered."
        if kind == "weekly"
        else "This is a daily weekday edition. Keep the overall mix varied and the total read manageable."
    )

    prompt = f"""You are the editor-in-chief of "The Magnolia Times", a personal newspaper, edition dated {date_str}.

{reader_ctx}

WHAT ALREADY RAN in recent editions (do NOT repeat stories, topics, or lessons; note the difficulty pattern):
{_history_block(history)}

{weekly_note}

Today's sections and candidate pools:

{chr(10).join(pools)}

For each section, assign the single best item, balancing: the reader's stated preferences,
their feedback patterns, novelty versus what already ran, difficulty rotation, and topical
variety across today's paper as a whole (no two sections about the same story).

Return JSON: {{"picks": [{{"section_id": "...", "candidate_number": <1-based number from that
section's candidate list, or null for in-house/pool sections>, "difficulty": "intro"|"intermediate"|"advanced"|"",
"directive": "<1-2 sentences for the section writer: the angle, depth, and what to emphasize or avoid>"}}]}}
with exactly one pick per section listed above."""

    result = generate_json(cfg.gemini_api_key, cfg.gemini_model, prompt)
    picks = {}
    for pick in result.get("picks", []) if isinstance(result, dict) else []:
        if isinstance(pick, dict) and pick.get("section_id"):
            picks[pick["section_id"]] = pick
    if not picks:
        raise RuntimeError("chief returned no usable picks")
    return picks


# --- stage 2: section writers ----------------------------------------------------

def write_section(
    cfg: Config,
    kind: str,
    section: dict,
    pool: list[dict],
    pick: dict,
    reader_ctx: str,
    history: list[dict],
    date_str: str,
    market_snapshot: str,
) -> dict:
    sid = section["id"]
    material = ""
    selected_item: dict | None = None
    if section["mode"] == "pick":
        num = pick.get("candidate_number")
        if isinstance(num, int) and 1 <= num <= len(pool):
            selected_item = pool[num - 1]
        else:
            if not pool:
                raise RuntimeError(f"no sourced candidates available for {sid}")
            selected_item = pool[0]
            num = 1
            print(f"  [editor] {sid}: chief pick unavailable; using newest sourced candidate")

        material = "ASSIGNED ITEM METADATA:\n" + _candidate_line(num, selected_item)
        full_text = fetch_article_text(selected_item.get("url", ""))
        if full_text:
            material = (
                material
                + "\n\nFULL ARTICLE TEXT (the real source content — your factual recap "
                "must be based strictly on this, not on outside knowledge):\n"
                + full_text
            )
        else:
            material += (
                "\n\n(Full article text could not be fetched — you only have the "
                "snippet above. Keep your factual recap brief and do not add outside "
                "claims or invented detail.)"
            )
    elif section["mode"] == "pool":
        material = "CANDIDATE ITEMS for the digest:\n" + _candidates_block(pool)

    if sid in ("finance", "weekly_finance"):
        material = (
            f"REAL MARKET DATA (latest closes):\n{market_snapshot or '(unavailable — say so rather than inventing numbers)'}"
            + (f"\n\n{material}" if material else "")
        )

    related = RELATED_SECTIONS.get(sid, {sid})
    prompt = f"""You are a section writer for "The Magnolia Times", edition dated {date_str}.

{reader_ctx}

SECTION: {section['heading']} ({sid})
ASSIGNMENT: {section['task']}

EDITOR-IN-CHIEF DIRECTIVE: {pick.get('directive') or '(none — use your judgment)'}
TARGET DIFFICULTY: {pick.get('difficulty') or 'your call'}

PREVIOUSLY RUN IN THIS SECTION (do not repeat topics or lessons):
{_history_block(history, related, cap=25)}

MATERIAL:
{material or '(none — this piece is written in-house)'}

{SOURCE_REPORTING_RULES if section["mode"] == "pick" else ""}

Copy "url", "authors", and "published" exactly from the source data; never invent them.
When FULL ARTICLE TEXT is present in MATERIAL, it is the real source content — your recap
of what happened/was found must be grounded strictly in that text, not in your own outside
knowledge. Confine any analysis, interpretation, or personal relevance to the separate
closing section the assignment describes; never blend it into the factual recap.
Write exactly ONE article. {ARTICLE_SHAPE}
Return a single JSON object (not an array)."""

    result = generate_json(cfg.gemini_api_key, cfg.gemini_model, prompt)
    if isinstance(result, list):
        result = result[0]
    if not isinstance(result, dict) or not result.get("headline"):
        raise RuntimeError(f"writer for {sid} returned no article")

    result["id"] = uuid.uuid4().hex[:8]
    for key, default in (
        ("url", ""), ("authors", []), ("publication", ""), ("published", ""),
        ("difficulty", ""), ("tags", []), ("why_chosen", ""), ("summary", ""), ("byline", ""),
    ):
        result.setdefault(key, default)

    # Gemini must never be allowed to turn a sourced section into an in-house
    # article or alter source metadata. Enforce the selected feed item after
    # generation rather than relying on prompt compliance.
    if selected_item is not None:
        authors = selected_item.get("authors", [])
        result["url"] = selected_item.get("url", "")
        result["authors"] = authors
        result["publication"] = selected_item.get("source", "")
        result["published"] = selected_item.get("published", "")
        result["byline"] = (
            f"{', '.join(author['name'] for author in authors)} · {result['publication']}"
            if authors
            else result["publication"]
        )
        if sid in ("spanish", "weekly_spanish"):
            result["headline"] = selected_item.get("title", result["headline"])
    return result


# --- assembly ---------------------------------------------------------------------

def build_edition(
    cfg: Config, kind: str, prefs: dict, feedback: list[dict], history: list[dict]
) -> dict:
    today = dt.date.today()
    date_str = today.isoformat()
    reader_ctx = _reader_context(prefs, feedback)
    market = fetch_market_snapshot()

    if kind == "daily":
        spec, candidates = DAILY_SECTIONS, gather_daily_candidates()
    else:
        spec, candidates = WEEKLY_SECTIONS, gather_weekly_candidates()

    picks: dict[str, dict] = {}
    try:
        picks = plan_edition(cfg, kind, spec, candidates, reader_ctx, history, date_str)
        print(f"  [chief] planned {len(picks)} sections")
    except Exception as exc:  # noqa: BLE001 - writers can pick for themselves
        print(f"  [chief] planning failed (writers will choose): {exc}")

    sections = []
    for section in spec:
        pool = candidates.get(section["id"], [])[:CANDIDATE_CAP]
        try:
            article = write_section(
                cfg, kind, section, pool, picks.get(section["id"], {}),
                reader_ctx, history, date_str, market,
            )
            sections.append(
                {
                    "id": section["id"],
                    "heading": section["heading"],
                    "kicker": section["kicker"],
                    "articles": [article],
                }
            )
            print(f"  [editor] {section['id']}: \"{article['headline'][:60]}\"")
        except Exception as exc:  # noqa: BLE001 - drop the section, keep the paper
            print(f"  [editor] {section['id']} FAILED, dropping section: {exc}")

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
