"use client";

import { useEffect, useState } from "react";
import type { EditionRow } from "@/lib/types";
import { supabase } from "@/lib/supabase";
import Masthead from "./Masthead";
import ArticleCard from "./ArticleCard";

interface UserMarks {
  ratings: Record<string, number>;
  notes: Record<string, string>;
}

export default function EditionView({ edition }: { edition: EditionRow }) {
  const [marks, setMarks] = useState<UserMarks | null>(null);

  useEffect(() => {
    (async () => {
      const [fb, nt] = await Promise.all([
        supabase().from("feedback").select("article_id,rating").eq("edition_id", edition.id),
        supabase().from("notes").select("article_id,content").eq("edition_id", edition.id),
      ]);
      const ratings: Record<string, number> = {};
      for (const row of fb.data ?? []) ratings[row.article_id] = row.rating;
      const notes: Record<string, string> = {};
      for (const row of nt.data ?? []) if (row.article_id) notes[row.article_id] = row.content;
      setMarks({ ratings, notes });
    })();
  }, [edition.id]);

  const content = edition.content;
  return (
    <div className="sheet">
      <Masthead
        date={content.date}
        volume={content.volume}
        motto={content.motto}
        kindLabel={content.kind === "weekly" ? "Sunday Weekly Edition" : "Daily Edition"}
      />
      {marks === null ? (
        <p className="center-note">Setting the type…</p>
      ) : (
        content.sections.map((section) => (
          <section key={section.id} className="section">
            <div className="kicker">{section.kicker}</div>
            <h2>{section.heading}</h2>
            <div className={section.articles.length > 1 ? "section-columns" : undefined}>
              {section.articles.map((article) => (
                <ArticleCard
                  key={article.id}
                  editionId={edition.id}
                  sectionId={section.id}
                  article={article}
                  initialRating={marks.ratings[article.id] ?? null}
                  initialNote={marks.notes[article.id] ?? ""}
                />
              ))}
            </div>
          </section>
        ))
      )}
      <footer className="footer-rule">
        THE MAGNOLIA TIMES — CURATED BY YOUR EDITOR AGENT — RATE ARTICLES TO STEER TOMORROW&rsquo;S PAPER
      </footer>
    </div>
  );
}
