"""
Base interface for bank rate scrapers
"""
from abc import ABC, abstractmethod
from typing import Dict, Optional, Tuple
from datetime import datetime


class BankScraper(ABC):
    """Abstract base class for bank interest rate scrapers"""

    def __init__(self):
        self.bank_name = "Unknown"
        self.bank_id = "unknown"

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
