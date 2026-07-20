"use client";

import { useState } from "react";
import { supabase } from "@/lib/supabase";

export default function Login() {
  const [mode, setMode] = useState<"signin" | "signup">("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    setNotice("");
    const auth = supabase().auth;
    const { error: err } =
      mode === "signin"
        ? await auth.signInWithPassword({ email, password })
        : await auth.signUp({
            email,
            password,
            options: { emailRedirectTo: window.location.origin },
          });
    if (err) setError(err.message);
    else if (mode === "signup")
      setNotice("Account created. Check your inbox for the confirmation link.");
    setBusy(false);
  }

  return (
    <div className="card">
      <h1>The Magnolia Times</h1>
      <p style={{ fontStyle: "italic", color: "var(--ink-soft)", marginTop: 0 }}>
        All the signal that&rsquo;s fit to print
      </p>
      <form onSubmit={submit}>
        <div className="field">
          <label htmlFor="email">Email</label>
          <input
            id="email"
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </div>
        <div className="field">
          <label htmlFor="password">Password</label>
          <input
            id="password"
            type="password"
            required
            minLength={6}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </div>
        <button className="btn" disabled={busy}>
          {mode === "signin" ? "Sign in" : "Create account"}
        </button>
      </form>
      {error && <p className="error-note">{error}</p>}
      {notice && <p className="status-note">{notice}</p>}
      <p style={{ fontSize: 13, marginTop: 18 }}>
        {mode === "signin" ? "First visit?" : "Already subscribed?"}{" "}
        <button
          className="btn btn-quiet"
          style={{ padding: "4px 10px", letterSpacing: 1 }}
          onClick={() => setMode(mode === "signin" ? "signup" : "signin")}
        >
          {mode === "signin" ? "Create an account" : "Sign in"}
        </button>
      </p>
    </div>
  );
}
