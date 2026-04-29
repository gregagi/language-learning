#!/usr/bin/env python3
"""Generate Anki audio files and inject [sound:...] tags into CSV rows.

Examples:
  uv run --with edge-tts python scripts/generate_anki_audio.py \
    --csv spanish/verbs.csv \
    --audio-dir spanish/audio \
    --voice es-ES-ElviraNeural

  uv run --with edge-tts python scripts/generate_anki_audio.py \
    --csv french/verbs.csv \
    --audio-dir french/audio \
    --voice fr-FR-DeniseNeural \
    --text-column Back
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import re
from pathlib import Path

import edge_tts

SOUND_RE = re.compile(r"\s*\[sound:[^\]]+\]\s*$")
PARENS_RE = re.compile(r"\s*\(.*\)")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", default="spanish/verbs.csv", help="CSV file to update")
    parser.add_argument("--audio-dir", default="spanish/audio", help="Directory for generated mp3 files")
    parser.add_argument("--voice", default="es-ES-ElviraNeural", help="edge-tts voice to use")
    parser.add_argument(
        "--text-column",
        default="Back",
        help="Header name of the column that contains the foreign-language text to speak",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Regenerate audio even if the mp3 already exists.",
    )
    parser.add_argument(
        "--keep-parenthetical",
        action="store_true",
        help="Speak the full cell text instead of stripping parenthetical conjugation/notes.",
    )
    return parser.parse_args()


def normalize_text(text: str) -> str:
    return SOUND_RE.sub("", text).strip()


def extract_spoken_text(text: str, keep_parenthetical: bool) -> str:
    clean = normalize_text(text)
    if not keep_parenthetical:
        clean = PARENS_RE.sub("", clean).strip()
    return clean.split(",", 1)[0].strip()


def target_filename(spoken_text: str) -> str:
    slug = re.sub(r"[^\w]+", "-", spoken_text.lower(), flags=re.UNICODE).strip("-")
    if not slug:
        raise ValueError(f"Could not build filename for text: {spoken_text!r}")
    return f"{slug}.mp3"


async def generate_file(text: str, voice: str, out_path: Path) -> None:
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(str(out_path))


def load_rows(csv_path: Path) -> list[list[str]]:
    with csv_path.open(newline="", encoding="utf-8") as f:
        return list(csv.reader(f))


def save_rows(csv_path: Path, rows: list[list[str]]) -> None:
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerows(rows)


async def main() -> None:
    args = parse_args()
    root = Path.cwd()
    csv_path = root / args.csv
    audio_dir = root / args.audio_dir
    audio_dir.mkdir(parents=True, exist_ok=True)

    rows = load_rows(csv_path)
    if not rows:
        raise SystemExit(f"CSV is empty: {csv_path}")

    header, *data_rows = rows
    if args.text_column not in header:
        raise SystemExit(f"Column {args.text_column!r} not found in {csv_path}: {header}")

    text_idx = header.index(args.text_column)
    generated: list[str] = []
    updated_rows = [header]

    for row in data_rows:
        if len(row) <= text_idx:
            updated_rows.append(row)
            continue

        cell = row[text_idx]
        clean_cell = normalize_text(cell)
        spoken_text = extract_spoken_text(clean_cell, args.keep_parenthetical)
        if not spoken_text:
            updated_rows.append(row)
            continue

        filename = target_filename(spoken_text)
        out_path = audio_dir / filename

        if args.force or not out_path.exists():
            await generate_file(spoken_text, args.voice, out_path)
            generated.append(str(out_path.relative_to(root)))

        row = list(row)
        row[text_idx] = f"{clean_cell} [sound:{filename}]"
        updated_rows.append(row)

    save_rows(csv_path, updated_rows)

    print(f"Updated CSV: {csv_path.relative_to(root)}")
    if generated:
        print("Generated audio files:")
        for path in generated:
            print(f"- {path}")
    else:
        print("No new audio files were needed.")


if __name__ == "__main__":
    asyncio.run(main())
