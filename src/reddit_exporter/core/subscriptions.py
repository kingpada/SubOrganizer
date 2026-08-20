from __future__ import annotations

from datetime import UTC, datetime

from reddit_exporter.core.reddit_client import translate_reddit_exception
from reddit_exporter.models import AccountIdentity, SubredditSubscription, SubscriptionSnapshot


def normalize_subscriptions(subreddits: list[object]) -> tuple[SubredditSubscription, ...]:
    deduped: dict[str, SubredditSubscription] = {}
    for item in subreddits:
        name = str(getattr(item, "display_name", "")).strip()
        if not name:
            continue
        prefixed = str(getattr(item, "display_name_prefixed", f"r/{name}")).strip() or f"r/{name}"
        key = name.casefold()
        if key not in deduped:
            deduped[key] = SubredditSubscription(name=name, display_name_prefixed=prefixed)

    ordered = sorted(deduped.values(), key=lambda sub: (sub.name.casefold(), sub.name))
    return tuple(ordered)


def filter_subscriptions(subscriptions: tuple[SubredditSubscription, ...], text: str) -> tuple[SubredditSubscription, ...]:
    query = text.strip()
    if not query:
        return subscriptions
    folded = query.casefold()
    return tuple(sub for sub in subscriptions if folded in sub.name.casefold())


def retrieve_snapshot(reddit) -> SubscriptionSnapshot:
    try:
        me = reddit.user.me()
        username = str(getattr(me, "name", "")).strip()
        listing = list(reddit.user.subreddits(limit=None))
    except Exception as exc:  # noqa: BLE001
        raise translate_reddit_exception(exc) from exc

    subs = normalize_subscriptions(listing)
    return SubscriptionSnapshot(
        account=AccountIdentity(username=username),
        retrieved_at_utc=datetime.now(UTC),
        subscriptions=subs,
    )
