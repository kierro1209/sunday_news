"use client";

import { useEffect, useState } from "react";
import type { Session } from "@supabase/supabase-js";
import { supabase } from "@/lib/supabase";
import Login from "./Login";

export default function AuthGate({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    supabase()
      .auth.getSession()
      .then(({ data }) => {
        setSession(data.session);
        setLoading(false);
      });
    const {
      data: { subscription },
    } = supabase().auth.onAuthStateChange((_event, next) => setSession(next));
    return () => subscription.unsubscribe();
  }, []);

  if (loading) return <p className="center-note">Unfolding the paper…</p>;
  if (!session) return <Login />;
  return <>{children}</>;
}
