from __future__ import annotations

import csv
import json
import os
import tempfile
from datetime import UTC
from pathlib import Path

from reddit_exporter.errors import ExportError
from reddit_exporter.models import SubscriptionSnapshot


def _json_payload(snapshot: SubscriptionSnapshot) -> dict:
    iso = snapshot.retrieved_at_utc.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "account": snapshot.account.username,
        "retrieved_at": iso,
        "count": len(snapshot.subscriptions),
        "subreddits": [sub.name for sub in snapshot.subscriptions],
    }


def render_txt(snapshot: SubscriptionSnapshot) -> str:
    lines = [sub.display_name_prefixed for sub in snapshot.subscriptions]
    return "\n".join(lines) + "\n"


def render_csv(snapshot: SubscriptionSnapshot) -> str:
    from io import StringIO

    buffer = StringIO(newline="")
    writer = csv.writer(buffer)
    writer.writerow(["subreddit"])
    for sub in snapshot.subscriptions:
        writer.writerow([sub.name])
    text = buffer.getvalue()
    if not text.endswith("\n"):
        text += "\n"
    return text


def render_json(snapshot: SubscriptionSnapshot) -> str:
    return json.dumps(_json_payload(snapshot), ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def export_snapshot(snapshot: SubscriptionSnapshot, output_path: Path, fmt: str, force: bool = False) -> None:
    path = Path(output_path)
    if path.exists() and not force:
        raise ExportError(f"Output file already exists: {path}. Use --force to overwrite.")

    fmt_lower = fmt.lower()
    if fmt_lower == "txt":
        content = render_txt(snapshot)
    elif fmt_lower == "csv":
        content = render_csv(snapshot)
    elif fmt_lower == "json":
        content = render_json(snapshot)
    else:
        raise ExportError(f"Unsupported export format: {fmt}")

    temp_path = None
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            delete=False,
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
        ) as handle:
            temp_path = Path(handle.name)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    except Exception as exc:  # noqa: BLE001
        if temp_path and temp_path.exists():
            temp_path.unlink(missing_ok=True)
        raise ExportError(f"Failed to export subscriptions to {path}: {exc}") from exc
