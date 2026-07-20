"use client";

import { use, useEffect, useState } from "react";
import type { EditionRow } from "@/lib/types";
import { supabase } from "@/lib/supabase";
import AuthGate from "@/components/AuthGate";
import EditionView from "@/components/EditionView";

function EditionLoader({ id }: { id: string }) {
  const [edition, setEdition] = useState<EditionRow | null | undefined>(undefined);

  useEffect(() => {
    supabase()
      .from("editions")
      .select("id,kind,edition_date,content")
      .eq("id", id)
      .single()
      .then(({ data }) => setEdition((data as EditionRow) ?? null));
  }, [id]);

  if (edition === undefined) return <p className="center-note">Pulling this issue from the stacks…</p>;
  if (edition === null) return <p className="center-note">Edition not found.</p>;
  return <EditionView edition={edition} />;
}

export default function EditionPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  return (
    <AuthGate>
      <EditionLoader id={id} />
    </AuthGate>
  );
}
