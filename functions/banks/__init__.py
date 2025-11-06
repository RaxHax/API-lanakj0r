"""
Bank scrapers for Icelandic banks
"""
from .base import BankScraper

__all__ = [
    'BankScraper',
    'LandsbankinScraper',
    'ArionBankiScraper',
    'IslandsbankiScraper',
]

# Lazy-loaded scraper registry
_SCRAPER_CACHE = {}


def _get_scraper_class(bank_id: str):
    """Lazy load scraper classes to avoid import issues"""
    if bank_id in _SCRAPER_CACHE:
        return _SCRAPER_CACHE[bank_id]

    if bank_id == 'landsbankinn':
        from .landsbankinn import LandsbankinScraper
        _SCRAPER_CACHE[bank_id] = LandsbankinScraper
        return LandsbankinScraper
    elif bank_id == 'arionbanki':
        from .arionbanki import ArionBankiScraper
        _SCRAPER_CACHE[bank_id] = ArionBankiScraper
        return ArionBankiScraper
    elif bank_id == 'islandsbanki':
        from .islandsbanki import IslandsbankiScraper
        _SCRAPER_CACHE[bank_id] = IslandsbankiScraper
        return IslandsbankiScraper
    else:
        return None


# Registry of all available banks
AVAILABLE_BANKS = {
    'landsbankinn': lambda: _get_scraper_class('landsbankinn'),
    'arionbanki': lambda: _get_scraper_class('arionbanki'),
    'islandsbanki': lambda: _get_scraper_class('islandsbanki'),
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

    scraper_class = _get_scraper_class(bank_id)
    if not scraper_class:
        raise ValueError(f"Failed to load scraper for bank: {bank_id}")

    return scraper_class()


# For backwards compatibility, provide module-level access to scraper classes
def __getattr__(name):
    """Lazy load scraper classes when accessed as module attributes"""
    if name == 'LandsbankinScraper':
        return _get_scraper_class('landsbankinn')
    elif name == 'ArionBankiScraper':
        return _get_scraper_class('arionbanki')
    elif name == 'IslandsbankiScraper':
        return _get_scraper_class('islandsbanki')
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
