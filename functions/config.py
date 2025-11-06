"""
Configuration management for API keys and environment variables.
Loads settings from environment variables with secure defaults.
"""
import os
from typing import Optional


class Config:
    """Configuration class for managing API keys and settings."""

    # OpenRouter API Configuration
    OPENROUTER_API_KEY: Optional[str] = os.getenv('OPENROUTER_API_KEY')
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_MODEL: str = os.getenv('OPENROUTER_MODEL', 'openai/gpt-oss-20b:free')

    # Cache Configuration
    CACHE_DURATION_HOURS: int = int(os.getenv('CACHE_DURATION_HOURS', '24'))

    # Application Settings
    DEBUG: bool = os.getenv('DEBUG', 'False').lower() == 'true'
    ENABLE_AI_PARSING: bool = os.getenv('ENABLE_AI_PARSING', 'True').lower() == 'true'
    AI_NULL_THRESHOLD: int = int(os.getenv('AI_NULL_THRESHOLD', '3'))

    # Firebase Configuration
    FIREBASE_PROJECT_ID: Optional[str] = os.getenv('FIREBASE_PROJECT_ID')

    @classmethod
    def validate(cls) -> bool:
        """
        Validate that required configuration is present.

        Returns:
            bool: True if configuration is valid, False otherwise
        """
        if cls.ENABLE_AI_PARSING and not cls.OPENROUTER_API_KEY:
            print("Warning: AI parsing enabled but OPENROUTER_API_KEY not set")
            return False
        return True

    @classmethod
    def get_openrouter_headers(cls, site_url: str = "https://api-lanakj0r.web.app") -> dict:
        """
        Get headers for OpenRouter API requests.

        Args:
            site_url: Your site URL for OpenRouter rankings

        Returns:
            dict: Headers for API requests
        """
        return {
            "Authorization": f"Bearer {cls.OPENROUTER_API_KEY}",
            "HTTP-Referer": site_url,
            "X-Title": "Icelandic Bank Interest Rate API"
        }


def load_env_file():
    """Load environment variables from .env file if it exists."""
    try:
        from dotenv import load_dotenv
        env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
        if os.path.exists(env_path):
            load_dotenv(env_path)
            print(f"Loaded environment variables from {env_path}")
        else:
            print("No .env file found, using system environment variables")
    except ImportError:
        print("python-dotenv not installed, using system environment variables only")


# Load environment variables on module import
load_env_file()

# Validate configuration
if not Config.validate():
    print("Configuration validation failed - some features may not work")
