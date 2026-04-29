---
name: anki-audio
description: Generate and maintain pronunciation audio for Anki CSV decks in this repo using edge-tts. Use when adding or refreshing mp3 files under a language audio directory, updating deck CSV rows with [sound:...] tags, or rerunning the reusable audio pipeline for Spanish or future languages.
---

# Anki Audio

Use the repo script to generate audio and update a deck CSV in one pass.

## Default pattern

```bash
uv run --with edge-tts python scripts/generate_anki_audio.py \
  --csv <language>/<deck>.csv \
  --audio-dir <language>/audio \
  --voice <edge-tts-voice>
```

## What it does

- generate missing mp3 files in the target audio directory
- derive spoken text from one CSV column
- rewrite that same column to include an Anki sound tag like `[sound:querer.mp3]`
- leave existing files alone unless `--force` is passed

## Common commands

Spanish verbs:

```bash
uv run --with edge-tts python scripts/generate_anki_audio.py \
  --csv spanish/verbs.csv \
  --audio-dir spanish/audio \
  --voice es-ES-ElviraNeural
```

Regenerate everything from scratch:

```bash
uv run --with edge-tts python scripts/generate_anki_audio.py \
  --csv spanish/verbs.csv \
  --audio-dir spanish/audio \
  --voice es-ES-ElviraNeural \
  --force
```

Use a different column or language:

```bash
uv run --with edge-tts python scripts/generate_anki_audio.py \
  --csv french/verbs.csv \
  --audio-dir french/audio \
  --voice fr-FR-DeniseNeural \
  --text-column Back
```

## Notes

- Keep repo audio files under `<language>/audio/`.
- In the CSV, use only the bare filename in the sound tag, not the repo path.
- By default, the script strips trailing sound tags and parenthetical notes before speaking.
- Use `--keep-parenthetical` if the full cell text should be spoken.
