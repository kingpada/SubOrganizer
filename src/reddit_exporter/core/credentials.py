from __future__ import annotations

import logging

import keyring
from keyring.errors import NoKeyringError

from reddit_exporter.errors import CredentialStoreError

LOGGER = logging.getLogger(__name__)
SERVICE_NAME = "reddit-subreddit-exporter"


class CredentialStore:
    def __init__(self, service_name: str = SERVICE_NAME) -> None:
        self.service_name = service_name

    def _assert_backend(self) -> None:
        backend = keyring.get_keyring()
        if backend is None or backend.priority < 1:
            raise CredentialStoreError(
                "No secure keyring backend is available. Use session-only authentication."
            )

    def is_available(self) -> bool:
        try:
            self._assert_backend()
        except CredentialStoreError:
            return False
        return True

    def set_secret(self, key: str, value: str) -> None:
        self._assert_backend()
        try:
            keyring.set_password(self.service_name, key, value)
        except NoKeyringError as exc:
            raise CredentialStoreError(
                "No secure keyring backend is available. Use session-only authentication."
            ) from exc
        except Exception as exc:  # pragma: no cover - keyring backend specific
            raise CredentialStoreError("Failed to save credentials to keyring.") from exc

    def get_secret(self, key: str) -> str | None:
        self._assert_backend()
        try:
            return keyring.get_password(self.service_name, key)
        except NoKeyringError as exc:
            raise CredentialStoreError(
                "No secure keyring backend is available. Use session-only authentication."
            ) from exc
        except Exception as exc:  # pragma: no cover
            raise CredentialStoreError("Failed to read credentials from keyring.") from exc

    def delete_secret(self, key: str) -> None:
        self._assert_backend()
        try:
            keyring.delete_password(self.service_name, key)
        except keyring.errors.PasswordDeleteError:
            return
        except NoKeyringError as exc:
            raise CredentialStoreError(
                "No secure keyring backend is available. Use session-only authentication."
            ) from exc
        except Exception as exc:  # pragma: no cover
            raise CredentialStoreError("Failed to delete credentials from keyring.") from exc


class SessionOnlyCredentialStore:
    def __init__(self) -> None:
        self._secrets: dict[str, str] = {}

    def set_secret(self, key: str, value: str) -> None:
        self._secrets[key] = value

    def get_secret(self, key: str) -> str | None:
        return self._secrets.get(key)

    def delete_secret(self, key: str) -> None:
        self._secrets.pop(key, None)
