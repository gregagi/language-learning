#!/usr/bin/env python3
"""Sync repo CSV decks and media into a local Anki profile via AnkiConnect.

This replaces the manual flow of copying media into collection.media and
re-importing CSV files in Anki Desktop.

Requirements:
  1. Anki Desktop is open.
  2. The AnkiConnect add-on is installed and listening on http://127.0.0.1:8765.

Example:
  uv run python scripts/sync_to_anki.py --language spanish

Safe preview:
  uv run python scripts/sync_to_anki.py --language spanish --dry-run
"""

from __future__ import annotations

import argparse
import base64
import csv
import html
import json
import re
import shutil
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_ANKI_URL = "http://127.0.0.1:8765"
DEFAULT_MODEL_NAME = "Basic"

# Current repo conventions. More languages/decks can be added here later.
DEFAULT_DECKS = {
    "spanish": [
        {"csv": "adjectives.csv", "deck": "Spanish Adjectives"},
        {"csv": "nouns_images.csv", "deck": "Spanish Image Nouns"},
        {"csv": "nouns.csv", "deck": "Spanish Nouns"},
        {"csv": "useful_phrases.csv", "deck": "Spanish Phrases"},
        {"csv": "verbs.csv", "deck": "Spanish Verbs"},
    ]
}

SOUND_RE = re.compile(r"\[sound:([^\]]+)\]")
IMG_RE = re.compile(r"<img\s+[^>]*src=[\"']([^\"']+)[\"'][^>]*>", re.IGNORECASE)


@dataclass(frozen=True)
class DeckSpec:
    csv_path: Path
    deck_name: str


@dataclass
class SyncStats:
    media_seen: int = 0
    media_uploaded: int = 0
    media_missing: int = 0
    notes_seen: int = 0
    notes_added: int = 0
    notes_updated: int = 0
    notes_unchanged: int = 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--language", default="spanish", help="Language directory to sync (default: spanish)")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Repo root (default: current directory)")
    parser.add_argument("--anki-url", default=DEFAULT_ANKI_URL, help=f"AnkiConnect URL (default: {DEFAULT_ANKI_URL})")
    parser.add_argument("--model-name", default=DEFAULT_MODEL_NAME, help=f"Anki note type/model (default: {DEFAULT_MODEL_NAME})")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing to Anki or copying media")
    parser.add_argument("--no-sync", action="store_true", help="Do not trigger AnkiWeb sync after local changes")
    parser.add_argument(
        "--copy-media-dir",
        type=Path,
        help="Optional Anki collection.media path. If set, media is copied there instead of uploaded via AnkiConnect.",
    )
    parser.add_argument(
        "--deck",
        action="append",
        metavar="CSV=DECK",
        help="Override/add a deck mapping, e.g. --deck nouns.csv='Spanish Nouns'. Can be repeated.",
    )
    return parser.parse_args()


def invoke(anki_url: str, action: str, params: dict[str, Any] | None = None) -> Any:
    payload = json.dumps({"action": action, "version": 6, "params": params or {}}).encode("utf-8")
    request = urllib.request.Request(anki_url, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise SystemExit(
            f"Could not reach AnkiConnect at {anki_url}. Open Anki Desktop and install/enable AnkiConnect.\n{exc}"
        ) from exc

    if data.get("error"):
        raise RuntimeError(f"AnkiConnect {action} failed: {data['error']}")
    return data.get("result")


def load_deck_specs(root: Path, language: str, overrides: list[str] | None) -> list[DeckSpec]:
    language_dir = root / language
    if not language_dir.exists():
        raise SystemExit(f"Language directory not found: {language_dir}")

    mappings = {item["csv"]: item["deck"] for item in DEFAULT_DECKS.get(language, [])}
    for override in overrides or []:
        if "=" not in override:
            raise SystemExit(f"Invalid --deck mapping {override!r}. Expected CSV=DECK")
        csv_name, deck_name = override.split("=", 1)
        mappings[csv_name.strip()] = deck_name.strip().strip("'\"")

    specs = [DeckSpec(language_dir / csv_name, deck_name) for csv_name, deck_name in mappings.items()]
    missing = [str(spec.csv_path) for spec in specs if not spec.csv_path.exists()]
    if missing:
        raise SystemExit("Configured CSV file(s) missing:\n" + "\n".join(missing))
    return specs


def load_csv_rows(csv_path: Path) -> list[dict[str, str]]:
    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise SystemExit(f"CSV has no header: {csv_path}")
        required = {"Front", "Back"}
        missing = required - set(reader.fieldnames)
        if missing:
            raise SystemExit(f"{csv_path} missing required columns: {', '.join(sorted(missing))}")
        return [dict(row) for row in reader]


def extract_media_names(*field_values: str) -> set[str]:
    names: set[str] = set()
    for value in field_values:
        names.update(SOUND_RE.findall(value or ""))
        names.update(html.unescape(match) for match in IMG_RE.findall(value or ""))
    return {name for name in names if name and not name.startswith(("http://", "https://", "/"))}


def find_media_file(language_dir: Path, filename: str) -> Path | None:
    for subdir in ("audio", "images"):
        candidate = language_dir / subdir / filename
        if candidate.exists():
            return candidate
    return None


def upload_or_copy_media(
    *,
    media_file: Path,
    filename: str,
    anki_url: str,
    copy_media_dir: Path | None,
    dry_run: bool,
) -> None:
    if dry_run:
        return

    if copy_media_dir:
        copy_media_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(media_file, copy_media_dir / filename)
        return

    encoded = base64.b64encode(media_file.read_bytes()).decode("ascii")
    invoke(anki_url, "storeMediaFile", {"filename": filename, "data": encoded})


def note_fields(row: dict[str, str]) -> dict[str, str]:
    return {"Front": row.get("Front", ""), "Back": row.get("Back", "")}


def load_existing_notes(anki_url: str, deck_name: str) -> dict[str, dict[str, Any]]:
    note_ids = invoke(anki_url, "findNotes", {"query": f'deck:"{deck_name}"'})
    if not note_ids:
        return {}
    notes = invoke(anki_url, "notesInfo", {"notes": note_ids})
    existing: dict[str, dict[str, Any]] = {}
    for note in notes:
        fields = note.get("fields", {})
        front = fields.get("Front", {}).get("value")
        if front is not None and front not in existing:
            existing[front] = note
    return existing


def fields_changed(existing_note: dict[str, Any], desired: dict[str, str]) -> bool:
    existing_fields = existing_note.get("fields", {})
    for key, value in desired.items():
        if existing_fields.get(key, {}).get("value") != value:
            return True
    return False


def sync_deck(
    *,
    spec: DeckSpec,
    language_dir: Path,
    anki_url: str,
    model_name: str,
    copy_media_dir: Path | None,
    dry_run: bool,
) -> SyncStats:
    rows = load_csv_rows(spec.csv_path)
    stats = SyncStats(notes_seen=len(rows))

    media_names: set[str] = set()
    for row in rows:
        media_names.update(extract_media_names(row.get("Front", ""), row.get("Back", "")))

    for filename in sorted(media_names):
        stats.media_seen += 1
        media_file = find_media_file(language_dir, filename)
        if not media_file:
            stats.media_missing += 1
            print(f"  ⚠ missing media referenced by {spec.csv_path.name}: {filename}")
            continue
        upload_or_copy_media(
            media_file=media_file,
            filename=filename,
            anki_url=anki_url,
            copy_media_dir=copy_media_dir,
            dry_run=dry_run,
        )
        stats.media_uploaded += 1

    if dry_run:
        # Avoid requiring AnkiConnect for a local preview.
        stats.notes_added = len(rows)
        return stats

    invoke(anki_url, "createDeck", {"deck": spec.deck_name})
    existing = load_existing_notes(anki_url, spec.deck_name)

    for row in rows:
        desired_fields = note_fields(row)
        front = desired_fields["Front"]
        existing_note = existing.get(front)
        if existing_note is None:
            invoke(
                anki_url,
                "addNote",
                {
                    "note": {
                        "deckName": spec.deck_name,
                        "modelName": model_name,
                        "fields": desired_fields,
                        "tags": ["language-learning", language_dir.name],
                        "options": {"allowDuplicate": False, "duplicateScope": "deck"},
                    }
                },
            )
            stats.notes_added += 1
        elif fields_changed(existing_note, desired_fields):
            invoke(anki_url, "updateNoteFields", {"note": {"id": existing_note["noteId"], "fields": desired_fields}})
            stats.notes_updated += 1
        else:
            stats.notes_unchanged += 1

    return stats


def main() -> None:
    args = parse_args()
    root = args.root.resolve()
    language_dir = root / args.language
    specs = load_deck_specs(root, args.language, args.deck)

    print(f"Syncing {args.language} decks from {root}")
    if args.dry_run:
        print("Dry run: no changes will be written.")
    elif args.copy_media_dir:
        print(f"Media mode: copy files to {args.copy_media_dir}")
    else:
        print(f"Media mode: upload files through AnkiConnect at {args.anki_url}")

    totals = SyncStats()
    for spec in specs:
        print(f"\n→ {spec.deck_name} ({spec.csv_path.relative_to(root)})")
        stats = sync_deck(
            spec=spec,
            language_dir=language_dir,
            anki_url=args.anki_url,
            model_name=args.model_name,
            copy_media_dir=args.copy_media_dir,
            dry_run=args.dry_run,
        )
        print(
            "  "
            f"notes={stats.notes_seen} add={stats.notes_added} update={stats.notes_updated} "
            f"unchanged={stats.notes_unchanged} media={stats.media_uploaded}/{stats.media_seen} "
            f"missing_media={stats.media_missing}"
        )
        for field in totals.__dataclass_fields__:
            setattr(totals, field, getattr(totals, field) + getattr(stats, field))

    if totals.media_missing:
        print(f"\nStopped before sync because {totals.media_missing} referenced media file(s) were missing.", file=sys.stderr)
        raise SystemExit(1)

    if not args.dry_run and not args.no_sync:
        print("\nTriggering Anki sync…")
        invoke(args.anki_url, "sync")

    print(
        "\nDone: "
        f"notes={totals.notes_seen} add={totals.notes_added} update={totals.notes_updated} "
        f"unchanged={totals.notes_unchanged} media={totals.media_uploaded}/{totals.media_seen}"
    )


if __name__ == "__main__":
    main()
