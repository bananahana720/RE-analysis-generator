"""Data validation utilities for property data."""

from typing import Any, Dict, List, Tuple, Optional


class DataValidator:
    """Validates property data for consistency and completeness."""

    def validate_property_data(
        self, data: Dict[str, Any], source: Optional[str] = None
    ) -> Tuple[bool, List[str]]:
        """Validate property data structure and content.

        Args:
            data: Property data to validate
            source: Source of the data (e.g., 'phoenix_mls', 'maricopa_county')

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        # Check for required fields based on source
        if source == "phoenix_mls":
            required_fields = ["price", "bedrooms", "bathrooms", "address"]
            for field in required_fields:
                if field not in data or data[field] is None:
                    errors.append(f"Missing required field: {field}")

            # Validate address structure
            if "address" in data and isinstance(data["address"], dict):
                address_fields = ["street", "city", "state", "zip_code"]
                for field in address_fields:
                    if field not in data["address"] or not data["address"][field]:
                        errors.append(f"Missing address field: {field}")

        elif source == "maricopa_county":
            required_fields = ["parcel_number", "property_address"]
            for field in required_fields:
                if field not in data or data[field] is None:
                    errors.append(f"Missing required field: {field}")

        # Common validations
        if "price" in data and data["price"] is not None:
            if not isinstance(data["price"], (int, float)) or data["price"] < 0:
                errors.append("Price must be a positive number")

        if "bedrooms" in data and data["bedrooms"] is not None:
            if not isinstance(data["bedrooms"], int) or data["bedrooms"] < 0:
                errors.append("Bedrooms must be a non-negative integer")

        if "bathrooms" in data and data["bathrooms"] is not None:
            if not isinstance(data["bathrooms"], (int, float)) or data["bathrooms"] < 0:
                errors.append("Bathrooms must be a non-negative number")

        if "square_feet" in data and data["square_feet"] is not None:
            if not isinstance(data["square_feet"], (int, float)) or data["square_feet"] <= 0:
                errors.append("Square feet must be a positive number")

        if "year_built" in data and data["year_built"] is not None:
            if (
                not isinstance(data["year_built"], int)
                or data["year_built"] < 1800
                or data["year_built"] > 2100
            ):
                errors.append("Year built must be between 1800 and 2100")

        return (len(errors) == 0, errors)
