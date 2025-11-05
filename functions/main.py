"""
Firebase Cloud Functions for Multi-Bank Interest Rate API
Supports: Landsbankinn, Arion Bank, Íslandsbanki
"""
import logging
from flask import jsonify, request
from firebase_functions import https_fn
from firebase_admin import initialize_app

from banks import get_bank_scraper, AVAILABLE_BANKS
from firestore_manager import FirestoreManager

# Initialize Firebase Admin
initialize_app()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@https_fn.on_request()
def get_rates(req: https_fn.Request) -> https_fn.Response:
    """
    GET /api/rates?bank=<bank_id>

    Get interest rates for a specific bank or all banks

    Query Parameters:
        bank: Optional bank ID (landsbankinn, arionbanki, islandsbanki)
              If not provided, returns rates for all banks

    Returns cached data if available and not expired,
    otherwise scrapes and parses the latest data
    """
    try:
        # Get bank parameter
        bank_id = request.args.get('bank', '').lower()

        logger.info(f"GET /api/rates - bank={bank_id or 'all'}")

        # Initialize Firestore manager
        firestore_mgr = FirestoreManager()

        # If no bank specified, return all banks
        if not bank_id:
            return get_all_banks_rates(firestore_mgr)

        # Validate bank ID
        if bank_id not in AVAILABLE_BANKS:
            return jsonify({
                "error": f"Invalid bank: {bank_id}",
                "available_banks": list(AVAILABLE_BANKS.keys())
            }), 400

        # Try to get cached data
        cached_data = firestore_mgr.get_cached_rates(bank_id=bank_id)

        if cached_data:
            logger.info(f"Returning cached rates for {bank_id}")
            response = firestore_mgr.format_response(cached_data, from_cache=True)
            return jsonify(response)

        # Cache miss - scrape fresh data
        logger.info(f"Cache miss - scraping {bank_id}")

        # Get bank scraper
        scraper = get_bank_scraper(bank_id)

        # Scrape rates
        rate_data, source_url = scraper.scrape_rates()

        if not rate_data:
            logger.error(f"Failed to scrape rates from {bank_id}")
            return jsonify({
                "error": f"Failed to scrape rates from {scraper.bank_name}"
            }), 500

        # Save to Firestore
        firestore_mgr.save_rates(
            rate_data,
            source_url,
            bank_id=scraper.bank_id,
            bank_name=scraper.bank_name
        )

        # Clean up old caches
        firestore_mgr.clear_old_caches(keep_latest=5)

        # Return fresh data
        response = firestore_mgr.format_response(
            {
                "bank_id": scraper.bank_id,
                "bank_name": scraper.bank_name,
                "data": rate_data,
                "effective_date": rate_data.get("effective_date"),
                "source_url": source_url
            },
            from_cache=False
        )

        logger.info(f"Returning freshly scraped rates for {bank_id}")
        return jsonify(response)

    except Exception as e:
        logger.error(f"Error in get_rates: {e}", exc_info=True)
        return jsonify({
            "error": "Internal server error",
            "details": str(e)
        }), 500


def get_all_banks_rates(firestore_mgr: FirestoreManager):
    """Get rates for all banks"""
    try:
        logger.info("Fetching rates for all banks")

        all_rates = {}
        any_fresh = False

        for bank_id in AVAILABLE_BANKS.keys():
            # Try cache first
            cached_data = firestore_mgr.get_cached_rates(bank_id=bank_id)

            if cached_data:
                all_rates[bank_id] = firestore_mgr.format_response(cached_data, from_cache=True)
            else:
                # Scrape fresh data
                try:
                    scraper = get_bank_scraper(bank_id)
                    rate_data, source_url = scraper.scrape_rates()

                    if rate_data:
                        # Save to cache
                        firestore_mgr.save_rates(
                            rate_data,
                            source_url,
                            bank_id=scraper.bank_id,
                            bank_name=scraper.bank_name
                        )

                        all_rates[bank_id] = firestore_mgr.format_response(
                            {
                                "bank_id": scraper.bank_id,
                                "bank_name": scraper.bank_name,
                                "data": rate_data,
                                "effective_date": rate_data.get("effective_date"),
                                "source_url": source_url
                            },
                            from_cache=False
                        )
                        any_fresh = True
                    else:
                        all_rates[bank_id] = {
                            "error": f"Failed to scrape {bank_id}"
                        }

                except Exception as e:
                    logger.error(f"Error scraping {bank_id}: {e}")
                    all_rates[bank_id] = {
                        "error": str(e)
                    }

        # Clean up old caches if we fetched fresh data
        if any_fresh:
            firestore_mgr.clear_old_caches(keep_latest=5)

        return jsonify({
            "banks": all_rates,
            "available_banks": list(AVAILABLE_BANKS.keys())
        })

    except Exception as e:
        logger.error(f"Error getting all banks rates: {e}", exc_info=True)
        return jsonify({
            "error": "Internal server error",
            "details": str(e)
        }), 500


@https_fn.on_request()
def refresh_rates(req: https_fn.Request) -> https_fn.Response:
    """
    GET /api/rates/refresh?bank=<bank_id>

    Force refresh of interest rates

    Query Parameters:
        bank: Optional bank ID (landsbankinn, arionbanki, islandsbanki)
              If not provided, refreshes all banks
    """
    try:
        # Get bank parameter
        bank_id = request.args.get('bank', '').lower()

        logger.info(f"GET /api/rates/refresh - bank={bank_id or 'all'}")

        # Initialize managers
        firestore_mgr = FirestoreManager()

        # If no bank specified, refresh all banks
        if not bank_id:
            return refresh_all_banks_rates(firestore_mgr)

        # Validate bank ID
        if bank_id not in AVAILABLE_BANKS:
            return jsonify({
                "error": f"Invalid bank: {bank_id}",
                "available_banks": list(AVAILABLE_BANKS.keys())
            }), 400

        # Get bank scraper
        scraper = get_bank_scraper(bank_id)

        # Scrape rates
        logger.info(f"Force refreshing rates for {bank_id}")
        rate_data, source_url = scraper.scrape_rates()

        if not rate_data:
            logger.error(f"Failed to scrape rates from {bank_id}")
            return jsonify({
                "error": f"Failed to scrape rates from {scraper.bank_name}"
            }), 500

        # Save to Firestore
        firestore_mgr.save_rates(
            rate_data,
            source_url,
            bank_id=scraper.bank_id,
            bank_name=scraper.bank_name
        )

        # Clean up old caches
        firestore_mgr.clear_old_caches(keep_latest=5)

        # Return fresh data
        response = firestore_mgr.format_response(
            {
                "bank_id": scraper.bank_id,
                "bank_name": scraper.bank_name,
                "data": rate_data,
                "effective_date": rate_data.get("effective_date"),
                "source_url": source_url
            },
            from_cache=False
        )

        logger.info(f"Returning force-refreshed rates for {bank_id}")
        return jsonify(response)

    except Exception as e:
        logger.error(f"Error in refresh_rates: {e}", exc_info=True)
        return jsonify({
            "error": "Internal server error",
            "details": str(e)
        }), 500


def refresh_all_banks_rates(firestore_mgr: FirestoreManager):
    """Force refresh rates for all banks"""
    try:
        logger.info("Force refreshing rates for all banks")

        all_rates = {}

        for bank_id in AVAILABLE_BANKS.keys():
            try:
                scraper = get_bank_scraper(bank_id)
                rate_data, source_url = scraper.scrape_rates()

                if rate_data:
                    # Save to cache
                    firestore_mgr.save_rates(
                        rate_data,
                        source_url,
                        bank_id=scraper.bank_id,
                        bank_name=scraper.bank_name
                    )

                    all_rates[bank_id] = firestore_mgr.format_response(
                        {
                            "bank_id": scraper.bank_id,
                            "bank_name": scraper.bank_name,
                            "data": rate_data,
                            "effective_date": rate_data.get("effective_date"),
                            "source_url": source_url
                        },
                        from_cache=False
                    )
                else:
                    all_rates[bank_id] = {
                        "error": f"Failed to scrape {bank_id}"
                    }

            except Exception as e:
                logger.error(f"Error scraping {bank_id}: {e}")
                all_rates[bank_id] = {
                    "error": str(e)
                }

        # Clean up old caches
        firestore_mgr.clear_old_caches(keep_latest=5)

        return jsonify({
            "banks": all_rates,
            "available_banks": list(AVAILABLE_BANKS.keys())
        })

    except Exception as e:
        logger.error(f"Error refreshing all banks rates: {e}", exc_info=True)
        return jsonify({
            "error": "Internal server error",
            "details": str(e)
        }), 500
