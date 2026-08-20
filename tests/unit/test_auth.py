from __future__ import annotations

import pytest

from reddit_exporter.core.auth import authenticate_via_oauth, generate_oauth_state
from reddit_exporter.errors import AuthenticationError, OAuthStateMismatch


class FakeAuth:
    def __init__(self):
        self.state = None

    def url(self, _scopes, state, _duration):
        self.state = state
        return "http://example.test/auth"

    def authorize(self, code):
        if code == "good-code":
            return "refresh-token"
        raise AuthenticationError("bad code")


class FakeUser:
    @staticmethod
    def me():
        class U:
            name = "ExampleUser"

        return U()


class FakeReddit:
    def __init__(self):
        self.auth = FakeAuth()
        self.user = FakeUser()


def test_state_generation_entropy() -> None:
    assert generate_oauth_state() != generate_oauth_state()


def test_oauth_state_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    from reddit_exporter.core import auth as auth_mod

    class FakeServer:
        def __init__(self, *_, **__):
            pass

        def start(self):
            return None

        def wait_for_callback(self):
            return auth_mod.OAuthCallbackResult(code="good-code", state="wrong", error=None)

        def shutdown(self):
            return None

    monkeypatch.setattr(auth_mod, "_CallbackServer", FakeServer)

    with pytest.raises(OAuthStateMismatch):
        authenticate_via_oauth(FakeReddit(), redirect_uri="http://localhost:8080", browser_opener=lambda _url: True)


def test_oauth_missing_code(monkeypatch: pytest.MonkeyPatch) -> None:
    from reddit_exporter.core import auth as auth_mod

    class FakeServer:
        def __init__(self, *_, **__):
            pass

        def start(self):
            return None

        def wait_for_callback(self):
            return auth_mod.OAuthCallbackResult(code=None, state="state", error=None)

        def shutdown(self):
            return None

    monkeypatch.setattr(auth_mod, "_CallbackServer", FakeServer)
    monkeypatch.setattr(auth_mod, "generate_oauth_state", lambda: "state")

    with pytest.raises(AuthenticationError):
        authenticate_via_oauth(FakeReddit(), redirect_uri="http://localhost:8080", browser_opener=lambda _url: True)
