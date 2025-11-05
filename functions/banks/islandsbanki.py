"""
Íslandsbanki interest rate scraper
"""
import requests
import re
import logging
from bs4 import BeautifulSoup
from typing import Dict, Optional, Tuple
from datetime import datetime

from .base import BankScraper

logger = logging.getLogger(__name__)


class IslandsbankiScraper(BankScraper):
    """Scraper for Íslandsbanki interest rates"""

    BASE_URL = "https://www.islandsbanki.is/is/grein/vaxtatafla"

    def __init__(self):
        super().__init__()
        self.bank_name = "Íslandsbanki"
        self.bank_id = "islandsbanki"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })

    def parse_percentage(self, value: str) -> Optional[float]:
        """Parse percentage string to float"""
        try:
            value = value.replace('%', '').replace(',', '.').strip()
            if value:
                return float(value)
        except (ValueError, AttributeError):
            pass
        return None

    def parse_effective_date(self, soup) -> Optional[str]:
        """Parse effective date from HTML"""
        try:
            # Look for date patterns in the HTML
            text = soup.get_text()

            months_icelandic = {
                'janúar': 1, 'febrúar': 2, 'mars': 3, 'apríl': 4,
                'maí': 5, 'júní': 6, 'júlí': 7, 'ágúst': 8,
                'september': 9, 'október': 10, 'nóvember': 11, 'desember': 12
            }

            # Pattern: "gildir frá X. month YYYY" or similar
            pattern = r'gildir frá (\d{1,2})\.\s*(\w+)\s+(\d{4})'
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

            # If no match, use current date
            return datetime.utcnow().strftime('%Y-%m-%d')

        except Exception as e:
            logger.warning(f"Error parsing effective date: {e}")
            return None

    def parse_table_rows(self, table) -> Dict[str, Dict]:
        """Parse rows from an interest rate table"""
        result = {}

        rows = table.find_all('tr')
        for row in rows:
            cells = row.find_all(['td', 'th'])
            if len(cells) < 2:
                continue

            # Get the account name/description
            account_name = cells[0].get_text().strip()

            # Get interest rate(s)
            rates = []
            for cell in cells[1:]:
                rate_text = cell.get_text().strip()
                rate = self.parse_percentage(rate_text)
                if rate is not None:
                    rates.append(rate)

            if rates and account_name:
                # Clean up account name for use as key
                key = account_name.lower().replace(' ', '_').replace('í', 'i').replace('ú', 'u').replace('ö', 'o').replace('æ', 'ae').replace('ð', 'd').replace('þ', 'th')
                key = re.sub(r'[^a-z0-9_]', '', key)

                if len(rates) == 1:
                    result[key] = rates[0]
                else:
                    result[key] = rates

        return result

    def parse_deposits(self, soup) -> Dict:
        """Parse deposit account rates"""
        deposits = {
            "veltureikningar": {},
            "sparireikningar_indexed": {},
            "sparireikningar_unindexed": {},
            "foreign_currency": {}
        }

        # Find Veltureikningar section
        veltureikningar_heading = soup.find(string=re.compile(r'Veltureikningar', re.I))
        if veltureikningar_heading:
            table = veltureikningar_heading.find_parent().find_next('table')
            if table:
                deposits["veltureikningar"] = self.parse_table_rows(table)

        # Find Verðtryggðir sparireikningar
        indexed_heading = soup.find(string=re.compile(r'Verðtryggðir sparireikningar', re.I))
        if indexed_heading:
            table = indexed_heading.find_parent().find_next('table')
            if table:
                deposits["sparireikningar_indexed"] = self.parse_table_rows(table)

        # Find Óverðtryggðir sparireikningar
        unindexed_heading = soup.find(string=re.compile(r'Óverðtryggðir sparireikningar', re.I))
        if unindexed_heading:
            table = unindexed_heading.find_parent().find_next('table')
            if table:
                deposits["sparireikningar_unindexed"] = self.parse_table_rows(table)

        # Parse specific accounts with known structure
        # Ávöxtun
        avox_elem = soup.find(string=re.compile(r'Ávöxtun', re.I))
        if avox_elem:
            parent = avox_elem.find_parent('tr')
            if parent:
                cells = parent.find_all('td')
                if len(cells) >= 2:
                    deposits["sparireikningar_unindexed"]["avoxtun"] = self.parse_percentage(cells[1].get_text())

        # Heiðursmerki (tiered)
        heidursmerki = {}
        for tier_name in ['Grunnþrep', '1. þrep', '2. þrep']:
            elem = soup.find(string=re.compile(tier_name, re.I))
            if elem:
                parent = elem.find_parent('tr')
                if parent:
                    cells = parent.find_all('td')
                    if len(cells) >= 2:
                        key = tier_name.lower().replace('.', '').replace(' ', '_')
                        heidursmerki[key] = self.parse_percentage(cells[1].get_text())

        if heidursmerki:
            deposits["sparireikningar_unindexed"]["heidursmerki"] = heidursmerki

        # Vaxtaþrep (tiered)
        vaxtaprep = {}
        for i in range(6):
            if i == 0:
                tier_name = "Grunnþrep"
            else:
                tier_name = f"{i}. þrep"

            elem = soup.find(string=re.compile(tier_name, re.I))
            if elem and 'Vaxtaþrep' in elem.find_parent('table').get_text():
                parent = elem.find_parent('tr')
                if parent:
                    cells = parent.find_all('td')
                    if len(cells) >= 2:
                        key = f"tier_{i}"
                        vaxtaprep[key] = self.parse_percentage(cells[1].get_text())

        if vaxtaprep:
            deposits["sparireikningar_unindexed"]["vaxtaprep"] = vaxtaprep

        return deposits

    def parse_loans(self, soup) -> Dict:
        """Parse loan rates (mortgages, vehicle loans, etc.)"""
        loans = {
            "mortgages": {
                "indexed": {},
                "unindexed": {}
            },
            "overdrafts": {},
            "credit_cards": {},
            "penalty_interest": None
        }

        # Look for all tables in the loans section
        # The website structure may have dropdowns, so we need to find all content

        # Overdrafts
        yfirdr_elem = soup.find(string=re.compile(r'Yfirdráttarlán', re.I))
        if yfirdr_elem:
            # Try to find rate in the same or next element
            parent = yfirdr_elem.find_parent('tr')
            if parent:
                cells = parent.find_all('td')
                if len(cells) >= 2:
                    loans["overdrafts"]["einstaklingar"] = self.parse_percentage(cells[-1].get_text())

        # Penalty interest
        drattr_elem = soup.find(string=re.compile(r'Dráttarvextir', re.I))
        if drattr_elem:
            parent = drattr_elem.find_parent('tr')
            if parent:
                cells = parent.find_all('td')
                if len(cells) >= 2:
                    loans["penalty_interest"] = self.parse_percentage(cells[-1].get_text())

        # Parse mortgage tables
        # Look for Íbúðalán section
        ibudalán_heading = soup.find(string=re.compile(r'Íbúðalán', re.I))
        if ibudalán_heading:
            # Find tables near this heading
            section = ibudalán_heading.find_parent()
            if section:
                tables = section.find_all_next('table', limit=5)
                for table in tables:
                    table_text = table.get_text()

                    # Check if this is indexed or unindexed
                    if 'verðtrygg' in table_text.lower():
                        # This is an indexed mortgage table
                        loans["mortgages"]["indexed"].update(self.parse_table_rows(table))
                    elif 'óverðtrygg' in table_text.lower():
                        # This is an unindexed mortgage table
                        loans["mortgages"]["unindexed"].update(self.parse_table_rows(table))

        return loans

    def scrape_rates(self) -> Tuple[Optional[Dict], Optional[str]]:
        """
        Scrape interest rates from Íslandsbanki website

        Returns:
            Tuple[Dict, str]: (rate_data, source_url) or (None, None)
        """
        try:
            logger.info(f"Fetching webpage: {self.BASE_URL}")
            response = self.session.get(self.BASE_URL, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Parse deposits
            deposits = self.parse_deposits(soup)

            # Parse loans
            loans = self.parse_loans(soup)

            # Combine all data
            rate_data = {
                "effective_date": self.parse_effective_date(soup),
                "deposits": deposits,
                "mortgages": loans["mortgages"],
                "overdrafts": loans["overdrafts"],
                "credit_cards": loans["credit_cards"],
                "penalty_interest": loans["penalty_interest"]
            }

            logger.info("Successfully scraped Íslandsbanki rates")
            return rate_data, self.BASE_URL

        except Exception as e:
            logger.error(f"Error scraping Íslandsbanki: {e}", exc_info=True)
            return None, None
