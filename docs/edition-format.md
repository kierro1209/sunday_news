# Edition JSON contract

`editions.content` holds one JSON document per paper. The Python pipeline writes it;
the web app and the email renderer read it. Keep the two sides in sync with this file.

```jsonc
{
  "kind": "daily",              // or "weekly"
  "date": "2026-07-20",         // edition date (PT)
  "volume": "Vol. 1, No. 42",   // printed under the masthead, pipeline-generated
  "motto": "All the signal that's fit to print",
  "sections": [
    {
      "id": "ml_deep_dive",     // stable section id, see list below
      "heading": "Machine Intelligence",
      "kicker": "Today's deep dive",   // small label above the heading
      "articles": [
        {
          "id": "a1b2c3",              // stable within the edition; feedback/notes key
          "headline": "…",
          "byline": "arXiv · Chen et al.",   // source attribution
          "url": "https://…",                // real source link ("" if none)
          "summary": "…",                    // 1-2 sentence dek
          "body": "…",                       // markdown; the main written piece
          "difficulty": "intermediate",      // "intro" | "intermediate" | "advanced" | ""
          "tags": ["transformers", "systems"],
          "why_chosen": "…"                  // one line: why the agent picked it
        }
      ]
    }
  ]
}
```

## Daily section ids (in print order)

| id                | contents |
| ----------------- | -------- |
| `ml_deep_dive`    | 1 ML / data-engineering / AI paper, blog post, or article; difficulty rotates; recency favored |
| `startup_biotech` | 2-3 startup & biotech stories; body explains the technical reasoning behind the moves |
| `biology`         | 1 biology paper or lesson building pharma intuition; body teaches, not just summarizes |
| `headlines`       | 4-6 short SF & LA news items |
| `finance`         | 1 finance-concept lesson (progressive curriculum) + 1 market-overview article with real index/mover data |
| `spanish`         | 1 intermediate Spanish article; body keeps the Spanish text and appends a vocab glossary + 2 comprehension questions |
| `journal`         | 1 short introspection/ambition prompt; no url |

## Weekly section ids (Sundays, separate edition with kind="weekly")

| id                  | contents |
| ------------------- | -------- |
| `weekly_ai_paper`   | 1 substantial AI research paper with a longer guided read |
| `weekly_finance`    | longer week-in-review market debrief + deeper concept treatment |
| `weekly_spanish`    | longer Spanish article with glossary and questions |
| `weekly_journal`    | longer reflective journal prompt |

Renderers must not assume every section is present — if a source or model call
failed, the pipeline drops that section rather than blocking the paper.
