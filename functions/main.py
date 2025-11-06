"""Firebase Cloud Functions entry points for the Interest Rate API."""

import logging
from flask import jsonify, request
from firebase_functions import https_fn
from firebase_admin import initialize_app

from services import RateService, RateServiceError, UnknownBankError

# Initialise Firebase Admin only once per cold start.
initialize_app()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create a singleton service instance that can be reused by multiple invocations
# within the same Cloud Function instance.
rate_service = RateService()


@https_fn.on_request()
def get_rates(req: https_fn.Request) -> https_fn.Response:
    """Return interest rates for one bank or every supported bank."""

    bank_id = (request.args.get("bank") or "").strip().lower()
    logger.info("GET /api/rates - bank=%s", bank_id or "all")

    try:
        if bank_id:
            payload = rate_service.get_bank_rates(bank_id)
            return jsonify(payload)

        payload = rate_service.get_all_bank_rates()
        return jsonify(payload)

    except UnknownBankError as exc:
        logger.warning("Invalid bank requested: %s", exc)
        return (
            jsonify(
                {
                    "error": str(exc),
                    "available_banks": list(rate_service.list_supported_banks()),
                }
            ),
            400,
        )
    except RateServiceError as exc:
        logger.error("Failed to return rates: %s", exc)
        return jsonify({"error": "Failed to fetch bank rates"}), 502
    except Exception as exc:  # pragma: no cover - defensive guard
        logger.error("Unexpected error in get_rates", exc_info=True)
        return jsonify({"error": "Internal server error", "details": str(exc)}), 500


@https_fn.on_request()
def refresh_rates(req: https_fn.Request) -> https_fn.Response:
    """Force a refresh of cached data and return the latest snapshot."""

    bank_id = (request.args.get("bank") or "").strip().lower()
    logger.info("GET /api/rates/refresh - bank=%s", bank_id or "all")

    try:
        if bank_id:
            payload = rate_service.get_bank_rates(bank_id, force_refresh=True)
            return jsonify(payload)

        payload = rate_service.get_all_bank_rates(force_refresh=True)
        return jsonify(payload)

    except UnknownBankError as exc:
        logger.warning("Invalid bank requested during refresh: %s", exc)
        return (
            jsonify(
                {
                    "error": str(exc),
                    "available_banks": list(rate_service.list_supported_banks()),
                }
            ),
            400,
        )
    except RateServiceError as exc:
        logger.error("Failed to refresh rates: %s", exc)
        return jsonify({"error": "Failed to refresh bank rates"}), 502
    except Exception as exc:  # pragma: no cover - defensive guard
        logger.error("Unexpected error in refresh_rates", exc_info=True)
        return jsonify({"error": "Internal server error", "details": str(exc)}), 500

