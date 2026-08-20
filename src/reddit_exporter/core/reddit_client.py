from __future__ import annotations

import socket

import praw
import prawcore

from reddit_exporter.errors import InsufficientScopeError, NetworkError, RateLimitError, RedditApiError


def create_oauth_reddit(*, client_id: str, redirect_uri: str, user_agent: str, refresh_token: str | None = None):
    kwargs = {
        "client_id": client_id,
        "client_secret": "",
        "redirect_uri": redirect_uri,
        "user_agent": user_agent,
    }
    if refresh_token:
        kwargs["refresh_token"] = refresh_token
    return praw.Reddit(**kwargs)


def create_script_reddit(
    *,
    client_id: str,
    client_secret: str,
    user_agent: str,
    username: str,
    password: str,
    otp: str | None,
):
    if otp:
        password = f"{password}:{otp}"
    kwargs = {
        "client_id": client_id,
        "client_secret": client_secret,
        "user_agent": user_agent,
        "username": username,
    }
    kwargs["password"] = password
    return praw.Reddit(**kwargs)


def translate_reddit_exception(exc: Exception) -> Exception:
    if isinstance(exc, (prawcore.OAuthException, prawcore.Forbidden)):
        return InsufficientScopeError(
            "The current authorization does not grant access to subreddit subscriptions. Sign in again and approve the required read-only permissions."
        )
    if isinstance(exc, prawcore.TooManyRequests):
        return RateLimitError("Reddit rate limit reached. Wait and try again.")
    if isinstance(exc, (prawcore.ServerError, prawcore.ResponseException)):
        return RedditApiError("Reddit API request failed. Try again later.")
    if isinstance(exc, (prawcore.RequestException, TimeoutError, socket.timeout, ConnectionError)):
        return NetworkError("Unable to reach Reddit. Check your connection and try again.")
    return RedditApiError("Reddit API request failed.")
