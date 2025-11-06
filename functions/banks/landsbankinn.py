"""
Landsbankinn interest rate scraper
"""
import requests
import re
import logging
import io
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


class LandsbankinScraper(BankScraper):
    """Scraper for Landsbankinn interest rates"""

    BASE_URL = "https://www.landsbankinn.is/vextir-og-verdskra"

    def __init__(self):
        super().__init__()
        self.bank_name = "Landsbankinn"
        self.bank_id = "landsbankinn"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })

    def get_pdf_url(self) -> Optional[str]:
        """Find the latest PDF URL on the Landsbankinn website"""
        try:
            logger.info(f"Fetching webpage: {self.BASE_URL}")
            response = self.session.get(self.BASE_URL, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Look for PDF links
            for link in soup.find_all('a', href=True):
                href = link['href']
                if href.endswith('.pdf') and 'vaxta' in href.lower():
                    if href.startswith('http'):
                        return href
                    else:
                        return f"https://www.landsbankinn.is{href}"

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
        """Parse effective date from PDF text"""
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

    def parse_rates(self, text: str) -> Dict:
        """Parse all rates from PDF text"""
        # Import the full parser
        from ..parser import InterestRateParser

        parser = InterestRateParser()
        parser.raw_text = text

        return {
            "bank_name": self.bank_name,
            "effective_date": self.parse_effective_date(text),
            "deposits": parser.parse_deposit_accounts(text),
            "mortgages": parser.parse_mortgage_loans(text),
            "vehicle_loans": parser.parse_vehicle_loans(text),
            "bonds_and_loans": parser.parse_bonds_and_loan_agreements(text),
            "short_term_loans": parser.parse_short_term_loans(text),
            "penalty_interest": parser.parse_penalty_interest(text)
        }

    def scrape_rates(self) -> Tuple[Optional[Dict], Optional[str]]:
        """
        Scrape interest rates from Landsbankinn

        Returns:
            Tuple[Dict, str]: (rate_data, source_url) or (None, None)
        """
        # Get PDF URL
        pdf_url = self.get_pdf_url()
        if not pdf_url:
            return None, None

        # Download PDF
        pdf_content = self.download_pdf(pdf_url)
        if not pdf_content:
            return None, None

        # Extract text
        text = self.extract_text_from_pdf(pdf_content)
        if not text:
            return None, None

        # Parse rates with regex
        rate_data = self.parse_rates(text)

        # Enhance with AI if needed
        rate_data = self.enhance_with_ai(text, rate_data, source_type="pdf")

        return rate_data, pdf_url
