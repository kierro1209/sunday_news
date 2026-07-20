"use client";

import { useEffect, useRef, useState } from "react";
import type { Article } from "@/lib/types";
import { supabase } from "@/lib/supabase";
import { Markdown } from "@/lib/markdown";

interface Props {
  editionId: string;
  sectionId: string;
  article: Article;
  initialRating: number | null;
  initialNote: string;
}

function formatDate(raw: string): string {
  const parsed = new Date(raw);
  if (isNaN(parsed.getTime())) return raw;
  return parsed.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

export default function ArticleCard({
  editionId,
  sectionId,
  article,
  initialRating,
  initialNote,
}: Props) {
  const [rating, setRating] = useState<number | null>(initialRating);
  const [note, setNote] = useState(initialNote);
  const [showNote, setShowNote] = useState(Boolean(initialNote));
  const [saveState, setSaveState] = useState<"idle" | "saving" | "saved">("idle");
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  async function rate(value: number) {
    const next = rating === value ? null : value;
    setRating(next);
    const { data } = await supabase().auth.getUser();
    if (!data.user) return;
    if (next === null) {
      await supabase()
        .from("feedback")
        .delete()
        .match({ edition_id: editionId, article_id: article.id, user_id: data.user.id });
    } else {
      await supabase().from("feedback").upsert(
        {
          user_id: data.user.id,
          edition_id: editionId,
          article_id: article.id,
          section_id: sectionId,
          headline: article.headline,
          rating: next,
          comment: "",
        },
        { onConflict: "user_id,edition_id,article_id" }
      );
    }
  }

  function onNoteChange(value: string) {
    setNote(value);
    setSaveState("saving");
    if (saveTimer.current) clearTimeout(saveTimer.current);
    saveTimer.current = setTimeout(async () => {
      const { data } = await supabase().auth.getUser();
      if (!data.user) return;
      await supabase().from("notes").upsert(
        {
          user_id: data.user.id,
          edition_id: editionId,
          article_id: article.id,
          content: value,
          updated_at: new Date().toISOString(),
        },
        { onConflict: "user_id,edition_id,article_id" }
      );
      setSaveState("saved");
    }, 800);
  }

  useEffect(() => () => {
    if (saveTimer.current) clearTimeout(saveTimer.current);
  }, []);

  const authors = article.authors ?? [];
  return (
    <article className="article">
      <h3>
        {article.url ? (
          <a href={article.url} target="_blank" rel="noreferrer">
            {article.headline}
          </a>
        ) : (
          article.headline
        )}
        {article.difficulty && <span className="badge">{article.difficulty}</span>}
      </h3>
      <div className="byline">
        {authors.length > 0 ? (
          <>
            By{" "}
            {authors.map((author, i) => (
              <span key={i}>
                {i > 0 && ", "}
                {author.url ? (
                  <a href={author.url} target="_blank" rel="noreferrer">
                    {author.name}
                  </a>
                ) : (
                  author.name
                )}
              </span>
            ))}
          </>
        ) : (
          article.byline
        )}
        {article.publication && <> &middot; {article.publication}</>}
        {article.published && <> &middot; {formatDate(article.published)}</>}
        {article.url && (
          <>
            {" "}
            &middot;{" "}
            <a href={article.url} target="_blank" rel="noreferrer">
              original source
            </a>
          </>
        )}
      </div>
      {article.summary && <p className="summary">{article.summary}</p>}
      <Markdown text={article.body} />
      {article.why_chosen && <div className="why-chosen">Why this: {article.why_chosen}</div>}

      <div className="article-tools">
        <button className={rating === 1 ? "active" : ""} onClick={() => rate(1)}>
          More like this
        </button>
        <button className={rating === -1 ? "active" : ""} onClick={() => rate(-1)}>
          Less like this
        </button>
        <button onClick={() => setShowNote(!showNote)}>
          {showNote ? "Hide notes" : "Notes"}
        </button>
        {saveState === "saving" && <span style={{ fontSize: 11, color: "var(--ink-faint)" }}>saving…</span>}
        {saveState === "saved" && <span style={{ fontSize: 11, color: "var(--accent)" }}>saved</span>}
      </div>
      {showNote && (
        <textarea
          className="notes-area"
          placeholder="Your notes on this piece…"
          value={note}
          onChange={(e) => onNoteChange(e.target.value)}
        />
      )}
    </article>
  );
}
