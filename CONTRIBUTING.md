# Contributing

1. Open an issue describing the change and expected behavior.
2. Add or update tests for contracts and edge cases.
3. Keep provider-specific logic inside the provider adapter.
4. Preserve `content_id`; do not silently discard source URLs or claims requiring verification.
5. Never add secrets, voice samples, copyrighted media, or client assets to Git.
6. Run `ruff check .`, `ruff format --check .`, and `pytest` before submitting.
