"""
Local testing Flask app for Multi-Bank Interest Rate API
Supports: Landsbankinn, Arion banki, Íslandsbanki
Run this locally before deploying to Firebase
"""
import logging
import sys
from datetime import datetime
from flask import Flask, jsonify, request, render_template_string

# Add functions directory to path
sys.path.insert(0, 'functions')

from functions.banks import get_bank_scraper, AVAILABLE_BANKS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# In-memory cache for local testing (per bank)
_cache = {}

CACHE_DURATION_SECONDS = 24 * 60 * 60  # 24 hours


def is_cache_valid(bank_id):
    """Check if in-memory cache is still valid for a specific bank"""
    if bank_id not in _cache:
        return False

    cache_entry = _cache[bank_id]
    if not cache_entry.get('data') or not cache_entry.get('timestamp'):
        return False

    cache_age = (datetime.utcnow() - cache_entry['timestamp']).total_seconds()
    return cache_age < CACHE_DURATION_SECONDS


def get_fresh_rates(bank_id):
    """Scrape and parse fresh rates for a specific bank"""
    try:
        scraper = get_bank_scraper(bank_id)
        if not scraper:
            logger.error(f"Unknown bank: {bank_id}")
            return None, None

        logger.info(f"Scraping rates for {scraper.bank_name}...")
        rate_data, source_url = scraper.scrape_rates()

        if not rate_data:
            logger.error(f"Failed to scrape rates for {bank_id}")
            return None, None

        return rate_data, source_url

    except Exception as e:
        logger.error(f"Error scraping {bank_id}: {e}", exc_info=True)
        return None, None


def format_single_bank_response(bank_id, rate_data, source_url, from_cache=False):
    """Format API response for a single bank"""
    return {
        "bank_id": bank_id,
        "bank_name": rate_data.get("bank_name", "Unknown"),
        "effective_date": rate_data.get("effective_date"),
        "last_updated": datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
        "data": rate_data,
        "source_url": source_url,
        "cached": from_cache
    }


def format_multi_bank_response(banks_data):
    """Format API response for multiple banks"""
    return {
        "banks": banks_data,
        "available_banks": list(AVAILABLE_BANKS.keys())
    }


@app.route('/', methods=['GET'])
def index():
    """Serve the web UI"""
    from ui_template import HTML_TEMPLATE
    return render_template_string(HTML_TEMPLATE)


@app.route('/api/rates', methods=['GET'])
def get_rates():
    """
    GET /api/rates?bank=<bank_id> - Return interest rates for specific bank
    GET /api/rates - Return interest rates for all banks

    Returns cached data if available and not expired,
    otherwise scrapes and parses the latest data
    """
    try:
        bank_id = request.args.get('bank')

        # If bank_id specified, return single bank
        if bank_id:
            if bank_id not in AVAILABLE_BANKS:
                return jsonify({
                    "error": f"Unknown bank: {bank_id}",
                    "available_banks": list(AVAILABLE_BANKS.keys())
                }), 400

            logger.info(f"GET /api/rates?bank={bank_id} - Request received")

            # Check cache
            if is_cache_valid(bank_id):
                logger.info(f"Returning cached rates for {bank_id}")
                cache_entry = _cache[bank_id]
                response = format_single_bank_response(
                    bank_id,
                    cache_entry['data'],
                    cache_entry['source_url'],
                    from_cache=True
                )
                return jsonify(response)

            # Cache miss - get fresh data
            logger.info(f"Cache miss - fetching fresh rates for {bank_id}")
            rate_data, source_url = get_fresh_rates(bank_id)

            if not rate_data:
                return jsonify({
                    "error": f"Failed to fetch interest rates for {bank_id}"
                }), 500

            # Update cache
            _cache[bank_id] = {
                'data': rate_data,
                'timestamp': datetime.utcnow(),
                'source_url': source_url
            }

            response = format_single_bank_response(
                bank_id, rate_data, source_url, from_cache=False
            )
            return jsonify(response)

        # No bank_id - return all banks
        logger.info("GET /api/rates - Request received (all banks)")

        banks_data = {}
        for bank_id in AVAILABLE_BANKS.keys():
            # Check cache
            if is_cache_valid(bank_id):
                logger.info(f"Using cached data for {bank_id}")
                cache_entry = _cache[bank_id]
                banks_data[bank_id] = format_single_bank_response(
                    bank_id,
                    cache_entry['data'],
                    cache_entry['source_url'],
                    from_cache=True
                )
            else:
                # Fetch fresh data
                logger.info(f"Fetching fresh data for {bank_id}")
                rate_data, source_url = get_fresh_rates(bank_id)

                if rate_data:
                    _cache[bank_id] = {
                        'data': rate_data,
                        'timestamp': datetime.utcnow(),
                        'source_url': source_url
                    }
                    banks_data[bank_id] = format_single_bank_response(
                        bank_id, rate_data, source_url, from_cache=False
                    )
                else:
                    banks_data[bank_id] = {
                        "bank_id": bank_id,
                        "error": "Failed to fetch data"
                    }

        response = format_multi_bank_response(banks_data)
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
    GET /api/rates/refresh?bank=<bank_id> - Force refresh for specific bank
    GET /api/rates/refresh - Force refresh all banks

    Scrapes and parses the latest data regardless of cache status
    """
    try:
        bank_id = request.args.get('bank')

        # If bank_id specified, refresh single bank
        if bank_id:
            if bank_id not in AVAILABLE_BANKS:
                return jsonify({
                    "error": f"Unknown bank: {bank_id}",
                    "available_banks": list(AVAILABLE_BANKS.keys())
                }), 400

            logger.info(f"GET /api/rates/refresh?bank={bank_id} - Request received")

            # Get fresh data
            rate_data, source_url = get_fresh_rates(bank_id)

            if not rate_data:
                return jsonify({
                    "error": f"Failed to fetch interest rates for {bank_id}"
                }), 500

            # Update cache
            _cache[bank_id] = {
                'data': rate_data,
                'timestamp': datetime.utcnow(),
                'source_url': source_url
            }

            response = format_single_bank_response(
                bank_id, rate_data, source_url, from_cache=False
            )
            return jsonify(response)

        # No bank_id - refresh all banks
        logger.info("GET /api/rates/refresh - Request received (all banks)")

        banks_data = {}
        for bank_id in AVAILABLE_BANKS.keys():
            logger.info(f"Refreshing {bank_id}...")
            rate_data, source_url = get_fresh_rates(bank_id)

            if rate_data:
                _cache[bank_id] = {
                    'data': rate_data,
                    'timestamp': datetime.utcnow(),
                    'source_url': source_url
                }
                banks_data[bank_id] = format_single_bank_response(
                    bank_id, rate_data, source_url, from_cache=False
                )
            else:
                banks_data[bank_id] = {
                    "bank_id": bank_id,
                    "error": "Failed to fetch data"
                }

        response = format_multi_bank_response(banks_data)
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
    cache_status = {}
    for bank_id in AVAILABLE_BANKS.keys():
        cache_status[bank_id] = is_cache_valid(bank_id)

    return jsonify({
        "status": "healthy",
        "timestamp": datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
        "available_banks": list(AVAILABLE_BANKS.keys()),
        "cache_status": cache_status
    })


if __name__ == '__main__':
    print("=" * 60)
    print("Multi-Bank Interest Rate API - Local Test Server")
    print("=" * 60)
    print("\n🏦 Supported Banks:")
    for bank_id, scraper_class in AVAILABLE_BANKS.items():
        scraper = scraper_class()
        print(f"  • {scraper.bank_name} ({bank_id})")
    print("\n📡 Available endpoints:")
    print("  GET http://localhost:5000/")
    print("  GET http://localhost:5000/api/rates")
    print("  GET http://localhost:5000/api/rates?bank=<bank_id>")
    print("  GET http://localhost:5000/api/rates/refresh")
    print("  GET http://localhost:5000/api/rates/refresh?bank=<bank_id>")
    print("  GET http://localhost:5000/health")
    print("\n" + "=" * 60)
    print("\n🌐 Opening web interface at http://localhost:5000")
    print("\n" + "=" * 60 + "\n")

    app.run(debug=True, host='0.0.0.0', port=5000)
