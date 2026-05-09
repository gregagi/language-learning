# Changelog

## Unreleased

- Added 11 Spanish color adjectives with pronunciation audio to the adjectives deck.
- Added `playground` to the shared noun seed list, Spanish noun deck, and Spanish image noun deck.
- Moved the Spanish image prompt manifest into `spanish/images/` so generation metadata lives with generated images instead of deck CSVs.
- Hardened `scripts/sync_to_anki.py` to remove accidental `Front`/`Back` header notes and normalize stale note fronts with old trailing parentheticals when syncing current CSV rows.
- Added three Spanish image noun cards for water, bathroom, and table, including generated flashcard images.
- Added a local `scripts/sync_to_anki.py` workflow that syncs Spanish CSV decks and referenced audio/image media into Anki via AnkiConnect, with dry-run, optional direct media copy, note upserts, and AnkiWeb sync trigger support.
