"""
Local testing Flask app for Landsbankinn Interest Rate API
Run this locally before deploying to Firebase
"""
import logging
import sys
from datetime import datetime
from flask import Flask, jsonify

# Add functions directory to path
sys.path.insert(0, 'functions')

from functions.scraper import LandsbankinScraper
from functions.parser import InterestRateParser

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# In-memory cache for local testing
_cache = {
    'data': None,
    'timestamp': None,
    'source_url': None
}

CACHE_DURATION_SECONDS = 24 * 60 * 60  # 24 hours


def is_cache_valid():
    """Check if in-memory cache is still valid"""
    if not _cache['data'] or not _cache['timestamp']:
        return False

    cache_age = (datetime.utcnow() - _cache['timestamp']).total_seconds()
    return cache_age < CACHE_DURATION_SECONDS


def get_fresh_rates():
    """Scrape and parse fresh rates"""
    scraper = LandsbankinScraper()
    parser = InterestRateParser()

    # Scrape PDF
    logger.info("Scraping latest PDF...")
    pdf_content, pdf_url = scraper.scrape_latest_pdf()

    if not pdf_content:
        logger.error("Failed to scrape PDF")
        return None, None

    # Parse PDF
    logger.info("Parsing PDF...")
    rate_data = parser.parse_all(pdf_content)

    if not rate_data:
        logger.error("Failed to parse PDF")
        return None, None

    return rate_data, pdf_url


def format_response(rate_data, source_url, from_cache=False):
    """Format API response"""
    return {
        "effective_date": rate_data.get("effective_date"),
        "last_updated": datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
        "data": rate_data,
        "source_url": source_url,
        "cached": from_cache
    }


@app.route('/api/rates', methods=['GET'])
def get_rates():
    """
    GET /api/rates - Return interest rates

    Returns cached data if available and not expired,
    otherwise scrapes and parses the latest PDF
    """
    try:
        logger.info("GET /api/rates - Request received")

        # Check cache
        if is_cache_valid():
            logger.info("Returning cached rates")
            response = format_response(
                _cache['data'],
                _cache['source_url'],
                from_cache=True
            )
            return jsonify(response)

        # Cache miss - get fresh data
        logger.info("Cache miss - fetching fresh rates")
        rate_data, source_url = get_fresh_rates()

        if not rate_data:
            return jsonify({
                "error": "Failed to fetch interest rates"
            }), 500

        # Update cache
        _cache['data'] = rate_data
        _cache['timestamp'] = datetime.utcnow()
        _cache['source_url'] = source_url

        response = format_response(rate_data, source_url, from_cache=False)
        return jsonify(response)

    except Exception as e:
        logger.error(f"Error in get_rates: {e}", exc_info=True)
        return jsonify({
            "error": "Internal server error",
            "details": str(e)
        }), 500


@app.route('/api/rates/refresh', methods=['GET'])
def refresh_rates():
    """
    GET /api/rates/refresh - Force refresh of interest rates

    Scrapes and parses the latest PDF regardless of cache status
    """
    try:
        logger.info("GET /api/rates/refresh - Request received")

        # Get fresh data
        logger.info("Fetching fresh rates (forced refresh)")
        rate_data, source_url = get_fresh_rates()

        if not rate_data:
            return jsonify({
                "error": "Failed to fetch interest rates"
            }), 500

        # Update cache
        _cache['data'] = rate_data
        _cache['timestamp'] = datetime.utcnow()
        _cache['source_url'] = source_url

        response = format_response(rate_data, source_url, from_cache=False)
        return jsonify(response)

    except Exception as e:
        logger.error(f"Error in refresh_rates: {e}", exc_info=True)
        return jsonify({
            "error": "Internal server error",
            "details": str(e)
        }), 500


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
        "cache_valid": is_cache_valid()
    })


if __name__ == '__main__':
    print("=" * 60)
    print("Landsbankinn Interest Rate API - Local Test Server")
    print("=" * 60)
    print("\nAvailable endpoints:")
    print("  GET http://localhost:5000/api/rates")
    print("  GET http://localhost:5000/api/rates/refresh")
    print("  GET http://localhost:5000/health")
    print("\n" + "=" * 60)
    print("\nStarting server...\n")

    app.run(debug=True, host='0.0.0.0', port=5000)
