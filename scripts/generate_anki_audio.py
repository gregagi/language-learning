#!/usr/bin/env python3
"""Generate Anki audio files and inject [sound:...] tags into CSV rows.

Examples:
  uv run --with edge-tts python scripts/generate_anki_audio.py \
    --preset spanish-verbs

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
import json
import re
import unicodedata
from pathlib import Path

import edge_tts

DEFAULT_CONFIG = "anki-audio-presets.json"
SOUND_RE = re.compile(r"\s*\[sound:[^\]]+\]\s*$")
PARENS_RE = re.compile(r"\s*\(.*\)")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preset", help="Preset name from the config file")
    parser.add_argument("--config", default=DEFAULT_CONFIG, help=f"Preset config path (default: {DEFAULT_CONFIG})")
    parser.add_argument("--csv", help="CSV file to update")
    parser.add_argument("--audio-dir", help="Directory for generated mp3 files")
    parser.add_argument("--voice", help="edge-tts voice to use")
    parser.add_argument(
        "--text-column",
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


def load_preset(root: Path, config_path: str, preset_name: str | None) -> dict:
    if not preset_name:
        return {}
    config_file = root / config_path
    data = json.loads(config_file.read_text(encoding="utf-8"))
    presets = data.get("presets", {})
    if preset_name not in presets:
        known = ", ".join(sorted(presets)) or "<none>"
        raise SystemExit(f"Preset {preset_name!r} not found in {config_file}. Known presets: {known}")
    return presets[preset_name]


def resolve_setting(cli_value, preset_value, default_value=None):
    if cli_value is not None:
        return cli_value
    if preset_value is not None:
        return preset_value
    return default_value


def normalize_text(text: str) -> str:
    return SOUND_RE.sub("", text).strip()


def extract_spoken_text(text: str, keep_parenthetical: bool) -> str:
    clean = normalize_text(text)
    if not keep_parenthetical:
        clean = PARENS_RE.sub("", clean).strip()
    return clean.strip()


def ascii_slug(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", ascii_only.lower()).strip("-")


def target_filename(spoken_text: str) -> str:
    slug = ascii_slug(spoken_text)
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
    preset = load_preset(root, args.config, args.preset)

    csv_value = resolve_setting(args.csv, preset.get("csv"), "spanish/verbs.csv")
    audio_dir_value = resolve_setting(args.audio_dir, preset.get("audio_dir"), "spanish/audio")
    voice = resolve_setting(args.voice, preset.get("voice"), "es-ES-ElviraNeural")
    text_column = resolve_setting(args.text_column, preset.get("text_column"), "Back")
    keep_parenthetical = args.keep_parenthetical or bool(preset.get("keep_parenthetical", False))

    csv_path = root / csv_value
    audio_dir = root / audio_dir_value
    audio_dir.mkdir(parents=True, exist_ok=True)

    rows = load_rows(csv_path)
    if not rows:
        raise SystemExit(f"CSV is empty: {csv_path}")

    header, *data_rows = rows
    if text_column not in header:
        raise SystemExit(f"Column {text_column!r} not found in {csv_path}: {header}")

    text_idx = header.index(text_column)
    generated: list[str] = []
    updated_rows = [header]

    for row in data_rows:
        if len(row) <= text_idx:
            updated_rows.append(row)
            continue

        cell = row[text_idx]
        clean_cell = normalize_text(cell)
        spoken_text = extract_spoken_text(clean_cell, keep_parenthetical)
        if not spoken_text:
            updated_rows.append(row)
            continue

        filename = target_filename(spoken_text)
        out_path = audio_dir / filename

        if args.force or not out_path.exists():
            await generate_file(spoken_text, voice, out_path)
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
