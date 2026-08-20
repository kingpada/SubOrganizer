from __future__ import annotations

from reddit_exporter.core.subscriptions import filter_subscriptions, normalize_subscriptions


class FakeSubreddit:
    def __init__(self, name: str, prefixed: str | None = None):
        self.display_name = name
        self.display_name_prefixed = prefixed or f"r/{name}"


def test_normalize_dedup_and_sort_case_insensitive() -> None:
    data = [FakeSubreddit("python"), FakeSubreddit("AskReddit"), FakeSubreddit("Python")]
    result = normalize_subscriptions(data)
    assert [item.name for item in result] == ["AskReddit", "python"]


def test_normalize_unicode_and_empty_values() -> None:
    data = [FakeSubreddit("éclair"), FakeSubreddit(""), FakeSubreddit("Zebra")]
    result = normalize_subscriptions(data)
    assert [item.name for item in result] == ["Zebra", "éclair"]


def test_filter_case_insensitive_and_empty() -> None:
    data = normalize_subscriptions([FakeSubreddit("python"), FakeSubreddit("learnpython"), FakeSubreddit("GoLang")])
    assert [item.name for item in filter_subscriptions(data, "python")] == ["learnpython", "python"]
    assert filter_subscriptions(data, "") == data
    assert filter_subscriptions(data, "nomatch") == ()
