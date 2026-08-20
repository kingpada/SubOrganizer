from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from reddit_exporter.core.exporters import export_snapshot, render_csv, render_json, render_txt
from reddit_exporter.errors import ExportError
from reddit_exporter.models import AccountIdentity, SubredditSubscription, SubscriptionSnapshot


def make_snapshot() -> SubscriptionSnapshot:
    return SubscriptionSnapshot(
        account=AccountIdentity(username="ExampleUser"),
        retrieved_at_utc=datetime(2026, 8, 20, 12, 34, 56, tzinfo=UTC),
        subscriptions=(
            SubredditSubscription(name="AskReddit", display_name_prefixed="r/AskReddit"),
            SubredditSubscription(name="learnpython", display_name_prefixed="r/learnpython"),
            SubredditSubscription(name="python", display_name_prefixed="r/python"),
        ),
    )


def test_render_txt_csv_json_exact_shape() -> None:
    snapshot = make_snapshot()
    assert render_txt(snapshot) == "r/AskReddit\nr/learnpython\nr/python\n"
    assert render_csv(snapshot) == "subreddit\r\nAskReddit\r\nlearnpython\r\npython\r\n"
    payload = render_json(snapshot)
    assert '"account": "ExampleUser"' in payload
    assert '"count": 3' in payload
    assert payload.endswith("\n")


def test_export_no_overwrite_without_force(tmp_path: Path) -> None:
    path = tmp_path / "subs.txt"
    path.write_text("existing\n", encoding="utf-8")
    with pytest.raises(ExportError):
        export_snapshot(make_snapshot(), path, fmt="txt", force=False)


def test_export_atomic_cleanup_on_replace_failure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    path = tmp_path / "subs.txt"
    path.write_text("old\n", encoding="utf-8")

    def boom(*_args, **_kwargs):
        raise OSError("replace failed")

    monkeypatch.setattr("reddit_exporter.core.exporters.os.replace", boom)
    with pytest.raises(ExportError):
        export_snapshot(make_snapshot(), path, fmt="txt", force=True)
    assert path.read_text(encoding="utf-8") == "old\n"
    assert not list(tmp_path.glob("*.tmp"))
