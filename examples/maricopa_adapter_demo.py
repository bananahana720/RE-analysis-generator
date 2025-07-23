#!/usr/bin/env python3
"""Demonstration script for Maricopa Data Adapter.

Shows how the adapter transforms raw Maricopa API responses into Epic 1 Property objects.
This example demonstrates the complete schema mapping and transformation process.
"""

import asyncio
import json

from phoenix_real_estate.collectors.maricopa.adapter import MaricopaDataAdapter


async def main():
    """Demonstrate the Maricopa Data Adapter functionality."""

    # Create adapter instance
    adapter = MaricopaDataAdapter(logger_name="demo")

    # Sample raw data from Maricopa API (realistic structure)
    sample_raw_data = {
        "address": {
            "house_number": "1542",
            "street_name": "Desert Bloom",
            "street_type": "Trail",
            "unit": "Unit B",
            "city": "Phoenix",
            "state": "AZ",
            "zipcode": "85048-1234",
        },
        "characteristics": {
            "bedrooms": 4,
            "bathrooms": 3.5,
            "half_bathrooms": 1,
            "living_area_sqft": "2,850",
            "lot_size_sqft": "9,600",
            "year_built": 2005,
            "floors": 2.0,
            "garage_spaces": 3,
            "pool": "yes",
            "fireplace": "true",
            "ac_type": "Central Air",
            "heating_type": "Gas Forced Air",
        },
        "assessment": {
            "assessed_value": "425,000",
            "market_value": "$485,000",
            "land_value": "150000",
            "improvement_value": "335000.00",
            "tax_amount": "4,980.50",
            "tax_year": 2024,
        },
        "property_info": {
            "apn": "217-32-045B",
            "legal_description": "Lot 15 Block 8 Desert Estates Phase II",
            "property_type": "Single Family Residential",
            "subdivision": "Desert Estates",
        },
    }

    print("=== Maricopa Data Adapter Demonstration ===\n")

    print("1. Raw API Data Structure:")
    print(json.dumps(sample_raw_data, indent=2))
    print()

    try:
        # Transform raw data to Epic 1 Property schema
        print("2. Transforming to Epic 1 Property Schema...")
        property_obj = await adapter.adapt_property(sample_raw_data)
        print("SUCCESS: Transformation successful!")
        print()

        # Display key components of the transformed property
        print("3. Transformed Property Components:")
        print(f"   Property ID: {property_obj.property_id}")
        print()

        print("   Address:")
        print(f"     Street: {property_obj.address.street}")
        print(f"     City: {property_obj.address.city}, {property_obj.address.state}")
        print(f"     ZIP: {property_obj.address.zipcode}")
        print(f"     Full Address: {property_obj.address.full_address}")
        print()

        print("   Features:")
        print(f"     Bedrooms: {property_obj.features.bedrooms}")
        print(
            f"     Bathrooms: {property_obj.features.bathrooms} + {property_obj.features.half_bathrooms} half"
        )
        print(f"     Square Feet: {property_obj.features.square_feet:,}")
        print(f"     Lot Size: {property_obj.features.lot_size_sqft:,} sqft")
        print(f"     Year Built: {property_obj.features.year_built}")
        print(f"     Garage: {property_obj.features.garage_spaces} spaces")
        print(f"     Pool: {property_obj.features.pool}")
        print(f"     Fireplace: {property_obj.features.fireplace}")
        print(f"     HVAC: {property_obj.features.ac_type} / {property_obj.features.heating_type}")
        print()

        print("   Price History:")
        for i, price in enumerate(property_obj.price_history, 1):
            print(
                f"     {i}. {price.price_type}: ${price.amount:,.2f} (confidence: {price.confidence})"
            )
        print()

        if property_obj.tax_info:
            print("   Tax Information:")
            print(f"     APN: {property_obj.tax_info.apn}")
            print(f"     Assessed Value: ${property_obj.tax_info.assessed_value:,}")
            print(f"     Annual Tax: ${property_obj.tax_info.tax_amount_annual:,}")
            print(f"     Tax Year: {property_obj.tax_info.tax_year}")
            print()

        print("   Data Quality & Metadata:")
        if property_obj.sources:
            metadata = property_obj.sources[0]
            print(f"     Source: {metadata.source.value}")
            print(f"     Quality Score: {metadata.quality_score}")
            print(f"     Collection Time: {metadata.collected_at}")
            print(f"     Data Hash: {metadata.raw_data_hash[:16]}...")
        print()

        # Demonstrate schema validation
        print("4. Schema Validation:")
        is_valid = adapter.validator.validate_property(property_obj)
        print(f"   Epic 1 Schema Valid: {'PASS' if is_valid else 'FAIL'}")
        print()

        # Show safe conversion examples
        print("5. Safe Conversion Examples:")
        print("   Raw Data -> Converted Values")
        print(f"   '2,850' (string) -> {property_obj.features.square_feet} (int)")
        print(f"   '$485,000' (formatted) -> {property_obj.price_history[0].amount} (float)")
        print(f"   'yes' (string) -> {property_obj.features.pool} (bool)")
        print(f"   'true' (string) -> {property_obj.features.fireplace} (bool)")

        # Demonstrate address normalization
        print()
        print("6. Address Normalization:")
        print("   Components: '1542' + 'Desert Bloom' + 'Trail' + 'Unit B'")
        print(f"   Normalized: '{property_obj.address.street}'")
        print("   Epic 1 Utility: normalize_address() applied")

    except Exception as e:
        print(f"ERROR: Transformation failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
