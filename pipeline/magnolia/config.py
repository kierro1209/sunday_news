import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


@dataclass(frozen=True)
class Config:
    gemini_api_key: str
    supabase_url: str
    supabase_service_role_key: str
    resend_api_key: str
    email_from: str
    email_to: str
    web_app_url: str
    gemini_model: str = "gemini-2.5-flash"


def load_config(require_delivery: bool = True) -> Config:
    """Load env config. Dry runs only need Gemini; real runs also need
    Supabase (storage) and Resend (email)."""
    required = ["GEMINI_API_KEY"]
    if require_delivery:
        required += ["SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY", "RESEND_API_KEY", "EMAIL_TO"]
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        raise SystemExit(
            f"Missing required env vars: {', '.join(missing)}\n"
            f"Fill them in pipeline/.env (see pipeline/.env.example)."
        )

    return Config(
        gemini_api_key=os.environ["GEMINI_API_KEY"],
        supabase_url=os.environ.get("SUPABASE_URL", "").rstrip("/"),
        supabase_service_role_key=os.environ.get("SUPABASE_SERVICE_ROLE_KEY", ""),
        resend_api_key=os.environ.get("RESEND_API_KEY", ""),
        email_from=os.environ.get("EMAIL_FROM", "The Magnolia Times <onboarding@resend.dev>"),
        email_to=os.environ.get("EMAIL_TO", ""),
        web_app_url=os.environ.get("WEB_APP_URL", "").rstrip("/"),
        gemini_model=os.environ.get("GEMINI_MODEL", "gemini-2.5-flash"),
    )
