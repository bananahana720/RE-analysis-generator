"""Sample property data fixtures for E2E testing.

This module provides realistic test data samples for both Phoenix MLS HTML
and Maricopa County JSON formats.
"""

from typing import Dict, Any, List


class PropertySamples:
    """Collection of sample property data for testing."""
    
    @staticmethod
    def get_phoenix_mls_samples() -> List[Dict[str, Any]]:
        """Get sample Phoenix MLS HTML properties."""
        return [
            {
                "id": "MLS-001",
                "html": """
                <div class="property-listing">
                    <div class="property-header">
                        <h1 class="address">1234 N Central Ave, Phoenix, AZ 85031</h1>
                        <div class="price">$389,900</div>
                    </div>
                    <div class="property-details">
                        <div class="basic-info">
                            <span class="beds">3 beds</span>
                            <span class="baths">2.5 baths</span>
                            <span class="sqft">1,875 sq ft</span>
                            <span class="lot">6,200 sq ft lot</span>
                        </div>
                        <div class="additional-info">
                            <p><strong>MLS#:</strong> 6789012</p>
                            <p><strong>Year Built:</strong> 2016</p>
                            <p><strong>Property Type:</strong> Single Family Residence</p>
                            <p><strong>Status:</strong> Active</p>
                            <p><strong>Days on Market:</strong> 12</p>
                        </div>
                        <div class="description">
                            <p>Beautiful move-in ready home in the heart of Phoenix! This stunning 
                            3-bedroom, 2.5-bathroom home features an open floor plan with upgraded 
                            kitchen, granite countertops, and stainless steel appliances. The master 
                            suite includes a walk-in closet and luxurious bathroom. Backyard is 
                            perfect for entertaining with covered patio and low-maintenance landscaping.</p>
                        </div>
                    </div>
                </div>
                """,
                "expected": {
                    "address": "1234 N Central Ave",
                    "city": "Phoenix",
                    "state": "AZ",
                    "zip_code": "85031",
                    "price": 389900,
                    "bedrooms": 3,
                    "bathrooms": 2.5,
                    "square_feet": 1875,
                    "lot_size": 6200,
                    "year_built": 2016,
                    "property_type": "Single Family",
                    "mls_number": "6789012",
                    "listing_status": "Active"
                }
            },
            {
                "id": "MLS-002",
                "html": """
                <div class="listing-container">
                    <header>
                        <div class="listing-address">5678 W Camelback Rd Unit 203, Phoenix, AZ 85033</div>
                        <div class="listing-price">
                            <span class="currency">$</span>
                            <span class="amount">275,500</span>
                        </div>
                    </header>
                    <section class="property-features">
                        <ul>
                            <li>Bedrooms: 2</li>
                            <li>Bathrooms: 2</li>
                            <li>Square Feet: 1,125</li>
                            <li>Year Built: 2019</li>
                            <li>HOA: $250/month</li>
                        </ul>
                    </section>
                    <section class="listing-details">
                        <div class="mls-info">MLS Number: 6789013</div>
                        <div class="property-type">Condominium</div>
                        <div class="status">For Sale</div>
                    </section>
                    <section class="description">
                        Modern condo in prime location! Features include quartz countertops,
                        vinyl plank flooring, in-unit washer/dryer, and private balcony.
                        Community amenities include pool, fitness center, and BBQ area.
                    </section>
                </div>
                """,
                "expected": {
                    "address": "5678 W Camelback Rd Unit 203",
                    "city": "Phoenix",
                    "state": "AZ",
                    "zip_code": "85033",
                    "price": 275500,
                    "bedrooms": 2,
                    "bathrooms": 2.0,
                    "square_feet": 1125,
                    "year_built": 2019,
                    "property_type": "Condo",
                    "mls_number": "6789013",
                    "listing_status": "For Sale"
                }
            },
            {
                "id": "MLS-003",
                "html": """
                <article class="property">
                    <h2>9101 S 7th St, Phoenix, AZ 85035</h2>
                    <div class="pricing">
                        <span class="label">List Price:</span>
                        <span class="value">$525,000</span>
                    </div>
                    <div class="specs">
                        <div class="spec-item">4 BR</div>
                        <div class="spec-item">3 BA</div>
                        <div class="spec-item">2,450 SqFt</div>
                        <div class="spec-item">8,500 SqFt Lot</div>
                    </div>
                    <dl class="property-metadata">
                        <dt>MLS ID:</dt><dd>6789014</dd>
                        <dt>Built:</dt><dd>2021</dd>
                        <dt>Type:</dt><dd>Single Family Home</dd>
                        <dt>Status:</dt><dd>Pending</dd>
                        <dt>DOM:</dt><dd>5 days</dd>
                    </dl>
                    <p class="remarks">
                        Gorgeous new construction! This 4-bedroom home features a gourmet kitchen,
                        spacious great room, and luxurious master suite. Energy-efficient design
                        with solar panels and smart home technology throughout. Three-car garage
                        and professionally landscaped yard complete this amazing property.
                    </p>
                </article>
                """,
                "expected": {
                    "address": "9101 S 7th St",
                    "city": "Phoenix",
                    "state": "AZ",
                    "zip_code": "85035",
                    "price": 525000,
                    "bedrooms": 4,
                    "bathrooms": 3.0,
                    "square_feet": 2450,
                    "lot_size": 8500,
                    "year_built": 2021,
                    "property_type": "Single Family",
                    "mls_number": "6789014",
                    "listing_status": "Pending"
                }
            }
        ]
    
    @staticmethod
    def get_maricopa_samples() -> List[Dict[str, Any]]:
        """Get sample Maricopa County JSON properties."""
        return [
            {
                "id": "MC-001",
                "json": {
                    "parcel_number": "123-45-678A",
                    "property_address": {
                        "address": "1234 N Central Ave",
                        "city": "Phoenix",
                        "state": "AZ",
                        "zip": "85031"
                    },
                    "owner_info": {
                        "name": "SMITH JOHN & JANE",
                        "mailing_address": "1234 N Central Ave, Phoenix, AZ 85031"
                    },
                    "property_details": {
                        "land_use": "SINGLE FAMILY RESIDENTIAL",
                        "year_built": 2016,
                        "living_area": 1875,
                        "lot_size": 6200,
                        "bedrooms": 3,
                        "bathrooms": 2.5,
                        "stories": 1,
                        "construction_type": "FRAME/STUCCO",
                        "roof_type": "TILE"
                    },
                    "valuation": {
                        "market_value": 389900,
                        "assessed_value": 350910,
                        "tax_year": 2024,
                        "limited_value": 325000,
                        "land_value": 125000,
                        "improvement_value": 264900
                    },
                    "legal_description": "LOT 123 PHOENIX SUBDIVISION PHASE 2",
                    "tax_info": {
                        "tax_rate": 0.0125,
                        "annual_tax": 4875.50,
                        "exemptions": ["PRIMARY_RESIDENCE"]
                    }
                },
                "expected": {
                    "parcel_number": "123-45-678A",
                    "address": "1234 N Central Ave",
                    "city": "Phoenix",
                    "state": "AZ",
                    "zip_code": "85031",
                    "owner_name": "SMITH JOHN & JANE",
                    "price": 389900,
                    "bedrooms": 3,
                    "bathrooms": 2.5,
                    "square_feet": 1875,
                    "lot_size": 6200,
                    "year_built": 2016,
                    "property_type": "Single Family"
                }
            },
            {
                "id": "MC-002",
                "json": {
                    "parcel_number": "234-56-789B",
                    "property_address": {
                        "address": "5678 W Camelback Rd Unit 203",
                        "city": "Phoenix",
                        "state": "AZ",
                        "zip": "85033"
                    },
                    "owner_info": {
                        "name": "JOHNSON ROBERT M",
                        "mailing_address": "PO Box 12345, Phoenix, AZ 85001"
                    },
                    "property_details": {
                        "land_use": "CONDOMINIUM",
                        "year_built": 2019,
                        "living_area": 1125,
                        "bedrooms": 2,
                        "bathrooms": 2,
                        "stories": 1,
                        "construction_type": "CONCRETE/STEEL",
                        "unit_number": "203",
                        "building_name": "CAMELBACK CONDOS"
                    },
                    "valuation": {
                        "market_value": 275500,
                        "assessed_value": 247950,
                        "tax_year": 2024,
                        "limited_value": 240000,
                        "land_value": 0,
                        "improvement_value": 275500
                    },
                    "hoa_info": {
                        "fee": 250,
                        "frequency": "MONTHLY",
                        "includes": ["POOL", "FITNESS", "COMMON_AREA_MAINT"]
                    }
                },
                "expected": {
                    "parcel_number": "234-56-789B",
                    "address": "5678 W Camelback Rd Unit 203",
                    "city": "Phoenix",
                    "state": "AZ",
                    "zip_code": "85033",
                    "owner_name": "JOHNSON ROBERT M",
                    "price": 275500,
                    "bedrooms": 2,
                    "bathrooms": 2.0,
                    "square_feet": 1125,
                    "year_built": 2019,
                    "property_type": "Condo"
                }
            },
            {
                "id": "MC-003",
                "json": {
                    "parcel_number": "345-67-890C",
                    "property_address": {
                        "address": "9101 S 7th St",
                        "city": "Phoenix",
                        "state": "AZ",
                        "zip": "85035"
                    },
                    "owner_info": {
                        "name": "WILLIAMS FAMILY TRUST",
                        "mailing_address": "9101 S 7th St, Phoenix, AZ 85035",
                        "ownership_type": "TRUST"
                    },
                    "property_details": {
                        "land_use": "SINGLE FAMILY RESIDENTIAL",
                        "year_built": 2021,
                        "living_area": 2450,
                        "lot_size": 8500,
                        "bedrooms": 4,
                        "bathrooms": 3,
                        "stories": 2,
                        "construction_type": "FRAME/STUCCO",
                        "roof_type": "TILE",
                        "garage_spaces": 3,
                        "pool": true,
                        "solar_panels": true
                    },
                    "valuation": {
                        "market_value": 525000,
                        "assessed_value": 472500,
                        "tax_year": 2024,
                        "limited_value": 450000,
                        "land_value": 175000,
                        "improvement_value": 350000
                    },
                    "improvements": [
                        {
                            "type": "POOL",
                            "year": 2021,
                            "value": 35000
                        },
                        {
                            "type": "SOLAR_SYSTEM",
                            "year": 2021,
                            "value": 25000
                        }
                    ]
                },
                "expected": {
                    "parcel_number": "345-67-890C",
                    "address": "9101 S 7th St",
                    "city": "Phoenix",
                    "state": "AZ",
                    "zip_code": "85035",
                    "owner_name": "WILLIAMS FAMILY TRUST",
                    "price": 525000,
                    "bedrooms": 4,
                    "bathrooms": 3.0,
                    "square_feet": 2450,
                    "lot_size": 8500,
                    "year_built": 2021,
                    "property_type": "Single Family"
                }
            }
        ]
    
    @staticmethod
    def get_edge_case_samples() -> List[Dict[str, Any]]:
        """Get edge case samples for robust testing."""
        return [
            {
                "id": "EDGE-001",
                "description": "Missing price information",
                "html": """
                <div class="property">
                    <h1>123 No Price Rd, Phoenix, AZ 85031</h1>
                    <div class="details">
                        <span>3 beds</span>
                        <span>2 baths</span>
                        <span>1,500 sq ft</span>
                    </div>
                    <p>MLS: 9999001</p>
                    <p>Price: Call for pricing</p>
                </div>
                """,
                "expected_behavior": "Should extract without price or set price to null/0"
            },
            {
                "id": "EDGE-002",
                "description": "Fractional bathrooms",
                "html": """
                <div class="listing">
                    <h2>456 Fraction Ave, Phoenix, AZ 85033</h2>
                    <p>$299,999</p>
                    <ul>
                        <li>Bedrooms: 4</li>
                        <li>Bathrooms: 2 full, 1 half</li>
                        <li>Size: 2,100 sq ft</li>
                    </ul>
                </div>
                """,
                "expected_behavior": "Should interpret as 2.5 bathrooms"
            },
            {
                "id": "EDGE-003",
                "description": "Price range instead of single price",
                "json": {
                    "parcel_number": "999-88-777",
                    "property_address": {
                        "address": "789 Range St",
                        "city": "Phoenix",
                        "zip": "85035"
                    },
                    "valuation": {
                        "market_value_min": 400000,
                        "market_value_max": 450000,
                        "estimated_value": 425000
                    },
                    "property_details": {
                        "bedrooms": 3,
                        "bathrooms": 2,
                        "living_area": 1800
                    }
                },
                "expected_behavior": "Should use estimated_value or average of range"
            },
            {
                "id": "EDGE-004",
                "description": "Unusual property type",
                "html": """
                <div class="property-card">
                    <h3>101 Mobile Home Park Space 42, Phoenix, AZ 85031</h3>
                    <p class="price">$85,000</p>
                    <p class="type">Manufactured/Mobile Home</p>
                    <p>2 beds, 1 bath, 980 sq ft</p>
                    <p>Year: 1995</p>
                    <p>MLS: 9999004</p>
                </div>
                """,
                "expected_behavior": "Should map to 'manufactured' property type"
            },
            {
                "id": "EDGE-005",
                "description": "HTML with special characters and encoding",
                "html": """
                <div class="listing">
                    <h1>123 Niño St, Phoenix, AZ 85033</h1>
                    <p>Price: $350,000 &mdash; Recently Reduced!</p>
                    <p>3 beds &bull; 2 baths &bull; 1,750 sq&nbsp;ft</p>
                    <p>MLS&reg; #9999005</p>
                    <p>Owner&apos;s notes: &quot;Must see!&quot;</p>
                </div>
                """,
                "expected_behavior": "Should handle special characters and HTML entities correctly"
            }
        ]
    
    @staticmethod
    def get_invalid_samples() -> List[Dict[str, Any]]:
        """Get invalid samples that should fail validation."""
        return [
            {
                "id": "INVALID-001",
                "description": "Completely empty HTML",
                "html": "<div></div>",
                "expected_error": "No property data found"
            },
            {
                "id": "INVALID-002",
                "description": "Non-property HTML content",
                "html": """
                <div class="navigation">
                    <a href="/home">Home</a>
                    <a href="/search">Search</a>
                    <a href="/contact">Contact Us</a>
                </div>
                """,
                "expected_error": "No property information extracted"
            },
            {
                "id": "INVALID-003",
                "description": "Malformed JSON",
                "json": '{"property": "incomplete json',
                "expected_error": "Invalid JSON format"
            },
            {
                "id": "INVALID-004",
                "description": "Wrong data structure",
                "json": {
                    "users": [
                        {"name": "John", "email": "john@example.com"},
                        {"name": "Jane", "email": "jane@example.com"}
                    ]
                },
                "expected_error": "Not a property data structure"
            }
        ]