"""
Arion Bank interest rate scraper
"""
import requests
import re
import logging
import io
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from typing import Dict, Optional, Tuple
from datetime import datetime

try:
    from pdfminer.high_level import extract_text
    from pdfminer.layout import LAParams
except ImportError:
    pass

from .base import BankScraper

logger = logging.getLogger(__name__)


class ArionBankiScraper(BankScraper):
    """Scraper for Arion Bank interest rates"""

    BASE_URL = "https://www.arionbanki.is/bankinn/fleira/vextir-og-verdskra/"
    API_URL = "https://www.arionbanki.is/api/interest-rates"  # Try their open API

    def __init__(self):
        super().__init__()
        self.bank_name = "Arion banki"
        self.bank_id = "arionbanki"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        # Ensure we do not inherit proxy settings from the environment which can
        # cause connectivity issues in serverless environments
        self.session.trust_env = False

    def try_api(self) -> Tuple[Optional[Dict], Optional[str]]:
        """Try to get rates from Arion Bank's open API"""
        try:
            logger.info("Attempting to use Arion Bank API")
            response = self.session.get(self.API_URL, timeout=30)

            if response.status_code == 200:
                data = response.json()
                logger.info("Successfully got data from Arion Bank API")
                return data, self.API_URL

            logger.warning(f"API returned status {response.status_code}")
            return None, None

        except Exception as e:
            logger.info(f"API not available, will try PDF: {e}")
            return None, None

    def _make_absolute_url(self, url: str) -> str:
        """Create an absolute URL for the Arion Bank website."""
        if not url:
            return ""

        url = url.strip()
        if url.startswith("http"):
            return url

        return urljoin(self.BASE_URL, url)

    def _find_pdf_in_detail_page(self, page_url: str) -> Optional[str]:
        """Follow an intermediate page to look for the actual PDF link."""
        try:
            logger.info(f"Fetching detail page for PDF discovery: {page_url}")
            response = self.session.get(page_url, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            for element in soup.find_all(['a', 'button']):
                candidate_urls = [
                    element.get('href'),
                    element.get('data-file'),
                    element.get('data-file-url'),
                    element.get('data-url'),
                ]

                for candidate in candidate_urls:
                    if not candidate:
                        continue
                    absolute = self._make_absolute_url(candidate)
                    if absolute.lower().endswith('.pdf'):
                        logger.info(f"Found PDF link on detail page: {absolute}")
                        return absolute

            logger.warning("No PDF link found on detail page")
            return None

        except Exception as e:
            logger.error(f"Error fetching PDF detail page: {e}")
            return None

    def get_pdf_url(self) -> Optional[str]:
        """Find the latest individual rates PDF URL."""
        try:
            logger.info(f"Fetching webpage: {self.BASE_URL}")
            response = self.session.get(self.BASE_URL, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Look for "Vaxtatafla einstaklinga" PDF link or intermediate page
            for element in soup.find_all(['a', 'button']):
                text = element.get_text(separator=' ', strip=True).lower()
                if 'vaxtatafla' not in text or 'einstaklinga' not in text:
                    continue

                candidate_urls = [
                    element.get('href'),
                    element.get('data-file'),
                    element.get('data-file-url'),
                    element.get('data-url'),
                ]

                for candidate in candidate_urls:
                    if not candidate or candidate.lower().startswith('javascript'):
                        continue

                    absolute = self._make_absolute_url(candidate)

                    if absolute.lower().endswith('.pdf'):
                        logger.info(f"Found direct PDF link: {absolute}")
                        return absolute

                    # Some links lead to an intermediate page where the PDF is located
                    pdf_from_detail = self._find_pdf_in_detail_page(absolute)
                    if pdf_from_detail:
                        return pdf_from_detail

            logger.warning("No PDF link found")
            return None

        except Exception as e:
            logger.error(f"Error getting PDF URL: {e}")
            return None

    def download_pdf(self, url: str) -> Optional[bytes]:
        """Download PDF content"""
        try:
            logger.info(f"Downloading PDF from: {url}")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.content
        except Exception as e:
            logger.error(f"Error downloading PDF: {e}")
            return None

    def extract_text_from_pdf(self, pdf_content: bytes) -> str:
        """Extract text from PDF"""
        try:
            pdf_file = io.BytesIO(pdf_content)
            laparams = LAParams()
            return extract_text(pdf_file, laparams=laparams)
        except Exception as e:
            logger.error(f"Error extracting text: {e}")
            return ""

    def parse_effective_date(self, text: str) -> Optional[str]:
        """Parse effective date from PDF text or data"""
        if isinstance(text, dict):
            # If it's JSON data from API
            return text.get('effective_date')

        # Parse from text
        months_icelandic = {
            'janúar': 1, 'febrúar': 2, 'mars': 3, 'apríl': 4,
            'maí': 5, 'júní': 6, 'júlí': 7, 'ágúst': 8,
            'september': 9, 'október': 10, 'nóvember': 11, 'desember': 12
        }

        pattern = r'(\d{1,2})\.\s*(\w+)\s+(\d{4})'
        match = re.search(pattern, text.lower())

        if match:
            day = int(match.group(1))
            month_name = match.group(2)
            year = int(match.group(3))

            month = months_icelandic.get(month_name)
            if month:
                try:
                    date = datetime(year, month, day)
                    return date.strftime('%Y-%m-%d')
                except ValueError:
                    pass

        return None

    def parse_rate(self, text: str, pattern: str) -> Optional[float]:
        """Helper to extract a single rate"""
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                value = match.group(1).replace(',', '.').replace('%', '').strip()
                return float(value)
            except (ValueError, IndexError):
                pass
        return None

    def parse_rates_from_pdf(self, text: str) -> Dict:
        """Parse rates from PDF text"""
        rates = {
            "deposits": {
                "veltureikningar": {},
                "sparireikningar": {},
                "foreign_currency": {}
            },
            "mortgages": {
                "indexed": {},
                "unindexed": {}
            },
            "vehicle_loans": {},
            "overdrafts": {},
            "credit_cards": {},
            "penalty_interest": None
        }

        # Parse deposit accounts
        rates["deposits"]["veltureikningar"]["almennir"] = self.parse_rate(text, r"Veltureikningur.*?(\d+[,\.]\d+)%")

        # Fríðindareikningur (tiered)
        fridindar = {}
        tier_patterns = [
            (r"1\. þrep.*?0-1 millj.*?(\d+[,\.]\d+)%", "tier_0_1m"),
            (r"2\. þrep.*?1-5 millj.*?(\d+[,\.]\d+)%", "tier_1m_5m"),
            (r"3\. þrep.*?5-20 millj.*?(\d+[,\.]\d+)%", "tier_5m_20m"),
            (r"4\. þrep.*?20-100 millj.*?(\d+[,\.]\d+)%", "tier_20m_100m"),
            (r"5\. þrep.*?yfir 100 millj.*?(\d+[,\.]\d+)%", "tier_100m_plus"),
        ]

        for pattern, key in tier_patterns:
            rate = self.parse_rate(text, pattern)
            if rate:
                fridindar[key] = rate

        if fridindar:
            rates["deposits"]["sparireikningar"]["fridindarreikningur"] = fridindar

        # Vöxtur accounts
        voxtur_30 = {}
        voxtur_patterns = [
            (r"Vöxtur 30.*?0-5 millj.*?(\d+[,\.]\d+)%", "tier_0_5m"),
            (r"Vöxtur 30.*?5-20 millj.*?(\d+[,\.]\d+)%", "tier_5m_20m"),
            (r"Vöxtur 30.*?20-50 millj.*?(\d+[,\.]\d+)%", "tier_20m_50m"),
            (r"Vöxtur 30.*?>50 millj.*?(\d+[,\.]\d+)%", "tier_50m_plus"),
        ]

        for pattern, key in voxtur_patterns:
            rate = self.parse_rate(text, pattern)
            if rate:
                voxtur_30[key] = rate

        if voxtur_30:
            rates["deposits"]["sparireikningar"]["voxtur_30"] = voxtur_30

        # Íbúðasparnaður
        rates["deposits"]["sparireikningar"]["ibudasparnadur"] = self.parse_rate(text, r"Íbúðasparnaður.*?(\d+[,\.]\d+)%")

        # Mortgage loans
        # Indexed mortgages
        rates["mortgages"]["indexed"]["variable_ibudalan_i"] = self.parse_rate(text, r"Verðtryggð íbúðalán.*?Breytilegir vextir.*?Íbúðalán I.*?(\d+[,\.]\d+)%")
        rates["mortgages"]["indexed"]["variable_ibudalan_ii"] = self.parse_rate(text, r"Íbúðalán II.*?(\d+[,\.]\d+)%")
        rates["mortgages"]["indexed"]["variable_ibudalan_iii"] = self.parse_rate(text, r"Íbúðalán III.*?(\d+[,\.]\d+)%")

        # Fixed 3 years
        rates["mortgages"]["indexed"]["fixed_3yr_ibudalan_i"] = self.parse_rate(text, r"Fastir vextir í 3 ár.*?Íbúðalán I.*?(\d+[,\.]\d+)%")
        rates["mortgages"]["indexed"]["fixed_3yr_ibudalan_ii"] = self.parse_rate(text, r"Fastir vextir í 3 ár.*?Íbúðalán II.*?(\d+[,\.]\d+)%")

        # Unindexed mortgages
        rates["mortgages"]["unindexed"]["variable_ibudalan_i"] = self.parse_rate(text, r"Óverðtryggð íbúðalán.*?Breytilegir vextir.*?Íbúðalán I.*?(\d+[,\.]\d+)%")
        rates["mortgages"]["unindexed"]["variable_ibudalan_ii"] = self.parse_rate(text, r"Óverðtryggð.*?Íbúðalán II.*?(\d+[,\.]\d+)%")

        # Vehicle loans
        rates["vehicle_loans"]["kjor_electric_50_under"] = self.parse_rate(text, r"Rafmagn.*?50%.*?(\d+[,\.]\d+)%")
        rates["vehicle_loans"]["kjor_electric_50_60"] = self.parse_rate(text, r"Rafmagn.*?50%.*?-.*?60%.*?(\d+[,\.]\d+)%")

        # Overdrafts
        rates["overdrafts"]["yfirdrattarlan_einstaklinga"] = self.parse_rate(text, r"Yfirdráttarlán einstaklinga.*?(\d+[,\.]\d+)%")
        rates["overdrafts"]["framfaerslulán"] = self.parse_rate(text, r"Framfærslulán.*?Menntasjóðs.*?(\d+[,\.]\d+)%")

        # Credit cards
        rates["credit_cards"]["greidsludreifing"] = self.parse_rate(text, r"Greiðsludreifing.*?kreditkorta.*?(\d+[,\.]\d+)%")

        # Penalty interest
        rates["penalty_interest"] = self.parse_rate(text, r"Dráttarvextir.*?(\d+[,\.]\d+)%")

        return rates

    def scrape_rates(self) -> Tuple[Optional[Dict], Optional[str]]:
        """
        Scrape interest rates from Arion Bank

        Returns:
            Tuple[Dict, str]: (rate_data, source_url) or (None, None)
        """
        # Try API first
        api_data, api_url = self.try_api()
        if api_data:
            return api_data, api_url

        # Fall back to PDF
        logger.info("Falling back to PDF scraping")

        pdf_url = self.get_pdf_url()
        if not pdf_url:
            return None, None

        pdf_content = self.download_pdf(pdf_url)
        if not pdf_content:
            return None, None

        text = self.extract_text_from_pdf(pdf_content)
        if not text:
            return None, None

        rate_data = self.parse_rates_from_pdf(text)
        rate_data["effective_date"] = self.parse_effective_date(text)

        return rate_data, pdf_url
