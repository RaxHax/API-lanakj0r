# Landsbankinn Interest Rate API

A Python API that scrapes the latest interest rates from Landsbankinn's website and serves them via a REST API. Built for Firebase Cloud Functions with Firestore caching.

> **⚡ Quick Start**: See [QUICKSTART.md](QUICKSTART.md) to get running in 5 minutes!
>
> **📋 Example Response**: See [example_response.json](example_response.json) for the complete API response structure

## Features

- 🔄 Automatic PDF scraping from Landsbankinn's website
- 📊 Comprehensive parsing of all interest rate categories
- 💾 Firestore caching (24-hour duration)
- 🚀 Firebase Cloud Functions deployment
- 🧪 Local testing with Flask
- 📱 iOS-ready JSON API

## Architecture

```
┌─────────────┐
│  iOS App    │
│ (Dreamflow) │
└──────┬──────┘
       │
       ▼
┌─────────────────┐
│ Cloud Functions │
│  - get_rates    │
│  - refresh_rates│
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌─────────┐  ┌──────────┐
│Firestore│  │ Scraper  │
│ Cache   │  │ + Parser │
└─────────┘  └──────────┘
                   │
                   ▼
            ┌──────────────┐
            │ Landsbankinn │
            │   Website    │
            └──────────────┘
```

## Data Extracted

The API parses the following sections from the Landsbankinn PDF:

### 1. Deposit Accounts (Innlán)
- **Veltureikningar** (Current accounts)
  - Business accounts, Personal accounts
  - Vörðureikningar (tiered)
- **Sparireikningar** (Savings accounts)
  - Kjörbók, Markmið app savings
  - Vaxtareikningur (multiple tiers)
  - Fixed-term accounts (3, 6, 12, 24 months)
  - Special accounts (Framtíðargrunnur, Fasteignagrunnur, Lífeyrisbók)
- **Foreign Currency Deposits**
  - USD, GBP, CAD, DKK, NOK, SEK, CHF, JPY, EUR, PLN

### 2. Mortgage Loans (Íbúðalán)
- **Unindexed (Óverðtryggð)**
  - Fixed rates (1, 3, 5 years) for LTV up to 55%, 65%, 75%, 80/85%
  - Variable rates
- **Indexed (Verðtryggð)**
  - Fixed rates for LTV up to 75%, 85%

### 3. Vehicle Loans (Bíla- og tækjafjármögnun)
- Electric vehicles vs. other vehicles
- LTV ranges: <51%, 51-69.9%, 70-80%

### 4. Bonds and Loan Agreements (Kjörvaxtaflokkar)
- 10 interest rate classes (0-9)
- Special categories (SpKef, Vestmannaeyjar, TM loans)

### 5. Short-term Loans
- Overdrafts (Yfirdráttarlán)
- Credit cards (Kreditkortalán)
- Student loans (Náman)

### 6. Penalty Interest (Dráttarvextir)

## Project Structure

```
API-lanakj0r/
├── functions/
│   ├── main.py              # Firebase Cloud Function handlers
│   ├── scraper.py           # PDF scraping from website
│   ├── parser.py            # PDF parsing logic
│   ├── firestore_manager.py # Firestore caching
│   └── requirements.txt     # Python dependencies
├── local_test.py            # Local Flask testing server
├── requirements.txt         # Local dependencies
├── firebase.json            # Firebase configuration
├── .firebaserc.template     # Firebase project template
└── README.md
```

## Setup Instructions

### Prerequisites

1. **Python 3.11+**
   ```bash
   python --version
   ```

2. **Firebase CLI**
   ```bash
   npm install -g firebase-tools
   ```

3. **Firebase Project**
   - Create a project at [Firebase Console](https://console.firebase.google.com/)
   - Enable Firestore Database
   - Enable Cloud Functions

### Local Development Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd API-lanakj0r
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run local test server**
   ```bash
   python local_test.py
   ```

   The server will start at `http://localhost:5000`

5. **Test the API**
   ```bash
   # Get rates (cached if available)
   curl http://localhost:5000/api/rates

   # Force refresh
   curl http://localhost:5000/api/rates/refresh

   # Health check
   curl http://localhost:5000/health
   ```

### Firebase Deployment

1. **Login to Firebase**
   ```bash
   firebase login
   ```

2. **Initialize Firebase (if not already done)**
   ```bash
   firebase init functions
   ```
   - Select "Python" as the language
   - Choose your Firebase project
   - Don't overwrite existing files

3. **Configure Firebase project**
   ```bash
   # Copy template and add your project ID
   cp .firebaserc.template .firebaserc
   # Edit .firebaserc and replace 'your-firebase-project-id'
   ```

4. **Deploy to Firebase**
   ```bash
   firebase deploy --only functions
   ```

5. **Get your Cloud Function URLs**
   ```bash
   firebase functions:list
   ```

   Example URLs:
   ```
   https://us-central1-your-project.cloudfunctions.net/get_rates
   https://us-central1-your-project.cloudfunctions.net/refresh_rates
   ```

### Firestore Setup

The Firestore database will be automatically created when the functions first run. The schema is:

**Collection: `interest_rates`**

```javascript
{
  effective_date: "2025-10-24",        // Date rates became effective
  last_updated: Timestamp,             // When data was cached
  data: {                              // Parsed rate data
    deposits: { ... },
    mortgages: { ... },
    vehicle_loans: { ... },
    bonds_and_loans: { ... },
    short_term_loans: { ... },
    penalty_interest: 15.25
  },
  source_url: "https://...",           // PDF URL
  cached: true
}
```

**Indexes**: None required (queries use simple ordering)

### iOS Integration

#### Using in Dreamflow

1. Add an API call component
2. Set the endpoint URL to your Cloud Function URL
3. Parse the JSON response

#### Example Swift/SwiftUI Integration

```swift
struct InterestRate: Codable {
    let effectiveDate: String
    let lastUpdated: String
    let data: RateData
    let sourceUrl: String
    let cached: Bool

    enum CodingKeys: String, CodingKey {
        case effectiveDate = "effective_date"
        case lastUpdated = "last_updated"
        case data
        case sourceUrl = "source_url"
        case cached
    }
}

struct RateData: Codable {
    let deposits: DepositRates
    let mortgages: MortgageRates
    // ... other rate categories
}

class RatesService {
    let baseURL = "https://us-central1-your-project.cloudfunctions.net"

    func fetchRates() async throws -> InterestRate {
        let url = URL(string: "\(baseURL)/get_rates")!
        let (data, _) = try await URLSession.shared.data(from: url)
        return try JSONDecoder().decode(InterestRate.self, from: data)
    }

    func refreshRates() async throws -> InterestRate {
        let url = URL(string: "\(baseURL)/refresh_rates")!
        let (data, _) = try await URLSession.shared.data(from: url)
        return try JSONDecoder().decode(InterestRate.self, from: data)
    }
}
```

## API Endpoints

### GET /api/rates

Returns cached interest rates if available and not expired (< 24 hours old), otherwise scrapes fresh data.

**Response:**
```json
{
  "effective_date": "2025-10-24",
  "last_updated": "2025-11-05T10:30:00Z",
  "data": {
    "deposits": {
      "veltureikningar": { ... },
      "sparireikningar": { ... },
      "foreign_currency": { ... }
    },
    "mortgages": {
      "unindexed": { ... },
      "indexed": { ... }
    },
    "vehicle_loans": { ... },
    "bonds_and_loans": { ... },
    "short_term_loans": { ... },
    "penalty_interest": 15.25
  },
  "source_url": "https://www.landsbankinn.is/.../vaxtatafla.pdf",
  "cached": true
}
```

### GET /api/rates/refresh

Forces a fresh scrape of the PDF regardless of cache status.

**Response:** Same as above, with `"cached": false`

## Configuration

### Cache Duration

Default: 24 hours

To modify, edit `firestore_manager.py`:

```python
CACHE_DURATION_HOURS = 24  # Change this value
```

### Number of Cached Entries to Keep

Default: 5 most recent entries

To modify, edit `main.py`:

```python
firestore_mgr.clear_old_caches(keep_latest=5)  # Change this value
```

## Troubleshooting

### PDF Scraping Issues

If the scraper can't find the PDF:

1. Check if the website URL has changed
2. Update `BASE_URL` in `functions/scraper.py`
3. Verify the PDF link pattern in `get_latest_pdf_url()`

### Parsing Issues

If rates are not being parsed correctly:

1. Download the latest PDF manually
2. Check if the format has changed
3. Update regex patterns in `functions/parser.py`

### Firebase Deployment Issues

```bash
# Check logs
firebase functions:log

# Deploy specific function
firebase deploy --only functions:get_rates
```

### Local Testing Issues

```bash
# Install dependencies in functions directory
cd functions
pip install -r requirements.txt
cd ..

# Run with debug mode
FLASK_DEBUG=1 python local_test.py
```

## Development

### Running Tests

```bash
# TODO: Add pytest tests
pytest tests/
```

### Code Style

```bash
# Format with black
black functions/ local_test.py

# Lint with flake8
flake8 functions/ local_test.py
```

## Cost Estimation

### Firebase Cloud Functions

- **Free tier**: 2M invocations/month
- **Typical usage**: ~10-100 requests/day = ~3,000/month
- **Expected cost**: $0 (within free tier)

### Firestore

- **Free tier**: 1GB storage, 50K reads/day, 20K writes/day
- **Typical usage**: <1MB storage, <100 reads/day, <10 writes/day
- **Expected cost**: $0 (within free tier)

## License

MIT License - See LICENSE file for details

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## Support

For issues or questions:
- Open an issue on GitHub
- Check the [Firebase documentation](https://firebase.google.com/docs)

## Roadmap

- [ ] Add unit tests
- [ ] Add data validation
- [ ] Support for historical rate data
- [ ] Rate change notifications
- [ ] GraphQL API option
- [ ] Rate comparison endpoints

---

Built with ❤️ for the Icelandic fintech community
