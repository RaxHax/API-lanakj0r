# Icelandic Banks Interest Rate API

A Python API that scrapes the latest interest rates from **three major Icelandic banks** and serves them via a REST API. Built for Firebase Cloud Functions with Firestore caching.

> **🏦 Multi-Bank Support**: Landsbankinn, Arion banki, and Íslandsbanki!
>
> **⚡ Quick Start**: See [QUICKSTART.md](QUICKSTART.md) to get running in 5 minutes!
>
> **🤖 AI Integration**: See [OPENROUTER_SETUP.md](OPENROUTER_SETUP.md) to enable free AI-powered data extraction
>
> **📋 Example Response**: See [example_response.json](example_response.json) for the complete API response structure
>
> **🔧 Multi-Bank Guide**: See [MULTI_BANK_SUPPORT.md](MULTI_BANK_SUPPORT.md) for complete multi-bank documentation

## Features

- 🏦 **Multi-bank support**: Landsbankinn, Arion banki, Íslandsbanki
- 🤖 **AI-powered parsing**: Free OpenRouter integration for intelligent data extraction
- 🔄 Multiple scraping strategies (PDF, API, HTML)
- 📊 Comprehensive parsing of all interest rate categories
- 💾 Firestore caching with per-bank storage (24-hour duration)
- 🚀 Firebase Cloud Functions deployment
- 🧪 Local testing with Flask
- 🧱 Hardened service layer with dedicated unit tests
- 📱 iOS-ready JSON API
- 🔍 Query specific banks or get all at once

## Architecture

```
┌─────────────┐
│  iOS App    │
│ (Dreamflow) │
└──────┬──────┘
       │ ?bank=landsbankinn|arionbanki|islandsbanki
       ▼
┌─────────────────────────┐
│   Cloud Functions       │
│ - get_rates (all/single)│
│ - refresh_rates         │
└─────────┬───────────────┘
          │
    ┌─────┴──────┐
    ▼            ▼
┌─────────┐  ┌──────────────────┐
│Firestore│  │  Bank Scrapers   │
│ Cache   │  ├──────────────────┤
│(per-bank│  │ • Landsbankinn   │
│storage) │  │   (PDF)          │
└─────────┘  │ • Arion banki    │
             │   (API/PDF)      │
             │ • Íslandsbanki   │
             │   (HTML)         │
             └─────┬────────────┘
                   │
           ┌───────┴────────┐
           ▼                ▼
    ┌──────────┐    ┌──────────────┐
    │   PDFs   │    │Bank Websites │
    └──────────┘    └──────────────┘
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
   source venv/bin/activate
   ```
   On Windows run the appropriate activation command after creating the environment:
   ```cmd
   venv\Scripts\activate
   ```
   ```powershell
   .\venv\Scripts\Activate.ps1
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure OpenRouter AI (Recommended)**

   The API uses AI to intelligently extract and enhance bank data. To enable this feature:

   ```bash
   # Copy the example environment file
   cp .env.example .env
   ```
   ```cmd
   REM Windows Command Prompt equivalent
   copy .env.example .env
   ```
   ```powershell
   # Windows PowerShell equivalent
   Copy-Item .env.example .env
   ```

   Then edit `.env` and add your OpenRouter API key:
   ```bash
   OPENROUTER_API_KEY=sk-or-v1-your-actual-key-here
   ```

   Get a **free** API key at: https://openrouter.ai/keys

   > **Note:** The AI uses a free model by default (`openai/gpt-oss-20b:free`), so there's no cost!
   > Without the API key, the scraper will still work but may have incomplete data extraction.

   If you're deploying to Firebase Functions you can alternatively store the key with:

   ```bash
   firebase functions:config:set openrouter.key="sk-or-v1-your-actual-key-here"
   # or, preferred for long term support:
   firebase functions:secrets:set OPENROUTER_API_KEY
   ```

   The runtime will now discover the key from either environment variables, legacy
   `functions:config` values, or Firebase Secrets Manager.

5. **Run local test server**
   ```bash
   python local_test.py
   ```

   The server will start at `http://localhost:5000`

6. **Test the API**
   ```bash
   # Get rates (cached if available)
   curl http://localhost:5000/api/rates

   # Force refresh
   curl http://localhost:5000/api/rates/refresh

   # Health check
   curl http://localhost:5000/health
   ```

7. **Run automated checks**
   ```bash
   pytest
   ```

   The service layer is fully unit-tested; running the test suite before committing helps catch regressions early.

### Firebase Deployment

For a detailed step-by-step walkthrough (including setting Firebase environment variables and provisioning service accounts), see [docs/FIREBASE_SETUP.md](docs/FIREBASE_SETUP.md). The summary below highlights the key commands once your project is configured.

> **Heads up:** Legacy single-bank entry points have been removed. Deployments now rely solely on `functions/main.py`, which exposes the production-ready HTTP functions.

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

### GET /api/rates?bank=<bank_id>

Get interest rates for a specific bank.

**Parameters:**
- `bank`: Bank ID (`landsbankinn`, `arionbanki`, or `islandsbanki`)

**Example:**
```bash
curl "https://your-project.cloudfunctions.net/get_rates?bank=landsbankinn"
```

**Response:**
```json
{
  "bank_id": "landsbankinn",
  "bank_name": "Landsbankinn",
  "effective_date": "2025-10-24",
  "last_updated": "2025-11-05T10:30:00Z",
  "data": {
    "deposits": { ... },
    "mortgages": { ... },
    "vehicle_loans": { ... },
    "bonds_and_loans": { ... },
    "short_term_loans": { ... },
    "penalty_interest": 15.25
  },
  "source_url": "https://www.landsbankinn.is/.../vaxtatafla.pdf",
  "cached": true
}
```

### GET /api/rates

Get interest rates for **all banks**.

**Example:**
```bash
curl "https://your-project.cloudfunctions.net/get_rates"
```

**Response:**
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
    "arionbanki": {
      "bank_id": "arionbanki",
      "bank_name": "Arion banki",
      "effective_date": "2025-10-30",
      "data": { ... },
      "cached": true
    },
    "islandsbanki": {
      "bank_id": "islandsbanki",
      "bank_name": "Íslandsbanki",
      "effective_date": "2025-11-01",
      "data": { ... },
      "cached": false
    }
  },
  "available_banks": ["landsbankinn", "arionbanki", "islandsbanki"]
}
```

### GET /api/rates/refresh?bank=<bank_id>

Force refresh rates for a specific bank or all banks.

**Parameters:**
- `bank`: Optional bank ID. If omitted, refreshes all banks.

**Examples:**
```bash
# Refresh specific bank
curl "https://your-project.cloudfunctions.net/refresh_rates?bank=arionbanki"

# Refresh all banks
curl "https://your-project.cloudfunctions.net/refresh_rates"
```

**Response:** Same structure as GET /api/rates, with `"cached": false`

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
