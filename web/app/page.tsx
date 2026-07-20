"use client";

import { useEffect, useState } from "react";
import type { EditionRow } from "@/lib/types";
import { supabase } from "@/lib/supabase";
import AuthGate from "@/components/AuthGate";
import EditionView from "@/components/EditionView";
import Masthead from "@/components/Masthead";

function LatestEdition() {
  const [edition, setEdition] = useState<EditionRow | null | undefined>(undefined);

  useEffect(() => {
    supabase()
      .from("editions")
      .select("id,kind,edition_date,content")
      .order("edition_date", { ascending: false })
      .order("created_at", { ascending: false })
      .limit(1)
      .then(({ data }) => setEdition((data?.[0] as EditionRow) ?? null));
  }, []);

  if (edition === undefined) return <p className="center-note">Fetching the morning edition…</p>;
  if (edition === null)
    return (
      <div className="sheet">
        <Masthead />
        <p className="center-note">
          No editions yet. Run the pipeline once
          (<code>python -m magnolia.run --kind daily</code>) and refresh.
        </p>
      </div>
    );
  return <EditionView edition={edition} />;
}

export default function Home() {
  return (
    <AuthGate>
      <LatestEdition />
    </AuthGate>
  );
}
