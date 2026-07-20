"use client";

import { useEffect, useState } from "react";
import type { Session } from "@supabase/supabase-js";
import { supabase } from "@/lib/supabase";
import Login from "./Login";

function VerifyEmail({ email }: { email: string }) {
  const [status, setStatus] = useState("");

  async function resend() {
    const { error } = await supabase().auth.resend({
      type: "signup",
      email,
      options: { emailRedirectTo: window.location.origin },
    });
    setStatus(error ? error.message : "Confirmation email re-sent. Check your inbox (and spam).");
  }

  async function recheck() {
    // Refresh pulls a new JWT; if the email was confirmed, the gate opens.
    await supabase().auth.refreshSession();
    window.location.reload();
  }

  return (
    <div className="card">
      <h1>Confirm your email</h1>
      <p style={{ color: "var(--ink-soft)" }}>
        We sent a confirmation link to <strong>{email}</strong>. The paper stays folded until
        you verify it&rsquo;s you.
      </p>
      <button className="btn" onClick={resend}>
        Resend confirmation
      </button>{" "}
      <button className="btn btn-quiet" onClick={recheck}>
        I&rsquo;ve confirmed
      </button>{" "}
      <button className="btn btn-quiet" onClick={() => supabase().auth.signOut()}>
        Sign out
      </button>
      {status && <p className="status-note">{status}</p>}
    </div>
  );
}

export default function AuthGate({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const [configError, setConfigError] = useState("");

  useEffect(() => {
    try {
      supabase()
        .auth.getSession()
        .then(({ data }) => {
          setSession(data.session);
          setLoading(false);
        })
        .catch((err: Error) => {
          setConfigError(err.message);
          setLoading(false);
        });
      const {
        data: { subscription },
      } = supabase().auth.onAuthStateChange((_event, next) => setSession(next));
      return () => subscription.unsubscribe();
    } catch (err) {
      setConfigError(err instanceof Error ? err.message : "Supabase is not configured.");
      setLoading(false);
    }
  }, []);

  if (loading) return <p className="center-note">Unfolding the paper…</p>;
  if (configError)
    return (
      <div className="card">
        <h1>Configuration needed</h1>
        <p className="error-note">{configError}</p>
      </div>
    );
  if (!session) return <Login />;
  if (!session.user.email_confirmed_at)
    return <VerifyEmail email={session.user.email ?? ""} />;
  return <>{children}</>;
}
