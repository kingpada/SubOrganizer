from __future__ import annotations

import secrets
import threading
import webbrowser
from collections.abc import Callable
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from queue import Empty, Queue
from urllib.parse import parse_qs, urlparse

from reddit_exporter.errors import AuthenticationError, AuthorizationDenied, OAuthStateMismatch
from reddit_exporter.models import AccountIdentity

SCOPES = ["identity", "mysubreddits"]


@dataclass(frozen=True, slots=True)
class OAuthCallbackResult:
    code: str | None
    state: str | None
    error: str | None


class _CallbackServer:
    def __init__(self, redirect_uri: str, timeout_seconds: int = 180) -> None:
        self.redirect_uri = redirect_uri
        self.timeout_seconds = timeout_seconds
        parsed = urlparse(redirect_uri)
        host = (parsed.hostname or "").lower()
        if host not in {"localhost", "127.0.0.1"}:
            raise AuthenticationError("OAuth redirect URI must use localhost or 127.0.0.1.")
        self._host = "127.0.0.1" if host == "127.0.0.1" else "localhost"
        self._port = parsed.port or 80
        self._path = parsed.path or "/"
        self._queue: Queue[OAuthCallbackResult] = Queue(maxsize=1)
        self._server: HTTPServer | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        queue = self._queue
        expected_path = self._path

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802
                parsed = urlparse(self.path)
                if parsed.path != expected_path:
                    self.send_response(404)
                    self.end_headers()
                    return
                values = parse_qs(parsed.query)
                result = OAuthCallbackResult(
                    code=(values.get("code", [None])[0]),
                    state=(values.get("state", [None])[0]),
                    error=(values.get("error", [None])[0]),
                )
                if queue.empty():
                    queue.put(result)
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(b"<html><body>Authentication complete. You can close this window.</body></html>")

            def log_message(self, format: str, *args):  # noqa: A003
                return

        try:
            self._server = HTTPServer((self._host, self._port), Handler)
        except OSError as exc:
            raise AuthenticationError("OAuth callback listener could not start. Port may be in use.") from exc

        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def wait_for_callback(self) -> OAuthCallbackResult:
        try:
            return self._queue.get(timeout=self.timeout_seconds)
        except Empty as exc:
            raise AuthenticationError("Timed out waiting for Reddit OAuth callback.") from exc

    def shutdown(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            self._server = None


def generate_oauth_state() -> str:
    return secrets.token_urlsafe(32)


def authenticate_via_oauth(
    reddit,
    *,
    redirect_uri: str,
    browser_opener: Callable[[str], bool] = webbrowser.open,
    timeout_seconds: int = 180,
) -> tuple[AccountIdentity, str]:
    state = generate_oauth_state()
    auth_url = reddit.auth.url(SCOPES, state, "permanent")

    listener = _CallbackServer(redirect_uri=redirect_uri, timeout_seconds=timeout_seconds)
    listener.start()

    try:
        browser_opener(auth_url)

        callback = listener.wait_for_callback()
        if callback.error:
            raise AuthorizationDenied("Reddit authorization was cancelled or denied.")
        if not callback.code:
            raise AuthenticationError("OAuth callback did not include an authorization code.")
        if not callback.state:
            raise AuthenticationError("OAuth callback did not include state.")
        if not secrets.compare_digest(callback.state, state):
            raise OAuthStateMismatch("OAuth state validation failed.")

        refresh_token = reddit.auth.authorize(callback.code)
        me = reddit.user.me()
        username = str(getattr(me, "name", "")).strip()
        return AccountIdentity(username=username), refresh_token
    except AuthorizationDenied:
        raise
    except OAuthStateMismatch:
        raise
    except AuthenticationError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise AuthenticationError("Reddit authentication failed.") from exc
    finally:
        listener.shutdown()
