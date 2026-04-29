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

## Spanish audio workflow

This repo now includes a reusable Spanish pronunciation workflow for Anki:

- audio files live in `spanish/audio/`
- `spanish/verbs.csv` stores inline Anki sound tags like `[sound:querer.mp3]`
- the generation script is `scripts/generate_spanish_audio.py`
- the repo-local skill is `skills/spanish-audio/SKILL.md`

Run it with:

```bash
uv run --with edge-tts python scripts/generate_spanish_audio.py
```

To regenerate all verb audio files from scratch:

```bash
uv run --with edge-tts python scripts/generate_spanish_audio.py --force
```
