from __future__ import annotations

from types import SimpleNamespace

import pytest

from reddit_exporter.cli import app
from reddit_exporter.models import AccountIdentity, SubredditSubscription, SubscriptionSnapshot


class FakeService:
    def __init__(self, *_args, **_kwargs):
        self.snapshot = SubscriptionSnapshot(
            account=AccountIdentity("ExampleUser"),
            retrieved_at_utc=__import__("datetime").datetime.now(__import__("datetime").UTC),
            subscriptions=(
                SubredditSubscription("python", "r/python"),
                SubredditSubscription("learnpython", "r/learnpython"),
            ),
        )

    def login_oauth(self):
        return SimpleNamespace(account=AccountIdentity("ExampleUser"), mode="oauth")

    def whoami(self):
        return AccountIdentity("ExampleUser")

    def list_filtered(self, _text=""):
        return self.snapshot

    def export(self, *_args, **_kwargs):
        return self.snapshot

    def fetch_snapshot(self):
        return self.snapshot

    def logout(self):
        return None


def test_help(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        app.main(["--help"])
    out = capsys.readouterr().out
    assert "reddit-exporter" in out


def test_list_plain(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(app, "_service", lambda _args: FakeService())
    rc = app.main(["list", "--plain"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "r/python" in out


def test_export(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(app, "_service", lambda _args: FakeService())
    rc = app.main(["export", "--format", "json", "--output", "out.json", "--force"])
    assert rc == 0
