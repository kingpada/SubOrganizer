from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from reddit_exporter.config import AppConfig
from reddit_exporter.core.auth import authenticate_via_oauth
from reddit_exporter.core.credentials import CredentialStore, SessionOnlyCredentialStore
from reddit_exporter.core.exporters import export_snapshot
from reddit_exporter.core.reddit_client import create_oauth_reddit, create_script_reddit
from reddit_exporter.core.subscriptions import filter_subscriptions, retrieve_snapshot
from reddit_exporter.errors import AuthenticationError, ConfigurationError
from reddit_exporter.models import AccountIdentity, SubscriptionSnapshot

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class AuthSession:
    mode: str
    account: AccountIdentity


class ExporterService:
    def __init__(
        self,
        config: AppConfig,
        credential_store: CredentialStore | SessionOnlyCredentialStore | None = None,
    ) -> None:
        self.config = config
        self.credential_store = credential_store or CredentialStore()
        self._session_auth: AuthSession | None = None
        self._session_reddit = None

    def _oauth_user_agent(self) -> str:
        return self.config.user_agent(platform="desktop", username="unknown")

    def login_oauth(self) -> AuthSession:
        if not self.config.oauth.client_id:
            raise ConfigurationError(
                "OAuth client ID is not configured. Add it to your local configuration before signing in."
            )

        reddit = create_oauth_reddit(
            client_id=self.config.oauth.client_id,
            redirect_uri=self.config.oauth.redirect_uri,
            user_agent=self._oauth_user_agent(),
        )
        account, refresh_token = authenticate_via_oauth(
            reddit,
            redirect_uri=self.config.oauth.redirect_uri,
        )
        self.credential_store.set_secret("oauth_refresh_token", refresh_token)
        self._session_auth = AuthSession(mode="oauth", account=account)
        self._session_reddit = create_oauth_reddit(
            client_id=self.config.oauth.client_id,
            redirect_uri=self.config.oauth.redirect_uri,
            user_agent=self.config.user_agent(platform="desktop", username=account.username),
            refresh_token=refresh_token,
        )
        LOGGER.info("OAuth login successful for user=%s", account.username)
        return self._session_auth

    def login_script(
        self,
        *,
        client_id: str,
        client_secret: str,
        username: str,
        password: str,
        otp: str | None = None,
    ) -> AuthSession:
        if not client_id:
            raise ConfigurationError("Script client ID is required for script login.")
        if not client_secret:
            raise ConfigurationError("Script client secret is required for script login.")
        if not username:
            raise ConfigurationError("Reddit username is required for script login.")
        if not password:
            raise ConfigurationError("Reddit password is required for script login.")

        reddit = create_script_reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=self.config.user_agent(platform="script", username=username),
            username=username,
            **{"password": password},
            otp=otp,
        )
        me = reddit.user.me()
        verified_username = str(getattr(me, "name", "")).strip()
        if not verified_username:
            raise AuthenticationError("Unable to verify authenticated Reddit username.")

        account = AccountIdentity(username=verified_username)
        self._session_auth = AuthSession(mode="script", account=account)
        self._session_reddit = reddit
        LOGGER.info("Script login successful for user=%s", verified_username)
        return self._session_auth

    def _load_oauth_reddit_from_store(self):
        refresh_token = self.credential_store.get_secret("oauth_refresh_token")
        if not refresh_token:
            raise AuthenticationError("You are not signed in. Run login first.")
        if not self.config.oauth.client_id:
            raise ConfigurationError("OAuth client ID is not configured.")
        return create_oauth_reddit(
            client_id=self.config.oauth.client_id,
            redirect_uri=self.config.oauth.redirect_uri,
            user_agent=self._oauth_user_agent(),
            refresh_token=refresh_token,
        )

    def _current_reddit(self):
        if self._session_reddit is not None:
            return self._session_reddit
        return self._load_oauth_reddit_from_store()

    def whoami(self) -> AccountIdentity:
        reddit = self._current_reddit()
        me = reddit.user.me()
        username = str(getattr(me, "name", "")).strip()
        if not username:
            raise AuthenticationError("Unable to verify authenticated Reddit username.")
        return AccountIdentity(username=username)

    def fetch_snapshot(self) -> SubscriptionSnapshot:
        reddit = self._current_reddit()
        snapshot = retrieve_snapshot(reddit)
        LOGGER.info("Retrieved %s subscriptions for user=%s", len(snapshot.subscriptions), snapshot.account.username)
        return snapshot

    def list_filtered(self, filter_text: str = "") -> SubscriptionSnapshot:
        snapshot = self.fetch_snapshot()
        filtered = filter_subscriptions(snapshot.subscriptions, filter_text)
        return SubscriptionSnapshot(
            account=snapshot.account,
            retrieved_at_utc=snapshot.retrieved_at_utc,
            subscriptions=filtered,
        )

    def export(self, fmt: str, output: Path, force: bool = False) -> SubscriptionSnapshot:
        snapshot = self.fetch_snapshot()
        export_snapshot(snapshot, output_path=output, fmt=fmt, force=force)
        LOGGER.info("Exported snapshot format=%s path=%s", fmt, output)
        return snapshot

    def logout(self) -> None:
        self.credential_store.delete_secret("oauth_refresh_token")
        self._session_reddit = None
        self._session_auth = None
        LOGGER.info("Credentials cleared and session signed out.")
