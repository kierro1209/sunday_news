"""Entry point: python -m magnolia.run --kind daily|weekly [--dry-run]"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config import load_config
from .editor import build_edition
from .emailer import send_edition
from .store import load_preferences, load_recent_feedback, save_edition


def main() -> None:
    parser = argparse.ArgumentParser(description="Build and send a Magnolia Times edition")
    parser.add_argument("--kind", choices=["daily", "weekly"], default="daily")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build the edition and write it to edition-preview.json without saving or emailing",
    )
    args = parser.parse_args()

    cfg = load_config(require_delivery=not args.dry_run)

    print(f"[run] building {args.kind} edition")
    prefs, feedback = {}, []
    if cfg.supabase_url:
        try:
            prefs = load_preferences(cfg)
            feedback = load_recent_feedback(cfg)
            print(f"[run] loaded prefs ({len(prefs)} keys) and {len(feedback)} feedback rows")
        except Exception as exc:  # noqa: BLE001 - publish anyway on a fresh install
            print(f"[run] could not load reader context (continuing without): {exc}")

    edition = build_edition(cfg, args.kind, prefs, feedback)

    if args.dry_run:
        out = Path("edition-preview.json")
        out.write_text(json.dumps(edition, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"[run] dry run — wrote {out.resolve()}")
        return

    edition_id = save_edition(cfg, edition)
    print(f"[run] saved edition {edition_id}")
    send_edition(cfg, edition)
    print("[run] done")


if __name__ == "__main__":
    main()
