# Copilot Instructions

- Keep architecture layered: `core` contains business logic, `cli` and `gui` are presentation only.
- Product scope is personal, local, read-only Reddit subscription management/export.
- Do not add Reddit write actions (no posting, voting, messaging, moderation, subscribe/unsubscribe).
- Keep secrets out of source control; never commit credentials or tokens.
- Use secure keyring storage where available; no plaintext secret fallback.
- Run tests with `pytest`.
- CLI/GUI must continue using shared core services; avoid duplicated business logic.
