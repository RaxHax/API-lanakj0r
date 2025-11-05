# Local Testing Guide

Guide for testing the Multi-Bank Interest Rate API locally before deploying to Firebase.

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Start the Local Server

```bash
python local_test.py
```

### 3. Open Web Interface

Navigate to **http://localhost:5000** in your browser.

You'll see a beautiful web interface with cards for each bank!

## 🌐 Web Interface Features

The web UI (`http://localhost:5000`) provides:

### Individual Bank Testing
- **Three bank cards**: Landsbankinn, Arion banki, Íslandsbanki
- **Fetch Rates button**: Get rates (uses cache if available)
- **Force Refresh button**: Bypass cache and scrape fresh data
- **Status badges**: Shows loading, cached, success, or error states
- **Meta information**: Displays effective date and cache status
- **JSON response viewer**: Pretty-printed JSON with syntax highlighting

### All Banks at Once
- **Fetch All Banks button**: Gets all three banks in parallel
- **Force Refresh All button**: Refreshes all banks simultaneously
- **Combined response viewer**: Shows the complete multi-bank response

### Visual Feedback
- Loading spinners during API calls
- Color-coded status badges (green for success, blue for cached, red for errors)
- Smooth animations and hover effects
- Scrollable JSON response boxes

## 📡 API Endpoints

### Get Rates (Cached)

```bash
# Single bank
curl "http://localhost:5000/api/rates?bank=landsbankinn"
curl "http://localhost:5000/api/rates?bank=arionbanki"
curl "http://localhost:5000/api/rates?bank=islandsbanki"

# All banks at once
curl "http://localhost:5000/api/rates"
```

### Force Refresh

```bash
# Single bank
curl "http://localhost:5000/api/rates/refresh?bank=landsbankinn"
curl "http://localhost:5000/api/rates/refresh?bank=arionbanki"
curl "http://localhost:5000/api/rates/refresh?bank=islandsbanki"

# All banks at once
curl "http://localhost:5000/api/rates/refresh"
```

### Health Check

```bash
curl "http://localhost:5000/health"
```

Response:
```json
{
  "status": "healthy",
  "timestamp": "2025-11-05T10:30:00Z",
  "available_banks": ["landsbankinn", "arionbanki", "islandsbanki"],
  "cache_status": {
    "landsbankinn": true,
    "arionbanki": false,
    "islandsbanki": true
  }
}
```

## 📋 Response Examples

### Single Bank Response

```json
{
  "bank_id": "landsbankinn",
  "bank_name": "Landsbankinn",
  "effective_date": "2025-10-24",
  "last_updated": "2025-11-05T10:30:00Z",
  "data": {
    "deposits": { ... },
    "mortgages": { ... },
    "loans": { ... }
  },
  "source_url": "https://...",
  "cached": true
}
```

### All Banks Response

```json
{
  "banks": {
    "landsbankinn": {
      "bank_id": "landsbankinn",
      "bank_name": "Landsbankinn",
      "effective_date": "2025-10-24",
      "data": { ... },
      "cached": true
    },
    "arionbanki": { ... },
    "islandsbanki": { ... }
  },
  "available_banks": ["landsbankinn", "arionbanki", "islandsbanki"]
}
```

## 🔧 Architecture

### Files

```
API-lanakj0r/
├── local_test.py           # Flask server for local testing
├── ui_template.py          # HTML/CSS/JS for web interface
└── functions/
    └── banks/
        ├── __init__.py     # Bank registry
        ├── base.py         # BankScraper interface
        ├── landsbankinn.py # Landsbankinn PDF scraper
        ├── arionbanki.py   # Arion Bank API/PDF scraper
        └── islandsbanki.py # Íslandsbanki HTML scraper
```

### Cache Behavior

The local server uses **in-memory caching** with a **24-hour TTL**:

- First request to a bank → Scrapes fresh data
- Subsequent requests → Returns cached data (if < 24 hours old)
- `/api/rates/refresh` → Always scrapes fresh data

Cache is **per-bank**, so each bank has independent caching.

### Bank Scraping Methods

| Bank | Method | Source |
|------|--------|--------|
| **Landsbankinn** | PDF parsing | Downloads and parses PDF from website |
| **Arion banki** | API (with fallback) | Tries API first, falls back to PDF |
| **Íslandsbanki** | HTML scraping | Scrapes HTML tables from vaxtatafla page |

## 🧪 Testing Scenarios

### 1. Test Individual Banks

1. Open web interface
2. Click "Fetch Rates" for Landsbankinn
3. Verify status shows "Cached ✓" or "Success ✓"
4. Check JSON response is properly formatted
5. Repeat for Arion banki and Íslandsbanki

### 2. Test Cache Behavior

1. Click "Fetch Rates" for a bank → Should scrape fresh data
2. Click "Fetch Rates" again → Should return cached data (status: "Cached ✓")
3. Click "Force Refresh" → Should scrape fresh data regardless

### 3. Test All Banks Endpoint

1. Click "Fetch All Banks" button
2. Verify all three bank cards update simultaneously
3. Check the response contains all three banks

### 4. Test Error Handling

Try requesting an invalid bank:
```bash
curl "http://localhost:5000/api/rates?bank=invalid"
```

Expected response:
```json
{
  "error": "Unknown bank: invalid",
  "available_banks": ["landsbankinn", "arionbanki", "islandsbanki"]
}
```

### 5. Test Health Endpoint

```bash
curl "http://localhost:5000/health"
```

Should return status and cache information for all banks.

## 🐛 Troubleshooting

### Dependencies Missing

```bash
ModuleNotFoundError: No module named 'bs4'
```

**Fix**: Install requirements
```bash
pip install -r requirements.txt
```

### Port Already in Use

```bash
OSError: [Errno 48] Address already in use
```

**Fix**: Kill existing process or use different port
```bash
# Kill process on port 5000
lsof -ti:5000 | xargs kill -9

# Or run on different port
python local_test.py  # Edit port in file
```

### Import Errors

```bash
ImportError: cannot import name 'AVAILABLE_BANKS'
```

**Fix**: Make sure you're running from the project root directory
```bash
cd /path/to/API-lanakj0r
python local_test.py
```

### Scraping Failures

If a bank scraper fails:
1. Check console logs for detailed error messages
2. Verify internet connectivity
3. Check if the bank's website is accessible
4. The website structure may have changed (requires scraper update)

## 🎨 UI Customization

The web interface is defined in `ui_template.py`. You can customize:

- **Colors**: Edit the CSS gradients and color variables
- **Layout**: Modify the grid layout in `.banks-grid`
- **Fonts**: Change the font-family in body styles
- **Animations**: Adjust transition and animation properties

## 📦 Before Deploying

Once local testing is successful:

1. ✅ Verify all three banks scrape successfully
2. ✅ Test cache behavior works correctly
3. ✅ Check error handling for invalid requests
4. ✅ Confirm JSON responses match expected format
5. ✅ Review console logs for any warnings

Then deploy:
```bash
firebase deploy --only functions
```

## 💡 Tips

- **Console logs**: Local server shows detailed logs for debugging
- **Network tab**: Use browser DevTools to inspect API requests
- **JSON formatting**: Response viewer auto-formats JSON with syntax highlighting
- **Parallel testing**: "Fetch All Banks" tests all scrapers simultaneously
- **Cache duration**: Set in `local_test.py` (default: 24 hours)

## 🔗 Related Documentation

- [MULTI_BANK_SUPPORT.md](MULTI_BANK_SUPPORT.md) - Multi-bank architecture guide
- [README.md](README.md) - Main project documentation
- [QUICKSTART.md](QUICKSTART.md) - Quick deployment guide
