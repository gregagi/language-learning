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

## Local Anki sync workflow

You can sync the repo CSVs and media into Anki Desktop without manually dragging files into `collection.media` or re-importing each CSV.

Requirements:

1. Open Anki Desktop on the computer that owns the collection.
2. Install the AnkiConnect add-on (`2055492159`).
3. Run a dry-run first:

```bash
uv run python scripts/sync_to_anki.py --language spanish --dry-run
```

Then run the real sync:

```bash
uv run python scripts/sync_to_anki.py --language spanish
```

Current Spanish deck mapping:

- `spanish/adjectives.csv` → `Spanish Adjectives`
- `spanish/nouns_images.csv` → `Spanish Image Nouns`
- `spanish/nouns.csv` → `Spanish Nouns`
- `spanish/useful_phrases.csv` → `Spanish Phrases`
- `spanish/verbs.csv` → `Spanish Verbs`

By default, media is uploaded through AnkiConnect. If you prefer direct file copy, pass your local media directory:

```bash
uv run python scripts/sync_to_anki.py \
  --language spanish \
  --copy-media-dir "/Users/rasul/Library/Application Support/Anki2/User 1/collection.media"
```

The script creates missing decks, uploads/copies referenced `[sound:...]` and `<img src="...">` files, adds new notes, updates existing notes matched by their `Front` field inside each deck, and triggers Anki sync unless `--no-sync` is passed.

It also cleans up two old manual-import artifacts when run against AnkiConnect:

- deletes accidental literal header notes where the note content is `Front` / `Back`
- normalizes stale notes whose `Front` had an old trailing parenthetical, like `to want (querer)`, when the current CSV now uses `to want`

## Anki image workflow

This repo also includes a reusable image-based deck workflow for any language:

- image files live in `<language>/images/`
- image-based deck CSVs reference bare filenames with HTML like `<img src="el-cafe.jpg">`
- the helper script is `scripts/generate_anki_image_deck.py`
- preset defaults live in `anki-image-presets.json`
- the repo-local skill is `skills/anki-images/SKILL.md`

Important: the script only scaffolds the deck CSV plus a prompt manifest. The actual image creation step happens separately via an image-generation tool/model or manual sourcing.

Preferred generation path: use OpenAI image generation through OpenClaw's OpenAI Codex OAuth subscription auth, for example `image_generate` with `openai/gpt-image-2`. Do not require or document a direct `OPENAI_API_KEY` for this workflow; the intended auth path is the same Codex OAuth subscription used by the agents/chats.

Spanish nouns example:

```bash
uv run python scripts/generate_anki_image_deck.py --preset spanish-nouns-images --overwrite-output
```

The script writes:

- an image-based deck CSV such as `spanish/nouns_images.csv`
- an editable prompt manifest in the image directory, such as `spanish/images/nouns_image_prompts.csv`

Use the prompt manifest as a starting point, then review and tighten prompts for ambiguous concepts before generating images at scale. Prompt manifests live next to images because they are generation metadata, not import decks.
