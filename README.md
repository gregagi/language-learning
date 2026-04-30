# language-learning

Anki import files for practical language learning.

## Structure

- `spanish/` - Spanish decks and import files
- future languages get their own directories at the repo root

## Importing into Anki

Most files are simple CSV imports.

Typical mapping:
- Front/Back vary by deck, and many decks include both directions in the same CSV.

Start small, keep decks practical, and optimize for real-world communication.

## Current Spanish starter decks

- `spanish/nouns.csv`
- `spanish/verbs.csv`
- `spanish/adjectives.csv`
- `spanish/useful_phrases.csv`
- `spanish/nouns_images.csv` - experimental image -> Spanish noun deck

## Anki audio workflow

This repo now includes a reusable pronunciation workflow for Anki across languages:

- audio files live in `<language>/audio/`
- deck CSVs store inline Anki sound tags like `[sound:querer.mp3]`
- the generation script is `scripts/generate_anki_audio.py`
- preset defaults live in `anki-audio-presets.json`
- the repo-local skill is `skills/anki-audio/SKILL.md`

Spanish verbs example:

```bash
uv run --with edge-tts python scripts/generate_anki_audio.py --preset spanish-verbs
```

Other current presets:

- `spanish-nouns`
- `spanish-adjectives`
- `spanish-useful-phrases`

To regenerate from scratch:

```bash
uv run --with edge-tts python scripts/generate_anki_audio.py --preset spanish-verbs --force
```

## Anki image workflow

This repo also includes a reusable image-based deck workflow for any language:

- image files live in `<language>/images/`
- image-based deck CSVs reference bare filenames with HTML like `<img src="el-cafe.jpg">`
- the helper script is `scripts/generate_anki_image_deck.py`
- preset defaults live in `anki-image-presets.json`
- the repo-local skill is `skills/anki-images/SKILL.md`

Important: the script only scaffolds the deck CSV plus a prompt manifest. The actual image creation step happens separately via an image-generation tool/model or manual sourcing.

Spanish nouns example:

```bash
uv run python scripts/generate_anki_image_deck.py --preset spanish-nouns-images --overwrite-output
```

The script writes:

- an image-based deck CSV such as `spanish/nouns_images.csv`
- an editable prompt manifest such as `spanish/nouns_image_prompts.csv`

Use the prompt manifest as a starting point, then review and tighten prompts for ambiguous concepts before generating images at scale.
