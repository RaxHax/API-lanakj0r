# Multi-Bank Support

The API now supports **three major Icelandic banks**:

## Supported Banks

| Bank | Bank ID | Scraping Method |
|------|---------|----------------|
| **Landsbankinn** | `landsbankinn` | PDF parsing |
| **Arion banki** | `arionbanki` | API (fallback to PDF) |
| **Íslandsbanki** | `islandsbanki` | HTML scraping |

## API Endpoints

### Get Rates for a Specific Bank

```bash
# Landsbankinn
GET /api/rates?bank=landsbankinn

# Arion banki
GET /api/rates?bank=arionbanki

# Íslandsbanki
GET /api/rates?bank=islandsbanki
```

### Get Rates for All Banks

```bash
GET /api/rates
```

**Response:**
```json
{
  "banks": {
    "landsbankinn": {
      "bank_id": "landsbankinn",
      "bank_name": "Landsbankinn",
      "effective_date": "2025-10-24",
      "last_updated": "2025-11-05T10:30:00Z",
      "data": { ... },
      "source_url": "https://...",
      "cached": true
    },
    "arionbanki": { ... },
    "islandsbanki": { ... }
  },
  "available_banks": ["landsbankinn", "arionbanki", "islandsbanki"]
}
```

### Force Refresh

```bash
# Refresh specific bank
GET /api/rates/refresh?bank=landsbankinn

# Refresh all banks
GET /api/rates/refresh
```

## Architecture

```
┌─────────────┐
│   iOS App   │
└──────┬──────┘
       │ GET /api/rates?bank=<id>
       ▼
┌──────────────────────────┐
│  Cloud Function (main.py)│
└──────────┬───────────────┘
           │
    ┌──────┴────────┐
    ▼               ▼
┌─────────┐    ┌────────────┐
│Firestore│    │Bank Scrapers│
│  Cache  │    │(Landsbankinn│
└─────────┘    │ Arion      │
               │ Íslandsbanki)│
               └────────────┘
```

### Bank Scrapers

All bank scrapers implement the `BankScraper` base class:

```python
from banks import get_bank_scraper

# Get a specific bank scraper
scraper = get_bank_scraper('landsbankinn')

# Scrape rates
rate_data, source_url = scraper.scrape_rates()
```

#### Landsbankinn (`banks/landsbankinn.py`)
- **Method**: PDF scraping
- **Source**: https://www.landsbankinn.is/vextir-og-verdskra
- **Strategy**: Find PDF link → Download → Extract text → Parse all rate categories

#### Arion Bank (`banks/arionbanki.py`)
- **Method**: API first, PDF fallback
- **Source**: https://www.arionbanki.is/api/interest-rates (API)
- **Fallback**: PDF from https://www.arionbanki.is/bankinn/fleira/vextir-og-verdskra/
- **Strategy**: Try API → If failed, download PDF → Parse

#### Íslandsbanki (`banks/islandsbanki.py`)
- **Method**: HTML scraping
- **Source**: https://www.islandsbanki.is/is/grein/vaxtatafla
- **Strategy**: Fetch HTML → Parse tables → Extract rates from dropdown sections

## Firestore Schema

Collection: `interest_rates`

```javascript
{
  bank_id: "landsbankinn",              // Bank identifier
  bank_name: "Landsbankinn",            // Display name
  effective_date: "2025-10-24",         // When rates became effective
  last_updated: Timestamp,              // When cached
  data: { ... },                        // Rate data structure
  source_url: "https://...",            // Source URL
  cached: true
}
```

## Adding a New Bank

1. Create a new scraper in `functions/banks/new_bank.py`:

```python
from .base import BankScraper

class NewBankScraper(BankScraper):
    def __init__(self):
        super().__init__()
        self.bank_name = "New Bank"
        self.bank_id = "newbank"

    def scrape_rates(self):
        # Implement scraping logic
        pass

    def parse_effective_date(self, data):
        # Parse effective date
        pass
```

2. Register in `functions/banks/__init__.py`:

```python
from .newbank import NewBankScraper

AVAILABLE_BANKS = {
    'landsbankinn': LandsbankinScraper,
    'arionbanki': ArionBankiScraper,
    'islandsbanki': IslandsbankiScraper,
    'newbank': NewBankScraper,  # Add here
}
```

3. Update Firestore manager's `get_all_banks_rates()` if needed.

## Local Testing

The local test server (`local_test.py`) supports multi-bank as well:

```bash
# Start server
python local_test.py

# Test endpoints
curl "http://localhost:5000/api/rates?bank=landsbankinn"
curl "http://localhost:5000/api/rates?bank=arionbanki"
curl "http://localhost:5000/api/rates?bank=islandsbanki"
curl "http://localhost:5000/api/rates"  # All banks
```

## iOS Integration

### Get rates for a specific bank

```swift
let baseURL = "https://your-project.cloudfunctions.net"

func fetchRates(for bank: String) async throws -> InterestRate {
    let url = URL(string: "\(baseURL)/get_rates?bank=\(bank)")!
    let (data, _) = try await URLSession.shared.data(from: url)
    return try JSONDecoder().decode(InterestRate.self, from: data)
}

// Usage
let landsbankinRates = try await fetchRates(for: "landsbankinn")
let arionRates = try await fetchRates(for: "arionbanki")
```

### Get all banks

```swift
struct AllBanksResponse: Codable {
    let banks: [String: InterestRate]
    let availableBanks: [String]

    enum CodingKeys: String, CodingKey {
        case banks
        case availableBanks = "available_banks"
    }
}

func fetchAllBanks() async throws -> AllBanksResponse {
    let url = URL(string: "\(baseURL)/get_rates")!
    let (data, _) = try await URLSession.shared.data(from: url)
    return try JSONDecoder().decode(AllBanksResponse.self, from: data)
}
```

## Migration from Single-Bank

If you were using the previous single-bank API:

**Before:**
```bash
GET /api/rates
```

**After (equivalent):**
```bash
GET /api/rates?bank=landsbankinn
```

**Or (all banks):**
```bash
GET /api/rates
```

The single-bank behavior is maintained when you specify `?bank=landsbankinn`. The default (no parameter) now returns all banks.

## Performance Notes

- **Caching**: Each bank's rates are cached separately with 24-hour expiry
- **Parallel scraping**: When fetching all banks, scraping happens sequentially (not parallel) to avoid overwhelming external services
- **Error handling**: If one bank fails, others will still return successfully

## Troubleshooting

### Bank-specific issues

```bash
# Check logs
firebase functions:log

# Test specific bank locally
python local_test.py
curl "http://localhost:5000/api/rates?bank=islandsbanki"
```

### Common Issues

1. **"Invalid bank" error**: Check the bank ID spelling
2. **Arion Bank API failing**: It will automatically fall back to PDF
3. **Íslandsbanki HTML changes**: May need to update HTML parsing selectors

---

**Status**: ✅ Production Ready
**Last Updated**: 2025-11-05
