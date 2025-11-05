"""
Íslandsbanki interest rate scraper
"""
from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import requests
from bs4 import BeautifulSoup

from .base import BankScraper

logger = logging.getLogger(__name__)


class IslandsbankiScraper(BankScraper):
    """Scraper for Íslandsbanki interest rates."""

    BASE_URL = "https://www.islandsbanki.is/is/grein/vaxtatafla"

    def __init__(self) -> None:
        super().__init__()
        self.bank_name = "Íslandsbanki"
        self.bank_id = "islandsbanki"
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36"
                )
            }
        )
        # Avoid inheriting proxy settings from the environment. Some hosting
        # environments configure outbound proxies that the Íslandsbanki site
        # blocks, which previously produced 403/407 tunnel errors.
        self.session.trust_env = False

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------
    def normalize_key(self, text: str) -> str:
        """Normalise Icelandic account names to safe dictionary keys."""

        if not text:
            return ""

        replacements = str.maketrans(
            {
                " ": "_",
                "á": "a",
                "Á": "a",
                "é": "e",
                "É": "e",
                "í": "i",
                "Í": "i",
                "ó": "o",
                "Ó": "o",
                "ú": "u",
                "Ú": "u",
                "ý": "y",
                "Ý": "y",
                "ö": "o",
                "Ö": "o",
                "æ": "ae",
                "Æ": "ae",
                "ð": "d",
                "Ð": "d",
                "þ": "th",
                "Þ": "th",
            }
        )

        cleaned = text.translate(replacements)
        cleaned = cleaned.lower()
        cleaned = re.sub(r"[^a-z0-9_]", "", cleaned)
        cleaned = re.sub(r"_+", "_", cleaned).strip("_")
        return cleaned

    def parse_percentage(self, value: str) -> Optional[float]:
        """Parse a percentage string to a float."""

        try:
            value = value.replace("%", "").replace(",", ".").strip()
            if value:
                return float(value)
        except (ValueError, AttributeError):
            pass
        return None

    def get_table_heading(self, table) -> str:
        """Return the most relevant heading text for a table."""

        heading_text = ""
        heading_priority = [
            ["h2", "h3", "h4", "h5"],
            ["strong", "p", "span", "button"],
        ]

        for tags in heading_priority:
            heading = table.find_previous(tags)
            while heading:
                text = heading.get_text(separator=" ", strip=True)
                if text and 2 <= len(text) <= 150:
                    heading_text = text
                    break
                heading = heading.find_previous(tags)

            if heading_text:
                break

        return heading_text

    def extract_tables_by_keywords(
        self, soup: BeautifulSoup, keyword_map: Dict[str, List[List[str]]]
    ) -> Dict[str, List]:
        """Group tables by matching heading keyword combinations."""

        grouped: Dict[str, List] = {key: [] for key in keyword_map.keys()}

        for table in soup.find_all("table"):
            heading_text = self.get_table_heading(table)
            if not heading_text:
                continue

            heading_lower = heading_text.lower()

            for key, keyword_groups in keyword_map.items():
                matched = False
                for group in keyword_groups:
                    if all(re.search(pattern, heading_lower) for pattern in group):
                        grouped[key].append(table)
                        matched = True
                        break
                if matched:
                    break

        return grouped

    def merge_table_data(self, tables: List) -> Dict[str, float | List[float]]:
        """Combine parsed rows from multiple tables into a single mapping."""

        combined: Dict[str, float | List[float]] = {}
        for table in tables:
            parsed = self.parse_table_rows(table)
            for key, value in parsed.items():
                if key not in combined:
                    combined[key] = value
        return combined

    # ------------------------------------------------------------------
    # Parsing helpers
    # ------------------------------------------------------------------
    def parse_effective_date(self, soup) -> Optional[str]:
        """Parse effective date from the rendered HTML."""

        try:
            text = soup.get_text(separator=" ")

            months_icelandic = {
                "janúar": 1,
                "febrúar": 2,
                "mars": 3,
                "apríl": 4,
                "maí": 5,
                "júní": 6,
                "júlí": 7,
                "ágúst": 8,
                "september": 9,
                "október": 10,
                "nóvember": 11,
                "desember": 12,
            }

            pattern = r"(?:gildir|tekur\s+gildi)\s+(?:frá\s+)?(\d{1,2})\.\s*(\w+)\s+(\d{4})"
            match = re.search(pattern, text.lower())

            if match:
                day = int(match.group(1))
                month_name = match.group(2)
                year = int(match.group(3))

                month = months_icelandic.get(month_name)
                if month:
                    try:
                        date_value = datetime(year, month, day)
                        return date_value.strftime("%Y-%m-%d")
                    except ValueError:
                        pass

            fallback_pattern = r"(\d{1,2})\.\s*(\w+)\s+(\d{4})"
            match = re.search(fallback_pattern, text.lower())
            if match:
                day = int(match.group(1))
                month_name = match.group(2)
                year = int(match.group(3))

                month = months_icelandic.get(month_name)
                if month:
                    try:
                        date_value = datetime(year, month, day)
                        return date_value.strftime("%Y-%m-%d")
                    except ValueError:
                        pass

            return datetime.utcnow().strftime("%Y-%m-%d")
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning("Error parsing effective date: %s", exc)
            return None

    def parse_table_rows(self, table) -> Dict[str, float | List[float]]:
        """Parse rows from an interest rate table."""

        result: Dict[str, float | List[float]] = {}

        for row in table.find_all("tr"):
            cells = row.find_all(["td", "th"])
            if len(cells) < 2:
                continue

            account_name = cells[0].get_text().strip()
            if not account_name:
                continue

            rates: List[float] = []
            for cell in cells[1:]:
                rate_text = cell.get_text().strip()
                rate = self.parse_percentage(rate_text)
                if rate is not None:
                    rates.append(rate)

            if not rates:
                continue

            key = self.normalize_key(account_name)
            if not key:
                continue

            base_key = key
            index = 2
            while key in result:
                key = f"{base_key}_{index}"
                index += 1

            if len(rates) == 1:
                result[key] = rates[0]
            else:
                result[key] = rates

        return result

    def parse_deposits(self, soup: BeautifulSoup) -> Dict:
        """Parse deposit account rates."""

        deposits = {
            "veltureikningar": {},
            "sparireikningar": {
                "indexed": {},
                "unindexed": {},
                "other": {},
            },
            "foreign_currency": {},
        }

        keyword_map = {
            "veltureikningar": [[r"veltureik"]],
            "spar_indexed": [[r"sparireik", r"verðtrygg"]],
            "spar_unindexed": [[r"sparireik", r"óverðtrygg"]],
            "spar_general": [[r"sparireik"]],
            "foreign_currency": [[r"gjaldmiðl"], [r"gjaldeyr"]],
        }

        tables = self.extract_tables_by_keywords(soup, keyword_map)

        if tables.get("veltureikningar"):
            deposits["veltureikningar"] = self.merge_table_data(
                tables["veltureikningar"]
            )

        if tables.get("spar_indexed"):
            deposits["sparireikningar"]["indexed"] = self.merge_table_data(
                tables["spar_indexed"]
            )

        if tables.get("spar_unindexed"):
            deposits["sparireikningar"]["unindexed"] = self.merge_table_data(
                tables["spar_unindexed"]
            )

        if (
            tables.get("spar_general")
            and not deposits["sparireikningar"]["indexed"]
            and not deposits["sparireikningar"]["unindexed"]
        ):
            deposits["sparireikningar"]["other"] = self.merge_table_data(
                tables["spar_general"]
            )

        if tables.get("foreign_currency"):
            deposits["foreign_currency"] = self.merge_table_data(
                tables["foreign_currency"]
            )

        return deposits

    def parse_penalty_interest(self, soup: BeautifulSoup) -> Optional[float]:
        """Parse penalty interest (dráttarvextir)."""

        drattr_elem = soup.find(string=re.compile(r"Dráttarvextir", re.I))
        if drattr_elem:
            parent = drattr_elem.find_parent("tr")
            if parent:
                cells = parent.find_all(["td", "th"])
                for cell in reversed(cells):
                    rate = self.parse_percentage(cell.get_text())
                    if rate is not None:
                        return rate

        text = soup.get_text(separator=" ", strip=True)
        match = re.search(r"dráttarvextir[^0-9]*(\d+[.,]\d+)\s*%", text, re.I)
        if match:
            return self.parse_percentage(match.group(1))

        return None

    def parse_loans(self, soup: BeautifulSoup) -> Dict:
        """Parse loan rates (mortgages, overdrafts, etc.)."""

        loans = {
            "mortgages": {
                "indexed": {},
                "unindexed": {},
            },
            "overdrafts": {},
            "credit_cards": {},
            "vehicle_loans": {},
            "penalty_interest": None,
        }

        keyword_map = {
            "mortgages_indexed": [[r"íbúðalán", r"verðtrygg"], [r"verðtrygg", r"fasteignalán"]],
            "mortgages_unindexed": [
                [r"íbúðalán", r"óverðtrygg"],
                [r"óverðtrygg", r"fasteignalán"],
            ],
            "mortgages_generic": [[r"íbúðalán"]],
            "overdrafts": [[r"yfirdrátt"]],
            "credit_cards": [[r"kort"], [r"kredit"]],
            "vehicle_loans": [
                [r"ökutæki"],
                [r"bíla"],
                [r"bifreið"],
                [r"bílalán"],
                [r"bíla\s*fjár"],
            ],
        }

        tables = self.extract_tables_by_keywords(soup, keyword_map)

        if tables.get("mortgages_indexed"):
            for table in tables["mortgages_indexed"]:
                loans["mortgages"]["indexed"].update(self.parse_table_rows(table))

        if tables.get("mortgages_unindexed"):
            for table in tables["mortgages_unindexed"]:
                loans["mortgages"]["unindexed"].update(self.parse_table_rows(table))

        if not loans["mortgages"]["indexed"] and tables.get("mortgages_generic"):
            for table in tables["mortgages_generic"]:
                loans["mortgages"]["unindexed"].update(self.parse_table_rows(table))

        if tables.get("overdrafts"):
            loans["overdrafts"] = self.merge_table_data(tables["overdrafts"])

        if tables.get("credit_cards"):
            loans["credit_cards"] = self.merge_table_data(tables["credit_cards"])

        if tables.get("vehicle_loans"):
            loans["vehicle_loans"] = self.merge_table_data(tables["vehicle_loans"])

        loans["penalty_interest"] = self.parse_penalty_interest(soup)

        return loans

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def scrape_rates(self) -> Tuple[Optional[Dict], Optional[str]]:
        """Scrape interest rates from Íslandsbanki website."""

        try:
            logger.info("Fetching webpage: %s", self.BASE_URL)
            response = self.session.get(self.BASE_URL, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")

            deposits = self.parse_deposits(soup)
            loans = self.parse_loans(soup)

            rate_data = {
                "bank_name": self.bank_name,
                "effective_date": self.parse_effective_date(soup),
                "deposits": deposits,
                "mortgages": loans["mortgages"],
                "vehicle_loans": loans.get("vehicle_loans", {}),
                "overdrafts": loans["overdrafts"],
                "credit_cards": loans["credit_cards"],
                "penalty_interest": loans["penalty_interest"],
            }

            logger.info("Successfully scraped Íslandsbanki rates")
            return rate_data, self.BASE_URL

        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("Error scraping Íslandsbanki: %s", exc, exc_info=True)
            return None, None
