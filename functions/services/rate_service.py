"""Application service responsible for interest rate retrieval and caching."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Dict, Iterable, Optional
import logging

from banks import AVAILABLE_BANKS, get_bank_scraper
from firestore_manager import FirestoreManager

logger = logging.getLogger(__name__)


class UnknownBankError(ValueError):
    """Raised when the caller references an unsupported bank."""


class RateServiceError(RuntimeError):
    """Raised when an unrecoverable error occurs while fetching rates."""


@dataclass
class RateResult:
    """Structured result produced by :class:`RateService`."""

    bank_id: str
    payload: Dict

    @property
    def cached(self) -> bool:
        return bool(self.payload.get("cached"))


class RateService:
    """Facade that orchestrates scrapers, caching and formatting logic."""

    def __init__(
        self,
        firestore_mgr: Optional[FirestoreManager] = None,
        scraper_factory: Callable[[str], object] = get_bank_scraper,
        keep_latest: int = 5,
    ) -> None:
        self._firestore = firestore_mgr or FirestoreManager()
        self._scraper_factory = scraper_factory
        self._keep_latest = keep_latest

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def list_supported_banks(self) -> Iterable[str]:
        """Return the identifiers of every bank the API knows about."""

        return AVAILABLE_BANKS.keys()

    def get_bank_rates(self, bank_id: str, force_refresh: bool = False) -> Dict:
        """Return data for a single bank, using cache when available."""

        scraper = self._get_scraper(bank_id)
        normalized_bank_id = scraper.bank_id

        if not force_refresh:
            cached = self._firestore.get_cached_rates(bank_id=normalized_bank_id)
            if cached:
                logger.info("Cache hit for bank '%s'", normalized_bank_id)
                response = self._firestore.format_response(cached, from_cache=True)
                self._ensure_metadata(response, scraper)
                return response

        logger.info("Fetching fresh rates for bank '%s'", normalized_bank_id)
        payload = self._scrape(scraper)
        formatted = self._persist_and_format(scraper, payload)
        return formatted

    def get_all_bank_rates(self, force_refresh: bool = False) -> Dict:
        """Return data for all configured banks."""

        results: Dict[str, Dict] = {}
        for bank_id in self.list_supported_banks():
            try:
                results[bank_id] = self.get_bank_rates(bank_id, force_refresh=force_refresh)
            except UnknownBankError as exc:  # pragma: no cover - should not happen
                logger.error("Requested unknown bank '%s': %s", bank_id, exc)
                results[bank_id] = {"bank_id": bank_id, "error": str(exc)}
            except RateServiceError as exc:
                logger.error("Failed to fetch rates for '%s': %s", bank_id, exc)
                results[bank_id] = {"bank_id": bank_id, "error": str(exc)}

        return {
            "banks": results,
            "available_banks": list(self.list_supported_banks()),
            "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _get_scraper(self, bank_id: str):
        try:
            scraper = self._scraper_factory(bank_id.strip().lower())
        except ValueError as exc:
            raise UnknownBankError(str(exc)) from exc

        if not scraper:
            raise UnknownBankError(
                f"Unknown bank '{bank_id}'. Supported banks: {list(self.list_supported_banks())}"
            )

        return scraper

    def _scrape(self, scraper) -> Dict:
        try:
            rate_data, source_url = scraper.scrape_rates()
        except Exception as exc:  # pragma: no cover - defensive guard
            raise RateServiceError(f"Failed to scrape rates for {scraper.bank_name}: {exc}") from exc

        if not rate_data:
            raise RateServiceError(f"Failed to scrape rates for {scraper.bank_name}")

        # Ensure downstream code has consistent metadata to work with
        rate_data.setdefault("bank_name", scraper.bank_name)
        rate_data.setdefault("bank_id", scraper.bank_id)
        if source_url:
            rate_data.setdefault("source_url", source_url)

        logger.info("Successfully scraped %s", scraper.bank_name)
        return rate_data

    def _persist_and_format(self, scraper, payload: Dict) -> Dict:
        source_url = payload.get("source_url")

        save_success = self._firestore.save_rates(
            payload,
            source_url or "",
            bank_id=scraper.bank_id,
            bank_name=scraper.bank_name,
        )

        if save_success:
            self._firestore.clear_old_caches(keep_latest=self._keep_latest)

        formatted_payload = {
            "bank_id": scraper.bank_id,
            "bank_name": scraper.bank_name,
            "data": payload,
            "effective_date": payload.get("effective_date"),
            "source_url": source_url,
        }

        response = self._firestore.format_response(formatted_payload, from_cache=False)
        self._ensure_metadata(response, scraper)
        return response

    @staticmethod
    def _ensure_metadata(response: Dict, scraper) -> None:
        response.setdefault("bank_id", scraper.bank_id)
        response.setdefault("bank_name", scraper.bank_name)

