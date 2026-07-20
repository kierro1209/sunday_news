"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { supabase } from "@/lib/supabase";
import AuthGate from "@/components/AuthGate";
import Masthead from "@/components/Masthead";

interface ArchiveRow {
  id: string;
  kind: string;
  edition_date: string;
}

function ArchiveList() {
  const [rows, setRows] = useState<ArchiveRow[] | null>(null);

  useEffect(() => {
    supabase()
      .from("editions")
      .select("id,kind,edition_date")
      .order("edition_date", { ascending: false })
      .limit(200)
      .then(({ data }) => setRows((data as ArchiveRow[]) ?? []));
  }, []);

  return (
    <div className="sheet">
      <Masthead kindLabel="The Archive" />
      <section className="section">
        <div className="kicker">Back issues</div>
        <h2>The Archive</h2>
        {rows === null ? (
          <p className="center-note">Opening the filing cabinet…</p>
        ) : rows.length === 0 ? (
          <p className="center-note">No editions yet.</p>
        ) : (
          <ul className="archive-list">
            {rows.map((row) => (
              <li key={row.id}>
                <Link href={`/edition/${row.id}`}>
                  {new Date(row.edition_date + "T12:00:00").toLocaleDateString("en-US", {
                    weekday: "long",
                    year: "numeric",
                    month: "long",
                    day: "numeric",
                  })}
                </Link>
                <span className="kicker">{row.kind === "weekly" ? "Sunday Weekly" : "Daily"}</span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

export default function ArchivePage() {
  return (
    <AuthGate>
      <ArchiveList />
    </AuthGate>
  );
}
