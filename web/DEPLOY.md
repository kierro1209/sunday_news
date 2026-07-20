# Deploying the web app on Vercel

This repo is a monorepo: the Next.js app lives in `web/`.

## Required Vercel project settings

| Setting | Value |
|---------|-------|
| **Root Directory** | `web` |
| **Framework Preset** | **Next.js** (not "Other") |
| **Output Directory** | leave blank if possible; if the UI forces a value use **`.next`** (never `public` or `.`) |
| **Build Command** | blank (uses `npm run build` from `web/vercel.json`) |
| **Install Command** | blank (uses `npm install`) |

If Framework Preset is "Other", Vercel treats the app as a static site and demands
`public` or `.` as Output Directory — that breaks Next.js App Router deploys.

## Environment variables (Production)

- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY` (anon/public key only — not service role)

Redeploy after changing any `NEXT_PUBLIC_*` variable (they are baked in at build time).
