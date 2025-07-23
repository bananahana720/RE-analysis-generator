"""Unit tests for Phoenix MLS address normalization functionality.

This module tests the normalize_address method and related functionality
for parsing and standardizing addresses from various formats.
"""

import pytest
from phoenix_real_estate.collectors.phoenix_mls.parser import PhoenixMLSParser


class TestAddressNormalization:
    """Test cases for address normalization functionality."""

    @pytest.fixture
    def parser(self):
        """Create a parser instance for testing."""
        return PhoenixMLSParser()

    # Test standard address formats

    @pytest.mark.unit
    def test_normalize_standard_address(self, parser):
        """Test normalizing a standard address format."""
        address = "123 Main Street, Phoenix, AZ 85001"
        result = parser.normalize_address(address)

        assert result["street"] == "123 Main St"
        assert result["city"] == "Phoenix"
        assert result["state"] == "AZ"
        assert result["zip"] == "85001"

    @pytest.mark.unit
    def test_normalize_address_with_avenue(self, parser):
        """Test normalizing addresses with Avenue."""
        address = "456 Oak Avenue, Scottsdale, AZ 85251"
        result = parser.normalize_address(address)

        assert result["street"] == "456 Oak Ave"
        assert result["city"] == "Scottsdale"
        assert result["state"] == "AZ"
        assert result["zip"] == "85251"

    @pytest.mark.unit
    def test_normalize_address_with_directions(self, parser):
        """Test normalizing addresses with directional prefixes."""
        test_cases = [
            ("123 North Main Street, Phoenix, AZ 85001", "123 N Main St"),
            ("456 South Oak Avenue, Mesa, AZ 85201", "456 S Oak Ave"),
            ("789 East Elm Road, Tempe, AZ 85281", "789 E Elm Rd"),
            ("321 West Pine Drive, Glendale, AZ 85301", "321 W Pine Dr"),
            ("555 Northwest Central Ave, Phoenix, AZ 85004", "555 NW Central Ave"),
        ]

        for address, expected_street in test_cases:
            result = parser.normalize_address(address)
            assert result["street"] == expected_street

    # Test various street type abbreviations

    @pytest.mark.unit
    def test_normalize_street_types(self, parser):
        """Test normalizing various street type abbreviations."""
        test_cases = [
            ("123 Main STREET, Phoenix, AZ 85001", "123 Main St"),
            ("123 Main St., Phoenix, AZ 85001", "123 Main St"),
            ("456 Oak AVENUE, Phoenix, AZ 85001", "456 Oak Ave"),
            ("456 Oak Ave., Phoenix, AZ 85001", "456 Oak Ave"),
            ("789 Elm ROAD, Phoenix, AZ 85001", "789 Elm Rd"),
            ("789 Elm Rd., Phoenix, AZ 85001", "789 Elm Rd"),
            ("321 Pine DRIVE, Phoenix, AZ 85001", "321 Pine Dr"),
            ("321 Pine Dr., Phoenix, AZ 85001", "321 Pine Dr"),
            ("555 Maple LANE, Phoenix, AZ 85001", "555 Maple Ln"),
            ("555 Maple Ln., Phoenix, AZ 85001", "555 Maple Ln"),
            ("777 Desert BOULEVARD, Phoenix, AZ 85001", "777 Desert Blvd"),
            ("777 Desert Blvd., Phoenix, AZ 85001", "777 Desert Blvd"),
            ("999 Valley COURT, Phoenix, AZ 85001", "999 Valley Ct"),
            ("111 Sunset PLACE, Phoenix, AZ 85001", "111 Sunset Pl"),
            ("222 Park CIRCLE, Phoenix, AZ 85001", "222 Park Cir"),
            ("333 River PARKWAY, Phoenix, AZ 85001", "333 River Pkwy"),
        ]

        for address, expected_street in test_cases:
            result = parser.normalize_address(address)
            assert result["street"] == expected_street

    # Test city normalization

    @pytest.mark.unit
    def test_normalize_phoenix_area_cities(self, parser):
        """Test normalizing common Phoenix area city names."""
        test_cases = [
            ("123 Main St, PHOENIX, AZ 85001", "Phoenix"),
            ("123 Main St, phoenix, AZ 85001", "Phoenix"),
            ("123 Main St, SCOTTSDALE, AZ 85251", "Scottsdale"),
            ("123 Main St, scottsdale, AZ 85251", "Scottsdale"),
            ("123 Main St, TEMPE, AZ 85281", "Tempe"),
            ("123 Main St, MESA, AZ 85201", "Mesa"),
            ("123 Main St, CHANDLER, AZ 85224", "Chandler"),
            ("123 Main St, GILBERT, AZ 85234", "Gilbert"),
            ("123 Main St, GLENDALE, AZ 85301", "Glendale"),
            ("123 Main St, PEORIA, AZ 85345", "Peoria"),
            ("123 Main St, QUEEN CREEK, AZ 85142", "Queen Creek"),
            ("123 Main St, FOUNTAIN HILLS, AZ 85268", "Fountain Hills"),
            ("123 Main St, PARADISE VALLEY, AZ 85253", "Paradise Valley"),
            ("123 Main St, SUN CITY, AZ 85351", "Sun City"),
            ("123 Main St, SUN CITY WEST, AZ 85375", "Sun City West"),
        ]

        for address, expected_city in test_cases:
            result = parser.normalize_address(address)
            assert result["city"] == expected_city

    # Test state normalization

    @pytest.mark.unit
    def test_normalize_state_abbreviations(self, parser):
        """Test normalizing state names to abbreviations."""
        test_cases = [
            ("123 Main St, Phoenix, Arizona 85001", "AZ"),
            ("123 Main St, Phoenix, ARIZONA 85001", "AZ"),
            ("123 Main St, Phoenix, Ariz 85001", "AZ"),
            ("123 Main St, Phoenix, ARIZ 85001", "AZ"),
            ("123 Main St, Phoenix, AZ 85001", "AZ"),
            ("123 Main St, Las Vegas, Nevada 89101", "NV"),
            ("123 Main St, Las Vegas, NEV 89101", "NV"),
            ("123 Main St, San Diego, California 92101", "CA"),
            ("123 Main St, San Diego, CALIF 92101", "CA"),
            ("123 Main St, Albuquerque, New Mexico 87101", "NM"),
            ("123 Main St, El Paso, Texas 79901", "TX"),
        ]

        for address, expected_state in test_cases:
            result = parser.normalize_address(address)
            assert result["state"] == expected_state

    # Test ZIP code handling

    @pytest.mark.unit
    def test_normalize_zip_codes(self, parser):
        """Test handling of various ZIP code formats."""
        test_cases = [
            ("123 Main St, Phoenix, AZ 85001", "85001"),
            ("123 Main St, Phoenix, AZ 85001-1234", "85001"),
            ("123 Main St, Phoenix, AZ 85001 - 1234", "85001"),
            ("123 Main St, Phoenix, AZ 850011234", "85001"),
        ]

        for address, expected_zip in test_cases:
            result = parser.normalize_address(address)
            assert result["zip"] == expected_zip

    # Test non-standard formats

    @pytest.mark.unit
    def test_normalize_missing_commas(self, parser):
        """Test addresses missing commas between components."""
        address = "123 Main Street Phoenix AZ 85001"
        result = parser.normalize_address(address)

        assert result["street"] == "123 Main St"
        assert result["city"] == "Phoenix"
        assert result["state"] == "AZ"
        assert result["zip"] == "85001"

    @pytest.mark.unit
    def test_normalize_extra_spaces(self, parser):
        """Test addresses with extra spaces."""
        address = "123   Main  Street ,  Phoenix ,  AZ   85001"
        result = parser.normalize_address(address)

        assert result["street"] == "123 Main St"
        assert result["city"] == "Phoenix"
        assert result["state"] == "AZ"
        assert result["zip"] == "85001"

    @pytest.mark.unit
    def test_normalize_mixed_case(self, parser):
        """Test addresses with mixed case formatting."""
        address = "123 mAiN sTreeT, pHoeNix, az 85001"
        result = parser.normalize_address(address)

        assert result["street"] == "123 Main St"
        assert result["city"] == "Phoenix"
        assert result["state"] == "AZ"
        assert result["zip"] == "85001"

    # Test edge cases

    @pytest.mark.unit
    def test_normalize_apartment_numbers(self, parser):
        """Test addresses with apartment/unit numbers."""
        test_cases = [
            "123 Main Street Apt 4B, Phoenix, AZ 85001",
            "123 Main Street #4B, Phoenix, AZ 85001",
            "123 Main Street Unit 4B, Phoenix, AZ 85001",
            "123 Main Street Suite 4B, Phoenix, AZ 85001",
        ]

        for address in test_cases:
            result = parser.normalize_address(address)
            assert "123 Main St" in result["street"]
            assert result["city"] == "Phoenix"
            assert result["state"] == "AZ"
            assert result["zip"] == "85001"

    @pytest.mark.unit
    def test_normalize_po_box(self, parser):
        """Test P.O. Box addresses."""
        address = "P.O. Box 1234, Phoenix, AZ 85001"
        result = parser.normalize_address(address)

        assert "Box 1234" in result["street"]
        assert result["city"] == "Phoenix"
        assert result["state"] == "AZ"
        assert result["zip"] == "85001"

    @pytest.mark.unit
    def test_normalize_numbered_streets(self, parser):
        """Test addresses with numbered streets."""
        test_cases = [
            ("123 1st Street, Phoenix, AZ 85001", "123 1st St"),
            ("456 2nd Avenue, Phoenix, AZ 85001", "456 2nd Ave"),
            ("789 3rd Road, Phoenix, AZ 85001", "789 3rd Rd"),
            ("321 21st Street, Phoenix, AZ 85001", "321 21st St"),
            ("555 42nd Avenue, Phoenix, AZ 85001", "555 42nd Ave"),
        ]

        for address, expected_street in test_cases:
            result = parser.normalize_address(address)
            assert result["street"] == expected_street

    @pytest.mark.unit
    def test_normalize_spanish_street_names(self, parser):
        """Test addresses with Spanish street names."""
        address = "123 Calle de Sol, Phoenix, AZ 85001"
        result = parser.normalize_address(address)

        assert result["street"] == "123 Calle De Sol"
        assert result["city"] == "Phoenix"
        assert result["state"] == "AZ"
        assert result["zip"] == "85001"

    # Test error handling

    @pytest.mark.unit
    def test_normalize_empty_address(self, parser):
        """Test handling of empty address."""
        with pytest.raises(ValueError, match="Address cannot be empty"):
            parser.normalize_address("")

    @pytest.mark.unit
    def test_normalize_none_address(self, parser):
        """Test handling of None address."""
        with pytest.raises(ValueError, match="Address cannot be empty"):
            parser.normalize_address(None)

    @pytest.mark.unit
    def test_normalize_invalid_address(self, parser):
        """Test handling of unparseable addresses."""
        invalid_addresses = [
            "Just some random text",
            "12345",
            "Phoenix Arizona",
            "Main Street",
        ]

        for address in invalid_addresses:
            with pytest.raises(ValueError, match="Could not parse address"):
                parser.normalize_address(address)

    # Test partial addresses

    @pytest.mark.unit
    def test_normalize_missing_zip(self, parser):
        """Test addresses missing ZIP code."""
        address = "123 Main Street, Phoenix, AZ"
        # Should attempt to parse but may use default ZIP
        try:
            result = parser.normalize_address(address)
            assert result["street"] == "123 Main St"
            assert result["city"] == "Phoenix"
            assert result["state"] == "AZ"
            assert result["zip"] in ["85001", None]  # Default or None
        except ValueError:
            # Also acceptable to raise error for incomplete address
            pass

    @pytest.mark.unit
    def test_normalize_missing_state(self, parser):
        """Test addresses missing state."""
        address = "123 Main Street, Phoenix 85001"
        # Should default to AZ for Phoenix addresses
        result = parser.normalize_address(address)
        assert result["street"] == "123 Main St"
        assert result["city"] == "Phoenix"
        assert result["state"] == "AZ"
        assert result["zip"] == "85001"

    # Test integration with parser

    @pytest.mark.unit
    def test_normalize_from_parsed_html(self, parser):
        """Test normalizing address extracted from HTML."""
        html = """
        <div class="property-detail">
            <h1 class="property-address">
                <span class="street-address">7890 DESERT VIEW ROAD</span>
                <span class="city-state-zip">SCOTTSDALE, ARIZONA 85251-1234</span>
            </h1>
        </div>
        """
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")

        # Extract address
        address = parser._extract_address(soup)
        assert address is not None

        # Normalize it
        result = parser.normalize_address(address)
        assert result["street"] == "7890 Desert View Rd"
        assert result["city"] == "Scottsdale"
        assert result["state"] == "AZ"
        assert result["zip"] == "85251"
