"""
Bank scrapers for Icelandic banks
"""
from .base import BankScraper
from .landsbankinn import LandsbankinScraper
from .arionbanki import ArionBankiScraper
from .islandsbanki import IslandsbankiScraper

__all__ = [
    'BankScraper',
    'LandsbankinScraper',
    'ArionBankiScraper',
    'IslandsbankiScraper',
]

# Registry of all available banks
AVAILABLE_BANKS = {
    'landsbankinn': LandsbankinScraper,
    'arionbanki': ArionBankiScraper,
    'islandsbanki': IslandsbankiScraper,
}


def get_bank_scraper(bank_id: str) -> BankScraper:
    """
    Get a bank scraper instance by bank ID

    Args:
        bank_id: Bank identifier (landsbankinn, arionbanki, islandsbanki)

    Returns:
        BankScraper: Instance of the appropriate bank scraper

    Raises:
        ValueError: If bank_id is not recognized
    """
    if bank_id not in AVAILABLE_BANKS:
        raise ValueError(f"Unknown bank: {bank_id}. Available banks: {list(AVAILABLE_BANKS.keys())}")

    return AVAILABLE_BANKS[bank_id]()
