"use client";

import Link from "next/link";
import { supabase } from "@/lib/supabase";

export default function Masthead({
  date,
  volume,
  motto,
  kindLabel,
}: {
  date?: string;
  volume?: string;
  motto?: string;
  kindLabel?: string;
}) {
  const displayDate = date
    ? new Date(date + "T12:00:00").toLocaleDateString("en-US", {
        weekday: "long",
        year: "numeric",
        month: "long",
        day: "numeric",
      })
    : "";

  return (
    <>
      <header className="masthead">
        <div className="dateline">
          <span>{kindLabel ?? ""}</span>
          <span>{displayDate}</span>
          <span>{volume ?? ""}</span>
        </div>
        <h1>The Magnolia Times</h1>
        <div className="motto">{motto ?? "All the signal that's fit to print"}</div>
      </header>
      <nav className="topnav no-print">
        <Link href="/">Today</Link>
        <Link href="/archive">Archive</Link>
        <Link href="/preferences">Preferences</Link>
        <button onClick={() => window.print()}>Export PDF</button>
        <button onClick={() => supabase().auth.signOut()}>Sign out</button>
      </nav>
    </>
  );
}
