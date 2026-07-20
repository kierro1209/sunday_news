# The Magnolia Times

A personal, agentic newspaper. Every morning a Python pipeline curates a daily edition
(ML/AI deep dives, startup & biotech news with technical reasoning, biology lessons,
SF/LA headlines, finance lessons + market overview, an intermediate Spanish article,
and a journal prompt), stores it in Supabase, and emails it to you via Resend.
On Sundays it also produces a longer weekly edition.

The Next.js web app renders editions in a newspaper layout with login, an archive,
per-article note-taking, feedback (which steers future curation), preferences, and
print-to-PDF export with ruled space to write on.

## Repository layout

```
pipeline/   Python agent: fetch sources -> Gemini curation -> Supabase -> Resend email
web/        Next.js app: newspaper UI, auth, notes, feedback, preferences, PDF export
db/         Supabase schema (run once in the Supabase SQL editor)
docs/       Edition JSON contract shared by pipeline and web
.github/    Cron workflows that run the pipeline daily/weekly for free
```

## Cost profile

- **Supabase free tier** — Postgres + auth (500 MB, plenty).
- **GitHub Actions free tier** — daily 5-minute pipeline run ≈ 150 min/month.
- **Gemini Flash** — a few curation/summarization calls per day; generous free tier.
- **Resend free tier** — 100 emails/day; this sends 1–2.
- **Vercel free tier (optional)** — host the web app, or run it locally.

## Setup

1. **Supabase**: create a free project, run `db/schema.sql` in the SQL editor,
   enable email/password auth. Note the project URL, anon key, and service-role key.
2. **Keys**: get a Gemini API key (aistudio.google.com) and a Resend API key.
   With no verified domain, Resend can send from `onboarding@resend.dev` to your
   own account email only — fine for personal use.
3. **Pipeline**: `cd pipeline && pip install -r requirements.txt`, copy
   `.env.example` to `.env`, fill it in, then `python -m magnolia.run --kind daily`.
4. **Web**: `cd web && npm install`, copy `.env.example` to `.env.local`, fill it in,
   then `npm run dev`. Sign up with the same email the pipeline sends to.
5. **Cron**: push to GitHub and add the pipeline `.env` values as repository secrets
   (see `.github/workflows/`). The daily job runs at 6:05 AM PT; Sundays it also
   builds the weekly edition.

## How curation learns from you

Thumbs up/down and comments on articles are stored in the `feedback` table.
Each morning the pipeline loads your preferences plus your recent feedback and
includes both in the Gemini curation prompt, so the paper drifts toward what
you find useful.
