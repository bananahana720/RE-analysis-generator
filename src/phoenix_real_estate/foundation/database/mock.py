"""Mock database implementations for testing."""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from phoenix_real_estate.foundation.database.schema import (
    Property, DailyReport, PropertyPrice, PropertyType, ListingStatus, DataSource
)
from phoenix_real_estate.foundation.utils.exceptions import ValidationError


class MockPropertyRepository:
    """Mock property repository for testing.
    
    This mock implementation provides an in-memory storage for properties
    with all the same interfaces as the real PropertyRepository.
    """
    
    def __init__(self):
        """Initialize mock repository with empty storage."""
        self._properties: Dict[str, Property] = {}
        self._lock = asyncio.Lock()
    
    async def create(self, property_data: Dict[str, Any]) -> str:
        """Create a new property record.
        
        Args:
            property_data: Property data dictionary
            
        Returns:
            The property_id of created property
            
        Raises:
            ValidationError: If property already exists or data is invalid
        """
        async with self._lock:
            if "property_id" not in property_data:
                raise ValidationError("Missing required field: property_id")
            
            property_id = property_data["property_id"]
            
            if property_id in self._properties:
                raise ValidationError(f"Property with ID '{property_id}' already exists")
            
            # Create Property instance from dict
            property_obj = Property(**property_data)
            property_obj.last_updated = datetime.now()
            
            self._properties[property_id] = property_obj
            return property_id
    
    async def get_by_property_id(self, property_id: str) -> Optional[Dict[str, Any]]:
        """Get property by ID.
        
        Args:
            property_id: Property identifier
            
        Returns:
            Property data as dict or None
        """
        async with self._lock:
            if property_id in self._properties:
                prop = self._properties[property_id]
                return prop.model_dump(by_alias=True, exclude={'id'})
            return None
    
    async def update(self, property_id: str, updates: Dict[str, Any]) -> bool:
        """Update property data.
        
        Args:
            property_id: Property to update
            updates: Fields to update
            
        Returns:
            True if updated, False if not found
        """
        async with self._lock:
            if property_id not in self._properties:
                return False
            
            prop = self._properties[property_id]
            prop_dict = prop.model_dump()
            
            # Apply updates
            for key, value in updates.items():
                if key in prop_dict:
                    prop_dict[key] = value
            
            # Recreate property with updates
            prop_dict['last_updated'] = datetime.now()
            self._properties[property_id] = Property(**prop_dict)
            
            return True
    
    async def upsert(self, property_data: Dict[str, Any]) -> tuple[str, bool]:
        """Create or update property.
        
        Args:
            property_data: Property data to upsert
            
        Returns:
            Tuple of (property_id, was_created)
        """
        async with self._lock:
            if "property_id" not in property_data:
                raise ValidationError("Missing required field: property_id")
            
            property_id = property_data["property_id"]
            was_created = property_id not in self._properties
            
            property_obj = Property(**property_data)
            property_obj.last_updated = datetime.now()
            
            self._properties[property_id] = property_obj
            return property_id, was_created
    
    async def search_by_zipcode(
        self,
        zipcode: str,
        skip: int = 0,
        limit: int = 20,
        sort_by: str = "last_updated",
        sort_order: int = -1,
    ) -> tuple[List[Dict[str, Any]], int]:
        """Search properties by zipcode.
        
        Args:
            zipcode: ZIP code to search
            skip: Number to skip for pagination
            limit: Maximum results
            sort_by: Field to sort by
            sort_order: 1 for asc, -1 for desc
            
        Returns:
            Tuple of (properties list, total count)
        """
        async with self._lock:
            # Filter by zipcode
            matching = [
                prop for prop in self._properties.values()
                if prop.address.zipcode == zipcode and prop.is_active
            ]
            
            # Sort
            reverse = sort_order == -1
            if sort_by == "last_updated":
                matching.sort(key=lambda p: p.last_updated, reverse=reverse)
            elif sort_by == "current_price":
                matching.sort(key=lambda p: p.current_price or 0, reverse=reverse)
            
            # Paginate
            total = len(matching)
            paginated = matching[skip:skip + limit]
            
            # Convert to dicts
            results = [
                prop.model_dump(by_alias=True, exclude={'id'})
                for prop in paginated
            ]
            
            return results, total
    
    async def get_recent_updates(
        self, since: datetime, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get recently updated properties.
        
        Args:
            since: Timestamp to search from
            limit: Maximum results
            
        Returns:
            List of recently updated properties
        """
        async with self._lock:
            matching = [
                prop for prop in self._properties.values()
                if prop.last_updated >= since and prop.is_active
            ]
            
            # Sort by update time desc
            matching.sort(key=lambda p: p.last_updated, reverse=True)
            
            # Limit and convert
            results = [
                prop.model_dump(by_alias=True, exclude={'id'})
                for prop in matching[:limit]
            ]
            
            return results
    
    async def get_price_statistics(self, zipcode: str) -> Dict[str, Any]:
        """Get price statistics for zipcode.
        
        Args:
            zipcode: ZIP code to analyze
            
        Returns:
            Price statistics dictionary
        """
        async with self._lock:
            prices = [
                prop.current_price
                for prop in self._properties.values()
                if prop.address.zipcode == zipcode 
                and prop.is_active 
                and prop.current_price is not None
            ]
            
            if not prices:
                return {
                    "zipcode": zipcode,
                    "count": 0,
                    "avg_price": None,
                    "min_price": None,
                    "max_price": None,
                    "median_price": None,
                }
            
            sorted_prices = sorted(prices)
            count = len(prices)
            
            # Calculate median
            if count % 2 == 0:
                median = (sorted_prices[count // 2 - 1] + sorted_prices[count // 2]) / 2
            else:
                median = sorted_prices[count // 2]
            
            return {
                "zipcode": zipcode,
                "count": count,
                "avg_price": round(sum(prices) / count, 2),
                "min_price": min(prices),
                "max_price": max(prices),
                "median_price": median,
            }
    
    async def add_price_history(
        self, property_id: str, price: float, date: datetime, source: str
    ) -> bool:
        """Add price history entry.
        
        Args:
            property_id: Property to update
            price: New price
            date: Date of price
            source: Source of price
            
        Returns:
            True if added, False if property not found
        """
        async with self._lock:
            if property_id not in self._properties:
                return False
            
            prop = self._properties[property_id]
            
            # Create price entry
            price_entry = PropertyPrice(
                amount=price,
                date=date,
                price_type="listing",
                source=DataSource(source),
            )
            
            # Add to history
            prop.price_history.append(price_entry)
            prop.current_price = price
            prop.last_updated = datetime.now()
            
            return True


class MockDailyReportRepository:
    """Mock daily report repository for testing."""
    
    def __init__(self):
        """Initialize mock repository."""
        self._reports: Dict[str, DailyReport] = {}
        self._lock = asyncio.Lock()
    
    async def create_report(self, report_data: Dict[str, Any]) -> str:
        """Create or update daily report.
        
        Args:
            report_data: Report data dictionary
            
        Returns:
            Date string of report
        """
        async with self._lock:
            if "date" not in report_data:
                raise ValidationError("Missing required field: date")
            
            # Create report instance
            report = DailyReport(**report_data)
            report.last_updated = datetime.now()
            
            # Store by date string
            date_key = report.date.strftime("%Y-%m-%d")
            self._reports[date_key] = report
            
            return date_key
    
    async def get_recent_reports(
        self, days: int = 7, include_stats: bool = True
    ) -> List[Dict[str, Any]]:
        """Get recent reports.
        
        Args:
            days: Number of days to look back
            include_stats: Whether to include full stats
            
        Returns:
            List of recent reports
        """
        async with self._lock:
            cutoff = datetime.now() - timedelta(days=days)
            
            matching = [
                report for report in self._reports.values()
                if report.date >= cutoff
            ]
            
            # Sort by date desc
            matching.sort(key=lambda r: r.date, reverse=True)
            
            # Convert to dicts
            if include_stats:
                results = [
                    report.model_dump(by_alias=True, exclude={'id'})
                    for report in matching
                ]
            else:
                # Limited fields
                results = [
                    {
                        "date": report.date,
                        "properties_collected": report.total_properties_processed,
                        "properties_processed": report.properties_updated,
                        "errors": report.error_count,
                        "duration_seconds": report.collection_duration_seconds,
                    }
                    for report in matching
                ]
            
            return results


class MockDatabaseConnection:
    """Mock database connection for testing.
    
    This provides a mock implementation of the DatabaseConnection
    that uses in-memory storage instead of MongoDB.
    """
    
    def __init__(self, uri: str = "mock://localhost", database_name: str = "test"):
        """Initialize mock connection.
        
        Args:
            uri: Mock URI (ignored)
            database_name: Database name (for compatibility)
        """
        self.uri = uri
        self.database_name = database_name
        self._is_connected = False
        self._property_repo = MockPropertyRepository()
        self._report_repo = MockDailyReportRepository()
    
    async def connect(self) -> None:
        """Simulate connection."""
        await asyncio.sleep(0.01)  # Simulate connection time
        self._is_connected = True
    
    async def close(self) -> None:
        """Simulate disconnection."""
        self._is_connected = False
    
    async def health_check(self) -> Dict[str, Any]:
        """Simulate health check."""
        return {
            "connected": self._is_connected,
            "ping_time_ms": 5.0,
            "database_stats": {
                "collections": 2,
                "data_size": len(self._property_repo._properties) * 1000,
                "storage_size": len(self._property_repo._properties) * 1500,
                "indexes": 12,
            },
            "connection_pool": {
                "max_size": 10,
                "min_size": 1,
            },
            "timestamp": datetime.now().isoformat(),
        }
    
    @property
    def property_repository(self) -> MockPropertyRepository:
        """Get property repository."""
        return self._property_repo
    
    @property
    def report_repository(self) -> MockDailyReportRepository:
        """Get report repository."""
        return self._report_repo
    
    def __repr__(self) -> str:
        """String representation."""
        return f"MockDatabaseConnection(database='{self.database_name}', connected={self._is_connected})"


# Test data builders for convenience
class TestDataBuilder:
    """Helper class to build test data."""
    
    @staticmethod
    def build_property(
        property_id: str = "test_123_main_st_85001",
        street: str = "123 Main St",
        zipcode: str = "85001",
        price: float = 350000,
        bedrooms: int = 3,
        bathrooms: float = 2.0,
        square_feet: int = 1800,
    ) -> Dict[str, Any]:
        """Build a test property data dict."""
        return {
            "property_id": property_id,
            "address": {
                "street": street,
                "city": "Phoenix",
                "state": "AZ",
                "zipcode": zipcode,
            },
            "property_type": PropertyType.SINGLE_FAMILY.value,
            "features": {
                "bedrooms": bedrooms,
                "bathrooms": bathrooms,
                "square_feet": square_feet,
                "year_built": 2010,
            },
            "current_price": price,
            "listing": {
                "status": ListingStatus.ACTIVE.value,
                "listing_date": datetime.now(),
            },
            "sources": [
                {
                    "source": DataSource.PHOENIX_MLS.value,
                    "collected_at": datetime.now(),
                }
            ],
        }
    
    @staticmethod
    def build_daily_report(
        date: Optional[datetime] = None,
        total_processed: int = 100,
        new_found: int = 10,
        updated: int = 85,
    ) -> Dict[str, Any]:
        """Build a test daily report dict."""
        if date is None:
            date = datetime.now()
        
        return {
            "date": date,
            "total_properties_processed": total_processed,
            "new_properties_found": new_found,
            "properties_updated": updated,
            "properties_by_source": {
                DataSource.PHOENIX_MLS.value: 60,
                DataSource.MARICOPA_COUNTY.value: 40,
            },
            "properties_by_zipcode": {
                "85001": 25,
                "85003": 30,
                "85004": 45,
            },
            "price_statistics": {
                "min": 150000,
                "max": 1200000,
                "avg": 425000,
                "median": 380000,
            },
            "data_quality_score": 0.92,
            "error_count": 5,
            "warning_count": 12,
            "collection_duration_seconds": 3600,
            "api_requests_made": 1500,
        }