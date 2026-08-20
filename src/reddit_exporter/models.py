from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class SubredditSubscription:
    name: str
    display_name_prefixed: str


@dataclass(frozen=True, slots=True)
class AccountIdentity:
    username: str


@dataclass(frozen=True, slots=True)
class SubscriptionSnapshot:
    account: AccountIdentity
    retrieved_at_utc: datetime
    subscriptions: tuple[SubredditSubscription, ...]
