#!/usr/bin/env python3
"""Build an image-based Anki deck plus a prompt manifest from an existing CSV deck.

This script does not generate images or manage provider auth. For agent-generated
images in this repo, prefer OpenAI image generation through OpenClaw's OpenAI
Codex OAuth subscription auth, e.g. `image_generate` with `openai/gpt-image-2`.
Do not require a direct OpenAI API key for the default image workflow.

Examples:
  python scripts/generate_anki_image_deck.py --preset spanish-nouns-images

  python scripts/generate_anki_image_deck.py \
    --source-csv spanish/nouns.csv \
    --output-csv spanish/nouns_images.csv \
    --image-dir spanish/images \
    --prompt-output spanish/images/nouns_image_prompts.csv
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import re
import unicodedata
from pathlib import Path

DEFAULT_CONFIG = "anki-image-presets.json"
SOUND_RE = re.compile(r"\s*\[sound:[^\]]+\]\s*$")
PARENS_RE = re.compile(r"\s*\([^)]*\)")
LEADING_ARTICLE_RE = re.compile(r"^(the|a|an)\s+", re.IGNORECASE)

DEFAULT_PROMPT_TEMPLATE = (
    "A realistic photo clearly showing {concept}. "
    "No visible words, letters, signs, logos, labels, menus, or watermarks anywhere in the image. "
    "Use a clean composition that makes the concept instantly recognizable for a language learner."
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preset", help="Preset name from the config file")
    parser.add_argument("--config", default=DEFAULT_CONFIG, help=f"Preset config path (default: {DEFAULT_CONFIG})")
    parser.add_argument("--source-csv", help="Source CSV to read from")
    parser.add_argument("--output-csv", help="Image-based CSV deck to write")
    parser.add_argument("--image-dir", help="Directory for image files")
    parser.add_argument("--prompt-output", help="CSV file to write generation prompts to")
    parser.add_argument("--front-column", help="Header name for the source-language gloss column")
    parser.add_argument("--back-column", help="Header name for the target-language answer column")
    parser.add_argument("--prompt-template", help="Prompt template with variables like {concept}, {front}, {back}, {basename}")
    parser.add_argument("--limit", type=int, help="Optional row limit for experiments")
    parser.add_argument("--overwrite-output", action="store_true", help="Overwrite the output deck even if it exists")
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


def strip_parenthetical(text: str) -> str:
    return PARENS_RE.sub("", text).strip()


def ascii_slug(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", ascii_only.lower()).strip("-")


def concept_from_front(front: str) -> str:
    clean = strip_parenthetical(front)
    clean = LEADING_ARTICLE_RE.sub("", clean).strip()
    return clean


def load_rows(csv_path: Path) -> list[list[str]]:
    with csv_path.open(newline="", encoding="utf-8") as f:
        return list(csv.reader(f))


def save_rows(csv_path: Path, rows: list[list[str]]) -> None:
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerows(rows)


def render_prompt(template: str, front: str, back: str, concept: str, basename: str) -> str:
    return template.format(front=front, back=back, concept=concept, basename=basename)


def display_path(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def main() -> None:
    args = parse_args()
    root = Path.cwd()
    preset = load_preset(root, args.config, args.preset)

    source_csv_value = resolve_setting(args.source_csv, preset.get("source_csv"))
    output_csv_value = resolve_setting(args.output_csv, preset.get("output_csv"))
    image_dir_value = resolve_setting(args.image_dir, preset.get("image_dir"))
    prompt_output_value = resolve_setting(args.prompt_output, preset.get("prompt_output"))
    front_column = resolve_setting(args.front_column, preset.get("front_column"), "Front")
    back_column = resolve_setting(args.back_column, preset.get("back_column"), "Back")
    prompt_template = resolve_setting(args.prompt_template, preset.get("prompt_template"), DEFAULT_PROMPT_TEMPLATE)
    limit = resolve_setting(args.limit, preset.get("limit"))

    if not source_csv_value or not output_csv_value or not image_dir_value or not prompt_output_value:
        raise SystemExit("source/output/image-dir/prompt-output are required either via CLI or preset")

    source_csv = root / source_csv_value
    output_csv = root / output_csv_value
    image_dir = root / image_dir_value
    prompt_output = root / prompt_output_value

    if output_csv.exists() and not args.overwrite_output:
        raise SystemExit(f"Output already exists: {output_csv}. Pass --overwrite-output to replace it.")

    image_dir.mkdir(parents=True, exist_ok=True)
    prompt_output.parent.mkdir(parents=True, exist_ok=True)
    output_csv.parent.mkdir(parents=True, exist_ok=True)

    rows = load_rows(source_csv)
    if not rows:
        raise SystemExit(f"CSV is empty: {source_csv}")

    header, *data_rows = rows
    if front_column not in header or back_column not in header:
        raise SystemExit(f"Missing expected columns in {source_csv}: {header}")

    front_idx = header.index(front_column)
    back_idx = header.index(back_column)

    output_rows = [["Front", "Back"]]
    prompt_rows = [["Front", "Back", "Concept", "ImageFilename", "Prompt"]]

    count = 0
    for row in data_rows:
        if limit is not None and count >= limit:
            break
        if len(row) <= max(front_idx, back_idx):
            continue

        front = row[front_idx].strip()
        back = row[back_idx].strip()
        if not front or not back:
            continue

        clean_back = normalize_text(back)
        concept = concept_from_front(front) or front
        basename = ascii_slug(clean_back)
        if not basename:
            raise SystemExit(f"Could not derive image filename from row: {row}")
        image_filename = f"{basename}.jpg"
        prompt = render_prompt(prompt_template, front=front, back=clean_back, concept=concept, basename=basename)

        output_rows.append([f'<img src="{html.escape(image_filename, quote=True)}">', back])
        prompt_rows.append([front, clean_back, concept, image_filename, prompt])
        count += 1

    save_rows(output_csv, output_rows)
    save_rows(prompt_output, prompt_rows)

    print(f"Wrote image deck: {display_path(output_csv, root)}")
    print(f"Wrote prompt manifest: {display_path(prompt_output, root)}")
    print(f"Image directory: {display_path(image_dir, root)}")
    print(f"Rows: {count}")


if __name__ == "__main__":
    main()
