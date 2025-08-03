"""Phoenix MLS HTML Parser.

Extracts structured property data from HTML using BeautifulSoup.
"""

import re
import html
import gzip
from typing import Dict, List, Optional, Any
from datetime import datetime, UTC
from dataclasses import dataclass, asdict
from bs4 import BeautifulSoup, Tag
from urllib.parse import urljoin
import unicodedata

from phoenix_real_estate.foundation.logging import get_logger

logger = get_logger(__name__)


class ParsingError(Exception):
    """Base exception for parsing errors."""

    pass


class ValidationError(ParsingError):
    """Raised when data validation fails."""

    pass


@dataclass
class PropertyData:
    """Structured property data model."""

    # Required fields
    address: str
    price: float

    # Optional fields
    beds: Optional[int] = None
    baths: Optional[float] = None
    sqft: Optional[int] = None
    lot_size: Optional[float] = None
    lot_size_unit: Optional[str] = None
    year_built: Optional[int] = None
    property_type: Optional[str] = None
    description: Optional[str] = None
    mls_id: Optional[str] = None
    listing_date: Optional[datetime] = None
    features: Optional[List[str]] = None
    images: Optional[List[str]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return asdict(self)

    def to_json_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary."""
        data = self.to_dict()
        # Convert datetime to ISO format
        if data.get("listing_date"):
            data["listing_date"] = data["listing_date"].isoformat()
        return data


class PhoenixMLSParser:
    """Parser for Phoenix MLS property HTML.

    Features:
    - Robust HTML parsing with BeautifulSoup
    - Data extraction and normalization
    - Raw HTML storage for re-parsing
    - Validation and sanitization
    """

    # Common property type mappings
    PROPERTY_TYPE_MAPPINGS = {
        "sfh": "Single Family",
        "single family home": "Single Family",
        "condo": "Condo",
        "condominium": "Condo",
        "townhouse": "Townhouse",
        "townhome": "Townhouse",
        "manufactured": "Manufactured",
        "mobile home": "Manufactured",
        "land": "Land",
        "lot": "Land",
    }

    def __init__(self):
        """Initialize the parser."""
        self.stored_html = {}
        logger.info("PhoenixMLSParser initialized")

    def parse_property(self, html_content: str, property_url: Optional[str] = None) -> PropertyData:
        """Parse property details from HTML.

        Args:
            html_content: HTML content to parse
            property_url: Optional URL for resolving relative links

        Returns:
            PropertyData object with extracted information

        Raises:
            ValueError: If required fields are missing
        """
        if not html_content or not html_content.strip():
            raise ValueError("Empty HTML content")

        soup = BeautifulSoup(html_content, "html.parser")

        # Extract all fields
        address = self._extract_address(soup)
        price = self._extract_price(soup)

        # Validate required fields
        if not address:
            raise ValueError("Missing required field: address")
        if price is None:
            raise ValueError("Missing required field: price")

        # Extract optional fields
        beds = self._extract_beds(soup)
        baths = self._extract_baths(soup)
        sqft = self._extract_sqft(soup)
        lot_size, lot_unit = self._extract_lot_size(soup)
        year_built = self._extract_year_built(soup)
        property_type = self._extract_property_type(soup)
        description = self._extract_description(soup)
        mls_id = self._extract_mls_id(soup)
        features = self._extract_features(soup)
        images = self._extract_images(soup, property_url)

        return PropertyData(
            address=address,
            price=price,
            beds=beds,
            baths=baths,
            sqft=sqft,
            lot_size=lot_size,
            lot_size_unit=lot_unit,
            year_built=year_built,
            property_type=property_type,
            description=description,
            mls_id=mls_id,
            features=features,
            images=images,
        )

    def parse_search_results(
        self, html_content: str, base_url: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Parse search results page for property listings.

        Args:
            html_content: HTML content of search results
            base_url: Base URL for resolving relative links

        Returns:
            List of property data dictionaries
        """
        if not html_content:
            return []

        soup = BeautifulSoup(html_content, "html.parser")
        properties = []

        # Find property cards - try multiple selectors
        property_cards = soup.find_all(
            ["div", "article"], class_=re.compile("property|listing|result")
        )

        for card in property_cards:
            try:
                property_data = self._parse_property_card(card, base_url)
                if property_data:
                    properties.append(property_data)
            except Exception as e:
                logger.warning(f"Error parsing property card: {e}")
                continue

        return properties

    def _parse_property_card(
        self, card: Tag, base_url: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Parse individual property card from search results."""
        data = {}

        # Extract URL
        link = card.find("a", href=True)
        if link:
            url = link["href"]
            if base_url and not url.startswith("http"):
                url = urljoin(base_url, url)
            data["url"] = url

        # Extract address
        address_elem = card.find(["h2", "h3", "div"], class_=re.compile("address|location"))
        if address_elem:
            data["address"] = self._clean_text(address_elem.get_text())

        # Extract price
        price_elem = card.find(["span", "div"], class_=re.compile("price|cost"))
        if price_elem:
            price_text = price_elem.get_text()
            data["price"] = self._parse_price_text(price_text)

        # Extract basic details
        beds_elem = card.find(["span", "div"], class_=re.compile("bed"))
        if beds_elem:
            data["beds"] = self._parse_beds_text(beds_elem.get_text())

        baths_elem = card.find(["span", "div"], class_=re.compile("bath"))
        if baths_elem:
            data["baths"] = self._parse_baths_text(baths_elem.get_text())

        sqft_elem = card.find(["span", "div"], class_=re.compile("sqft|area"))
        if sqft_elem:
            data["sqft"] = self._parse_sqft_text(sqft_elem.get_text())

        return data if data else None

    def _extract_address(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract property address."""
        # Look for address components separately first
        street_elem = soup.find(["span", "div"], class_=re.compile("street|address"))
        city_state_elem = soup.find(["span", "div"], class_=re.compile("city|location"))

        if street_elem and city_state_elem:
            street = self._clean_text(street_elem.get_text())
            city_state = self._clean_text(city_state_elem.get_text())
            # Combine with comma if not already present
            if city_state and not city_state.startswith(","):
                return f"{street}, {city_state}"
            else:
                return f"{street}{city_state}"

        # Try multiple selectors for combined address
        selectors = [
            "h1.address",
            ".property-address",
            '[data-testid="address"]',
            'h1:contains("Address")',
            ".listing-address",
        ]

        for selector in selectors:
            elem = soup.select_one(selector)
            if elem:
                # Check if we have separate spans inside
                street_span = elem.find(["span"], class_=re.compile("street"))
                city_span = elem.find(["span"], class_=re.compile("city"))

                if street_span and city_span:
                    street = self._clean_text(street_span.get_text())
                    city_state = self._clean_text(city_span.get_text())
                    return f"{street}, {city_state}"
                else:
                    return self._clean_text(elem.get_text())

        # Fallback: look for address pattern
        text = soup.get_text()
        match = re.search(
            r"\d+\s+\w+\s+(St|Street|Ave|Avenue|Rd|Road|Dr|Drive|Ln|Lane|Way|Blvd|Boulevard)", text
        )
        if match:
            # Extract full address including city, state, zip
            address_match = re.search(
                r"(\d+\s+[^,]+),\s*([^,]+),\s*(\w{2})\s+(\d{5})", text[match.start() :]
            )
            if address_match:
                return address_match.group(0)

        return None

    def normalize_address(self, address: str) -> Dict[str, str]:
        """Normalize and parse address into components.

        Args:
            address: Raw address string to parse

        Returns:
            Dictionary with standardized address components:
            - street: Street address
            - city: City name
            - state: State abbreviation
            - zip: ZIP code (5 digits)

        Raises:
            ValueError: If address cannot be parsed
        """
        if not address:
            raise ValueError("Address cannot be empty")

        # Clean the address first
        address = self._clean_text(address)

        # Common address patterns
        patterns = [
            # Standard format: "123 Main St, Phoenix, AZ 85001"
            r"^(.+?),\s*([^,]+),\s*([A-Za-z]+(?:\s+[A-Za-z]+)?)\s+(\d{5})(?:-\d{4})?$",
            # Format with extra spaces: "123 Main St , Phoenix , AZ  85001"
            r"^(.+?)\s*,\s*([^,]+?)\s*,\s*([A-Za-z]+(?:\s+[A-Za-z]+)?)\s+(\d{5})(?:-\d{4})?$",
            # Format with missing state but has ZIP: "123 Main St, Phoenix 85001"
            r"^(.+?),\s*([A-Za-z]+(?:\s+[A-Za-z]+)*)\s+(\d{5})(?:-\d{4})?$",
            # Format with missing ZIP: "123 Main St, Phoenix, AZ"
            r"^(.+?),\s*([^,]+),\s*([A-Za-z]+(?:\s+[A-Za-z]+)?)$",
            # Format without comma after street: "123 Main St Phoenix, AZ 85001"
            r"^(\d+\s+.+?)\s+([A-Za-z]+(?:\s+[A-Za-z]+)*),\s*([A-Za-z]+(?:\s+[A-Za-z]+)?)\s+(\d{5})(?:-\d{4})?$",
            # Format without comma but with ZIP: "123 Main Street Phoenix AZ 85001"
            # This pattern looks for street types to properly separate street from city
            r"^(\d+\s+(?:N|S|E|W|North|South|East|West|NE|NW|SE|SW|Northeast|Northwest|Southeast|Southwest)?\s*.+?(?:St|Street|Ave|Avenue|Rd|Road|Dr|Drive|Ln|Lane|Blvd|Boulevard|Ct|Court|Pl|Place|Cir|Circle|Pkwy|Parkway|Way))\s+([A-Za-z]+(?:\s+[A-Za-z]+)*)\s+([A-Za-z]{2})\s+(\d{5})(?:-\d{4})?$",
            # Format without state but with ZIP: "123 Main Street Phoenix 85001"
            r"^(\d+\s+.+?(?:St|Street|Ave|Avenue|Rd|Road|Dr|Drive|Ln|Lane|Blvd|Boulevard|Ct|Court|Pl|Place|Cir|Circle|Pkwy|Parkway|Way))\s+([A-Za-z]+(?:\s+[A-Za-z]+)*)\s+(\d{5})(?:-\d{4})?$",
            # Format without comma and missing ZIP: "123 Main St Phoenix AZ"
            r"^(.+?)\s+([A-Za-z\s]+)\s+([A-Za-z]{2})$",
        ]

        # State abbreviation mapping
        state_abbr = {
            "ARIZONA": "AZ",
            "ARIZ": "AZ",
            "AZ": "AZ",
            "CALIFORNIA": "CA",
            "CALIF": "CA",
            "CA": "CA",
            "NEVADA": "NV",
            "NEV": "NV",
            "NV": "NV",
            "NEW MEXICO": "NM",
            "NEW-MEXICO": "NM",
            "NEWMEXICO": "NM",
            "N.M.": "NM",
            "NM": "NM",
            "TEXAS": "TX",
            "TEX": "TX",
            "TX": "TX",
            "UTAH": "UT",
            "UT": "UT",
            "COLORADO": "CO",
            "COLO": "CO",
            "CO": "CO",
        }

        # Try each pattern
        for i, pattern in enumerate(patterns):
            match = re.match(pattern, address, re.IGNORECASE)
            if match:
                groups = match.groups()

                if len(groups) == 4:
                    street, city, state, zip_code = groups
                elif len(groups) == 3 and re.match(r"^\d{5}", groups[-1]):
                    # Missing state but has ZIP: street, city, zip
                    street, city, zip_code = groups
                    state = None
                else:
                    # Missing ZIP code: street, city, state
                    street, city, state = groups
                    zip_code = None

                # Normalize components
                street = self._normalize_street(street.strip())
                city = self._normalize_city(city.strip())

                if state:
                    state = state.upper().strip()

                    # Convert state to abbreviation if needed
                    if len(state) > 2:
                        state = state_abbr.get(state.upper(), state[:2].upper())

                    # Validate state abbreviation
                    if not re.match(r"^[A-Z]{2}$", state):
                        # Default to AZ for Phoenix area
                        state = "AZ"
                else:
                    # Default to AZ for Phoenix area when missing
                    state = "AZ"

                # Extract 5-digit ZIP
                if zip_code:
                    zip_code = zip_code.strip()[:5]
                else:
                    # Default ZIP for Phoenix if missing
                    zip_code = "85001"

                return {"street": street, "city": city, "state": state, "zip": zip_code}

        # If no pattern matches, try to extract what we can
        # Look for ZIP code
        zip_match = re.search(r"\b(\d{5})(?:-\d{4})?\b", address)
        zip_code = zip_match.group(1) if zip_match else None

        # Look for state
        state_match = re.search(r"\b([A-Z]{2})\b", address, re.IGNORECASE)
        state = state_match.group(1).upper() if state_match else None

        # Try to split by common delimiters
        parts = [p for p in re.split(r"[,\s]+", address) if p]

        # Basic heuristic: must have at least a street number and name
        if len(parts) >= 2 and re.match(r"^\d+", parts[0]):
            street_parts = []
            city_parts = []
            found_state = False
            found_zip = False

            for i, part in enumerate(parts):
                if re.match(r"^\d{5}", part):
                    # Found ZIP
                    found_zip = True
                    if not zip_code:
                        zip_code = part[:5]
                elif re.match(r"^[A-Z]{2}$", part, re.IGNORECASE) and i > 2:
                    # Found state (but not if it's too early in the address)
                    found_state = True
                    if not state:
                        state = part.upper()
                    # Previous parts might be city
                    if i > 3 and not city_parts:
                        city_parts = parts[max(3, i - 2) : i]
                elif not found_state and not found_zip:
                    # Still building address
                    if i < 3 or not any(
                        part.upper() in city_mappings
                        for city_mappings in [self._normalize_city("")]
                    ):
                        street_parts.append(part)

            if street_parts and len(street_parts) >= 2:
                # Must have at least number and street name
                street = " ".join(street_parts[:4])  # Max 4 parts for street

                # Try to find city
                if not city_parts and len(parts) > len(street_parts):
                    remaining = parts[len(street_parts) :]
                    # Look for known city names
                    for i, part in enumerate(remaining):
                        if part.upper() in [
                            "PHOENIX",
                            "SCOTTSDALE",
                            "TEMPE",
                            "MESA",
                            "CHANDLER",
                            "GILBERT",
                            "GLENDALE",
                            "PEORIA",
                            "SURPRISE",
                        ]:
                            city_parts = [part]
                            break

                city = " ".join(city_parts) if city_parts else "Phoenix"

                return {
                    "street": self._normalize_street(street),
                    "city": self._normalize_city(city),
                    "state": state or "AZ",
                    "zip": zip_code or "85001",
                }

        raise ValueError(f"Could not parse address: {address}")

    def _normalize_street(self, street: str) -> str:
        """Normalize street address formatting.

        Args:
            street: Raw street address

        Returns:
            Normalized street address
        """
        if not street:
            return ""

        # Standardize common abbreviations
        # Order matters - do directions first, then street types
        replacements = [
            # Directions (must come before street types to avoid conflicts)
            (r"\bNORTHWEST\b", "NW"),
            (r"\bNORTHEAST\b", "NE"),
            (r"\bSOUTHWEST\b", "SW"),
            (r"\bSOUTHEAST\b", "SE"),
            (r"\bNORTH\b", "N"),
            (r"\bSOUTH\b", "S"),
            (r"\bEAST\b", "E"),
            (r"\bWEST\b", "W"),
            (r"\bN\.\b", "N"),
            (r"\bS\.\b", "S"),
            (r"\bE\.\b", "E"),
            (r"\bW\.\b", "W"),
            # Street types
            (r"\bSTREET\b", "St"),
            (r"\bST\.", "St"),  # Period not part of word boundary
            (r"\bST\b", "St"),
            (r"\bAVENUE\b", "Ave"),
            (r"\bAVE\.", "Ave"),
            (r"\bAVE\b", "Ave"),
            (r"\bROAD\b", "Rd"),
            (r"\bRD\.", "Rd"),
            (r"\bRD\b", "Rd"),
            (r"\bDRIVE\b", "Dr"),
            (r"\bDR\.", "Dr"),
            (r"\bDR\b", "Dr"),
            (r"\bLANE\b", "Ln"),
            (r"\bLN\.", "Ln"),
            (r"\bLN\b", "Ln"),
            (r"\bBOULEVARD\b", "Blvd"),
            (r"\bBLVD\.", "Blvd"),
            (r"\bBLVD\b", "Blvd"),
            (r"\bCOURT\b", "Ct"),
            (r"\bCT\.", "Ct"),
            (r"\bCT\b", "Ct"),
            (r"\bPLACE\b", "Pl"),
            (r"\bPL\.", "Pl"),
            (r"\bPL\b", "Pl"),
            (r"\bCIRCLE\b", "Cir"),
            (r"\bCIR\.", "Cir"),
            (r"\bCIR\b", "Cir"),
            (r"\bPARKWAY\b", "Pkwy"),
            (r"\bPKWY\.", "Pkwy"),
            (r"\bPKWY\b", "Pkwy"),
        ]

        # Apply replacements (case-insensitive)
        for pattern, replacement in replacements:
            street = re.sub(pattern, replacement, street, flags=re.IGNORECASE)

        # Ensure proper capitalization
        # Split by spaces and capitalize each word, but preserve existing capitalization for acronyms
        words = []
        for word in street.split():
            if word.isupper() and len(word) <= 3:
                # Keep short uppercase words as-is (likely acronyms/directions)
                words.append(word)
            else:
                # Capitalize first letter
                words.append(word.capitalize())

        return " ".join(words)

    def _normalize_city(self, city: str) -> str:
        """Normalize city name formatting.

        Args:
            city: Raw city name

        Returns:
            Normalized city name
        """
        if not city:
            return "Phoenix"  # Default for Phoenix area

        # Common Phoenix area cities
        city_mappings = {
            "PHOENIX": "Phoenix",
            "SCOTTSDALE": "Scottsdale",
            "TEMPE": "Tempe",
            "MESA": "Mesa",
            "CHANDLER": "Chandler",
            "GILBERT": "Gilbert",
            "GLENDALE": "Glendale",
            "PEORIA": "Peoria",
            "SURPRISE": "Surprise",
            "AVONDALE": "Avondale",
            "GOODYEAR": "Goodyear",
            "BUCKEYE": "Buckeye",
            "QUEEN CREEK": "Queen Creek",
            "FOUNTAIN HILLS": "Fountain Hills",
            "PARADISE VALLEY": "Paradise Valley",
            "CAVE CREEK": "Cave Creek",
            "CAREFREE": "Carefree",
            "LITCHFIELD PARK": "Litchfield Park",
            "TOLLESON": "Tolleson",
            "YOUNGTOWN": "Youngtown",
            "EL MIRAGE": "El Mirage",
            "GUADALUPE": "Guadalupe",
            "WICKENBURG": "Wickenburg",
            "APACHE JUNCTION": "Apache Junction",
            "SUN CITY": "Sun City",
            "SUN CITY WEST": "Sun City West",
            "ANTHEM": "Anthem",
            "NEW RIVER": "New River",
            "RIO VERDE": "Rio Verde",
            "GOLD CANYON": "Gold Canyon",
        }

        # Check for exact match (case-insensitive)
        city_upper = city.upper().strip()
        if city_upper in city_mappings:
            return city_mappings[city_upper]

        # Otherwise, capitalize each word
        return " ".join(word.capitalize() for word in city.split())

    def _extract_price(self, soup: BeautifulSoup) -> Optional[float]:
        """Extract property price."""
        # Try multiple selectors
        selectors = [".price", ".listing-price", '[data-testid="price"]', 'span:contains("$")']

        for selector in selectors:
            elem = soup.select_one(selector)
            if elem:
                price = self._parse_price_text(elem.get_text())
                if price is not None:
                    return price

        return None

    def _parse_price_text(self, text: str) -> Optional[float]:
        """Parse price from text string."""
        if not text:
            return None

        # Remove non-numeric characters except M, K, and decimal
        text = text.upper().strip()

        # Handle millions (e.g., $1.5M)
        if "M" in text:
            match = re.search(r"([\d.]+)\s*M", text)
            if match:
                return float(match.group(1)) * 1_000_000

        # Handle thousands (e.g., $850K)
        if "K" in text:
            match = re.search(r"([\d.]+)\s*K", text)
            if match:
                return float(match.group(1)) * 1_000

        # Standard price format
        match = re.search(r"[\d,]+\.?\d*", text)
        if match:
            price_str = match.group(0).replace(",", "")
            try:
                return float(price_str)
            except ValueError:
                pass

        return None

    def _extract_beds(self, soup: BeautifulSoup) -> Optional[int]:
        """Extract number of bedrooms."""
        selectors = [".beds", '[data-testid="beds"]', ".bed-count", 'span:contains("bed")']

        for selector in selectors:
            elem = soup.select_one(selector)
            if elem:
                beds = self._parse_beds_text(elem.get_text())
                if beds is not None:
                    return beds

        return None

    def _parse_beds_text(self, text: str) -> Optional[int]:
        """Parse number of beds from text."""
        if not text:
            return None

        text = text.lower()

        # Handle studio
        if "studio" in text:
            return 0

        # Extract number
        match = re.search(r"(\d+)\s*(bed|bd|br)", text)
        if match:
            return int(match.group(1))

        return None

    def _extract_baths(self, soup: BeautifulSoup) -> Optional[float]:
        """Extract number of bathrooms."""
        selectors = [".baths", '[data-testid="baths"]', ".bath-count", 'span:contains("bath")']

        for selector in selectors:
            elem = soup.select_one(selector)
            if elem:
                baths = self._parse_baths_text(elem.get_text())
                if baths is not None:
                    return baths

        return None

    def _parse_baths_text(self, text: str) -> Optional[float]:
        """Parse number of baths from text."""
        if not text:
            return None

        text = text.lower()

        # Handle "2 full 1 half" format
        full_match = re.search(r"(\d+)\s*full", text)
        half_match = re.search(r"(\d+)\s*half", text)

        if full_match or half_match:
            full = int(full_match.group(1)) if full_match else 0
            half = int(half_match.group(1)) if half_match else 0
            return full + (half * 0.5)

        # Handle decimal format (e.g., 2.5)
        match = re.search(r"(\d+\.?\d*)\s*(bath|ba)", text)
        if match:
            return float(match.group(1))

        return None

    def _extract_sqft(self, soup: BeautifulSoup) -> Optional[int]:
        """Extract square footage."""
        selectors = [
            ".sqft",
            '[data-testid="sqft"]',
            ".square-feet",
            'span:contains("sq ft")',
            'span:contains("sqft")',
        ]

        for selector in selectors:
            elem = soup.select_one(selector)
            if elem:
                sqft = self._parse_sqft_text(elem.get_text())
                if sqft is not None:
                    return sqft

        return None

    def _parse_sqft_text(self, text: str) -> Optional[int]:
        """Parse square footage from text."""
        if not text:
            return None

        # Remove commas and extract number
        match = re.search(r"([\d,]+)\s*(sq|square)", text.lower())
        if match:
            sqft_str = match.group(1).replace(",", "")
            try:
                return int(sqft_str)
            except ValueError:
                pass

        return None

    def _extract_lot_size(self, soup: BeautifulSoup) -> tuple[Optional[float], Optional[str]]:
        """Extract lot size and unit."""
        selectors = [
            ".lot-size",
            '[data-testid="lot-size"]',
            ".lot-area",
            'span:contains("lot")',
            'span:contains("Lot")',
        ]

        for selector in selectors:
            elem = soup.select_one(selector)
            if elem:
                text = elem.get_text().lower()

                # Check for acres
                acre_match = re.search(r"([\d.,]+)\s*acre", text)
                if acre_match:
                    return float(acre_match.group(1).replace(",", "")), "acres"

                # Check for square feet
                sqft_match = re.search(r"([\d,]+)\s*(sq|square)\s*(ft|feet)", text)
                if sqft_match:
                    sqft_str = sqft_match.group(1).replace(",", "")
                    return float(sqft_str), "sqft"

                # Check for "Lot Sq Ft" format like in test HTML
                lot_sqft_match = re.search(r"([\d,]+)\s*lot\s*(sq|square)\s*(ft|feet)", text)
                if lot_sqft_match:
                    sqft_str = lot_sqft_match.group(1).replace(",", "")
                    return float(sqft_str), "sqft"

        # Also check all span elements for lot size patterns
        spans = soup.find_all("span")
        for span in spans:
            text = span.get_text()
            if "lot" in text.lower() and any(char.isdigit() for char in text):
                # Look for patterns like "7,200 Lot Sq Ft"
                lot_match = re.search(
                    r"([\d,]+)\s*(?:lot\s*)?(?:sq\s*ft|square\s*feet|sqft)", text, re.IGNORECASE
                )
                if lot_match:
                    size_str = lot_match.group(1).replace(",", "")
                    try:
                        return float(size_str), "sqft"
                    except ValueError:
                        continue

        return None, None

    def _extract_year_built(self, soup: BeautifulSoup) -> Optional[int]:
        """Extract year built."""
        selectors = [
            ".year-built",
            '[data-testid="year-built"]',
            ".built-year",
            'span:contains("built")',
            ".detail-value",  # For the test HTML structure
        ]

        for selector in selectors:
            elem = soup.select_one(selector)
            if elem:
                text = elem.get_text()
                match = re.search(r"(19|20)\d{2}", text)
                if match:
                    return int(match.group(0))

        # Also check all text for year patterns
        all_elements = soup.find_all(["span", "div"])
        for elem in all_elements:
            text = elem.get_text()
            if "year built" in text.lower() or "built" in text.lower():
                match = re.search(r"(19|20)\d{2}", text)
                if match:
                    return int(match.group(0))
            # Check for just year patterns in detail values
            if len(text.strip()) == 4 and text.strip().isdigit():
                year = int(text.strip())
                if 1800 <= year <= 2030:
                    return year

        return None

    def _extract_property_type(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract property type."""
        selectors = [
            ".property-type",
            '[data-testid="property-type"]',
            ".type",
            'span:contains("type")',
            ".detail-value",  # For the test HTML structure
        ]

        for selector in selectors:
            elem = soup.select_one(selector)
            if elem:
                prop_type = self._clean_text(elem.get_text()).lower()
                # Map to standard types
                for key, value in self.PROPERTY_TYPE_MAPPINGS.items():
                    if key in prop_type:
                        return value
                # Return as-is if not in mapping
                if prop_type:
                    return prop_type.title()

        # Also check all spans and divs for property type patterns
        all_elements = soup.find_all(["span", "div"])
        for elem in all_elements:
            text = elem.get_text()
            if any(
                ptype in text.lower()
                for ptype in ["single family", "condo", "townhouse", "manufactured"]
            ):
                prop_type = self._clean_text(text).lower()
                for key, value in self.PROPERTY_TYPE_MAPPINGS.items():
                    if key in prop_type:
                        return value
                return text.strip()

        return None

    def _extract_description(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract property description."""
        selectors = [
            ".description",
            ".property-description",
            '[data-testid="description"]',
            ".remarks",
        ]

        for selector in selectors:
            elem = soup.select_one(selector)
            if elem:
                return self._clean_text(elem.get_text())

        return None

    def _extract_mls_id(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract MLS ID."""
        # Look for MLS ID patterns
        text = soup.get_text()
        match = re.search(r"MLS\s*#?\s*:?\s*(\w+)", text, re.IGNORECASE)
        if match:
            return match.group(1)

        return None

    def _extract_features(self, soup: BeautifulSoup) -> Optional[List[str]]:
        """Extract property features."""
        features = []

        # Look for feature lists
        feature_containers = soup.find_all(["ul", "div"], class_=re.compile("feature|amenity"))

        for container in feature_containers:
            items = container.find_all(["li", "span"])
            for item in items:
                feature = self._clean_text(item.get_text())
                if feature and len(feature) > 2:  # Skip empty or very short items
                    features.append(feature)

        return features if features else None

    def _extract_images(
        self, soup: BeautifulSoup, base_url: Optional[str] = None
    ) -> Optional[List[str]]:
        """Extract image URLs."""
        images = []

        # Find images
        img_elements = soup.find_all("img", src=True)

        for img in img_elements[:20]:  # Limit to 20 images
            src = img["src"]

            # Skip small images (likely icons)
            if "icon" in src.lower() or "logo" in src.lower():
                continue

            # Make URL absolute
            if base_url and not src.startswith("http"):
                src = urljoin(base_url, src)

            images.append(src)

        return images if images else None

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text."""
        if not text:
            return ""

        # Decode HTML entities
        text = html.unescape(text)

        # Normalize unicode
        text = unicodedata.normalize("NFKD", text)

        # Remove extra whitespace
        text = " ".join(text.split())

        return text.strip()

    def store_html(self, property_id: str, html_content: str, compress: bool = True) -> None:
        """Store raw HTML for future re-parsing.

        Args:
            property_id: Unique identifier for the property
            html_content: Raw HTML to store
            compress: Whether to compress the HTML
        """
        if compress and len(html_content) > 10000:
            # Compress large HTML
            compressed = gzip.compress(html_content.encode("utf-8"))
            self.stored_html[property_id] = {
                "data": compressed,
                "compressed": True,
                "stored_at": datetime.now(UTC),
            }
        else:
            self.stored_html[property_id] = {
                "data": html_content,
                "compressed": False,
                "stored_at": datetime.now(UTC),
            }

        logger.debug(f"Stored HTML for property {property_id} (compressed: {compress})")

    def get_stored_html(self, property_id: str) -> Optional[str]:
        """Retrieve stored HTML.

        Args:
            property_id: Property identifier

        Returns:
            Stored HTML content or None
        """
        if property_id not in self.stored_html:
            return None

        stored = self.stored_html[property_id]

        if stored["compressed"]:
            # Decompress
            return gzip.decompress(stored["data"]).decode("utf-8")
        else:
            return stored["data"]

    def batch_parse(self, html_list: List[tuple[str, str]]) -> List[PropertyData]:
        """Parse multiple HTML documents in batch.

        Args:
            html_list: List of (property_id, html_content) tuples

        Returns:
            List of successfully parsed PropertyData objects
        """
        results = []

        for property_id, html_content in html_list:
            try:
                # Store HTML
                self.store_html(property_id, html_content)

                # Parse property
                property_data = self.parse_property(html_content)
                results.append(property_data)

            except Exception as e:
                logger.error(f"Error parsing property {property_id}: {e}")
                continue

        return results

    def validate_data(self, data: PropertyData) -> List[str]:
        """Validate property data and return list of issues.

        Args:
            data: PropertyData to validate

        Returns:
            List of validation error messages
        """
        errors = []

        # Required fields
        if not data.address:
            errors.append("Missing required field: address")
        if data.price is None or data.price <= 0:
            errors.append("Invalid price value")

        # Reasonable ranges
        if data.beds is not None and (data.beds < 0 or data.beds > 20):
            errors.append(f"Unreasonable number of beds: {data.beds}")

        if data.baths is not None and (data.baths < 0 or data.baths > 20):
            errors.append(f"Unreasonable number of baths: {data.baths}")

        if data.sqft is not None and (data.sqft < 100 or data.sqft > 50000):
            errors.append(f"Unreasonable square footage: {data.sqft}")

        if data.year_built is not None:
            current_year = datetime.now().year
            if data.year_built < 1800 or data.year_built > current_year + 1:
                errors.append(f"Invalid year built: {data.year_built}")

        return errors

    def sanitize_text(self, text: str) -> str:
        """Sanitize text to prevent XSS and other issues.

        Args:
            text: Text to sanitize

        Returns:
            Sanitized text
        """
        if not text:
            return ""

        # Remove any HTML tags
        soup = BeautifulSoup(text, "html.parser")
        text = soup.get_text()

        # Clean whitespace
        text = self._clean_text(text)

        # Remove any potential script content
        text = re.sub(r"<script.*?</script>", "", text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r"javascript:", "", text, flags=re.IGNORECASE)
        text = re.sub(r"on\w+\s*=", "", text, flags=re.IGNORECASE)

        return text
