from __future__ import annotations

import argparse
import logging
import sys
from getpass import getpass
from pathlib import Path

from reddit_exporter.config import load_config
from reddit_exporter.core.app_service import ExporterService
from reddit_exporter.core.credentials import CredentialStore, SessionOnlyCredentialStore
from reddit_exporter.errors import (
    AppError,
    AuthenticationError,
    ConfigurationError,
    CredentialStoreError,
    ExportError,
    InsufficientScopeError,
    NetworkError,
    RateLimitError,
    RedditApiError,
)

EXIT_SUCCESS = 0
EXIT_USAGE = 2
EXIT_AUTH = 3
EXIT_SCOPE = 4
EXIT_API = 5
EXIT_EXPORT = 6


def configure_logging(debug: bool = False) -> None:
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s: %(message)s")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="reddit-exporter")
    parser.add_argument("--config", type=Path, help="Path to config.toml")
    parser.add_argument("--debug", action="store_true", help="Enable sanitized debug logs")

    sub = parser.add_subparsers(dest="command", required=True)

    login = sub.add_parser("login", help="Authenticate")
    login.add_argument("--mode", choices=["oauth", "script"], default="oauth")

    sub.add_parser("whoami", help="Show authenticated username")

    list_cmd = sub.add_parser("list", help="List subscriptions")
    list_cmd.add_argument("--filter", default="", help="Case-insensitive local filter")
    list_cmd.add_argument("--plain", action="store_true", help="Only print r/subreddit lines")

    export = sub.add_parser("export", help="Export subscriptions")
    export.add_argument("--format", required=True, choices=["txt", "csv", "json"])
    export.add_argument("--output", required=True, type=Path)
    export.add_argument("--force", action="store_true")

    sub.add_parser("refresh", help="Refresh and display count")
    sub.add_parser("logout", help="Clear saved credentials")
    sub.add_parser("gui", help="Launch Tkinter GUI")

    return parser


def _service(args: argparse.Namespace) -> ExporterService:
    config = load_config(args.config)
    try:
        store = CredentialStore()
        if not store.is_available():
            logging.info("Secure keyring unavailable; using session-only credentials.")
            store = SessionOnlyCredentialStore()
    except Exception as exc:  # noqa: BLE001
        logging.info("Secure keyring unavailable; using session-only credentials: %s", exc.__class__.__name__)
        store = SessionOnlyCredentialStore()
    return ExporterService(config=config, credential_store=store)


def _handle_error(exc: Exception) -> int:
    if isinstance(exc, ConfigurationError):
        print(str(exc), file=sys.stderr)
        return EXIT_USAGE
    if isinstance(exc, CredentialStoreError):
        print(str(exc), file=sys.stderr)
        return EXIT_USAGE
    if isinstance(exc, InsufficientScopeError):
        print(str(exc), file=sys.stderr)
        return EXIT_SCOPE
    if isinstance(exc, AuthenticationError):
        print(str(exc), file=sys.stderr)
        return EXIT_AUTH
    if isinstance(exc, (RateLimitError, RedditApiError, NetworkError)):
        print(str(exc), file=sys.stderr)
        return EXIT_API
    if isinstance(exc, ExportError):
        print(str(exc), file=sys.stderr)
        return EXIT_EXPORT
    if isinstance(exc, AppError):
        print(str(exc), file=sys.stderr)
        return EXIT_API
    print("Unexpected error. Re-run with --debug for diagnostics.", file=sys.stderr)
    return EXIT_API


def _print_snapshot(snapshot, plain: bool = False) -> None:
    if plain:
        for sub in snapshot.subscriptions:
            print(sub.display_name_prefixed)
        return
    print(f"Authenticated as: {snapshot.account.username}")
    print(f"Total subscriptions: {len(snapshot.subscriptions)}")
    for sub in snapshot.subscriptions:
        print(f"- {sub.display_name_prefixed}")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    configure_logging(args.debug)

    try:
        service = _service(args)

        if args.command == "login":
            if args.mode == "oauth":
                auth = service.login_oauth()
                print(f"Signed in as {auth.account.username} via oauth")
                return EXIT_SUCCESS

            client_id = input("Script client ID: ").strip()
            client_secret = getpass("Script client secret: ").strip()
            username = input("Reddit username: ").strip()
            password = getpass("Reddit password: ")
            otp = getpass("Temporary 2FA code (optional): ").strip() or None
            auth = service.login_script(
                client_id=client_id,
                client_secret=client_secret,
                username=username,
                **{"password": password},
                otp=otp,
            )
            print(f"Signed in as {auth.account.username} via script")
            return EXIT_SUCCESS

        if args.command == "whoami":
            identity = service.whoami()
            print(identity.username)
            return EXIT_SUCCESS

        if args.command == "list":
            snapshot = service.list_filtered(args.filter)
            _print_snapshot(snapshot, plain=args.plain)
            return EXIT_SUCCESS

        if args.command == "export":
            snapshot = service.export(args.format, args.output, force=args.force)
            print(
                f"Exported {len(snapshot.subscriptions)} subscriptions for {snapshot.account.username} to {args.output}"
            )
            return EXIT_SUCCESS

        if args.command == "refresh":
            snapshot = service.fetch_snapshot()
            print(f"Refreshed {len(snapshot.subscriptions)} subscriptions for {snapshot.account.username}")
            return EXIT_SUCCESS

        if args.command == "logout":
            service.logout()
            print("Signed out and cleared saved credentials.")
            return EXIT_SUCCESS

        if args.command == "gui":
            from reddit_exporter.gui.app import run

            run(config_path=args.config)
            return EXIT_SUCCESS

        parser.print_help()
        return EXIT_USAGE
    except Exception as exc:  # noqa: BLE001
        if args.debug:
            raise
        return _handle_error(exc)
