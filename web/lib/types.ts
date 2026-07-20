// Mirrors docs/edition-format.md — keep in sync with the Python pipeline.

export interface ArticleAuthor {
  name: string;
  url: string;
}

export interface Article {
  id: string;
  headline: string;
  byline: string;
  /* Optional because editions generated before these fields existed lack them. */
  authors?: ArticleAuthor[];
  publication?: string;
  published?: string;
  url: string;
  summary: string;
  body: string;
  difficulty: "intro" | "intermediate" | "advanced" | "";
  tags: string[];
  why_chosen: string;
}

export interface Section {
  id: string;
  heading: string;
  kicker: string;
  articles: Article[];
}

export interface EditionContent {
  kind: "daily" | "weekly";
  date: string;
  volume: string;
  motto: string;
  sections: Section[];
}

export interface EditionRow {
  id: string;
  kind: "daily" | "weekly";
  edition_date: string;
  content: EditionContent;
}

export interface Preferences {
  difficulty_bias?: "gentler" | "mixed" | "harder";
  spanish_level?: "beginner" | "intermediate" | "advanced";
  topic_notes?: string;
  muted_topics?: string[];
  extra_interests?: string[];
}
