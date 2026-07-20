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
          "byline": "Chen et al. · arXiv",   // short printed attribution
          "authors": [                        // real authors from source metadata
            { "name": "Ada Chen", "url": "https://…" }  // url "" when unknown
          ],
          "publication": "arXiv",            // venue/outlet; "The Magnolia Times" for in-house
          "published": "2026-07-18T…",       // source publication date string ("" if in-house)
          "url": "https://…",                // real source link ("" for in-house pieces)
          "summary": "…",                    // 1-2 sentence dek
          "body": "…",                       // markdown; supports **bold**, *italics*, bullets, [links](url)
          "difficulty": "intermediate",      // "intro" | "intermediate" | "advanced" | ""
          "tags": ["transformers", "systems"],
          "why_chosen": "…"                  // one line: why the chief picked it
        }
      ]
    }
  ]
}
```

## Editorial flow

The pipeline runs two stages: an **editor-in-chief** call sees all candidate pools,
the reader's preferences, recent feedback, and the history of what already ran
(last ~16 editions), then assigns exactly ONE item per section with a directive
and target difficulty. **Section writer** calls then file one article each.
Every section carries exactly one article per edition.

## Daily section ids (in print order)

| id                | contents |
| ----------------- | -------- |
| `ml_deep_dive`    | 1 ML / data-engineering / AI deep dive; difficulty rotates; recency favored |
| `startup_biotech` | 1 startup OR biotech story (alternating across days); body explains the technical reasoning behind the move |
| `biology`         | 1 biology paper or lesson building pharma intuition; body teaches, not just summarizes |
| `headlines`       | 1 "Wire" digest article whose body is 4-6 bulleted SF & LA briefs with inline source links |
| `finance`         | 1 combined piece: progressive finance-concept lesson + market overview from real index data |
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
