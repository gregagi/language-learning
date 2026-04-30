---
name: anki-images
description: Generate and maintain image-based Anki CSV decks in this repo for Spanish or future languages. Use when creating image -> foreign-language cards, preparing prompt manifests for image generation, storing media under a language image directory, or updating deck CSV rows to reference image filenames.
---

# Anki Images

Use the repo script to build an image-based deck CSV and a prompt manifest from an existing deck.

## Preferred pattern

Use presets when they exist:

```bash
uv run python scripts/generate_anki_image_deck.py --preset <preset-name> --overwrite-output
```

Or pass explicit arguments:

```bash
uv run python scripts/generate_anki_image_deck.py \
  --source-csv <language>/<deck>.csv \
  --output-csv <language>/<deck>_images.csv \
  --image-dir <language>/images \
  --prompt-output <language>/<deck>_image_prompts.csv \
  --overwrite-output
```

## What it does

- read a source CSV deck
- build a new image-based CSV whose front side is `<img src="...">`
- preserve the existing answer side, including audio tags when present
- write a prompt manifest that can be used to generate or source images
- derive stable image filenames from the target-language text

## Prompt guidance

Use the generated prompts as a starting point, then tighten or override them when a concept is ambiguous.

Default prompt goals:
- show the real-world concept, not text on a sign or label
- forbid visible words, letters, logos, labels, menus, or watermarks
- keep composition clear and recognizably centered on the concept

For ambiguous nouns, rewrite the prompt to describe the intended sense more concretely.
Examples:
- `café` may need a café place/interior scene instead of just a coffee cup
- `bill` may need a restaurant check, not a paper invoice or a bird beak

## Suggested workflow

1. Run the script to generate the image deck CSV and prompt manifest.
2. Review the prompt manifest and adjust rows that are too vague.
3. Generate or source images into `<language>/images/` using the filenames from the manifest.
4. Import the CSV into Anki and copy image files into Anki media alongside audio.
5. Inspect a few sample cards for concept quality before scaling.

## Common commands

Spanish noun prototype:

```bash
uv run python scripts/generate_anki_image_deck.py --preset spanish-nouns-images --overwrite-output
```

Small experiment first:

```bash
uv run python scripts/generate_anki_image_deck.py --preset spanish-nouns-images --limit 5 --overwrite-output
```

Use a different language or deck:

```bash
uv run python scripts/generate_anki_image_deck.py \
  --source-csv french/nouns.csv \
  --output-csv french/nouns_images.csv \
  --image-dir french/images \
  --prompt-output french/nouns_image_prompts.csv \
  --overwrite-output
```

## Notes

- Keep repo image files under `<language>/images/`.
- In the CSV, use only the bare filename in the image tag, not the repo path.
- Presets live in `anki-image-presets.json`.
- The prompt manifest is intentionally editable; do not treat generated prompts as final truth.
- Review generated images for hidden text, wrong senses, and overly stylized outputs before scaling.
