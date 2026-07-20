import { createClient, type SupabaseClient } from "@supabase/supabase-js";

let client: SupabaseClient | null = null;

function requireEnv(name: "NEXT_PUBLIC_SUPABASE_URL" | "NEXT_PUBLIC_SUPABASE_ANON_KEY"): string {
  const value = process.env[name]?.trim();
  if (!value) {
    throw new Error(
      `${name} is missing in this deployment. On Vercel: Settings → Environment Variables → ` +
        `add it for Production, then redeploy (NEXT_PUBLIC_* values are baked in at build time).`
    );
  }
  return value;
}

export function supabase(): SupabaseClient {
  if (!client) {
    client = createClient(
      requireEnv("NEXT_PUBLIC_SUPABASE_URL"),
      requireEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY")
    );
  }
  return client;
}
