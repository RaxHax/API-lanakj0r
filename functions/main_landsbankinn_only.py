"""
Firebase Cloud Functions for Landsbankinn Interest Rate API
"""
import logging
from flask import jsonify
from firebase_functions import https_fn
from firebase_admin import initialize_app

from scraper import LandsbankinScraper
from parser import InterestRateParser
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
    GET /api/rates - Return cached interest rates

    Returns cached data if available and not expired,
    otherwise scrapes and parses the latest PDF
    """
    try:
        logger.info("GET /api/rates - Request received")

        # Initialize managers
        firestore_mgr = FirestoreManager()

        # Try to get cached data
        cached_data = firestore_mgr.get_cached_rates()

        if cached_data:
            logger.info("Returning cached rates")
            response = firestore_mgr.format_response(cached_data, from_cache=True)
            return jsonify(response)

        # Cache miss - scrape and parse
        logger.info("Cache miss - scraping latest PDF")

        scraper = LandsbankinScraper()
        pdf_content, pdf_url = scraper.scrape_latest_pdf()

        if not pdf_content:
            logger.error("Failed to scrape PDF")
            return jsonify({
                "error": "Failed to scrape PDF from Landsbankinn website"
            }), 500

        # Parse PDF
        parser = InterestRateParser()
        rate_data = parser.parse_all(pdf_content)

        if not rate_data:
            logger.error("Failed to parse PDF")
            return jsonify({
                "error": "Failed to parse interest rate data from PDF"
            }), 500

        # Save to Firestore
        firestore_mgr.save_rates(rate_data, pdf_url)

        # Clean up old caches
        firestore_mgr.clear_old_caches(keep_latest=5)

        # Return fresh data
        response = firestore_mgr.format_response(
            {
                "data": rate_data,
                "effective_date": rate_data.get("effective_date"),
                "source_url": pdf_url
            },
            from_cache=False
        )

        logger.info("Returning freshly scraped rates")
        return jsonify(response)

    except Exception as e:
        logger.error(f"Error in get_rates: {e}", exc_info=True)
        return jsonify({
            "error": "Internal server error",
            "details": str(e)
        }), 500


@https_fn.on_request()
def refresh_rates(req: https_fn.Request) -> https_fn.Response:
    """
    GET /api/rates/refresh - Force refresh of interest rates

    Scrapes and parses the latest PDF regardless of cache status
    """
    try:
        logger.info("GET /api/rates/refresh - Request received")

        # Initialize managers
        scraper = LandsbankinScraper()
        parser = InterestRateParser()
        firestore_mgr = FirestoreManager()

        # Scrape latest PDF
        logger.info("Scraping latest PDF (forced refresh)")
        pdf_content, pdf_url = scraper.scrape_latest_pdf()

        if not pdf_content:
            logger.error("Failed to scrape PDF")
            return jsonify({
                "error": "Failed to scrape PDF from Landsbankinn website"
            }), 500

        # Parse PDF
        rate_data = parser.parse_all(pdf_content)

        if not rate_data:
            logger.error("Failed to parse PDF")
            return jsonify({
                "error": "Failed to parse interest rate data from PDF"
            }), 500

        # Save to Firestore
        firestore_mgr.save_rates(rate_data, pdf_url)

        # Clean up old caches
        firestore_mgr.clear_old_caches(keep_latest=5)

        # Return fresh data
        response = firestore_mgr.format_response(
            {
                "data": rate_data,
                "effective_date": rate_data.get("effective_date"),
                "source_url": pdf_url
            },
            from_cache=False
        )

        logger.info("Returning freshly scraped rates (forced refresh)")
        return jsonify(response)

    except Exception as e:
        logger.error(f"Error in refresh_rates: {e}", exc_info=True)
        return jsonify({
            "error": "Internal server error",
            "details": str(e)
        }), 500
