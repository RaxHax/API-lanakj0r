# Quick Start Guide

Get your Landsbankinn Interest Rate API running in 5 minutes!

## Option 1: Local Testing (Fastest)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the server
python local_test.py

# 3. Test it
curl http://localhost:5000/api/rates
```

That's it! The API will scrape and return the latest rates.

## Option 2: Firebase Deployment

### Prerequisites
- Firebase account (free tier works)
- Firebase CLI installed: `npm install -g firebase-tools`

### Steps

```bash
# 1. Login to Firebase
firebase login

# 2. Create/select a Firebase project in the console
# https://console.firebase.google.com/

# 3. Configure your project
cp .firebaserc.template .firebaserc
# Edit .firebaserc and add your project ID

# 4. Deploy
firebase deploy --only functions

# 5. Get your function URLs
firebase functions:list
```

Your API is now live at:
```
https://us-central1-YOUR-PROJECT.cloudfunctions.net/get_rates
```

## Testing Your Deployed API

```bash
# Get rates (cached)
curl https://us-central1-YOUR-PROJECT.cloudfunctions.net/get_rates

# Force refresh
curl https://us-central1-YOUR-PROJECT.cloudfunctions.net/refresh_rates
```

## Using in iOS (Dreamflow)

1. In Dreamflow, add an **API Call** component
2. Set the URL to your Cloud Function endpoint
3. Method: GET
4. Parse the JSON response

### Example Response Structure

```json
{
  "effective_date": "2025-10-24",
  "last_updated": "2025-11-05T10:30:00Z",
  "data": {
    "deposits": {
      "veltureikningar": {
        "almennir_veltureikningar": 0.75,
        "einkareikningar": 0.75
      },
      "sparireikningar": {
        "vaxtareikningur_30": {
          "tier_0_1m": 6.50,
          "tier_1m_5m": 6.70,
          "tier_5m_20m": 6.90
        }
      }
    },
    "mortgages": {
      "unindexed": {
        "fixed_rates": {
          "up_to_55_ltv": {
            "1_year": 8.60,
            "3_year": 8.40,
            "5_year": 8.15
          }
        }
      }
    }
  },
  "cached": true
}
```

## Common Issues

### "Failed to scrape PDF"
- Check your internet connection
- The Landsbankinn website might be down
- Try the `/refresh` endpoint

### "Module not found" errors
```bash
pip install -r requirements.txt
```

### Firebase deployment fails
```bash
# Make sure you're logged in
firebase login

# Check your project ID
firebase projects:list
```

## Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Customize the cache duration in `functions/firestore_manager.py`
- Add your own rate calculations or filtering
- Set up automated testing

## Need Help?

- Check the [troubleshooting section](README.md#troubleshooting) in the README
- Open an issue on GitHub
- Review Firebase Cloud Functions docs

---

Happy coding! 🚀
