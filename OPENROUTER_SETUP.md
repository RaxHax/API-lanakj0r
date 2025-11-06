# OpenRouter AI Integration Setup

This guide explains how to configure OpenRouter AI integration to improve bank data extraction.

## What's New?

The API now uses **OpenRouter's free AI models** (specifically `openai/gpt-oss-20b:free`) to intelligently parse bank interest rate data when regex-based parsing fails or returns incomplete results.

### Features:
- ✅ Free AI model integration via OpenRouter
- ✅ Automatic fallback: Uses AI only when regex parsing has gaps
- ✅ Secure API key storage with environment variables
- ✅ Works with all three banks (Landsbankinn, Arion, Íslandsbanki)
- ✅ No changes to existing API endpoints

## Quick Start

### 1. Get Your Free OpenRouter API Key

1. Visit [OpenRouter](https://openrouter.ai/keys)
2. Sign up or log in
3. Create a new API key
4. Copy the key (starts with `sk-or-v1-...`)

### 2. Configure Environment Variables

Create a `.env` file in the project root:

```bash
# Copy the example file
cp .env.example .env

# Edit .env with your API key
nano .env
```

Add your OpenRouter API key:

```env
# OpenRouter API Configuration
OPENROUTER_API_KEY=sk-or-v1-your-actual-key-here

# Model Selection (free models available)
OPENROUTER_MODEL=openai/gpt-oss-20b:free

# Feature Flags
ENABLE_AI_PARSING=True
DEBUG=False

# Cache Settings
CACHE_DURATION_HOURS=24
```

### 3. Install Dependencies

```bash
cd functions
pip install -r requirements.txt
```

This installs:
- `openai>=1.12.0` - OpenRouter client library
- `python-dotenv>=1.0.0` - Environment variable loader

### 4. Test Locally

Run the local test server:

```bash
python local_test.py
```

Visit `http://localhost:8000` and test the bank scrapers.

### 5. Deploy to Firebase (Optional)

If you're using Firebase Functions, you can set a runtime configuration value:

```bash
firebase functions:config:set openrouter.key="sk-or-v1-your-actual-key-here"
firebase deploy --only functions
```

For long-term support (after the legacy config service is retired), migrate the key to
Firebase Secrets Manager:

```bash
firebase functions:secrets:set OPENROUTER_API_KEY
firebase deploy --only functions
```

## How It Works

### Intelligent Fallback System

1. **First**: Regex-based parsing extracts data from PDFs/HTML
2. **Check**: Count how many values are null/empty
3. **AI Enhancement**: If ≥5 null values, use OpenRouter to re-parse
4. **Merge**: Combine regex and AI results (prefer non-null values)
5. **Return**: Enhanced data with fewer missing values

### Example Flow:

```
Arion Bank PDF → Extract Text → Regex Parser
                                      ↓
                              [Result: 15 null values]
                                      ↓
                              OpenRouter AI Parser
                                      ↓
                              [Result: 3 null values]
                                      ↓
                              Merge & Return
```

## Available Free Models

You can change the model in `.env`:

```env
# Fast and free (recommended)
OPENROUTER_MODEL=openai/gpt-oss-20b:free

# Alternative free models
OPENROUTER_MODEL=meta-llama/llama-3.2-3b-instruct:free
OPENROUTER_MODEL=google/gemma-2-9b-it:free
```

See [OpenRouter's free models](https://openrouter.ai/docs#models) for more options.

## Configuration Options

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENROUTER_API_KEY` | None | Your OpenRouter API key (required) |
| `OPENROUTER_MODEL` | `openai/gpt-oss-20b:free` | Model to use for parsing |
| `ENABLE_AI_PARSING` | `True` | Enable/disable AI enhancement |
| `CACHE_DURATION_HOURS` | `24` | How long to cache results |
| `DEBUG` | `False` | Enable debug logging |

### Disabling AI Parsing

To disable AI and use only regex parsing:

```env
ENABLE_AI_PARSING=False
```

Or remove/don't set `OPENROUTER_API_KEY`.

## Testing AI Integration

Test the AI processor directly:

```bash
cd functions
python ai_processor.py
```

This runs a sample parsing test to verify your API key works.

## Troubleshooting

### "OpenRouter API key not configured"

- Check that `.env` exists in the project root
- Verify `OPENROUTER_API_KEY` is set correctly
- Make sure the key starts with `sk-or-v1-`

### AI parsing not working

- Check `ENABLE_AI_PARSING=True` in `.env`
- Verify the model name is correct
- Check API key has credits/is valid at [OpenRouter](https://openrouter.ai/credits)

### Import errors

```bash
pip install openai python-dotenv
```

### Firebase Functions errors

Set config explicitly:

```bash
firebase functions:config:set openrouter.key="your-key"
firebase functions:config:get  # Verify it's set
```

## Security Notes

- ✅ `.env` is in `.gitignore` - your key won't be committed
- ✅ Use `.env.example` as a template (no real keys)
- ✅ For production: Use Firebase Secret Manager or Google Cloud Secret Manager
- ⚠️ Never commit real API keys to git
- ⚠️ Don't share your `.env` file

## Cost & Limits

- The `openai/gpt-oss-20b:free` model is **completely free**
- Rate limits apply (check [OpenRouter pricing](https://openrouter.ai/docs#limits))
- Consider paid models for higher limits if needed

## Files Modified

- ✅ `functions/config.py` - Configuration management
- ✅ `functions/ai_processor.py` - OpenRouter integration
- ✅ `functions/banks/base.py` - AI enhancement methods
- ✅ `functions/banks/landsbankinn.py` - AI-enhanced scraper
- ✅ `functions/banks/arionbanki.py` - AI-enhanced scraper
- ✅ `functions/banks/islandsbanki.py` - AI-enhanced scraper
- ✅ `functions/requirements.txt` - Added dependencies

## Support

For issues or questions:
1. Check the logs for error messages
2. Verify your API key at [OpenRouter](https://openrouter.ai/keys)
3. Test with `python ai_processor.py` directly
4. Open an issue on GitHub if problems persist
