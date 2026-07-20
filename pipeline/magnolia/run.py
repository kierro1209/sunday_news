"""Entry point: python -m magnolia.run --kind daily|weekly [--dry-run]"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from .config import load_config
from .editor import build_edition
from .emailer import send_edition
from .store import load_preferences, load_recent_feedback, load_recent_history, save_edition


def main() -> None:
    print("[run] START", file=sys.stderr, flush=True)
    sys.stderr.flush()
    
    parser = argparse.ArgumentParser(description="Build and send a Magnolia Times edition")
    parser.add_argument("--kind", choices=["daily", "weekly"], default="daily")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build the edition and write it to edition-preview.json without saving or emailing",
    )
    args = parser.parse_args()

    print(f"[run] loading config (dry_run={args.dry_run})", file=sys.stderr, flush=True)
    sys.stderr.flush()
    cfg = load_config(require_delivery=not args.dry_run)
    print(f"[run] config loaded", file=sys.stderr, flush=True)
    sys.stderr.flush()

    print(f"[run] building {args.kind} edition")
    prefs, feedback, history = {}, [], []
    if cfg.supabase_url:
        try:
            print(f"[run] loading preferences...", file=sys.stderr, flush=True)
            sys.stderr.flush()
            prefs = load_preferences(cfg)
            print(f"[run] loading feedback...", file=sys.stderr, flush=True)
            sys.stderr.flush()
            feedback = load_recent_feedback(cfg)
            print(f"[run] loading history...", file=sys.stderr, flush=True)
            sys.stderr.flush()
            history = load_recent_history(cfg)
            print(
                f"[run] loaded prefs ({len(prefs)} keys), {len(feedback)} feedback rows, "
                f"{len(history)} past articles"
            )
        except Exception as exc:  # noqa: BLE001 - publish anyway on a fresh install
            print(f"[run] could not load reader context (continuing without): {exc}")

    edition = build_edition(cfg, args.kind, prefs, feedback, history)

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
