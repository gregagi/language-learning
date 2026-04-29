---
name: spanish-audio
description: Generate and maintain Spanish Anki pronunciation audio in this repo using edge-tts. Use when adding or refreshing mp3 files under spanish/audio/, updating spanish/verbs.csv with [sound:...] tags, or rerunning the reusable Spanish audio pipeline.
---

# Spanish Audio

Use the repo script to generate audio and update the CSV in one pass.

## Default command

```bash
uv run --with edge-tts python scripts/generate_spanish_audio.py
```

## What it does

- generate missing mp3 files in `spanish/audio/`
- use `es-ES-ElviraNeural` by default
- derive the spoken word from the Spanish lemma at the start of each `Back` cell
- rewrite each `Back` cell to include an Anki sound tag like `[sound:querer.mp3]`
- leave existing files alone unless `--force` is passed

## Common commands

Regenerate everything:

```bash
uv run --with edge-tts python scripts/generate_spanish_audio.py --force
```

Use a different voice:

```bash
uv run --with edge-tts python scripts/generate_spanish_audio.py --voice es-MX-DaliaNeural
```

## Notes

- Keep repo audio files under `spanish/audio/`.
- In the CSV, use only the bare filename in the sound tag, not the repo path.
- For now this workflow targets `spanish/verbs.csv`; extend the script if nouns/adjectives/phrases also need audio.
