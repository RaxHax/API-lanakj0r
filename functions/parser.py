"""
PDF parser for Landsbankinn interest rate data
"""
import re
from datetime import datetime
from typing import Dict, Optional, List
import logging
import io
try:
    from pdfminer.high_level import extract_text
    from pdfminer.layout import LAParams
except ImportError:
    # Fallback for different environments
    pass

logger = logging.getLogger(__name__)


class InterestRateParser:
    """Parser for Landsbankinn interest rate PDF"""

    def __init__(self):
        self.effective_date = None
        self.raw_text = ""

    def extract_text_from_pdf(self, pdf_content: bytes) -> str:
        """
        Extract text from PDF using pdfminer

        Args:
            pdf_content: PDF file content as bytes

        Returns:
            str: Extracted text
        """
        try:
            pdf_file = io.BytesIO(pdf_content)
            laparams = LAParams()
            text = extract_text(pdf_file, laparams=laparams)
            logger.info(f"Extracted {len(text)} characters from PDF")
            return text
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {e}")
            return ""

    def parse_effective_date(self, text: str) -> Optional[str]:
        """
        Extract the effective date from the PDF text

        Args:
            text: PDF text content

        Returns:
            str: Effective date in ISO format (YYYY-MM-DD) or None
        """
        # Pattern: "24. október 2025" or similar
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
                    logger.warning(f"Invalid date: {day}/{month}/{year}")

        return None

    def parse_percentage(self, value: str) -> Optional[float]:
        """
        Parse a percentage string to float

        Args:
            value: String like "8,60%" or "8.60%"

        Returns:
            float: Percentage as decimal (e.g., 8.60) or None
        """
        try:
            # Remove % sign and whitespace
            value = value.replace('%', '').strip()
            # Replace comma with period for Icelandic format
            value = value.replace(',', '.')
            # Handle asterisk or other markers
            value = value.replace('*', '').strip()
            if value:
                return float(value)
        except (ValueError, AttributeError):
            pass
        return None

    def parse_deposit_accounts(self, text: str) -> Dict:
        """Parse deposit account rates (Veltureikningar and Sparireikningar)"""
        deposits = {
            "veltureikningar": {},
            "sparireikningar": {},
            "foreign_currency": {}
        }

        # Parse Veltureikningar (Current accounts)
        deposits["veltureikningar"]["almennir_veltureikningar"] = self._extract_rate(text, r"Almennir veltureikningar fyrirtækja\s+([\d,]+)%")
        deposits["veltureikningar"]["einkareikningar"] = self._extract_rate(text, r"Einkareikningar\s+([\d,]+)%")
        deposits["veltureikningar"]["namu_klassareikningar"] = self._extract_rate(text, r"Námu- og Klassareikningar\s+([\d,]+)%")

        # Vörðureikningar tiers
        deposits["veltureikningar"]["vordureikningar"] = {
            "tier_1": self._extract_rate(text, r"1\. þrep 0-250\.000 kr\.\s+([\d,]+)%"),
            "tier_2": self._extract_rate(text, r"2\. þrep fá 250\.000 kr\.\s+([\d,]+)%")
        }

        # Parse Sparireikningar (Savings accounts)
        # Kjörbók
        deposits["sparireikningar"]["kjorbok"] = self._extract_rate(text, r"Kjörbók.*?\n.*?([\d,]+)%")

        # Markmið - Sparað í appi
        markmi_rates = self._extract_multiple_rates(text, r"Markmið - Sparað í appi.*?\n.*?([\d,]+)%\s+([\d,]+)%")
        if markmi_rates and len(markmi_rates) >= 2:
            deposits["sparireikningar"]["markmi_app"] = {
                "unindexed": markmi_rates[0],
                "indexed": markmi_rates[1]
            }

        # Vaxtareikningur (tiered)
        deposits["sparireikningar"]["vaxtareikningur"] = self._parse_tiered_accounts(text, "Vaxtareikningur/Vaxtareikningur Sjálfbær")
        deposits["sparireikningar"]["vaxtareikningur_vardan_60"] = self._parse_tiered_accounts(text, "Vaxtareikningur Varðan 60")
        deposits["sparireikningar"]["vaxtareikningur_30"] = self._parse_tiered_accounts(text, "Vaxtareikningur 30")

        # Fastvaxtareikningar (Fixed rate accounts)
        deposits["sparireikningar"]["fastvaxtareikningar"] = {
            "3_months": self._extract_rate(text, r"Fastvaxtareikningur - 3ja mánaða binding\s+([\d,]+)%"),
            "6_months": self._extract_rate(text, r"Fastvaxtareikningur - 6 mánaða binding\s+([\d,]+)%"),
            "12_months": self._extract_rate(text, r"Fastvaxtareikningur - 12 mánaða binding\s+([\d,]+)%"),
            "24_months": self._extract_rate(text, r"Fastvaxtareikningur - 24 mánaða binding\s+([\d,]+)%")
        }

        # Other savings accounts
        deposits["sparireikningar"]["sparireikningur_3"] = self._extract_rate(text, r"Sparireikningur 3, 3ja mánaða binding\s+([\d,]+)%")
        deposits["sparireikningar"]["sparireikningur_12"] = self._extract_rate(text, r"Sparireikningur 12, 12 mánaða binding\s+([\d,]+)%")
        deposits["sparireikningar"]["sparireikningur_24"] = self._extract_rate(text, r"Sparireikningur 24, 24 mánaða binding\s+([\d,]+)%")
        deposits["sparireikningar"]["landsbok"] = self._extract_rate(text, r"Landsbók.*?11 mánaða binding.*?\n.*?([\d,]+)%")
        deposits["sparireikningar"]["orlofsreikningar"] = self._extract_rate(text, r"Orlofsreikningar.*?\n.*?([\d,]+)%")

        # Special accounts with indexed/unindexed options
        deposits["sparireikningar"]["framti_argrunnur"] = self._extract_two_column_rates(text, "Framtíðargrunnur")
        deposits["sparireikningar"]["fasteignagrunnur"] = self._extract_two_column_rates(text, "Fasteignagrunnur")
        deposits["sparireikningar"]["lifeyrisbok"] = self._extract_two_column_rates(text, "Lífeyrisbók")

        # Foreign currency accounts
        currencies = ['USD', 'GBP', 'CAD', 'DKK', 'NOK', 'SEK', 'CHF', 'JPY', 'EUR', 'PLN']
        for currency in currencies:
            rates = self._extract_multiple_rates(text, rf"Innstæður í {currency}\s+([\d,]+)%\s+([\d,]+)%\s+([\d,]+)%")
            if rates and len(rates) >= 3:
                deposits["foreign_currency"][currency] = {
                    "unbound": rates[0],
                    "3_months": rates[1],
                    "6_months": rates[2]
                }

        return deposits

    def parse_mortgage_loans(self, text: str) -> Dict:
        """Parse mortgage loan rates (Íbúðalán)"""
        mortgages = {
            "unindexed": {
                "fixed_rates": {},
                "variable_rates": {},
                "old_loans": {}
            },
            "indexed": {
                "fixed_rates": {},
                "old_loans": {}
            }
        }

        # Unindexed mortgages - fixed rates
        # Up to 55% LTV
        rates_55 = self._extract_multiple_rates(text, r"Íbúðalán, allt að 55% veðsetning\s+([\d,]+)%\s+([\d,]+)%\s+([\d,]+)%")
        if rates_55 and len(rates_55) >= 3:
            mortgages["unindexed"]["fixed_rates"]["up_to_55_ltv"] = {
                "1_year": rates_55[0],
                "3_year": rates_55[1],
                "5_year": rates_55[2]
            }

        # Up to 65% LTV
        rates_65 = self._extract_multiple_rates(text, r"Íbúðalán, allt að 65% veðsetning\s+([\d,]+)%\s+([\d,]+)%\s+([\d,]+)%")
        if rates_65 and len(rates_65) >= 3:
            mortgages["unindexed"]["fixed_rates"]["up_to_65_ltv"] = {
                "1_year": rates_65[0],
                "3_year": rates_65[1],
                "5_year": rates_65[2]
            }

        # Up to 75% LTV
        rates_75 = self._extract_multiple_rates(text, r"Íbúðalán, allt að 75% veðsetning\s+([\d,]+)%\s+([\d,]+)%\s+([\d,]+)%")
        if rates_75 and len(rates_75) >= 3:
            mortgages["unindexed"]["fixed_rates"]["up_to_75_ltv"] = {
                "1_year": rates_75[0],
                "3_year": rates_75[1],
                "5_year": rates_75[2]
            }

        # Up to 80/85% LTV
        rates_80 = self._extract_multiple_rates(text, r"Íbúðalán, allt að 80/85% veðsetning.*?\s+([\d,]+)%\s+([\d,]+)%\s+([\d,]+)%")
        if rates_80 and len(rates_80) >= 3:
            mortgages["unindexed"]["fixed_rates"]["up_to_80_85_ltv"] = {
                "1_year": rates_80[0],
                "3_year": rates_80[1],
                "5_year": rates_80[2]
            }

        # Variable rate mortgages
        var_rates = self._extract_multiple_rates(text, r"Íbúðalán, allt að 85% veðsetning.*?Breytilegir.*?\s+([\d,]+)%\s+([\d,]+)%")
        if var_rates and len(var_rates) >= 2:
            mortgages["unindexed"]["variable_rates"]["up_to_85_ltv"] = {
                "fixed_premium": var_rates[0],
                "total_rate": var_rates[1]
            }

        # Old unindexed loans
        mortgages["unindexed"]["old_loans"]["grunnlan_up_to_70"] = self._extract_rate(text, r"Grunnlán allt að 70% veðsetning.*?\s+([\d,]+)%")
        mortgages["unindexed"]["old_loans"]["vibotar_70_80_85"] = self._extract_rate(text, r"Viðbótarlán\. 70-80/85%.*?\s+([\d,]+)%")

        # Indexed mortgages - fixed for life
        mortgages["indexed"]["fixed_rates"]["up_to_75_ltv"] = self._extract_rate(text, r"Verðtryggð íbúðalán, allt að 75% veðsetning\s+([\d,]+)%")
        mortgages["indexed"]["fixed_rates"]["up_to_85_ltv"] = self._extract_rate(text, r"Verðtryggð íbúðalán, allt að 85% veðsetning.*?\s+([\d,]+)%")

        # Old indexed loans
        mortgages["indexed"]["old_loans"]["grunnlan_up_to_70"] = self._extract_rate(text, r"Verðtryggð grunnlán, allt að 70% veðsetning.*?\s+([\d,]+)%")
        mortgages["indexed"]["old_loans"]["vibotar_70_80_85"] = self._extract_rate(text, r"Verðtryggð viðbótarlán\. 70-80/85%.*?\s+([\d,]+)%")

        return mortgages

    def parse_vehicle_loans(self, text: str) -> Dict:
        """Parse vehicle and equipment financing rates"""
        vehicle_loans = {
            "electric_vehicles": {},
            "other_vehicles": {}
        }

        # Pattern: LTV ranges with two rates (electric, other)
        # < 51%
        rates_51 = self._extract_multiple_rates(text, r"Lánshlutfall <51%\s+([\d,]+)%\s+([\d,]+)%")
        if rates_51 and len(rates_51) >= 2:
            vehicle_loans["electric_vehicles"]["ltv_under_51"] = rates_51[0]
            vehicle_loans["other_vehicles"]["ltv_under_51"] = rates_51[1]

        # 51-69.9%
        rates_51_69 = self._extract_multiple_rates(text, r"Lánshlutfall 51-69,9%\s+([\d,]+)%\s+([\d,]+)%")
        if rates_51_69 and len(rates_51_69) >= 2:
            vehicle_loans["electric_vehicles"]["ltv_51_69"] = rates_51_69[0]
            vehicle_loans["other_vehicles"]["ltv_51_69"] = rates_51_69[1]

        # 70-80%
        rates_70_80 = self._extract_multiple_rates(text, r"Lánshlutfall 70-80%\s+([\d,]+)%\s+([\d,]+)%")
        if rates_70_80 and len(rates_70_80) >= 2:
            vehicle_loans["electric_vehicles"]["ltv_70_80"] = rates_70_80[0]
            vehicle_loans["other_vehicles"]["ltv_70_80"] = rates_70_80[1]

        return vehicle_loans

    def parse_bonds_and_loan_agreements(self, text: str) -> Dict:
        """Parse bonds and loan agreement rates (Kjörvaxtaflokkar)"""
        bonds = {
            "kjorvaxtaflokkar": {}
        }

        # Parse kjörvextir 0-9
        for i in range(10):
            pattern = rf"{i}\. kjörvax.*?\s+([\d,]+)%\s+([\d,]+)%"
            rates = self._extract_multiple_rates(text, pattern)
            if rates and len(rates) >= 2:
                bonds["kjorvaxtaflokkar"][f"kjorvaxtaflokkur_{i}"] = {
                    "indexed": rates[0],
                    "unindexed": rates[1]
                }

        # Special categories
        bonds["eldri_lan_an_kjorvaxta"] = self._extract_two_column_rates(text, "Eldri lán án kjörvaxta")
        bonds["kjor_lan_spkef"] = self._extract_two_column_rates(text, "Kjörvextir lána SpKef")
        bonds["kjor_lan_vestmannaeyja"] = self._extract_two_column_rates(text, "Kjörvextir lána Sp. Vestmannaeyja og Norðurlands")
        bonds["tm_kjorvextir"] = self._extract_two_column_rates(text, "TM kjörvextir")
        bonds["tm_bilalan"] = self._extract_two_column_rates(text, "TM Bílalán")
        bonds["tm_onnur_lan"] = self._extract_two_column_rates(text, "TM Önnur lán")

        return bonds

    def parse_short_term_loans(self, text: str) -> Dict:
        """Parse short-term loans (overdrafts, credit cards)"""
        short_term = {
            "overdrafts": {},
            "credit_cards": {}
        }

        # Overdrafts
        short_term["overdrafts"]["fyrirtaekja"] = self._extract_rate(text, r"Yfirdráttarlán og reikningslán fyrirtækja\s+([\d,]+)%")
        short_term["overdrafts"]["einstaklinga"] = self._extract_rate(text, r"Yfirdráttarlán einstaklinga.*?Einkareikningar.*?\s+([\d,]+)%")
        short_term["overdrafts"]["vordufélaga_high"] = self._extract_rate(text, r"Yfirdráttarlán Vörðufélaga, hæstu vextir\s+([\d,]+)%")
        short_term["overdrafts"]["vordufélaga_low"] = self._extract_rate(text, r"Yfirdráttarlán Vörðufélaga, lægstu vextir\s+([\d,]+)%")
        short_term["overdrafts"]["naman_menntasjo_ur"] = self._extract_rate(text, r"Náman vegna Menntasjóðs námsmanna\s+([\d,]+)%")
        short_term["overdrafts"]["naman_almennir"] = self._extract_rate(text, r"Náman almennir reikningar\s+([\d,]+)%")

        # Credit cards
        short_term["credit_cards"]["greiðsludreifing"] = self._extract_rate(text, r"Greiðsludreifing kreditkorta.*?\s+([\d,]+)%")

        return short_term

    def parse_penalty_interest(self, text: str) -> Optional[float]:
        """Parse penalty interest rate (Dráttarvextir)"""
        return self._extract_rate(text, r"Dráttarvextir.*?\s+([\d,]+)%")

    def _extract_rate(self, text: str, pattern: str) -> Optional[float]:
        """Helper to extract a single rate using regex"""
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            return self.parse_percentage(match.group(1))
        return None

    def _extract_multiple_rates(self, text: str, pattern: str) -> List[Optional[float]]:
        """Helper to extract multiple rates using regex"""
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            return [self.parse_percentage(match.group(i)) for i in range(1, len(match.groups()) + 1)]
        return []

    def _extract_two_column_rates(self, text: str, account_name: str) -> Dict[str, Optional[float]]:
        """Helper to extract indexed and unindexed rates"""
        pattern = rf"{re.escape(account_name)}.*?\s+([\d,]+)%\s+([\d,]+)%"
        rates = self._extract_multiple_rates(text, pattern)
        if rates and len(rates) >= 2:
            return {
                "indexed": rates[0],
                "unindexed": rates[1]
            }
        return {"indexed": None, "unindexed": None}

    def _parse_tiered_accounts(self, text: str, account_name: str) -> Dict:
        """Parse tiered accounts with multiple balance tiers"""
        tiers = {}

        # Common tier patterns
        tier_patterns = [
            (r"0-999\.999 kr\.", "tier_0_1m"),
            (r"1\.000\.000-4\.999\.999 kr\.", "tier_1m_5m"),
            (r"5\.000\.000-19\.999\.999 kr\.", "tier_5m_20m"),
            (r"20\.000\.000 kr\. og hærri", "tier_20m_plus"),
            (r"0-20\.000\.000 kr\.", "tier_0_20m"),
            (r"60\.000\.000 kr\. og hærri", "tier_60m_plus")
        ]

        # Find the section for this account
        account_section_match = re.search(rf"{re.escape(account_name)}.*?(?=\n\w+:|$)", text, re.IGNORECASE | re.DOTALL)
        if account_section_match:
            section = account_section_match.group(0)

            for tier_pattern, tier_key in tier_patterns:
                # Look for rates in this tier (may have 1-3 columns)
                full_pattern = rf"{tier_pattern}\s*\*?\s+([\d,]+)%(\s+([\d,]+)%)?(\s+([\d,]+)%)?"
                match = re.search(full_pattern, section, re.IGNORECASE)
                if match:
                    rates = []
                    for i in [1, 3, 5]:
                        if match.group(i):
                            rate = self.parse_percentage(match.group(i))
                            if rate is not None:
                                rates.append(rate)

                    if len(rates) == 1:
                        tiers[tier_key] = rates[0]
                    elif len(rates) == 2:
                        tiers[tier_key] = {
                            "indexed": rates[0],
                            "unindexed": rates[1]
                        }
                    elif len(rates) >= 3:
                        tiers[tier_key] = {
                            "unbound": rates[0],
                            "3_months": rates[1],
                            "6_months": rates[2] if len(rates) > 2 else None
                        }

        return tiers

    def parse_all(self, pdf_content: bytes) -> Dict:
        """
        Parse all data from PDF

        Args:
            pdf_content: PDF file content as bytes

        Returns:
            Dict: Complete interest rate data
        """
        # Extract text from PDF
        self.raw_text = self.extract_text_from_pdf(pdf_content)

        if not self.raw_text:
            logger.error("Failed to extract text from PDF")
            return {}

        # Parse effective date
        effective_date = self.parse_effective_date(self.raw_text)
        if not effective_date:
            logger.warning("Could not parse effective date from PDF")

        # Parse all sections
        result = {
            "effective_date": effective_date,
            "deposits": self.parse_deposit_accounts(self.raw_text),
            "mortgages": self.parse_mortgage_loans(self.raw_text),
            "vehicle_loans": self.parse_vehicle_loans(self.raw_text),
            "bonds_and_loans": self.parse_bonds_and_loan_agreements(self.raw_text),
            "short_term_loans": self.parse_short_term_loans(self.raw_text),
            "penalty_interest": self.parse_penalty_interest(self.raw_text)
        }

        logger.info("Successfully parsed all interest rate data")
        return result
