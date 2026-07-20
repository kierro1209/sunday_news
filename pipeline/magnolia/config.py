import os
from dataclasses import dataclass
from pathlib import Path

# Only load .env if it exists (local dev); GitHub Actions passes env vars directly
env_file = Path(__file__).resolve().parent.parent / ".env"
if env_file.exists():
    from dotenv import load_dotenv
    load_dotenv(env_file)


@dataclass(frozen=True)
class Config:
    gemini_api_key: str
    supabase_url: str
    supabase_service_role_key: str
    resend_api_key: str
    email_from: str
    email_to: str
    web_app_url: str
    gemini_model: str = "gemini-3-flash-preview"


def load_config(require_delivery: bool = True) -> Config:
    """Load env config. Dry runs only need Gemini; real runs also need
    Supabase (storage) and Resend (email)."""
    required = ["GEMINI_API_KEY"]
    if require_delivery:
        required += ["SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY", "RESEND_API_KEY", "EMAIL_TO"]
    env_path = Path(__file__).resolve().parent.parent / ".env"
    missing: list[str] = []
    empty: list[str] = []
    
    for name in required:
        value = os.environ.get(name)
        if value is None:
            missing.append(name)
        elif not value.strip():
            empty.append(name)
    
    if missing or empty:
        parts = []
        if missing:
            parts.append(f"Missing env vars: {', '.join(missing)}")
        if empty:
            parts.append(f"Empty env vars (key present, no value): {', '.join(empty)}")
        if os.environ.get("GITHUB_ACTIONS") == "true":
            parts.append(
                "Running on GitHub Actions — local pipeline/.env is NOT used.\n"
                "Add these as repository secrets (exact names, no spaces):\n"
                "  github.com/kierro1209/sunday_news/settings/secrets/actions\n"
                "Required: GEMINI_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, "
                "RESEND_API_KEY, EMAIL_TO\n"
                "Optional: EMAIL_FROM, WEB_APP_URL"
            )
        else:
            parts.append(f"Fill them in {env_path} (see pipeline/.env.example).")
            if empty and not missing:
                parts.append("If you edited .env in the editor, save the file first - Python reads from disk.")
        
        # Debug: show what we found
        print("[DEBUG] Env var check:")
        for name in required:
            val = os.environ.get(name)
            if val is None:
                print(f"  {name}: NOT SET")
            else:
                print(f"  {name}: {len(val)} chars, first 20: {val[:20]!r}")
        
        raise SystemExit("\n".join(parts))

    def clean_secret(val: str) -> str:
        """Remove control chars that break HTTP headers."""
        val = val.strip()
        return "".join(c for c in val if ord(c) >= 32 or c == "\t")

    return Config(
        gemini_api_key=clean_secret(os.environ["GEMINI_API_KEY"]),
        supabase_url=clean_secret(os.environ.get("SUPABASE_URL", "")).rstrip("/"),
        supabase_service_role_key=clean_secret(os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")),
        resend_api_key=clean_secret(os.environ.get("RESEND_API_KEY", "")),
        email_from=clean_secret(os.environ.get("EMAIL_FROM", "The Magnolia Times <onboarding@resend.dev>")),
        email_to=clean_secret(os.environ.get("EMAIL_TO", "")),
        web_app_url=clean_secret(os.environ.get("WEB_APP_URL", "")).rstrip("/"),
        gemini_model=clean_secret(os.environ.get("GEMINI_MODEL", "gemini-3-flash-preview")),
    )
