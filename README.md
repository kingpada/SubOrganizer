# Reddit Subreddit Exporter

A personal, local, non-commercial, **read-only** Reddit account utility for exporting your own subscribed subreddit list.

## What this project does

- Authenticates the account owner (OAuth browser flow by default, script auth as advanced mode)
- Verifies the authenticated username
- Retrieves the complete `/subreddits/mine/subscriber` listing via PRAW (`limit=None`)
- Deduplicates case-insensitively, preserves canonical casing, sorts deterministically
- Provides local search/filter and sorting
- Exports to UTF-8 TXT, CSV, and JSON with atomic writes
- Provides both CLI and native Tkinter desktop GUI using one shared core layer

## What this project does **not** do

- No scraping
- No bot/service hosting
- No posting, commenting, voting, messaging, moderation, subscribe/unsubscribe, or account changes
- No telemetry/analytics/cloud sync/data resale/model training
- No access to other users' private subreddit subscriptions

## Scope

Personal, local, read-only account-management backup/export utility for the account owner only.

## Requirements

- Python 3.10+ (3.12 recommended)
- Reddit Data API app registration/approval for your account

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

Development:

```bash
python -m pip install -e ".[dev]"
```

## Configuration

Copy `config.example.toml` to your local config file (for example `~/.config/reddit-subreddit-exporter/config.toml`) and update non-secret fields.

Precedence:
1. explicit CLI option (`--config`)
2. environment variables
3. user config file
4. packaged defaults

Do not store real secrets in TOML.

## Authentication modes

### 1) Browser OAuth (default)

- Uses minimum read scopes: `identity`, `mysubreddits`
- Loopback callback on localhost/127.0.0.1 (default `http://localhost:8080`)
- Cryptographic OAuth state + constant-time validation
- Stores refresh token in OS keyring (`reddit-subreddit-exporter` service)

### 2) Advanced script auth

- Prompts for client ID, client secret, username, password, optional OTP
- Password/OTP are never persisted by default
- Uses masked GUI fields and hidden CLI prompts
- Keep in mind OAuth and script auth often require different Reddit app registrations

## Secure credential storage

Uses `keyring` and OS secure credential store where available.

If secure keyring backend is unavailable, session-only operation remains available; no plaintext fallback is used.

## CLI usage

```bash
reddit-exporter --help
reddit-exporter login
reddit-exporter login --mode oauth
reddit-exporter login --mode script
reddit-exporter whoami
reddit-exporter list
reddit-exporter list --filter python
reddit-exporter list --plain
reddit-exporter export --format txt --output subreddits.txt
reddit-exporter export --format csv --output subreddits.csv
reddit-exporter export --format json --output subreddits.json
reddit-exporter export --format json --output subreddits.json --force
reddit-exporter refresh
reddit-exporter logout
reddit-exporter gui
python -m reddit_exporter
```

### Exit codes

- `0` success
- `2` invalid usage/configuration
- `3` authentication failure
- `4` authorization/scope failure
- `5` Reddit/network/API failure
- `6` filesystem/export failure

## GUI usage

```bash
reddit-exporter gui
# or
python run_gui.py
```

GUI features:
- Sign in with Reddit (OAuth)
- Advanced authentication dialog (script)
- Refresh
- Local search/filter (no API calls)
- Export (TXT/CSV/JSON)
- Sign out/clear session

## Export formats

- TXT: one `r/subreddit` per line, trailing newline
- CSV: header `subreddit`, canonical names without `r/`
- JSON: account, UTC retrieval timestamp, count, subreddit array; pretty printed and deterministic

All exports use atomic write/replace in destination directory.

## Privacy & security

- Read-only scope and behavior
- No token/password logging
- Sanitized local logging
- Loopback-only OAuth callback server with timeout
- No shell-based browser launch (`webbrowser` module used)

## Rate limits

Respects Reddit API/PRAW rate limiting behavior and surfaces actionable errors.

## Troubleshooting

- **Redirect URI mismatch**: ensure configured redirect URI exactly matches Reddit app registration.
- **Keyring unavailable**: install/configure a secure OS keyring backend; session-only still works.
- **Scope errors**: sign in again and approve read scopes.

## Testing

```bash
pytest
```

Tests run without real Reddit credentials using fakes/mocks.

## Optional packaging

You can package the GUI with PyInstaller after verifying source behavior. Source correctness is the primary deliverable.

## Developer note

Reddit developer/API requirements can change. Re-check official docs before future API/auth changes.
