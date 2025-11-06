"""
AI-powered data extraction and enhancement using OpenRouter API.
Uses free models to parse and structure bank interest rate data.
"""
import json
import logging
from typing import Dict, Any, Optional
from openai import OpenAI
from config import Config

logger = logging.getLogger(__name__)


class AIProcessor:
    """Process bank data using OpenRouter's free AI models."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize the AI processor.

        Args:
            api_key: OpenRouter API key (defaults to Config.OPENROUTER_API_KEY)
            model: Model to use (defaults to Config.OPENROUTER_MODEL)
        """
        self.api_key = api_key or Config.OPENROUTER_API_KEY
        self.model = model or Config.OPENROUTER_MODEL

        if not self.api_key:
            raise ValueError("OpenRouter API key not configured")

        self.client = OpenAI(
            base_url=Config.OPENROUTER_BASE_URL,
            api_key=self.api_key
        )

    def parse_bank_data(self, raw_text: str, bank_name: str, source_type: str = "pdf") -> Dict[str, Any]:
        """
        Parse raw text from bank sources using AI.

        Args:
            raw_text: Raw text extracted from PDF/HTML
            bank_name: Name of the bank
            source_type: Type of source ("pdf" or "html")

        Returns:
            Dictionary with structured interest rate data
        """
        try:
            prompt = self._create_parsing_prompt(raw_text, bank_name, source_type)

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at extracting structured financial data from Icelandic bank documents. Always respond with valid JSON only, no additional text."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,  # Low temperature for consistent extraction
                max_tokens=2000
            )

            result_text = response.choices[0].message.content.strip()

            # Extract JSON from response (in case model adds markdown formatting)
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()

            parsed_data = json.loads(result_text)
            logger.info(f"Successfully parsed {bank_name} data using AI")

            return parsed_data

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            logger.error(f"Response was: {result_text[:500]}")
            return self._get_empty_structure()
        except Exception as e:
            logger.error(f"AI parsing failed for {bank_name}: {e}")
            return self._get_empty_structure()

    def enhance_parsed_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhance already-parsed data by filling in gaps and normalizing values.

        Args:
            data: Partially parsed data structure

        Returns:
            Enhanced data with filled gaps and normalized values
        """
        # Count null/empty values
        null_count = self._count_nulls(data)

        if null_count == 0:
            return data  # Data is complete, no enhancement needed

        logger.info(f"Enhancing data with {null_count} null/empty values")
        return data  # For now, return as-is. Can be extended later.

    def _create_parsing_prompt(self, raw_text: str, bank_name: str, source_type: str) -> str:
        """Create a detailed prompt for the AI to parse bank data."""

        return f"""Extract interest rate data from this {source_type} text from {bank_name}.

RAW TEXT:
{raw_text[:4000]}

Return ONLY valid JSON in this exact structure (use null for missing values, NEVER leave fields empty):

{{
  "effective_date": "YYYY-MM-DD or null",
  "penalty_interest": float or null,
  "deposits": {{
    "veltureikningar": {{
      "almennir": float or null,
      "ungmenna": float or null
    }},
    "sparireikningar": {{
      "indexed": {{
        "regular": float or null,
        "children": float or null
      }},
      "unindexed": {{
        "regular": float or null,
        "children": float or null
      }},
      "ibudasparnadur": float or null,
      "other": {{}}
    }},
    "foreign_currency": {{}}
  }},
  "mortgages": {{
    "indexed": {{
      "variable_ibudalan_i": float or null,
      "variable_ibudalan_ii": float or null,
      "variable_ibudalan_iii": float or null,
      "fixed_3yr_ibudalan_i": float or null,
      "fixed_3yr_ibudalan_ii": float or null
    }},
    "unindexed": {{
      "variable_ibudalan_i": float or null,
      "variable_ibudalan_ii": float or null
    }}
  }},
  "vehicle_loans": {{
    "kjor_electric_50_under": float or null,
    "kjor_electric_50_60": float or null
  }},
  "overdrafts": {{
    "yfirdrattarlan_einstaklinga": float or null,
    "framfaerslulán": float or null
  }},
  "credit_cards": {{
    "greidsludreifing": float or null
  }}
}}

IMPORTANT:
- Extract interest rates as percentages (e.g., 8.6 for 8.6%)
- Use null for missing values, not 0
- Parse Icelandic dates to YYYY-MM-DD format
- Common Icelandic terms:
  * "vextir" = interest
  * "íbúðalán" = mortgage
  * "ökutækjalán" = vehicle loan
  * "yfirdráttur" = overdraft
  * "tryggð" or "verðtryggt" = indexed
  * "óverðtryggt" = unindexed
  * "bundnir" = fixed rate
  * "breytilegir" = variable rate
"""

    def _get_empty_structure(self) -> Dict[str, Any]:
        """Return empty data structure matching expected format."""
        return {
            "effective_date": None,
            "penalty_interest": None,
            "deposits": {
                "veltureikningar": {},
                "sparireikningar": {
                    "indexed": {},
                    "unindexed": {},
                    "other": {}
                },
                "foreign_currency": {}
            },
            "mortgages": {
                "indexed": {},
                "unindexed": {}
            },
            "vehicle_loans": {},
            "overdrafts": {},
            "credit_cards": {}
        }

    def _count_nulls(self, data: Any) -> int:
        """Recursively count null and empty values in data structure."""
        if data is None:
            return 1
        elif isinstance(data, dict):
            if not data:  # Empty dict
                return 1
            return sum(self._count_nulls(v) for v in data.values())
        elif isinstance(data, list):
            if not data:  # Empty list
                return 1
            return sum(self._count_nulls(item) for item in data)
        else:
            return 0


def test_ai_processor():
    """Test the AI processor with sample data."""
    if not Config.OPENROUTER_API_KEY:
        print("❌ OPENROUTER_API_KEY not set in environment")
        return

    processor = AIProcessor()

    sample_text = """
    Vaxtatafla fyrir einstaklinga
    Gildistími: 24. október 2025

    Veltureikningar
    Almennir veltureikningar: 0,10%

    Íbúðalán - Verðtryggt
    Íbúðalán I (breytilegir vextir): 8,60%
    Íbúðalán II (breytilegir vextir): 9,10%

    Dráttarvextir: 15,25%
    """

    print("Testing AI processor...")
    result = processor.parse_bank_data(sample_text, "Test Bank", "pdf")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    test_ai_processor()
