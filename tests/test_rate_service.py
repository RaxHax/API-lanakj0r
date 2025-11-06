from datetime import datetime, timezone

import pytest

from functions.firestore_manager import FirestoreManager
from functions.services.rate_service import RateService, RateServiceError, UnknownBankError
from functions.services import rate_service as rate_service_module


class FakeFirestoreManager:
    def __init__(self):
        self._formatter = FirestoreManager()
        self.saved_documents = []
        self.cache = {}
        self.cleared = 0

    def get_cached_rates(self, bank_id: str):
        return self.cache.get(bank_id)

    def save_rates(self, rate_data, source_url, bank_id: str, bank_name: str) -> bool:
        document = {
            "bank_id": bank_id,
            "bank_name": bank_name,
            "effective_date": rate_data.get("effective_date"),
            "last_updated": datetime.now(timezone.utc),
            "data": rate_data,
            "source_url": source_url,
        }
        self.saved_documents.append(document)
        self.cache[bank_id] = document
        return True

    def clear_old_caches(self, keep_latest: int = 5) -> int:
        self.cleared += 1
        return 0

    def format_response(self, data, from_cache: bool = True):
        return self._formatter.format_response(data, from_cache)


class SuccessfulScraper:
    bank_id = "testbank"
    bank_name = "Test Bank"

    def scrape_rates(self):
        return (
            {
                "bank_id": self.bank_id,
                "bank_name": self.bank_name,
                "effective_date": "2024-01-01",
                "deposits": {"checking": 1.5},
            },
            "https://example.com/rates.pdf",
        )


class FailingScraper(SuccessfulScraper):
    def scrape_rates(self):
        return None, None


@pytest.fixture
def fake_service(monkeypatch):
    fake_firestore = FakeFirestoreManager()
    monkeypatch.setattr(
        rate_service_module,
        "AVAILABLE_BANKS",
        {"testbank": lambda: SuccessfulScraper},
    )

    def factory(bank_id: str):
        if bank_id == "testbank":
            return SuccessfulScraper()
        raise ValueError("Unknown bank")

    service = RateService(firestore_mgr=fake_firestore, scraper_factory=factory)
    return service, fake_firestore


def test_returns_cached_result(fake_service):
    service, fake_firestore = fake_service
    cached_doc = {
        "bank_id": "testbank",
        "bank_name": "Test Bank",
        "effective_date": "2024-01-01",
        "last_updated": datetime.now(timezone.utc),
        "data": {"deposits": {"checking": 1.1}},
        "source_url": "https://example.com/rates.pdf",
    }
    fake_firestore.cache["testbank"] = cached_doc

    result = service.get_bank_rates("testbank")

    assert result["cached"] is True
    assert result["bank_id"] == "testbank"
    assert fake_firestore.saved_documents == []


def test_force_refresh_bypasses_cache(fake_service):
    service, fake_firestore = fake_service
    fake_firestore.cache["testbank"] = {
        "bank_id": "testbank",
        "bank_name": "Test Bank",
        "effective_date": "2024-01-01",
        "last_updated": datetime.now(timezone.utc),
        "data": {"deposits": {"checking": 1.1}},
        "source_url": "https://example.com/rates.pdf",
    }

    result = service.get_bank_rates("testbank", force_refresh=True)

    assert result["cached"] is False
    assert fake_firestore.saved_documents  # fresh data stored
    assert fake_firestore.cleared == 1


def test_unknown_bank_raises(monkeypatch):
    fake_firestore = FakeFirestoreManager()
    monkeypatch.setattr(rate_service_module, "AVAILABLE_BANKS", {})

    with pytest.raises(UnknownBankError):
        RateService(firestore_mgr=fake_firestore).get_bank_rates("invalid")


def test_scraper_failure_raises(fake_service, monkeypatch):
    service, fake_firestore = fake_service

    def failing_factory(bank_id: str):
        return FailingScraper()

    service = RateService(firestore_mgr=fake_firestore, scraper_factory=failing_factory)

    with pytest.raises(RateServiceError):
        service.get_bank_rates("testbank", force_refresh=True)


def test_get_all_bank_rates(fake_service):
    service, fake_firestore = fake_service

    payload = service.get_all_bank_rates(force_refresh=True)

    assert "banks" in payload
    assert list(payload["banks"].keys()) == ["testbank"]
    assert payload["banks"]["testbank"]["bank_name"] == "Test Bank"
    assert payload["banks"]["testbank"]["cached"] is False
    assert "fetched_at" in payload

