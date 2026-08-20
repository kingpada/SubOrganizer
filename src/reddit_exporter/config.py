from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import tomllib

from reddit_exporter.errors import ConfigurationError


@dataclass(frozen=True, slots=True)
class OAuthConfig:
    client_id: str = ""
    redirect_uri: str = "http://localhost:8080"


@dataclass(frozen=True, slots=True)
class ScriptConfig:
    client_id: str = ""
    username: str = ""


@dataclass(frozen=True, slots=True)
class UiConfig:
    remember_window_geometry: bool = True


@dataclass(frozen=True, slots=True)
class AppConfig:
    app_version: str = "0.1.0"
    user_agent_app_id: str = "reddit-subreddit-exporter"
    oauth: OAuthConfig = OAuthConfig()
    script: ScriptConfig = ScriptConfig()
    ui: UiConfig = UiConfig()

    def user_agent(self, platform: str, username: str) -> str:
        return f"{platform}:{self.user_agent_app_id}:{self.app_version} (by /u/{username})"


DEFAULT_CONFIG = AppConfig()


def _read_toml(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open("rb") as handle:
        data = tomllib.load(handle)
    if not isinstance(data, dict):
        raise ConfigurationError(f"Configuration file {path} is malformed.")
    return data


def default_user_config_path() -> Path:
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        return Path(xdg) / "reddit-subreddit-exporter" / "config.toml"
    return Path.home() / ".config" / "reddit-subreddit-exporter" / "config.toml"


def load_config(explicit_path: Path | None = None, env: dict[str, str] | None = None) -> AppConfig:
    env = env or dict(os.environ)
    base = DEFAULT_CONFIG

    config_path = explicit_path or (
        Path(env["REDDIT_EXPORTER_CONFIG"]) if env.get("REDDIT_EXPORTER_CONFIG") else default_user_config_path()
    )
    parsed = _read_toml(config_path)

    oauth_section = parsed.get("oauth", {}) if isinstance(parsed.get("oauth", {}), dict) else {}
    script_section = parsed.get("script", {}) if isinstance(parsed.get("script", {}), dict) else {}
    ui_section = parsed.get("ui", {}) if isinstance(parsed.get("ui", {}), dict) else {}

    app_version = env.get("REDDIT_EXPORTER_APP_VERSION", parsed.get("app_version", base.app_version))
    app_id = env.get("REDDIT_EXPORTER_APP_ID", parsed.get("user_agent_app_id", base.user_agent_app_id))

    oauth_client_id = env.get("REDDIT_EXPORTER_OAUTH_CLIENT_ID", oauth_section.get("client_id", base.oauth.client_id))
    oauth_redirect = env.get("REDDIT_EXPORTER_OAUTH_REDIRECT_URI", oauth_section.get("redirect_uri", base.oauth.redirect_uri))

    script_client_id = env.get("REDDIT_EXPORTER_SCRIPT_CLIENT_ID", script_section.get("client_id", base.script.client_id))
    script_username = env.get("REDDIT_EXPORTER_SCRIPT_USERNAME", script_section.get("username", base.script.username))

    remember_window_geometry = ui_section.get("remember_window_geometry", base.ui.remember_window_geometry)
    if isinstance(remember_window_geometry, str):
        remember_window_geometry = remember_window_geometry.lower() in {"1", "true", "yes"}

    return AppConfig(
        app_version=str(app_version),
        user_agent_app_id=str(app_id),
        oauth=OAuthConfig(client_id=str(oauth_client_id), redirect_uri=str(oauth_redirect)),
        script=ScriptConfig(client_id=str(script_client_id), username=str(script_username)),
        ui=UiConfig(remember_window_geometry=bool(remember_window_geometry)),
    )
