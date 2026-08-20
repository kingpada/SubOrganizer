from __future__ import annotations

import pytest

from reddit_exporter.core.credentials import CredentialStore, SessionOnlyCredentialStore
from reddit_exporter.errors import CredentialStoreError


class FakeBackend:
    priority = 1


class MissingBackend:
    priority = 0


def test_session_store_roundtrip() -> None:
    store = SessionOnlyCredentialStore()
    store.set_secret("k", "v")
    assert store.get_secret("k") == "v"
    store.delete_secret("k")
    assert store.get_secret("k") is None


def test_keyring_backend_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("reddit_exporter.core.credentials.keyring.get_keyring", lambda: MissingBackend())
    with pytest.raises(CredentialStoreError):
        CredentialStore().set_secret("a", "b")


def test_keyring_roundtrip(monkeypatch: pytest.MonkeyPatch) -> None:
    memory: dict[tuple[str, str], str] = {}

    monkeypatch.setattr("reddit_exporter.core.credentials.keyring.get_keyring", lambda: FakeBackend())
    monkeypatch.setattr(
        "reddit_exporter.core.credentials.keyring.set_password",
        lambda service, key, value: memory.__setitem__((service, key), value),
    )
    monkeypatch.setattr(
        "reddit_exporter.core.credentials.keyring.get_password",
        lambda service, key: memory.get((service, key)),
    )
    monkeypatch.setattr(
        "reddit_exporter.core.credentials.keyring.delete_password",
        lambda service, key: memory.pop((service, key), None),
    )

    store = CredentialStore()
    store.set_secret("x", "y")
    assert store.get_secret("x") == "y"
    store.delete_secret("x")
    assert store.get_secret("x") is None
