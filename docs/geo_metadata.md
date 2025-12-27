# Geo Metadata Integration

This repository seeds restaurant metadata with deterministic location values (city, state, latitude, longitude) generated in `scripts/generate_seed_data.py`. The same metadata is persisted to Postgres (`restaurants` table), Whoosh (lexical index), and Qdrant payloads (semantic index).

## Current Flow

- **Seeding**: `scripts/generate_seed_data.py` emits `city`, `state`, and `(latitude, longitude)` for each restaurant. The seed data is stored in `input/` JSON files.
- **Ingestion**: `src/ingest.py` and `src/ingest_qdrant_postgres.py` propagate those fields to Whoosh documents and Qdrant payloads.
- **Storage**: `src/db/postgres.py` stores the same metadata in the `restaurants` table, exposing it for downstream joins and filters.
- **Search**: `src/search/hybrid_search.py` merges lexical and semantic results while preserving the geo metadata so location-aware filters can run locally.

## Future Geocoding Hook

When ready to replace the seeded coordinates with live geocoding:

1. Introduce a geocoding client that converts the restaurant street address into `(latitude, longitude)` and structured city/state values.
2. Call the geocoding client inside the ingestion flow before inserting restaurants (see `ingest_qdrant_postgres.py`).
3. Persist the geocoding response in the same fields (`city`, `state`, `latitude`, `longitude`) so no downstream changes are required.
4. Optionally cache or memoize geocoding lookups to avoid rate limits.

Because the schema and search stack already expect these fields, swapping in a real geocoder requires no changes beyond the ingestion step that populates the metadata.
