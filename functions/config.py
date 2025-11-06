"""Configuration helpers for API keys and runtime settings."""

from __future__ import annotations

import json
import logging
import os
from functools import lru_cache
from typing import Any, Dict, Optional

try:  # Optional dependency available only in the Firebase runtime
    from firebase_functions import params
except Exception:  # pragma: no cover - module not available during local tests
    params = None  # type: ignore

LOGGER = logging.getLogger(__name__)


def _load_env_file() -> None:
    """Load variables from a local ``.env`` file when available."""

    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    if not os.path.exists(env_path):
        LOGGER.debug("No .env file found at %s", env_path)
        return

    try:
        from dotenv import load_dotenv

        load_dotenv(env_path)
        LOGGER.info("Loaded environment variables from %s", env_path)
    except ImportError:  # pragma: no cover - optional dependency
        LOGGER.warning("python-dotenv not installed; skipping .env loading")


def _load_functions_config() -> Dict[str, Any]:
    """Return Firebase ``functions:config`` values when available."""

    raw_config = (
        os.getenv("FIREBASE_FUNCTIONS_CONFIG")
        or os.getenv("FUNCTIONS_CONFIG")
        or os.getenv("FUNCTIONS_CONFIG_JSON")
    )

    if not raw_config:
        return {}

    try:
        return json.loads(raw_config)
    except json.JSONDecodeError:
        LOGGER.warning("Failed to parse Firebase functions config JSON")
        return {}


def _read_nested(config: Dict[str, Any], *path: str) -> Optional[str]:
    """Safely read a nested value from ``config`` following ``path``."""

    current: Any = config
    for step in path:
        if not isinstance(current, dict) or step not in current:
            return None
        current = current[step]
    return current if isinstance(current, str) else None


@lru_cache
def _resolve_openrouter_secret() -> Optional[str]:
    """Resolve the OpenRouter API key from multiple possible sources."""

    # 1) Explicit environment variables (preferred for local development)
    direct = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENROUTER_KEY")
    if direct:
        return direct

    # 2) Legacy ``firebase functions:config:set openrouter.key=...`` storage
    config = _load_functions_config()
    for candidate in ("key", "api_key"):
        legacy_value = _read_nested(config, "openrouter", candidate)
        if legacy_value:
            return legacy_value

    # 3) Firebase secret manager via ``firebase functions:secrets:set``
    if params is not None:  # pragma: no branch - executed only when available
        try:
            secret = params.SecretParam("OPENROUTER_API_KEY")
            return secret.value
        except Exception:  # pragma: no cover - runtime only
            LOGGER.warning("Firebase secret OPENROUTER_API_KEY is not accessible")

    return None


_load_env_file()


class Config:
    """Central access point for runtime configuration."""

    # OpenRouter configuration -------------------------------------------------
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL", "openai/gpt-oss-20b:free")

    # Cache configuration ------------------------------------------------------
    CACHE_DURATION_HOURS: int = int(os.getenv("CACHE_DURATION_HOURS", "24"))

    # Feature flags ------------------------------------------------------------
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    ENABLE_AI_PARSING: bool = os.getenv("ENABLE_AI_PARSING", "True").lower() == "true"
    AI_NULL_THRESHOLD: int = int(os.getenv("AI_NULL_THRESHOLD", "3"))

    # Firebase settings --------------------------------------------------------
    FIREBASE_PROJECT_ID: Optional[str] = os.getenv("FIREBASE_PROJECT_ID")

    @classmethod
    def get_openrouter_api_key(cls) -> Optional[str]:
        """Return the configured OpenRouter API key, if any."""

        return _resolve_openrouter_secret()

    # Expose backwards-compatible attribute used throughout the codebase. The
    # concrete value is populated immediately after class creation.
    OPENROUTER_API_KEY: Optional[str] = None

    @classmethod
    def validate(cls) -> bool:
        """Validate that the active configuration is usable."""

        if cls.ENABLE_AI_PARSING and not cls.get_openrouter_api_key():
            LOGGER.warning("AI parsing enabled but no OpenRouter API key configured")
            return False
        return True

    @classmethod
    def get_openrouter_headers(cls, site_url: str = "https://api-lanakj0r.web.app") -> Dict[str, str]:
        """Return headers required by the OpenRouter API."""

        api_key = cls.get_openrouter_api_key()
        if not api_key:
            raise RuntimeError("OpenRouter API key is not configured")

        return {
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": site_url,
            "X-Title": "Icelandic Bank Interest Rate API",
        }


Config.OPENROUTER_API_KEY = Config.get_openrouter_api_key()

if not Config.validate():  # pragma: no cover - defensive guard
    LOGGER.warning("Configuration validation failed - AI features will be disabled")
