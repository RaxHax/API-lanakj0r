"""Local development server that mirrors the production Firebase API."""

import logging
import sys
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

# Ensure the Firebase function sources are importable when running locally
sys.path.insert(0, "functions")

from functions.banks import AVAILABLE_BANKS
from functions.firestore_manager import FirestoreManager
from functions.services import RateService, RateServiceError, UnknownBankError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class InMemoryCacheManager(FirestoreManager):
    """A lightweight Firestore replacement for local development."""

    def __init__(self, ttl_hours: int = 24):
        # Intentionally skip the Firestore initialisation in the base class.
        self.db = None
        self.CACHE_DURATION_HOURS = ttl_hours
        self._documents: List[Dict] = []

    # The base implementation already provides ``format_response`` which we reuse.

    def get_cached_rates(self, bank_id: Optional[str] = None) -> Optional[Dict]:
        if not bank_id:
            return None

        matching = [doc for doc in self._documents if doc.get("bank_id") == bank_id]
        if not matching:
            return None

        latest = max(matching, key=lambda doc: doc["last_updated"])
        if datetime.now(timezone.utc) - latest["last_updated"] > timedelta(hours=self.CACHE_DURATION_HOURS):
            return None

        return latest

    def save_rates(self, rate_data: Dict, source_url: str, bank_id: str, bank_name: str) -> bool:
        document = {
            "bank_id": bank_id,
            "bank_name": bank_name,
            "effective_date": rate_data.get("effective_date"),
            "last_updated": datetime.now(timezone.utc),
            "data": rate_data,
            "source_url": source_url,
        }
        self._documents.append(document)
        return True

    def clear_old_caches(self, keep_latest: int = 5) -> int:
        deleted = 0
        by_bank: Dict[str, List[Dict]] = {}
        for doc in self._documents:
            by_bank.setdefault(doc["bank_id"], []).append(doc)

        new_store: List[Dict] = []
        for bank_id, docs in by_bank.items():
            docs.sort(key=lambda doc: doc["last_updated"], reverse=True)
            new_store.extend(docs[:keep_latest])
            deleted += max(len(docs) - keep_latest, 0)

        self._documents = new_store
        return deleted


def build_rate_service() -> RateService:
    return RateService(firestore_mgr=InMemoryCacheManager())


def create_app():
    from flask import Flask, jsonify, render_template_string, request

    app = Flask(__name__)
    rate_service = build_rate_service()

    from ui_template import HTML_TEMPLATE

    @app.route("/")
    def index():
        return render_template_string(HTML_TEMPLATE)

    @app.route("/api/rates")
    def get_rates():
        bank_id = (request.args.get("bank") or "").strip().lower()
        try:
            if bank_id:
                payload = rate_service.get_bank_rates(bank_id)
                return jsonify(payload)
            payload = rate_service.get_all_bank_rates()
            return jsonify(payload)
        except UnknownBankError as exc:
            return (
                jsonify(
                    {
                        "error": str(exc),
                        "available_banks": list(AVAILABLE_BANKS.keys()),
                    }
                ),
                400,
            )
        except RateServiceError as exc:
            return jsonify({"error": str(exc)}), 502

    @app.route("/api/rates/refresh")
    def refresh_rates():
        bank_id = (request.args.get("bank") or "").strip().lower()
        try:
            if bank_id:
                payload = rate_service.get_bank_rates(bank_id, force_refresh=True)
                return jsonify(payload)
            payload = rate_service.get_all_bank_rates(force_refresh=True)
            return jsonify(payload)
        except UnknownBankError as exc:
            return (
                jsonify(
                    {
                        "error": str(exc),
                        "available_banks": list(AVAILABLE_BANKS.keys()),
                    }
                ),
                400,
            )
        except RateServiceError as exc:
            return jsonify({"error": str(exc)}), 502

    @app.route("/health")
    def health():
        snapshot = {}
        for bank_id in AVAILABLE_BANKS.keys():
            try:
                snapshot[bank_id] = bool(rate_service.get_bank_rates(bank_id))
            except Exception:  # pragma: no cover - surface status in response instead
                snapshot[bank_id] = False
        return jsonify(
            {
                "status": "healthy",
                "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "available_banks": list(AVAILABLE_BANKS.keys()),
                "cache_status": snapshot,
            }
        )

    return app


if __name__ == "__main__":
    app = create_app()

    print("=" * 72)
    print("Multi-Bank Interest Rate API - Local Development Server")
    print("=" * 72)
    print("\n🏦 Supported Banks:")
    for bank_id in AVAILABLE_BANKS.keys():
        print(f"  • {bank_id}")
    print("\n📡 Available endpoints:")
    print("  GET http://localhost:5000/")
    print("  GET http://localhost:5000/api/rates")
    print("  GET http://localhost:5000/api/rates?bank=<bank_id>")
    print("  GET http://localhost:5000/api/rates/refresh")
    print("  GET http://localhost:5000/api/rates/refresh?bank=<bank_id>")
    print("  GET http://localhost:5000/health")
    print("\n" + "=" * 72)
    print("\n🌐 Opening web interface at http://localhost:5000")
    print("\n" + "=" * 72 + "\n")

    app.run(debug=True, host="0.0.0.0", port=5000)
