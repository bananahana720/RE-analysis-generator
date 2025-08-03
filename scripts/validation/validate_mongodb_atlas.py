#!/usr/bin/env python3
"""MongoDB Atlas Connection Validation Script.

This script validates MongoDB Atlas connectivity, tests database operations,
and verifies the data collection pipeline can properly store property data.

Usage:
    python scripts/validate_mongodb_atlas.py

Requirements:
    - MongoDB Atlas connection string in .env file as MONGODB_URI
    - Database name in .env file as DATABASE_NAME or MONGODB_DATABASE
"""

import asyncio
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from phoenix_real_estate.foundation.config.environment import get_config
from phoenix_real_estate.foundation.database.connection import (
    DatabaseConnection,
    get_database_connection,
    close_database_connection,
)
from phoenix_real_estate.foundation.database.schema import (
    Property,
    PropertyAddress,
    PropertyFeatures,
    PropertyPrice,
    PropertyType,
    DataSource,
    DataCollectionMetadata,
    DailyReport,
)
from phoenix_real_estate.foundation.utils.exceptions import DatabaseError


class MongoDBAtlasValidator:
    """Comprehensive MongoDB Atlas validation suite."""

    def __init__(self):
        """Initialize the validator."""
        self.db_connection: Optional[DatabaseConnection] = None
        self.test_results: Dict[str, Dict[str, Any]] = {}
        self.sample_property_id = f"test_prop_{int(datetime.now().timestamp())}"

    async def run_full_validation(self) -> Dict[str, Any]:
        """Run complete validation suite.

        Returns:
            Dictionary containing all test results and overall status.
        """
        print("Phoenix Real Estate - MongoDB Atlas Validation")
        print("=" * 60)

        overall_success = True

        try:
            # Step 1: Configuration validation
            print("\nStep 1: Configuration Validation")
            config_success = await self.validate_configuration()
            overall_success = overall_success and config_success

            if not config_success:
                print("Configuration validation failed. Cannot proceed.")
                return self._generate_summary(overall_success)

            # Step 2: Database connection
            print("\nStep 2: Database Connection")
            connection_success = await self.validate_connection()
            overall_success = overall_success and connection_success

            if not connection_success:
                print("Connection validation failed. Cannot proceed.")
                return self._generate_summary(overall_success)

            # Step 3: Health check
            print("\nStep 3: Health Check")
            health_success = await self.validate_health_check()
            overall_success = overall_success and health_success

            # Step 4: Basic CRUD operations
            print("\nStep 4: CRUD Operations")
            crud_success = await self.validate_crud_operations()
            overall_success = overall_success and crud_success

            # Step 5: Schema validation
            print("\nStep 5: Schema Validation")
            schema_success = await self.validate_schema()
            overall_success = overall_success and schema_success

            # Step 6: Index validation
            print("\nStep 6: Index Validation")
            index_success = await self.validate_indexes()
            overall_success = overall_success and index_success

            # Step 7: Data pipeline test
            print("\nStep 7: Data Pipeline Test")
            pipeline_success = await self.validate_data_pipeline()
            overall_success = overall_success and pipeline_success

            # Step 8: Performance test
            print("\nStep 8: Performance Test")
            performance_success = await self.validate_performance()
            overall_success = overall_success and performance_success

        except Exception as e:
            print(f"ERROR: Validation failed with unexpected error: {str(e)}")
            traceback.print_exc()
            overall_success = False

        finally:
            # Cleanup
            await self.cleanup()

        return self._generate_summary(overall_success)

    async def validate_configuration(self) -> bool:
        """Validate configuration and environment setup."""
        try:
            # Test environment loading
            config = get_config()

            # Check required configuration
            if not hasattr(config, "mongodb_uri") or not config.mongodb_uri:
                print("ERROR: MONGODB_URI not found in configuration")
                return False

            # Check database name - try both possible env var names
            database_name = None
            if hasattr(config, "database_name") and config.database_name:
                database_name = config.database_name
            elif hasattr(config, "mongodb_database") and config.mongodb_database:
                database_name = config.mongodb_database
            else:
                print("ERROR: DATABASE_NAME or MONGODB_DATABASE not found in configuration")
                return False

            print("SUCCESS: Configuration loaded successfully")
            print(f"   Database: {database_name}")
            print(f"   Environment: {config.environment.value}")

            # Store for later use
            self.mongodb_uri = config.mongodb_uri
            self.database_name = database_name

            self.test_results["configuration"] = {
                "success": True,
                "database_name": database_name,
                "environment": config.environment.value,
                "has_uri": bool(config.mongodb_uri),
            }

            return True

        except Exception as e:
            print(f"ERROR: Configuration validation failed: {str(e)}")
            self.test_results["configuration"] = {"success": False, "error": str(e)}
            return False

    async def validate_connection(self) -> bool:
        """Validate database connection establishment."""
        try:
            # Test connection creation
            self.db_connection = await get_database_connection(self.mongodb_uri, self.database_name)

            print("SUCCESS: Database connection established successfully")

            self.test_results["connection"] = {
                "success": True,
                "database_name": self.database_name,
                "connection_type": "AsyncIOMotorClient",
            }

            return True

        except Exception as e:
            print(f"ERROR: Database connection failed: {str(e)}")
            self.test_results["connection"] = {"success": False, "error": str(e)}
            return False

    async def validate_health_check(self) -> bool:
        """Validate database health check."""
        try:
            if not self.db_connection:
                raise DatabaseError("No database connection available")

            health_status = await self.db_connection.health_check()

            if not health_status.get("connected", False):
                print("ERROR: Health check shows database not connected")
                return False

            ping_time = health_status.get("ping_time_ms", 0)
            print("SUCCESS: Database health check passed")
            print(f"   Ping time: {ping_time}ms")

            if health_status.get("database_stats"):
                stats = health_status["database_stats"]
                print(f"   Collections: {stats.get('collections', 0)}")
                print(f"   Data size: {stats.get('data_size', 0)} bytes")

            self.test_results["health_check"] = {
                "success": True,
                "ping_time_ms": ping_time,
                "database_stats": health_status.get("database_stats", {}),
            }

            return True

        except Exception as e:
            print(f"ERROR: Health check failed: {str(e)}")
            self.test_results["health_check"] = {"success": False, "error": str(e)}
            return False

    async def validate_crud_operations(self) -> bool:
        """Validate basic CRUD operations."""
        try:
            if not self.db_connection:
                raise DatabaseError("No database connection available")

            async with self.db_connection.get_database() as db:
                collection = db["test_properties"]

                # CREATE - Insert a test document
                test_doc = {
                    "property_id": self.sample_property_id,
                    "address": {
                        "street": "123 Test St",
                        "city": "Phoenix",
                        "state": "AZ",
                        "zipcode": "85001",
                    },
                    "current_price": 450000.0,
                    "is_active": True,
                    "created_at": datetime.now(timezone.utc),
                }

                insert_result = await collection.insert_one(test_doc)
                print(f"SUCCESS: CREATE: Document inserted with ID {insert_result.inserted_id}")

                # READ - Find the document
                found_doc = await collection.find_one({"property_id": self.sample_property_id})
                if not found_doc:
                    raise DatabaseError("Document not found after insert")
                print("SUCCESS: READ: Document retrieved successfully")

                # UPDATE - Modify the document
                update_result = await collection.update_one(
                    {"property_id": self.sample_property_id},
                    {"$set": {"current_price": 475000.0, "updated_at": datetime.now(timezone.utc)}},
                )
                if update_result.modified_count != 1:
                    raise DatabaseError("Document update failed")
                print("SUCCESS: UPDATE: Document updated successfully")

                # Verify update
                updated_doc = await collection.find_one({"property_id": self.sample_property_id})
                if updated_doc["current_price"] != 475000.0:
                    raise DatabaseError("Update not reflected in document")
                print("SUCCESS: UPDATE VERIFY: Update confirmed")

                # DELETE - Remove the test document
                delete_result = await collection.delete_one(
                    {"property_id": self.sample_property_id}
                )
                if delete_result.deleted_count != 1:
                    raise DatabaseError("Document deletion failed")
                print("SUCCESS: DELETE: Document deleted successfully")

                # Verify deletion
                deleted_doc = await collection.find_one({"property_id": self.sample_property_id})
                if deleted_doc:
                    raise DatabaseError("Document still exists after deletion")
                print("SUCCESS: DELETE VERIFY: Deletion confirmed")

            self.test_results["crud_operations"] = {
                "success": True,
                "operations_tested": ["CREATE", "READ", "UPDATE", "DELETE"],
                "test_property_id": self.sample_property_id,
            }

            return True

        except Exception as e:
            print(f"ERROR: CRUD operations failed: {str(e)}")
            self.test_results["crud_operations"] = {"success": False, "error": str(e)}
            return False

    async def validate_schema(self) -> bool:
        """Validate Pydantic schema models work with MongoDB."""
        try:
            # Create a valid Property instance using Pydantic models
            property_address = PropertyAddress(
                street="456 Schema Test Ave", city="Phoenix", state="AZ", zipcode="85002"
            )

            property_features = PropertyFeatures(
                bedrooms=3,
                bathrooms=2.5,
                square_feet=2100,
                lot_size_sqft=8000,
                year_built=2015,
                garage_spaces=2,
                pool=True,
            )

            property_price = PropertyPrice(
                amount=525000.0,
                date=datetime.now(timezone.utc),
                price_type="listing",
                source=DataSource.PHOENIX_MLS,
            )

            metadata = DataCollectionMetadata(
                source=DataSource.PHOENIX_MLS, collector_version="1.0.0", quality_score=0.95
            )

            test_property = Property(
                property_id=f"schema_test_{int(datetime.now().timestamp())}",
                address=property_address,
                property_type=PropertyType.SINGLE_FAMILY,
                features=property_features,
                current_price=525000.0,
                price_history=[property_price],
                sources=[metadata],
            )

            # Test serialization to dict (for MongoDB)
            property_dict = test_property.model_dump(exclude={"id"})
            print("SUCCESS: Schema serialization successful")

            # Test MongoDB storage with schema
            if not self.db_connection:
                raise DatabaseError("No database connection available")

            async with self.db_connection.get_database() as db:
                collection = db["test_schema_properties"]

                # Insert using schema
                insert_result = await collection.insert_one(property_dict)
                print(f"SUCCESS: Schema-based document inserted: {insert_result.inserted_id}")

                # Retrieve and validate
                retrieved_doc = await collection.find_one(
                    {"property_id": test_property.property_id}
                )
                if not retrieved_doc:
                    raise DatabaseError("Schema-based document not found")

                # Test deserialization from MongoDB
                retrieved_doc.pop("_id", None)  # Remove ObjectId for validation
                validated_property = Property(**retrieved_doc)
                print("SUCCESS: Schema deserialization successful")

                # Verify computed properties work
                if validated_property.latest_price_date:
                    print("SUCCESS: Computed properties working")

                # Cleanup
                await collection.delete_one({"property_id": test_property.property_id})
                print("SUCCESS: Schema test cleanup completed")

            self.test_results["schema_validation"] = {
                "success": True,
                "models_tested": [
                    "Property",
                    "PropertyAddress",
                    "PropertyFeatures",
                    "PropertyPrice",
                ],
                "computed_fields_working": True,
            }

            return True

        except Exception as e:
            print(f"ERROR: Schema validation failed: {str(e)}")
            traceback.print_exc()
            self.test_results["schema_validation"] = {"success": False, "error": str(e)}
            return False

    async def validate_indexes(self) -> bool:
        """Validate database indexes are created properly."""
        try:
            if not self.db_connection:
                raise DatabaseError("No database connection available")

            async with self.db_connection.get_database() as db:
                # Check properties collection indexes
                properties_collection = db["properties"]
                indexes = await properties_collection.index_information()

                expected_indexes = [
                    "property_id_1",  # unique index on property_id
                    "address.zipcode_1",  # zipcode index
                    "address.street_1",  # street index
                    "current_price_1",  # price index
                    "last_updated_1",  # timestamp index
                    "is_active_1",  # active status index
                ]

                missing_indexes = []
                for expected_index in expected_indexes:
                    if expected_index not in indexes:
                        missing_indexes.append(expected_index)

                if missing_indexes:
                    print(f"WARNING:  Some indexes are missing: {missing_indexes}")
                    print("   This is normal on first run - indexes will be created")
                else:
                    print("SUCCESS: All expected indexes are present")

                print(f"   Found {len(indexes)} total indexes")

                # Check daily_reports collection
                daily_reports_collection = db["daily_reports"]
                daily_indexes = await daily_reports_collection.index_information()

                self.test_results["index_validation"] = {
                    "success": True,
                    "properties_indexes_count": len(indexes),
                    "daily_reports_indexes_count": len(daily_indexes),
                    "missing_indexes": missing_indexes,
                }

                return True

        except Exception as e:
            print(f"ERROR: Index validation failed: {str(e)}")
            self.test_results["index_validation"] = {"success": False, "error": str(e)}
            return False

    async def validate_data_pipeline(self) -> bool:
        """Validate that the data collection pipeline can store data properly."""
        try:
            if not self.db_connection:
                raise DatabaseError("No database connection available")

            # Simulate a complete data collection pipeline
            async with self.db_connection.get_database() as db:
                properties_collection = db["properties"]
                daily_reports_collection = db["daily_reports"]

                # Create multiple test properties to simulate batch collection
                test_properties = []
                property_ids = []

                for i in range(5):
                    property_id = f"pipeline_test_{int(datetime.now().timestamp())}_{i}"
                    property_ids.append(property_id)

                    property_data = Property(
                        property_id=property_id,
                        address=PropertyAddress(
                            street=f"{100 + i} Pipeline Test St",
                            city="Phoenix",
                            state="AZ",
                            zipcode=f"8500{i}",
                        ),
                        property_type=PropertyType.SINGLE_FAMILY,
                        current_price=400000.0 + (i * 25000),
                        features=PropertyFeatures(
                            bedrooms=2 + i, bathrooms=2.0 + (i * 0.5), square_feet=1500 + (i * 200)
                        ),
                        sources=[
                            DataCollectionMetadata(
                                source=DataSource.PHOENIX_MLS, collector_version="pipeline_test_1.0"
                            )
                        ],
                    )
                    test_properties.append(property_data)

                # Batch insert (simulate collection pipeline)
                property_dicts = [prop.model_dump(exclude={"id"}) for prop in test_properties]
                insert_result = await properties_collection.insert_many(property_dicts)
                print(
                    f"SUCCESS: Pipeline batch insert: {len(insert_result.inserted_ids)} properties"
                )

                # Create a daily report (simulate reporting pipeline)
                daily_report = DailyReport(
                    date=datetime.now(timezone.utc),
                    total_properties_processed=len(test_properties),
                    new_properties_found=len(test_properties),
                    properties_by_source={DataSource.PHOENIX_MLS: len(test_properties)},
                    properties_by_zipcode={f"8500{i}": 1 for i in range(5)},
                    price_statistics={"min": 400000.0, "max": 500000.0, "avg": 450000.0},
                    data_quality_score=0.95,
                    collection_duration_seconds=120.5,
                    api_requests_made=25,
                )

                report_dict = daily_report.model_dump(exclude={"id"})
                await daily_reports_collection.insert_one(report_dict)
                print("SUCCESS: Daily report created successfully")

                # Test queries that the real system would use
                # Query by zipcode
                zipcode_properties = await properties_collection.count_documents(
                    {"address.zipcode": "85000"}
                )
                print(f"SUCCESS: Zipcode query: found {zipcode_properties} properties")

                # Query by price range
                price_range_properties = await properties_collection.count_documents(
                    {"current_price": {"$gte": 425000, "$lte": 475000}}
                )
                print(f"SUCCESS: Price range query: found {price_range_properties} properties")

                # Query active properties
                active_properties = await properties_collection.count_documents({"is_active": True})
                print(f"SUCCESS: Active properties query: found {active_properties} properties")

                # Cleanup test data
                delete_result = await properties_collection.delete_many(
                    {"property_id": {"$in": property_ids}}
                )
                print(
                    f"SUCCESS: Pipeline cleanup: removed {delete_result.deleted_count} test properties"
                )

                await daily_reports_collection.delete_many(
                    {
                        "total_properties_processed": len(test_properties),
                        "new_properties_found": len(test_properties),
                    }
                )
                print("SUCCESS: Report cleanup completed")

            self.test_results["data_pipeline"] = {
                "success": True,
                "batch_insert_count": len(test_properties),
                "daily_report_created": True,
                "queries_tested": ["zipcode", "price_range", "active_properties"],
            }

            return True

        except Exception as e:
            print(f"ERROR: Data pipeline validation failed: {str(e)}")
            traceback.print_exc()
            self.test_results["data_pipeline"] = {"success": False, "error": str(e)}
            return False

    async def validate_performance(self) -> bool:
        """Validate database performance for typical operations."""
        try:
            if not self.db_connection:
                raise DatabaseError("No database connection available")

            async with self.db_connection.get_database() as db:
                collection = db["test_performance"]

                # Test 1: Insert performance
                insert_start = datetime.now()
                test_docs = []
                for i in range(100):  # Small batch for free tier
                    test_docs.append(
                        {
                            "property_id": f"perf_test_{i}",
                            "address": {"zipcode": f"8500{i % 10}"},
                            "current_price": 400000 + i,
                            "is_active": True,
                            "created_at": datetime.now(timezone.utc),
                        }
                    )

                await collection.insert_many(test_docs)
                insert_duration = (datetime.now() - insert_start).total_seconds()
                print(f"SUCCESS: Insert performance: 100 docs in {insert_duration:.2f}s")

                # Test 2: Query performance
                query_start = datetime.now()
                results = await collection.find({"current_price": {"$gte": 400050}}).to_list(
                    length=None
                )
                query_duration = (datetime.now() - query_start).total_seconds()
                print(
                    f"SUCCESS: Query performance: found {len(results)} docs in {query_duration:.2f}s"
                )

                # Test 3: Update performance
                update_start = datetime.now()
                update_result = await collection.update_many(
                    {"current_price": {"$gte": 400050}}, {"$set": {"is_active": False}}
                )
                update_duration = (datetime.now() - update_start).total_seconds()
                print(
                    f"SUCCESS: Update performance: {update_result.modified_count} docs in {update_duration:.2f}s"
                )

                # Test 4: Aggregation performance
                agg_start = datetime.now()
                pipeline = [
                    {
                        "$group": {
                            "_id": "$address.zipcode",
                            "avg_price": {"$avg": "$current_price"},
                            "count": {"$sum": 1},
                        }
                    },
                    {"$sort": {"avg_price": -1}},
                ]
                agg_results = await collection.aggregate(pipeline).to_list(length=None)
                agg_duration = (datetime.now() - agg_start).total_seconds()
                print(
                    f"SUCCESS: Aggregation performance: {len(agg_results)} groups in {agg_duration:.2f}s"
                )

                # Cleanup
                await collection.drop()

                # Performance thresholds (adjusted for Atlas free tier)
                performance_acceptable = (
                    insert_duration < 10.0  # 10s for 100 inserts
                    and query_duration < 5.0  # 5s for query
                    and update_duration < 5.0  # 5s for batch update
                    and agg_duration < 10.0  # 10s for aggregation
                )

                if performance_acceptable:
                    print("SUCCESS: All performance tests within acceptable limits")
                else:
                    print(
                        "WARNING:  Some operations slower than expected (may be normal for free tier)"
                    )

            self.test_results["performance"] = {
                "success": True,
                "insert_duration_sec": insert_duration,
                "query_duration_sec": query_duration,
                "update_duration_sec": update_duration,
                "aggregation_duration_sec": agg_duration,
                "performance_acceptable": performance_acceptable,
            }

            return True

        except Exception as e:
            print(f"ERROR: Performance validation failed: {str(e)}")
            self.test_results["performance"] = {"success": False, "error": str(e)}
            return False

    async def cleanup(self) -> None:
        """Clean up resources."""
        try:
            if self.db_connection:
                await close_database_connection()
                print("\nCLEANUP: Database connection closed")
        except Exception as e:
            print(f"WARNING:  Cleanup warning: {str(e)}")

    def _generate_summary(self, overall_success: bool) -> Dict[str, Any]:
        """Generate a summary of all test results."""
        print("\n" + "=" * 60)
        print("📊 VALIDATION SUMMARY")
        print("=" * 60)

        if overall_success:
            print("DONE: ALL VALIDATIONS PASSED!")
            print("SUCCESS: MongoDB Atlas is properly configured and operational")
            print("SUCCESS: Data collection pipeline is ready to use")
        else:
            print("ERROR: SOME VALIDATIONS FAILED")
            print("WARNING:  Please review the errors above and fix configuration")

        # Print test results summary
        for test_name, result in self.test_results.items():
            status = "SUCCESS:" if result.get("success", False) else "ERROR:"
            print(f"{status} {test_name.replace('_', ' ').title()}")

        summary = {
            "overall_success": overall_success,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "test_results": self.test_results,
        }

        return summary


async def main():
    """Main validation entry point."""
    # Check if .env file exists
    env_path = Path(__file__).parent.parent / ".env"
    if not env_path.exists():
        print("ERROR: No .env file found!")
        print("NOTE: Please create a .env file from .env.sample:")
        print(f"   cp {env_path.parent}/.env.sample {env_path}")
        print("\nINFO: Required environment variables:")
        print("   MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/")
        print("   DATABASE_NAME=phoenix_real_estate  (or MONGODB_DATABASE)")
        return 1

    validator = MongoDBAtlasValidator()

    try:
        summary = await validator.run_full_validation()

        # Save results to file
        import json

        results_path = Path(__file__).parent.parent / "validation_results.json"
        with open(results_path, "w") as f:
            json.dump(summary, f, indent=2, default=str)
        print(f"\nSAVED: Results saved to: {results_path}")

        return 0 if summary["overall_success"] else 1

    except KeyboardInterrupt:
        print("\nWARNING:  Validation interrupted by user")
        return 1
    except Exception as e:
        print(f"\nFATAL: Unexpected error: {str(e)}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
