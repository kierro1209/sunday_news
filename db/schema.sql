-- The Magnolia Times — Supabase schema.
-- Run once in the Supabase SQL editor (Dashboard -> SQL Editor -> New query).

-- One row per generated paper. The pipeline writes these with the service-role
-- key; signed-in readers get read-only access.
create table if not exists public.editions (
  id uuid primary key default gen_random_uuid(),
  kind text not null check (kind in ('daily', 'weekly')),
  edition_date date not null,
  content jsonb not null,
  created_at timestamptz not null default now(),
  unique (kind, edition_date)
);

-- Thumbs up/down + optional comment on an article. article_id refers to the
-- article's id inside editions.content; the pipeline feeds recent rows back
-- into the curation prompt.
create table if not exists public.feedback (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  edition_id uuid not null references public.editions (id) on delete cascade,
  article_id text not null,
  section_id text not null,
  headline text not null default '',
  rating smallint not null check (rating in (-1, 1)),
  comment text not null default '',
  created_at timestamptz not null default now(),
  unique (user_id, edition_id, article_id)
);

-- Free-form notes. article_id is null for edition-level notes.
create table if not exists public.notes (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  edition_id uuid not null references public.editions (id) on delete cascade,
  article_id text,
  content text not null default '',
  updated_at timestamptz not null default now(),
  unique (user_id, edition_id, article_id)
);

-- One row per user. prefs is free-form JSON consumed by the curation prompt:
-- { "difficulty_bias": "mixed", "spanish_level": "intermediate",
--   "topic_notes": "...", "muted_topics": [...], "extra_interests": [...] }
create table if not exists public.preferences (
  user_id uuid primary key references auth.users (id) on delete cascade,
  prefs jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);

-- Row-level security -------------------------------------------------------

alter table public.editions enable row level security;
alter table public.feedback enable row level security;
alter table public.notes enable row level security;
alter table public.preferences enable row level security;

create policy "editions readable by signed-in users"
  on public.editions for select to authenticated using (true);

create policy "own feedback" on public.feedback
  for all to authenticated
  using (auth.uid() = user_id) with check (auth.uid() = user_id);

create policy "own notes" on public.notes
  for all to authenticated
  using (auth.uid() = user_id) with check (auth.uid() = user_id);

create policy "own preferences" on public.preferences
  for all to authenticated
  using (auth.uid() = user_id) with check (auth.uid() = user_id);

create index if not exists editions_date_idx on public.editions (edition_date desc);
create index if not exists feedback_created_idx on public.feedback (created_at desc);
