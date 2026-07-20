"use client";

import { useEffect, useState } from "react";
import type { Preferences } from "@/lib/types";
import { supabase } from "@/lib/supabase";
import AuthGate from "@/components/AuthGate";
import Masthead from "@/components/Masthead";

function PreferencesForm() {
  const [prefs, setPrefs] = useState<Preferences>({});
  const [loaded, setLoaded] = useState(false);
  const [status, setStatus] = useState("");

  useEffect(() => {
    (async () => {
      const { data: auth } = await supabase().auth.getUser();
      if (!auth.user) return;
      const { data } = await supabase()
        .from("preferences")
        .select("prefs")
        .eq("user_id", auth.user.id)
        .maybeSingle();
      setPrefs((data?.prefs as Preferences) ?? {});
      setLoaded(true);
    })();
  }, []);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setStatus("");
    const { data: auth } = await supabase().auth.getUser();
    if (!auth.user) return;
    const { error } = await supabase().from("preferences").upsert(
      { user_id: auth.user.id, prefs, updated_at: new Date().toISOString() },
      { onConflict: "user_id" }
    );
    setStatus(error ? `Could not save: ${error.message}` : "Saved. Tomorrow's paper will use this.");
  }

  return (
    <div className="sheet">
      <Masthead kindLabel="Reader Preferences" />
      <section className="section" style={{ maxWidth: 640, margin: "26px auto 0" }}>
        <div className="kicker">Standing instructions to your editor</div>
        <h2>Preferences</h2>
        {!loaded ? (
          <p className="center-note">Loading…</p>
        ) : (
          <form onSubmit={save}>
            <div className="field">
              <label htmlFor="difficulty">Technical difficulty bias</label>
              <select
                id="difficulty"
                value={prefs.difficulty_bias ?? "mixed"}
                onChange={(e) =>
                  setPrefs({ ...prefs, difficulty_bias: e.target.value as Preferences["difficulty_bias"] })
                }
              >
                <option value="gentler">Gentler — more intros and explainers</option>
                <option value="mixed">Mixed — vary it day to day</option>
                <option value="harder">Harder — more papers, fewer explainers</option>
              </select>
            </div>
            <div className="field">
              <label htmlFor="spanish">Spanish level</label>
              <select
                id="spanish"
                value={prefs.spanish_level ?? "intermediate"}
                onChange={(e) =>
                  setPrefs({ ...prefs, spanish_level: e.target.value as Preferences["spanish_level"] })
                }
              >
                <option value="beginner">Beginner (A2)</option>
                <option value="intermediate">Intermediate (B1)</option>
                <option value="advanced">Advanced (B2+)</option>
              </select>
            </div>
            <div className="field">
              <label htmlFor="muted">Muted topics (comma-separated)</label>
              <input
                id="muted"
                placeholder="e.g. crypto, celebrity news"
                value={(prefs.muted_topics ?? []).join(", ")}
                onChange={(e) =>
                  setPrefs({
                    ...prefs,
                    muted_topics: e.target.value.split(",").map((s) => s.trim()).filter(Boolean),
                  })
                }
              />
            </div>
            <div className="field">
              <label htmlFor="extra">Extra interests (comma-separated)</label>
              <input
                id="extra"
                placeholder="e.g. RNA therapeutics, distributed systems"
                value={(prefs.extra_interests ?? []).join(", ")}
                onChange={(e) =>
                  setPrefs({
                    ...prefs,
                    extra_interests: e.target.value.split(",").map((s) => s.trim()).filter(Boolean),
                  })
                }
              />
            </div>
            <div className="field">
              <label htmlFor="notes">Anything else for the editor</label>
              <textarea
                id="notes"
                rows={4}
                placeholder="e.g. I liked the CRISPR series; more on data lakehouse architecture; shorter market overviews."
                value={prefs.topic_notes ?? ""}
                onChange={(e) => setPrefs({ ...prefs, topic_notes: e.target.value })}
              />
            </div>
            <button className="btn">Save preferences</button>
            {status && <p className="status-note">{status}</p>}
          </form>
        )}
      </section>
    </div>
  );
}

export default function PreferencesPage() {
  return (
    <AuthGate>
      <PreferencesForm />
    </AuthGate>
  );
}
