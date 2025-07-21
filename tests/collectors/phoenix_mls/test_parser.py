"""Unit tests for Phoenix MLS HTML parser functionality.

This module implements TDD tests for parsing property listings from Phoenix MLS Search website.
Tests cover HTML parsing, data extraction, validation, sanitization, and edge cases.
"""

import pytest
from bs4 import BeautifulSoup
from decimal import Decimal
from typing import Dict, Any, Optional
from datetime import datetime
from unittest.mock import Mock, patch

# Import will fail initially (TDD), but shows the expected module structure
from phoenix_real_estate.collectors.phoenix_mls.parser import (
    PhoenixMLSParser,
    PropertyData,
    ParsingError,
    ValidationError
)


class TestPhoenixMLSParser:
    """Test cases for the PhoenixMLSParser class."""
    
    @pytest.fixture
    def parser(self):
        """Create a parser instance for testing."""
        return PhoenixMLSParser()
    
    @pytest.fixture
    def sample_property_html(self):
        """Sample HTML for a complete property listing."""
        return '''
        <div class="property-detail">
            <div class="property-header">
                <h1 class="property-address">
                    <span class="street-address">123 Main Street</span>
                    <span class="city-state-zip">Phoenix, AZ 85001</span>
                </h1>
                <div class="property-price">
                    <span class="price-value">$450,000</span>
                </div>
            </div>
            <div class="property-features">
                <div class="feature-group">
                    <span class="feature beds">
                        <span class="feature-value">3</span>
                        <span class="feature-label">Beds</span>
                    </span>
                    <span class="feature baths">
                        <span class="feature-value">2.5</span>
                        <span class="feature-label">Baths</span>
                    </span>
                    <span class="feature sqft">
                        <span class="feature-value">1,850</span>
                        <span class="feature-label">Sq Ft</span>
                    </span>
                    <span class="feature lot-size">
                        <span class="feature-value">7,200</span>
                        <span class="feature-label">Lot Sq Ft</span>
                    </span>
                </div>
            </div>
            <div class="property-details">
                <div class="detail-item">
                    <span class="detail-label">Property Type:</span>
                    <span class="detail-value">Single Family</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Year Built:</span>
                    <span class="detail-value">2005</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">MLS #:</span>
                    <span class="detail-value">6789012</span>
                </div>
            </div>
        </div>
        '''
    
    @pytest.fixture
    def minimal_property_html(self):
        """Minimal HTML with only required fields."""
        return '''
        <div class="property-detail">
            <h1 class="property-address">
                <span class="street-address">456 Oak Avenue</span>
                <span class="city-state-zip">Phoenix, AZ 85002</span>
            </h1>
            <div class="property-price">
                <span class="price-value">$325,000</span>
            </div>
        </div>
        '''
    
    @pytest.fixture
    def malformed_property_html(self):
        """Malformed HTML with missing and broken elements."""
        return '''
        <div class="property-detail">
            <h1 class="property-address">
                <span class="street-address">789 Elm Street
                <span class="city-state-zip">Phoenix, AZ</span>
            </h1>
            <div class="property-price">
                <span class="price-value">Price Upon Request</span>
            </div>
            <div class="property-features">
                <span class="feature beds">
                    <span class="feature-value">Studio</span>
                </span>
                <span class="feature baths">
                    <span class="feature-value">1 full, 1 half</span>
                </span>
            </div>
        </div>
        '''
    
    @pytest.fixture
    def search_results_html(self):
        """Sample HTML for search results page with multiple listings."""
        return '''
        <div class="search-results">
            <div class="results-container">
                <article class="property-card" data-listing-id="123456">
                    <div class="card-content">
                        <h3 class="property-address">
                            <a href="/property/123456">123 Main St, Phoenix, AZ 85001</a>
                        </h3>
                        <div class="property-price">$450,000</div>
                        <div class="property-info">
                            <span class="beds">3 bd</span>
                            <span class="baths">2 ba</span>
                            <span class="sqft">1,850 sqft</span>
                        </div>
                    </div>
                </article>
                <article class="property-card" data-listing-id="789012">
                    <div class="card-content">
                        <h3 class="property-address">
                            <a href="/property/789012">456 Oak Ave, Phoenix, AZ 85002</a>
                        </h3>
                        <div class="property-price">$525,000</div>
                        <div class="property-info">
                            <span class="beds">4 bd</span>
                            <span class="baths">3 ba</span>
                            <span class="sqft">2,200 sqft</span>
                        </div>
                    </div>
                </article>
            </div>
        </div>
        '''
    
    # Test Basic Parsing Functionality
    
    @pytest.mark.unit
    def test_parser_initialization(self, parser):
        """Test parser initializes correctly."""
        assert parser is not None
        assert hasattr(parser, 'parse_property')
        assert hasattr(parser, 'parse_search_results')
        assert hasattr(parser, 'validate_property_data')
        assert hasattr(parser, 'store_raw_html')
    
    @pytest.mark.unit
    def test_parse_complete_property(self, parser, sample_property_html):
        """Test parsing a complete property listing with all fields."""
        result = parser.parse_property(sample_property_html)
        
        assert result is not None
        assert isinstance(result, PropertyData)
        assert result.address == "123 Main Street, Phoenix, AZ 85001"
        assert result.street_address == "123 Main Street"
        assert result.city == "Phoenix"
        assert result.state == "AZ"
        assert result.zip_code == "85001"
        assert result.price == 450000
        assert result.beds == 3
        assert result.baths == 2.5
        assert result.square_feet == 1850
        assert result.lot_size == 7200
        assert result.property_type == "Single Family"
        assert result.year_built == 2005
        assert result.mls_number == "6789012"
        assert result.raw_html == sample_property_html
    
    @pytest.mark.unit
    def test_parse_minimal_property(self, parser, minimal_property_html):
        """Test parsing property with only required fields."""
        result = parser.parse_property(minimal_property_html)
        
        assert result is not None
        assert result.address == "456 Oak Avenue, Phoenix, AZ 85002"
        assert result.price == 325000
        assert result.beds is None
        assert result.baths is None
        assert result.square_feet is None
        assert result.lot_size is None
        assert result.property_type is None
        assert result.year_built is None
        assert result.raw_html == minimal_property_html
    
    # Test Data Extraction
    
    @pytest.mark.unit
    def test_extract_address_components(self, parser):
        """Test address extraction and parsing."""
        html = '''
        <h1 class="property-address">
            <span class="street-address">789 Desert View Rd</span>
            <span class="city-state-zip">Scottsdale, AZ 85251</span>
        </h1>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        address_data = parser.extract_address(soup)
        
        assert address_data['full_address'] == "789 Desert View Rd, Scottsdale, AZ 85251"
        assert address_data['street'] == "789 Desert View Rd"
        assert address_data['city'] == "Scottsdale"
        assert address_data['state'] == "AZ"
        assert address_data['zip_code'] == "85251"
    
    @pytest.mark.unit
    def test_extract_price_variations(self, parser):
        """Test price extraction with different formats."""
        test_cases = [
            ("$450,000", 450000),
            ("$1,250,000", 1250000),
            ("$325,500", 325500),
            ("$2,500,000+", 2500000),
            ("Price: $450K", 450000),
            ("$1.5M", 1500000),
            ("$850k", 850000),
        ]
        
        for price_text, expected in test_cases:
            html = f'<span class="price-value">{price_text}</span>'
            soup = BeautifulSoup(html, 'html.parser')
            price = parser.extract_price(soup)
            assert price == expected, f"Failed to parse {price_text}"
    
    @pytest.mark.unit
    def test_extract_beds_baths_variations(self, parser):
        """Test extraction of beds and baths with various formats."""
        test_cases = [
            ("3 beds", "2 baths", 3, 2.0),
            ("4 bd", "3 ba", 4, 3.0),
            ("5 bedrooms", "2.5 bathrooms", 5, 2.5),
            ("Studio", "1 bath", 0, 1.0),
            ("3", "2.5", 3, 2.5),
            ("3 beds", "2 full, 1 half", 3, 2.5),
            ("4 BR", "3.5 BA", 4, 3.5),
        ]
        
        for beds_text, baths_text, expected_beds, expected_baths in test_cases:
            html = f'''
            <span class="beds">{beds_text}</span>
            <span class="baths">{baths_text}</span>
            '''
            soup = BeautifulSoup(html, 'html.parser')
            beds = parser.extract_beds(soup)
            baths = parser.extract_baths(soup)
            assert beds == expected_beds, f"Failed to parse beds: {beds_text}"
            assert baths == expected_baths, f"Failed to parse baths: {baths_text}"
    
    @pytest.mark.unit
    def test_extract_square_footage_formats(self, parser):
        """Test square footage extraction with different formats."""
        test_cases = [
            ("1,850 sqft", 1850),
            ("2,200 sq ft", 2200),
            ("1850 square feet", 1850),
            ("3,500 SF", 3500),
            ("1,234", 1234),
            ("850 sq. ft.", 850),
        ]
        
        for sqft_text, expected in test_cases:
            html = f'<span class="sqft">{sqft_text}</span>'
            soup = BeautifulSoup(html, 'html.parser')
            sqft = parser.extract_square_feet(soup)
            assert sqft == expected, f"Failed to parse sqft: {sqft_text}"
    
    @pytest.mark.unit
    def test_extract_lot_size_formats(self, parser):
        """Test lot size extraction with various formats."""
        test_cases = [
            ("7,200 sq ft lot", 7200),
            ("0.25 acres", 10890),  # 0.25 acres = 10,890 sq ft
            ("1.5 acre lot", 65340),  # 1.5 acres = 65,340 sq ft
            ("8,500 sqft lot", 8500),
            ("Lot: 10,000 SF", 10000),
        ]
        
        for lot_text, expected in test_cases:
            html = f'<span class="lot-size">{lot_text}</span>'
            soup = BeautifulSoup(html, 'html.parser')
            lot_size = parser.extract_lot_size(soup)
            # Allow small margin for acre conversions
            if "acre" in lot_text.lower():
                assert abs(lot_size - expected) < 10
            else:
                assert lot_size == expected, f"Failed to parse lot size: {lot_text}"
    
    # Test Search Results Parsing
    
    @pytest.mark.unit
    def test_parse_search_results(self, parser, search_results_html):
        """Test parsing search results page with multiple listings."""
        results = parser.parse_search_results(search_results_html)
        
        assert len(results) == 2
        
        # First property
        assert results[0]['listing_id'] == "123456"
        assert results[0]['address'] == "123 Main St, Phoenix, AZ 85001"
        assert results[0]['price'] == 450000
        assert results[0]['beds'] == 3
        assert results[0]['baths'] == 2.0
        assert results[0]['square_feet'] == 1850
        assert results[0]['url'] == "/property/123456"
        
        # Second property
        assert results[1]['listing_id'] == "789012"
        assert results[1]['address'] == "456 Oak Ave, Phoenix, AZ 85002"
        assert results[1]['price'] == 525000
        assert results[1]['beds'] == 4
        assert results[1]['baths'] == 3.0
        assert results[1]['square_feet'] == 2200
        assert results[1]['url'] == "/property/789012"
    
    # Test Data Validation and Sanitization
    
    @pytest.mark.unit
    def test_validate_required_fields(self, parser):
        """Test validation of required property fields."""
        # Valid data
        valid_data = PropertyData(
            address="123 Main St, Phoenix, AZ 85001",
            price=450000,
            raw_html="<html>...</html>"
        )
        assert parser.validate_property_data(valid_data) is True
        
        # Missing address
        invalid_data1 = PropertyData(
            address=None,
            price=450000,
            raw_html="<html>...</html>"
        )
        with pytest.raises(ValidationError, match="Missing required field: address"):
            parser.validate_property_data(invalid_data1)
        
        # Missing price
        invalid_data2 = PropertyData(
            address="123 Main St",
            price=None,
            raw_html="<html>...</html>"
        )
        with pytest.raises(ValidationError, match="Missing required field: price"):
            parser.validate_property_data(invalid_data2)
    
    @pytest.mark.unit
    def test_validate_data_ranges(self, parser):
        """Test validation of data ranges and logical constraints."""
        # Price too low
        with pytest.raises(ValidationError, match="Price must be greater than 0"):
            parser.validate_property_data(PropertyData(
                address="123 Main St",
                price=-1000,
                raw_html="<html></html>"
            ))
        
        # Invalid beds count
        with pytest.raises(ValidationError, match="Beds count must be between 0 and 50"):
            parser.validate_property_data(PropertyData(
                address="123 Main St",
                price=450000,
                beds=100,
                raw_html="<html></html>"
            ))
        
        # Invalid baths count
        with pytest.raises(ValidationError, match="Baths count must be between 0 and 20"):
            parser.validate_property_data(PropertyData(
                address="123 Main St",
                price=450000,
                baths=25.5,
                raw_html="<html></html>"
            ))
        
        # Invalid square footage
        with pytest.raises(ValidationError, match="Square footage must be between"):
            parser.validate_property_data(PropertyData(
                address="123 Main St",
                price=450000,
                square_feet=100000,
                raw_html="<html></html>"
            ))
    
    @pytest.mark.unit
    def test_sanitize_text_input(self, parser):
        """Test text sanitization for security and consistency."""
        test_cases = [
            ("  123 Main St  ", "123 Main St"),
            ("123\nMain\tSt", "123 Main St"),
            ("123 <script>alert('xss')</script> Main St", "123 Main St"),
            ("123 Main St™", "123 Main St"),
            ("123  Main   St", "123 Main St"),  # Multiple spaces
            ("", None),  # Empty string
            ("   ", None),  # Only whitespace
        ]
        
        for input_text, expected in test_cases:
            result = parser.sanitize_text(input_text)
            assert result == expected, f"Failed to sanitize: {input_text!r}"
    
    @pytest.mark.unit
    def test_sanitize_numeric_input(self, parser):
        """Test numeric input sanitization."""
        test_cases = [
            ("$450,000", 450000),
            ("1,234.56", 1234.56),
            ("  123  ", 123),
            ("abc123def", 123),
            ("no numbers", None),
            ("", None),
        ]
        
        for input_text, expected in test_cases:
            result = parser.sanitize_numeric(input_text)
            assert result == expected, f"Failed to sanitize numeric: {input_text!r}"
    
    # Test Edge Cases and Error Handling
    
    @pytest.mark.unit
    def test_parse_malformed_html(self, parser, malformed_property_html):
        """Test parsing malformed or incomplete HTML."""
        result = parser.parse_property(malformed_property_html)
        
        assert result is not None
        assert result.address == "789 Elm Street, Phoenix, AZ"
        assert result.price is None  # "Price Upon Request" should return None
        assert result.beds == 0  # "Studio" should be 0
        assert result.baths == 1.5  # "1 full, 1 half" should be 1.5
        assert result.raw_html == malformed_property_html
    
    @pytest.mark.unit
    def test_parse_empty_html(self, parser):
        """Test parsing empty or minimal HTML."""
        empty_cases = [
            "",
            "<html></html>",
            "<div></div>",
            None,
        ]
        
        for html in empty_cases:
            with pytest.raises(ParsingError, match="No valid property data found"):
                parser.parse_property(html)
    
    @pytest.mark.unit
    def test_parse_non_property_html(self, parser):
        """Test parsing HTML that doesn't contain property data."""
        non_property_html = '''
        <div class="header">
            <h1>Welcome to Phoenix MLS</h1>
            <nav>
                <a href="/search">Search</a>
                <a href="/about">About</a>
            </nav>
        </div>
        '''
        
        with pytest.raises(ParsingError, match="No valid property data found"):
            parser.parse_property(non_property_html)
    
    @pytest.mark.unit
    def test_handle_different_property_types(self, parser):
        """Test parsing different property types."""
        property_types = [
            "Single Family",
            "Condo",
            "Townhouse",
            "Multi-Family",
            "Land",
            "Commercial",
            "Mobile Home",
            "Apartment",
        ]
        
        for prop_type in property_types:
            html = f'''
            <div class="property-detail">
                <h1 class="property-address">
                    <span class="street-address">123 Test St</span>
                    <span class="city-state-zip">Phoenix, AZ 85001</span>
                </h1>
                <div class="property-price">
                    <span class="price-value">$300,000</span>
                </div>
                <div class="property-type">{prop_type}</div>
            </div>
            '''
            
            result = parser.parse_property(html)
            assert result.property_type == prop_type
    
    # Test Raw HTML Storage
    
    @pytest.mark.unit
    def test_store_raw_html(self, parser, sample_property_html):
        """Test storing raw HTML for future re-parsing."""
        property_id = "123456"
        timestamp = datetime.now()
        
        # Store the HTML
        stored_path = parser.store_raw_html(
            property_id=property_id,
            html=sample_property_html,
            timestamp=timestamp
        )
        
        assert stored_path is not None
        assert property_id in stored_path
        assert stored_path.endswith('.html')
        
        # Verify retrieval
        retrieved_html = parser.retrieve_raw_html(property_id, timestamp)
        assert retrieved_html == sample_property_html
    
    @pytest.mark.unit
    def test_store_raw_html_with_compression(self, parser):
        """Test storing raw HTML with compression."""
        large_html = "<div>" + "x" * 10000 + "</div>"
        property_id = "789012"
        
        stored_path = parser.store_raw_html(
            property_id=property_id,
            html=large_html,
            compress=True
        )
        
        assert stored_path.endswith('.html.gz')
        
        # Verify compressed file is smaller
        import os
        compressed_size = os.path.getsize(stored_path)
        assert compressed_size < len(large_html)
    
    # Test Batch Processing
    
    @pytest.mark.unit
    def test_batch_parse_properties(self, parser):
        """Test parsing multiple properties in batch."""
        html_list = [
            '''
            <div class="property-detail">
                <h1 class="property-address">
                    <span class="street-address">111 First St</span>
                    <span class="city-state-zip">Phoenix, AZ 85001</span>
                </h1>
                <div class="property-price">
                    <span class="price-value">$300,000</span>
                </div>
            </div>
            ''',
            '''
            <div class="property-detail">
                <h1 class="property-address">
                    <span class="street-address">222 Second Ave</span>
                    <span class="city-state-zip">Phoenix, AZ 85002</span>
                </h1>
                <div class="property-price">
                    <span class="price-value">$400,000</span>
                </div>
            </div>
            ''',
        ]
        
        results = parser.batch_parse_properties(html_list)
        
        assert len(results) == 2
        assert results[0].address == "111 First St, Phoenix, AZ 85001"
        assert results[0].price == 300000
        assert results[1].address == "222 Second Ave, Phoenix, AZ 85002"
        assert results[1].price == 400000
    
    # Test Performance and Memory
    
    @pytest.mark.unit
    def test_parse_large_html_performance(self, parser):
        """Test parsing performance with large HTML documents."""
        import time
        
        # Create a large HTML document with many properties
        large_html = '<div class="search-results">'
        for i in range(100):
            large_html += f'''
            <article class="property-card" data-listing-id="{i}">
                <h3 class="property-address">{i} Test St, Phoenix, AZ 85001</h3>
                <div class="property-price">${300000 + i * 1000}</div>
                <div class="property-info">
                    <span class="beds">3 bd</span>
                    <span class="baths">2 ba</span>
                    <span class="sqft">1,850 sqft</span>
                </div>
            </article>
            '''
        large_html += '</div>'
        
        start_time = time.time()
        results = parser.parse_search_results(large_html)
        end_time = time.time()
        
        assert len(results) == 100
        assert end_time - start_time < 1.0  # Should parse in under 1 second
    
    # Test Special Characters and Unicode
    
    @pytest.mark.unit
    def test_parse_unicode_addresses(self, parser):
        """Test parsing addresses with unicode characters."""
        html = '''
        <div class="property-detail">
            <h1 class="property-address">
                <span class="street-address">123 Cañón Road</span>
                <span class="city-state-zip">Phoenix, AZ 85001</span>
            </h1>
            <div class="property-price">
                <span class="price-value">$450,000</span>
            </div>
        </div>
        '''
        
        result = parser.parse_property(html)
        assert result.address == "123 Cañón Road, Phoenix, AZ 85001"
        assert result.street_address == "123 Cañón Road"
    
    @pytest.mark.unit
    def test_parse_special_characters_in_price(self, parser):
        """Test parsing prices with special characters and formats."""
        test_cases = [
            ("€450,000", None),  # Non-USD currency
            ("$450,000 USD", 450000),
            ("$450,000*", 450000),  # With asterisk
            ("~$450,000", 450000),  # Approximate
            ("$450,000 (reduced)", 450000),
        ]
        
        for price_text, expected in test_cases:
            html = f'<span class="price-value">{price_text}</span>'
            soup = BeautifulSoup(html, 'html.parser')
            price = parser.extract_price(soup)
            assert price == expected, f"Failed to parse price: {price_text}"


class TestPropertyData:
    """Test cases for the PropertyData model."""
    
    @pytest.mark.unit
    def test_property_data_creation(self):
        """Test creating PropertyData instances."""
        data = PropertyData(
            address="123 Main St, Phoenix, AZ 85001",
            price=450000,
            beds=3,
            baths=2.5,
            square_feet=1850,
            raw_html="<html>...</html>"
        )
        
        assert data.address == "123 Main St, Phoenix, AZ 85001"
        assert data.price == 450000
        assert data.beds == 3
        assert data.baths == 2.5
        assert data.square_feet == 1850
        assert data.raw_html == "<html>...</html>"
    
    @pytest.mark.unit
    def test_property_data_to_dict(self):
        """Test converting PropertyData to dictionary."""
        data = PropertyData(
            address="123 Main St, Phoenix, AZ 85001",
            street_address="123 Main St",
            city="Phoenix",
            state="AZ",
            zip_code="85001",
            price=450000,
            beds=3,
            baths=2.5,
            square_feet=1850,
            lot_size=7200,
            property_type="Single Family",
            year_built=2005,
            mls_number="123456",
            raw_html="<html>...</html>"
        )
        
        result = data.to_dict()
        
        assert isinstance(result, dict)
        assert result['address'] == "123 Main St, Phoenix, AZ 85001"
        assert result['price'] == 450000
        assert result['beds'] == 3
        assert result['baths'] == 2.5
        assert result['square_feet'] == 1850
        assert result['lot_size'] == 7200
        assert result['property_type'] == "Single Family"
        assert result['year_built'] == 2005
        assert result['mls_number'] == "123456"
        assert 'raw_html' in result
    
    @pytest.mark.unit
    def test_property_data_json_serialization(self):
        """Test JSON serialization of PropertyData."""
        import json
        
        data = PropertyData(
            address="123 Main St, Phoenix, AZ 85001",
            price=450000,
            beds=3,
            baths=2.5,
            raw_html="<html>...</html>"
        )
        
        json_str = data.to_json()
        assert isinstance(json_str, str)
        
        # Verify it can be deserialized
        parsed = json.loads(json_str)
        assert parsed['address'] == "123 Main St, Phoenix, AZ 85001"
        assert parsed['price'] == 450000
        assert parsed['beds'] == 3
        assert parsed['baths'] == 2.5


class TestParserIntegration:
    """Integration tests for the parser with external dependencies."""
    
    @pytest.mark.integration
    @patch('phoenix_real_estate.collectors.phoenix_mls.parser.aiohttp.ClientSession')
    async def test_parse_from_url(self, mock_session, parser, sample_property_html):
        """Test parsing property directly from URL."""
        mock_response = Mock()
        mock_response.text = Mock(return_value=sample_property_html)
        mock_response.status = 200
        
        mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = mock_response
        
        url = "https://www.phoenixmlssearch.com/property/123456"
        result = await parser.parse_from_url(url)
        
        assert result is not None
        assert result.address == "123 Main Street, Phoenix, AZ 85001"
        assert result.price == 450000
    
    @pytest.mark.integration
    def test_parser_with_database_storage(self, parser, sample_property_html):
        """Test parser integration with database storage."""
        from phoenix_real_estate.foundation.database import PropertyRepository
        
        # Parse property
        property_data = parser.parse_property(sample_property_html)
        
        # Convert to database model
        db_model = {
            'property_id': 'phoenix_mls_123456',
            'address': {
                'street': property_data.street_address,
                'city': property_data.city,
                'zip': property_data.zip_code
            },
            'prices': [{
                'date': datetime.now(),
                'amount': property_data.price,
                'source': 'phoenix_mls'
            }],
            'features': {
                'beds': property_data.beds,
                'baths': property_data.baths,
                'sqft': property_data.square_feet,
                'lot_size': property_data.lot_size
            },
            'listing_details': {
                'property_type': property_data.property_type,
                'year_built': property_data.year_built,
                'mls_number': property_data.mls_number
            },
            'last_updated': datetime.now()
        }
        
        # Verify structure matches schema
        assert 'property_id' in db_model
        assert 'address' in db_model
        assert 'prices' in db_model
        assert isinstance(db_model['prices'], list)
        assert 'features' in db_model
        assert 'listing_details' in db_model