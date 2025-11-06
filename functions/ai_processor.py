"""AI-powered data extraction and enhancement using the OpenRouter API."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

from openai import OpenAI

from config import Config

logger = logging.getLogger(__name__)


class AIProcessor:
    """Process bank data using OpenRouter-hosted models."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None) -> None:
        self.api_key = api_key or Config.get_openrouter_api_key()
        self.model = model or Config.OPENROUTER_MODEL

        if not self.api_key:
            raise ValueError("OpenRouter API key not configured")

        self.client = OpenAI(base_url=Config.OPENROUTER_BASE_URL, api_key=self.api_key)

    def parse_bank_data(
        self,
        raw_text: str,
        bank_name: str,
        source_type: str = "pdf",
        bank_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Parse raw text from bank sources using OpenRouter."""

        if not raw_text.strip():
            logger.warning("Empty input text supplied to AI parser for %s", bank_name)
            return self._get_empty_structure(bank_name=bank_name, bank_id=bank_id)

        system_message = (
            "You convert Icelandic bank documents into machine readable data. "
            "Respond with JSON only, matching the provided schema."
        )

        prompt = self._create_parsing_prompt(raw_text, bank_name, source_type, bank_id)

        request_payload = dict(
            model=self.model,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=2000,
        )

        try:
            response = self.client.chat.completions.create(
                **request_payload,
                response_format={"type": "json_object"},
            )
        except Exception as exc:  # pragma: no cover - network failure fallback
            logger.warning("Falling back to free-form response for %s: %s", bank_name, exc)
            response = self.client.chat.completions.create(**request_payload)

        message = response.choices[0].message if response.choices else None
        result_text = (message.content or "").strip() if message else ""

        if not result_text:
            logger.error("AI response for %s was empty", bank_name)
            return self._get_empty_structure(bank_name=bank_name, bank_id=bank_id)

        result_text = self._extract_json_block(result_text)

        try:
            parsed_data = json.loads(result_text)
        except json.JSONDecodeError as exc:
            logger.error("Failed to parse AI response for %s: %s", bank_name, exc)
            logger.debug("Raw AI response: %s", result_text[:500])
            return self._get_empty_structure(bank_name=bank_name, bank_id=bank_id)

        if not isinstance(parsed_data, dict):
            logger.error("AI response for %s was not a JSON object", bank_name)
            return self._get_empty_structure(bank_name=bank_name, bank_id=bank_id)

        parsed_data.setdefault("bank_name", bank_name)
        if bank_id:
            parsed_data.setdefault("bank_id", bank_id)

        logger.info("Successfully parsed %s data using AI", bank_name)
        return parsed_data

    def enhance_parsed_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance already-parsed data by filling in gaps and normalising values."""

        if self._count_nulls(data) == 0:
            return data

        logger.info("Enhancement hook currently passes data through unchanged")
        return data

    @staticmethod
    def _extract_json_block(response_text: str) -> str:
        """Extract a JSON block from Markdown fenced code if necessary."""

        if "```json" in response_text:
            return response_text.split("```json", 1)[1].split("```", 1)[0].strip()
        if "```" in response_text:
            return response_text.split("```", 1)[1].split("```", 1)[0].strip()
        return response_text

    def _create_parsing_prompt(
        self, raw_text: str, bank_name: str, source_type: str, bank_id: Optional[str]
    ) -> str:
        """Create a detailed prompt for the AI to parse bank data."""

        template = json.dumps(
            self._get_empty_structure(bank_name=bank_name, bank_id=bank_id),
            ensure_ascii=False,
            indent=2,
        )

        identifier_note = f" (bank_id: {bank_id})" if bank_id else ""

        return (
            f"Extract interest rate data from this {source_type.upper()} text for {bank_name}{identifier_note}.\n"
            f"- Return ONLY JSON that matches the provided template.\n"
            f"- Use numeric percentages (e.g. 8.6 for 8.6%).\n"
            f"- For missing values use null.\n"
            f"- Convert Icelandic dates to YYYY-MM-DD.\n\n"
            f"TEMPLATE:\n{template}\n\n"
            f"RAW TEXT (trimmed to 4000 characters):\n{raw_text[:4000]}"
        )

    def _get_empty_structure(self, bank_name: Optional[str] = None, bank_id: Optional[str] = None) -> Dict[str, Any]:
        """Return empty data structure matching expected format."""

        return {
            "bank_name": bank_name,
            "bank_id": bank_id,
            "effective_date": None,
            "penalty_interest": None,
            "deposits": {
                "veltureikningar": {},
                "sparireikningar": {
                    "indexed": {},
                    "unindexed": {},
                    "other": {},
                },
                "foreign_currency": {},
            },
            "mortgages": {
                "indexed": {},
                "unindexed": {},
            },
            "vehicle_loans": {},
            "overdrafts": {},
            "credit_cards": {},
        }

    def _count_nulls(self, data: Any) -> int:
        """Recursively count null values in data structure (ignoring empty containers)."""
        if data is None:
            return 1
        if isinstance(data, dict):
            if not data:
                return 0
            return sum(self._count_nulls(value) for value in data.values())
        if isinstance(data, list):
            if not data:
                return 0
            return sum(self._count_nulls(item) for item in data)
        return 0


def test_ai_processor() -> None:
    """Manual smoke test for the AI processor."""
    if not Config.get_openrouter_api_key():
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
    result = processor.parse_bank_data(sample_text, "Test Bank", "pdf", bank_id="testbank")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    test_ai_processor()
