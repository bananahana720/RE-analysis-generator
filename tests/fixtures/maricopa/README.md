# Maricopa County API Test Fixtures

This directory contains sample API response fixtures for testing the Maricopa County API client and adapter implementations.

## Files

### `search_response.json`
Sample response from the `/search/property` endpoint showing multiple property results with basic information.

**Usage**: Testing property search functionality, pagination, and result parsing.

### `parcel_details.json` 
Comprehensive parcel information response from the `/parcel/{apn}` endpoint including all property details, ownership, sales history, and permits.

**Usage**: Testing complete property data transformation and Epic 1 schema compliance.

### `valuations.json`
Historical valuation data from the `/parcel/{apn}/valuations` endpoint showing 5 years of assessment data.

**Usage**: Testing price history extraction and valuation trend analysis.

### `residential_details.json`
Detailed residential property characteristics from the `/parcel/{apn}/residential-details` endpoint.

**Usage**: Testing feature extraction and property characteristic mapping.

### `property_info.json`
Legal and administrative property information from the `/parcel/{apn}/propertyinfo` endpoint.

**Usage**: Testing legal description parsing, zoning information, and property metadata.

### `error_responses.json`
Sample error responses for various failure scenarios (401, 404, 429, 500, 503).

**Usage**: Testing error handling, retry logic, and graceful degradation.

## Usage in Tests

```python
import json
from pathlib import Path

# Load fixture data
fixtures_dir = Path(__file__).parent / "fixtures" / "maricopa"
with open(fixtures_dir / "parcel_details.json") as f:
    sample_data = json.load(f)

# Use in mock responses
mock_response.json = AsyncMock(return_value=sample_data)
```

## Data Structure Notes

These fixtures are based on the real Maricopa County API documentation and represent realistic response structures. They include:

- **Complete Data**: Full property records with all available fields
- **Realistic Values**: Actual Phoenix-area data patterns and ranges
- **Edge Cases**: Empty fields, missing sections, and various data formats
- **Error Conditions**: Standard HTTP error responses with proper formatting

## Field Mapping

The fixtures use field names that match the adapter's field mapping configuration:

- `address` → `situs_address` (real API structure)
- `characteristics` → `residential_details` (real API structure)  
- `assessment` → `valuation` (real API structure)
- `property_info` → top-level fields (real API structure)

## Maintenance

When updating the Maricopa client or adapter, ensure fixture data remains compatible with:

1. Real API response structures
2. Adapter field mappings
3. Epic 1 schema requirements
4. Test validation logic