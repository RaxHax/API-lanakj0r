"""
Base interface for bank rate scrapers
"""
from abc import ABC, abstractmethod
from typing import Dict, Optional, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class BankScraper(ABC):
    """Abstract base class for bank interest rate scrapers"""

    def __init__(self):
        self.bank_name = "Unknown"
        self.bank_id = "unknown"
        self.use_ai_parsing = True  # Enable AI parsing by default

    @abstractmethod
    def scrape_rates(self) -> Tuple[Optional[Dict], Optional[str]]:
        """
        Scrape interest rates from the bank

        Returns:
            Tuple[Dict, str]: (rate_data, source_url) or (None, None) if failed
        """
        pass

    @abstractmethod
    def parse_effective_date(self, data) -> Optional[str]:
        """
        Extract the effective date from the data

        Args:
            data: Raw data (HTML, PDF content, JSON, etc.)

        Returns:
            str: Effective date in ISO format (YYYY-MM-DD) or None
        """
        pass

    def get_metadata(self) -> Dict:
        """
        Get metadata about this bank scraper

        Returns:
            Dict: Metadata including bank name, ID, etc.
        """
        return {
            "bank_name": self.bank_name,
            "bank_id": self.bank_id,
            "last_run": datetime.utcnow().isoformat()
        }

    def enhance_with_ai(self, raw_text: str, parsed_data: Dict, source_type: str = "pdf") -> Dict:
        """
        Enhance parsed data using AI if enabled and configured.

        Args:
            raw_text: Original text extracted from source
            parsed_data: Data parsed by regex methods
            source_type: Type of source ("pdf" or "html")

        Returns:
            Dict: Enhanced data (or original if AI unavailable)
        """
        if not self.use_ai_parsing:
            return parsed_data

        try:
            from ..config import Config
            from ..ai_processor import AIProcessor

            if not Config.OPENROUTER_API_KEY or not Config.ENABLE_AI_PARSING:
                logger.debug("AI parsing not configured, using regex results")
                return parsed_data

            # Count how many null values we have
            null_count = self._count_nulls(parsed_data)

            # Only use AI if we have significant missing data
            if null_count < 5:
                logger.info(f"{self.bank_name}: Regex parsing successful ({null_count} nulls), skipping AI")
                return parsed_data

            logger.info(f"{self.bank_name}: Using AI to enhance data ({null_count} null values)")
            processor = AIProcessor()
            ai_data = processor.parse_bank_data(raw_text, self.bank_name, source_type)

            # Merge AI results with regex results (prefer non-null values)
            enhanced_data = self._merge_data(parsed_data, ai_data)

            new_null_count = self._count_nulls(enhanced_data)
            logger.info(f"{self.bank_name}: AI enhancement reduced nulls from {null_count} to {new_null_count}")

            return enhanced_data

        except ImportError as e:
            logger.warning(f"AI processor not available: {e}")
            return parsed_data
        except Exception as e:
            logger.error(f"AI enhancement failed: {e}")
            return parsed_data

    def _count_nulls(self, data) -> int:
        """Count null and empty values recursively."""
        if data is None:
            return 1
        elif isinstance(data, dict):
            if not data:
                return 1
            return sum(self._count_nulls(v) for v in data.values())
        elif isinstance(data, list):
            if not data:
                return 1
            return sum(self._count_nulls(item) for item in data)
        else:
            return 0

    def _merge_data(self, original: Dict, ai_data: Dict) -> Dict:
        """
        Merge AI-parsed data with original data.
        Prefer non-null values from either source.
        """
        if not isinstance(original, dict) or not isinstance(ai_data, dict):
            return original if original is not None else ai_data

        merged = {}
        all_keys = set(original.keys()) | set(ai_data.keys())

        for key in all_keys:
            orig_val = original.get(key)
            ai_val = ai_data.get(key)

            if isinstance(orig_val, dict) and isinstance(ai_val, dict):
                merged[key] = self._merge_data(orig_val, ai_val)
            elif orig_val is None or (isinstance(orig_val, dict) and not orig_val):
                merged[key] = ai_val
            elif ai_val is None or (isinstance(ai_val, dict) and not ai_val):
                merged[key] = orig_val
            else:
                # Both have values, prefer original (regex-based)
                merged[key] = orig_val

        return merged
