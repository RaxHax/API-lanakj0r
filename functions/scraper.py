"""
PDF scraper for Landsbankinn interest rates
"""
import requests
from bs4 import BeautifulSoup
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class LandsbankinScraper:
    """Scraper for Landsbankinn interest rate PDF"""

    BASE_URL = "https://www.landsbankinn.is/vextir-og-verdskra"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })

    def get_latest_pdf_url(self) -> Optional[str]:
        """
        Scrape the Landsbankinn website to find the latest PDF URL

        Returns:
            str: URL to the latest PDF, or None if not found
        """
        try:
            logger.info(f"Fetching webpage: {self.BASE_URL}")
            response = self.session.get(self.BASE_URL, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Look for PDF links on the page
            # Common patterns: links containing 'vaxta', 'pdf', etc.
            pdf_links = []

            for link in soup.find_all('a', href=True):
                href = link['href']
                if href.endswith('.pdf') and 'vaxta' in href.lower():
                    # Make absolute URL if relative
                    if href.startswith('http'):
                        pdf_links.append(href)
                    else:
                        pdf_links.append(f"https://www.landsbankinn.is{href}")

            if pdf_links:
                # Return the first matching PDF (usually the most recent)
                logger.info(f"Found PDF URL: {pdf_links[0]}")
                return pdf_links[0]

            logger.warning("No PDF link found on the page")
            return None

        except Exception as e:
            logger.error(f"Error scraping webpage: {e}")
            return None

    def download_pdf(self, pdf_url: str) -> Optional[bytes]:
        """
        Download PDF content from URL

        Args:
            pdf_url: URL to the PDF file

        Returns:
            bytes: PDF content, or None if download failed
        """
        try:
            logger.info(f"Downloading PDF from: {pdf_url}")
            response = self.session.get(pdf_url, timeout=30)
            response.raise_for_status()

            logger.info(f"Successfully downloaded PDF ({len(response.content)} bytes)")
            return response.content

        except Exception as e:
            logger.error(f"Error downloading PDF: {e}")
            return None

    def scrape_latest_pdf(self) -> Tuple[Optional[bytes], Optional[str]]:
        """
        Scrape and download the latest PDF

        Returns:
            Tuple[bytes, str]: (PDF content, PDF URL) or (None, None) if failed
        """
        pdf_url = self.get_latest_pdf_url()
        if not pdf_url:
            return None, None

        pdf_content = self.download_pdf(pdf_url)
        if not pdf_content:
            return None, None

        return pdf_content, pdf_url
