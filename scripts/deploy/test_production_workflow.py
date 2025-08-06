#!/usr/bin/env python3
"""Production workflow end-to-end test script.

This script tests the complete production workflow from data collection
through LLM processing to email reporting, validating all components
in a controlled test environment.
"""

import asyncio
import sys
import logging
from pathlib import Path
from datetime import datetime, UTC
import argparse

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from phoenix_real_estate.foundation.config.base import EnvironmentConfigProvider
from phoenix_real_estate.foundation.database.connection import DatabaseConnection
from phoenix_real_estate.orchestration.processing_integrator import ProcessingIntegrator
from phoenix_real_estate.services.email_service import EmailReportService, ReportData
from phoenix_real_estate.models.property import PropertyDetails


def setup_logging(verbose: bool = False) -> logging.Logger:
    """Set up logging for the test script."""
    logger = logging.getLogger(__name__)
    level = logging.DEBUG if verbose else logging.INFO
    logger.setLevel(level)

    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Test Phoenix Real Estate production workflow")

    parser.add_argument(
        "--skip-database", action="store_true", help="Skip database connectivity tests"
    )

    parser.add_argument("--skip-llm", action="store_true", help="Skip LLM processing tests")

    parser.add_argument("--skip-email", action="store_true", help="Skip email service tests")

    parser.add_argument(
        "--test-email-send",
        action="store_true",
        help="Actually send test email (requires valid email configuration)",
    )

    parser.add_argument(
        "--use-production-env",
        action="store_true",
        help="Use production environment configuration (.env.production)",
    )

    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")

    return parser.parse_args()


async def test_database_connection(
    logger: logging.Logger, config_provider: EnvironmentConfigProvider
) -> bool:
    """Test database connectivity and operations."""
    logger.info("Testing database connection...")

    try:
        # Test database connection
        db_connection = DatabaseConnection(config_provider, "phoenix_real_estate_test")
        await db_connection.connect()

        logger.info("Database connection successful")

        # Test collections
        database = db_connection.database
        collections = await database.list_collection_names()
        logger.info(f"Available collections: {collections}")

        # Test write operation
        test_collection = database.test_collection
        test_doc = {
            "test_id": "production_test",
            "timestamp": datetime.now(UTC).isoformat(),
            "data": {"test": True},
        }

        result = await test_collection.insert_one(test_doc)
        logger.info(f"Test document inserted: {result.inserted_id}")

        # Test read operation
        retrieved_doc = await test_collection.find_one({"test_id": "production_test"})
        if retrieved_doc:
            logger.info("Test document retrieved successfully")
        else:
            logger.error("Failed to retrieve test document")
            return False

        # Cleanup
        await test_collection.delete_one({"test_id": "production_test"})
        await db_connection.close()

        logger.info("Database test completed successfully")
        return True

    except Exception as e:
        logger.error(f"Database test failed: {e}")
        return False


async def test_llm_processing(
    logger: logging.Logger, config_provider: EnvironmentConfigProvider
) -> bool:
    """Test LLM processing pipeline."""
    logger.info("Testing LLM processing pipeline...")

    try:
        # Create test property data
        test_properties = [
            {
                "property_id": "test_001",
                "raw_html": """
                <div class="property-details">
                    <h1>123 Test Street, Phoenix, AZ 85031</h1>
                    <div class="price">$425,000</div>
                    <div class="beds-baths">3 beds • 2 baths</div>
                    <div class="sqft">1,850 sq ft</div>
                    <div class="property-type">Single Family Home</div>
                </div>
                """,
                "source": "test_data",
            }
        ]

        # Test processing pipeline
        async with ProcessingIntegrator(config_provider) as integrator:
            results = await integrator.process_batch(test_properties, batch_size=1)

            if results.successful > 0:
                logger.info(f"LLM processing successful: {results.successful} properties processed")
                logger.info(f"Processing time: {results.processing_time:.2f}s")
                return True
            else:
                logger.error(f"LLM processing failed: {results.errors}")
                return False

    except Exception as e:
        logger.error(f"LLM processing test failed: {e}")
        return False


async def test_email_service(
    logger: logging.Logger, config_provider: EnvironmentConfigProvider, send_test: bool = False
) -> bool:
    """Test email service functionality."""
    logger.info("Testing email service...")

    try:
        # Check if email is enabled
        email_enabled = config_provider.get_typed("email.enabled", bool, False)
        if not email_enabled:
            logger.warning("Email service is disabled, enabling for test...")
            config_provider.config.setdefault("email", {})["enabled"] = True

        # Create email service
        email_service = EmailReportService(config_provider)

        # Test configuration
        logger.info("Testing email configuration...")
        config = email_service.get_configuration()
        logger.info(f"SMTP Host: {config.smtp_host}")
        logger.info(f"SMTP Port: {config.smtp_port}")
        logger.info(f"Sender: {config.sender_email}")
        logger.info(f"Recipients: {len(config.recipient_emails)}")

        # Test template generation
        logger.info("Testing email template generation...")

        # Create test report data
        test_properties = [
            PropertyDetails(
                property_id="test_001",
                address="123 Test Street, Phoenix, AZ 85031",
                price=425000.0,
                bedrooms=3,
                bathrooms=2,
                square_feet=1850,
                property_type="single_family",
            )
        ]

        report_data = ReportData(
            title="Production Test Report",
            summary="This is a test of the production email reporting system",
            properties=test_properties,
            metrics={
                "collection_mode": "test",
                "zip_codes": ["85031"],
                "properties_collected": 1,
                "success_rate": 100.0,
                "processing_time": 5.2,
            },
            report_type="daily",
        )

        # Generate templates
        html_content = email_service._generate_daily_report_html(
            report_data, include_properties=True
        )
        text_content = email_service._generate_daily_report_text(report_data)

        if "Production Test Report" in html_content and "Production Test Report" in text_content:
            logger.info("Email template generation successful")
        else:
            logger.error("Email template generation failed")
            return False

        # Test connection (if configured)
        if email_enabled and send_test:
            logger.info("Testing SMTP connection...")
            connection_results = await email_service.test_connection()

            if connection_results.get("smtp_connection"):
                logger.info("SMTP connection test successful")

                # Send test email
                logger.info("Sending test email...")
                success = await email_service.send_test_email()

                if success:
                    logger.info("Test email sent successfully")
                else:
                    logger.error("Failed to send test email")
                    return False
            else:
                logger.warning("SMTP connection test failed, but template generation works")
        else:
            logger.info("Skipping SMTP connection test (email disabled or not requested)")

        return True

    except Exception as e:
        logger.error(f"Email service test failed: {e}")
        return False


async def test_integrated_workflow(
    logger: logging.Logger, config_provider: EnvironmentConfigProvider
) -> bool:
    """Test complete integrated workflow."""
    logger.info("Testing integrated workflow...")

    try:
        # Mock a complete data collection workflow
        test_properties = [
            {
                "property_id": "workflow_test_001",
                "raw_html": """
                <div class="property-listing">
                    <h2>456 Integration Ave, Phoenix, AZ 85033</h2>
                    <div class="price">$375,000</div>
                    <div class="details">4 bd | 3 ba | 2,100 sqft</div>
                    <div class="type">Single Family</div>
                </div>
                """,
                "source": "integration_test",
            }
        ]

        # Step 1: Process with LLM
        logger.info("Step 1: Processing data with LLM...")
        async with ProcessingIntegrator(config_provider) as integrator:
            processing_results = await integrator.process_batch(test_properties, batch_size=1)

        if processing_results.successful == 0:
            logger.error("LLM processing failed in integrated workflow")
            return False

        logger.info(f"LLM processing completed: {processing_results.successful} properties")

        # Step 2: Store to database
        logger.info("Step 2: Storing results to database...")
        db_connection = DatabaseConnection(config_provider, "phoenix_real_estate_test")
        await db_connection.connect()

        test_collection = db_connection.database.workflow_test
        await test_collection.insert_one(
            {
                "workflow_id": "production_test",
                "timestamp": datetime.now(UTC).isoformat(),
                "processing_results": {
                    "total_processed": processing_results.total_processed,
                    "successful": processing_results.successful,
                    "failed": processing_results.failed,
                    "processing_time": processing_results.processing_time,
                },
            }
        )

        await db_connection.close()
        logger.info("Database storage completed")

        # Step 3: Generate email report
        logger.info("Step 3: Generating email report...")
        if config_provider.get_typed("email.enabled", bool, False):
            email_service = EmailReportService(config_provider)

            # Create report data from processing results
            report_data = ReportData(
                title="Production Workflow Test",
                summary="Integrated workflow test completed successfully",
                metrics={
                    "workflow_mode": "integrated_test",
                    "properties_processed": processing_results.successful,
                    "processing_time": processing_results.processing_time,
                    "success_rate": (
                        processing_results.successful / processing_results.total_processed
                    )
                    * 100,
                },
                report_type="test",
            )

            # Generate report (don't send, just validate generation)
            html_report = email_service._generate_daily_report_html(report_data)
            if "Production Workflow Test" in html_report:
                logger.info("Email report generation successful")
            else:
                logger.error("Email report generation failed")
                return False
        else:
            logger.info("Email service disabled, skipping report generation")

        logger.info("Integrated workflow test completed successfully")
        return True

    except Exception as e:
        logger.error(f"Integrated workflow test failed: {e}")
        return False


async def main():
    """Main test function."""
    args = parse_arguments()
    logger = setup_logging(args.verbose)

    logger.info("Phoenix Real Estate Production Workflow Test")
    logger.info("=" * 60)

    # Configure environment
    if args.use_production_env:
        # Load production environment
        env_file = Path(".env.production")
        if env_file.exists():
            import os

            with open(env_file) as f:
                for line in f:
                    if "=" in line and not line.strip().startswith("#"):
                        key, value = line.strip().split("=", 1)
                        os.environ[key] = value
            logger.info("Using production environment configuration")
        else:
            logger.error("Production environment file not found: .env.production")
            return 1

    config_provider = EnvironmentConfigProvider()

    success_count = 0
    total_tests = 0

    # Define test suite
    tests = []

    if not args.skip_database:
        tests.append(
            ("Database Connection", lambda: test_database_connection(logger, config_provider))
        )

    if not args.skip_llm:
        tests.append(("LLM Processing", lambda: test_llm_processing(logger, config_provider)))

    if not args.skip_email:
        tests.append(
            (
                "Email Service",
                lambda: test_email_service(logger, config_provider, args.test_email_send),
            )
        )

    # Always run integrated workflow test unless all components are skipped
    if not (args.skip_database and args.skip_llm and args.skip_email):
        tests.append(
            ("Integrated Workflow", lambda: test_integrated_workflow(logger, config_provider))
        )

    if not tests:
        logger.info("No tests selected. Use --help for available options.")
        return 1

    # Run tests
    for test_name, test_func in tests:
        logger.info(f"\nRunning {test_name} test...")
        total_tests += 1

        try:
            result = await test_func()
            if result:
                success_count += 1
                logger.info(f"✓ {test_name} test passed")
            else:
                logger.error(f"✗ {test_name} test failed")
        except Exception as e:
            logger.error(f"✗ {test_name} test failed with exception: {e}")

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info(f"Test Summary: {success_count}/{total_tests} tests passed")

    if success_count == total_tests:
        logger.info("🎉 All production workflow tests passed!")
        logger.info("\nProduction system is ready for deployment!")
        logger.info("\nNext steps:")
        logger.info("1. Configure production secrets (API keys, email credentials)")
        logger.info("2. Run GitHub Actions workflow: data-collection.yml")
        logger.info("3. Monitor logs and email reports")
        logger.info("4. Set up automated daily collection schedule")
        return 0
    else:
        logger.warning(f"⚠️ {total_tests - success_count} tests failed")
        logger.info("Please review the errors above and fix issues before deployment")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
