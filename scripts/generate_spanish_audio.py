#!/usr/bin/env python3
"""Generate Spanish Anki audio files and inject sound tags into CSV rows.

Usage:
  uv run --with edge-tts python scripts/generate_spanish_audio.py
  uv run --with edge-tts python scripts/generate_spanish_audio.py --force
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import re
from pathlib import Path

import edge_tts

DEFAULT_VOICE = "es-ES-ElviraNeural"
SOUND_RE = re.compile(r"\s*\[sound:[^\]]+\]\s*$")
PARENS_RE = re.compile(r"\s*\(.*\)")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--csv",
        default="spanish/verbs.csv",
        help="CSV file to update (default: spanish/verbs.csv)",
    )
    parser.add_argument(
        "--audio-dir",
        default="spanish/audio",
        help="Directory for generated mp3 files (default: spanish/audio)",
    )
    parser.add_argument(
        "--voice",
        default=DEFAULT_VOICE,
        help=f"edge-tts voice to use (default: {DEFAULT_VOICE})",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Regenerate audio even if the mp3 already exists.",
    )
    return parser.parse_args()


def normalize_back(text: str) -> str:
    return SOUND_RE.sub("", text).strip()


def extract_lemma(text: str) -> str:
    clean = normalize_back(text)
    clean = PARENS_RE.sub("", clean).strip()
    return clean.split(",", 1)[0].strip()


def target_filename(lemma: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", lemma.lower()).strip("-")
    if not slug:
        raise ValueError(f"Could not build filename for lemma: {lemma!r}")
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
    if len(header) < 2 or header[:2] != ["Front", "Back"]:
        raise SystemExit(f"Unexpected CSV header in {csv_path}: {header}")

    generated = []
    updated_rows = [header]

    for row in data_rows:
        if len(row) < 2:
            updated_rows.append(row)
            continue

        front, back = row[0], row[1]
        clean_back = normalize_back(back)
        lemma = extract_lemma(clean_back)
        filename = target_filename(lemma)
        out_path = audio_dir / filename

        if args.force or not out_path.exists():
            await generate_file(lemma, args.voice, out_path)
            generated.append(str(out_path.relative_to(root)))

        tagged_back = f"{clean_back} [sound:{filename}]"
        updated_rows.append([front, tagged_back, *row[2:]])

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
