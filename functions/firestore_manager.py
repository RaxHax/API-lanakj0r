"""Utility helpers for storing and retrieving cache documents in Firestore."""

from datetime import datetime, timedelta, timezone
from typing import Dict, Optional
import logging

from config import Config

try:
    from google.cloud import firestore
except ImportError:  # pragma: no cover - optional dependency during tests
    # For local testing without Firebase. The service will gracefully
    # continue operating without persistence when the Firestore SDK is
    # unavailable (for example during unit tests or local development).
    firestore = None


logger = logging.getLogger(__name__)


class FirestoreManager:
    """Manager for Firestore operations"""

    COLLECTION_NAME = "interest_rates"
    CACHE_DURATION_HOURS = Config.CACHE_DURATION_HOURS

    def __init__(self):
        """Initialize Firestore client"""
        if firestore:
            try:
                self.db = firestore.Client()
                logger.info("Firestore client initialized")
            except Exception as e:
                logger.warning(f"Could not initialize Firestore client: {e}")
                self.db = None
        else:
            logger.warning("Firestore library not available")
            self.db = None

    def get_cached_rates(self, bank_id: Optional[str] = None) -> Optional[Dict]:
        """
        Get cached interest rates from Firestore

        Args:
            bank_id: Specific bank ID to get rates for (e.g., 'landsbankinn', 'arionbanki', 'islandsbanki')
                     If None, returns most recent cache (backwards compatible)

        Returns:
            Dict: Cached data with rates, or None if cache miss or expired
        """
        if not self.db:
            logger.warning("Firestore not available, cannot get cached rates")
            return None

        try:
            # Build query
            query = self.db.collection(self.COLLECTION_NAME)

            # Filter by bank if specified
            if bank_id:
                query = query.where("bank_id", "==", bank_id)

            # Get the most recent document
            docs = (
                query.order_by("last_updated", direction=firestore.Query.DESCENDING)
                .limit(1)
                .stream()
            )

            doc = next(docs, None)
            if not doc:
                logger.info(f"No cached rates found for bank: {bank_id or 'any'}")
                return None

            data = doc.to_dict()

            # Check if cache is still valid
            last_updated = data.get("last_updated")
            if not last_updated:
                logger.warning("Cached data has no last_updated timestamp")
                return None

            # Convert to datetime if it's a timestamp
            if hasattr(last_updated, 'timestamp'):
                last_updated = datetime.fromtimestamp(last_updated.timestamp())
            elif isinstance(last_updated, str):
                last_updated = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))

            # Check if cache is expired
            if isinstance(last_updated, datetime):
                if last_updated.tzinfo is None:
                    last_updated = last_updated.replace(tzinfo=timezone.utc)
                else:
                    last_updated = last_updated.astimezone(timezone.utc)
            cache_age = datetime.now(timezone.utc) - last_updated
            if cache_age > timedelta(hours=self.CACHE_DURATION_HOURS):
                logger.info(f"Cache expired (age: {cache_age})")
                return None

            logger.info(f"Retrieved valid cached rates for bank: {bank_id or 'any'}")
            return data

        except Exception as e:
            logger.error(f"Error getting cached rates: {e}")
            return None

    def save_rates(self, rate_data: Dict, source_url: str, bank_id: str = "landsbankinn", bank_name: str = "Landsbankinn") -> bool:
        """
        Save interest rates to Firestore

        Args:
            rate_data: Parsed interest rate data
            source_url: URL of the source PDF/webpage
            bank_id: Bank identifier (landsbankinn, arionbanki, islandsbanki)
            bank_name: Bank display name

        Returns:
            bool: True if successful, False otherwise
        """
        if not self.db:
            logger.warning("Firestore not available, cannot save rates")
            return False

        try:
            # Prepare document
            doc_data = {
                "bank_id": bank_id,
                "bank_name": bank_name,
                "effective_date": rate_data.get("effective_date"),
                "last_updated": firestore.SERVER_TIMESTAMP,
                "data": rate_data,
                "source_url": source_url,
                "cached": True
            }

            # Add document to collection
            doc_ref = self.db.collection(self.COLLECTION_NAME).document()
            doc_ref.set(doc_data)

            logger.info(f"Successfully saved rates for {bank_name} to Firestore (doc_id: {doc_ref.id})")
            return True

        except Exception as e:
            logger.error(f"Error saving rates to Firestore: {e}")
            return False

    def clear_old_caches(self, keep_latest: int = 5) -> int:
        """
        Clean up old cached entries, keeping only the most recent ones

        Args:
            keep_latest: Number of most recent entries to keep

        Returns:
            int: Number of documents deleted
        """
        if not self.db:
            logger.warning("Firestore not available, cannot clear old caches")
            return 0

        try:
            # Get all documents ordered by last_updated
            docs = (
                self.db.collection(self.COLLECTION_NAME)
                .order_by("last_updated", direction=firestore.Query.DESCENDING)
                .stream()
            )

            all_docs = list(docs)
            if len(all_docs) <= keep_latest:
                logger.info(f"No old caches to clear ({len(all_docs)} docs)")
                return 0

            # Delete old documents
            deleted_count = 0
            for doc in all_docs[keep_latest:]:
                doc.reference.delete()
                deleted_count += 1

            logger.info(f"Deleted {deleted_count} old cache entries")
            return deleted_count

        except Exception as e:
            logger.error(f"Error clearing old caches: {e}")
            return 0

    def get_all_banks_rates(self) -> Dict[str, Optional[Dict]]:
        """
        Get cached rates for all banks

        Returns:
            Dict: Dictionary mapping bank_id to rate data
        """
        banks = ['landsbankinn', 'arionbanki', 'islandsbanki']
        result = {}

        for bank_id in banks:
            result[bank_id] = self.get_cached_rates(bank_id=bank_id)

        return result

    def format_response(self, data: Dict, from_cache: bool = True) -> Dict:
        """Return a consistently shaped payload for API responses."""

        # Handle different data structures
        if "data" in data:
            # From Firestore
            rate_data = data["data"]
            effective_date = data.get("effective_date")
            source_url = data.get("source_url")
            last_updated = data.get("last_updated")
            bank_id = data.get("bank_id")
            bank_name = data.get("bank_name")
        else:
            # From parser
            rate_data = data
            effective_date = data.get("effective_date")
            source_url = data.get("source_url")
            last_updated = datetime.now(timezone.utc)
            bank_id = data.get("bank_id")
            bank_name = data.get("bank_name")

        # Convert timestamp to ISO format
        if hasattr(last_updated, "timestamp"):
            last_updated = datetime.fromtimestamp(last_updated.timestamp(), tz=timezone.utc)

        if isinstance(last_updated, datetime):
            last_updated_str = last_updated.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        elif isinstance(last_updated, str):
            last_updated_str = last_updated
        else:
            last_updated_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        # Fall back to sensible defaults for metadata
        if not bank_id and rate_data:
            bank_id = rate_data.get("bank_id")
        if not bank_name and rate_data:
            bank_name = rate_data.get("bank_name")

        return {
            "bank_id": bank_id,
            "bank_name": bank_name,
            "effective_date": effective_date,
            "last_updated": last_updated_str,
            "data": rate_data,
            "source_url": source_url,
            "cached": from_cache,
        }
