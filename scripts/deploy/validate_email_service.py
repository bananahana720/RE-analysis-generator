#!/usr/bin/env python3
"""Email service validation script.

This script validates the email service configuration and functionality
without sending actual emails (unless explicitly requested).
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, UTC
import argparse
import logging

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from phoenix_real_estate.foundation.config.base import EnvironmentConfigProvider
from phoenix_real_estate.services.email_service import EmailReportService, ReportData
from phoenix_real_estate.orchestration.processing_integrator import BatchIntegrationResult
from phoenix_real_estate.models.property import PropertyDetails


def setup_logging(verbose: bool = False) -> logging.Logger:
    """Set up logging for the validation script."""
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
    parser = argparse.ArgumentParser(description="Validate Phoenix Real Estate email service")

    parser.add_argument(
        "--test-connection", action="store_true", help="Test SMTP connection without sending emails"
    )

    parser.add_argument(
        "--send-test-email",
        action="store_true",
        help="Send actual test email (requires valid configuration)",
    )

    parser.add_argument(
        "--validate-templates", action="store_true", help="Validate email template generation"
    )

    parser.add_argument("--check-config", action="store_true", help="Check email configuration")

    parser.add_argument(
        "--all", action="store_true", help="Run all validation checks except sending test email"
    )

    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")

    return parser.parse_args()


async def validate_email_configuration(logger: logging.Logger) -> bool:
    """Validate email configuration loading."""
    logger.info("🔧 Validating email configuration...")

    try:
        config_provider = EnvironmentConfigProvider()

        # Check if email is enabled
        email_enabled = config_provider.get_typed("email.enabled", bool, False)
        logger.info(f"Email enabled: {email_enabled}")

        if not email_enabled:
            logger.warning("⚠️ Email service is disabled in configuration")
            logger.info("Set email.enabled=true or EMAIL_ENABLED=true to enable")
            return False

        # Try to create email service
        try:
            email_service = EmailReportService(config_provider)
            logger.info("✅ Email service created successfully")

            # Get configuration (sensitive data masked)
            config = email_service.get_configuration()
            logger.info(f"SMTP Host: {config.smtp_host}")
            logger.info(f"SMTP Port: {config.smtp_port}")
            logger.info(f"Use TLS: {config.use_tls}")
            logger.info(f"Use SSL: {config.use_ssl}")
            logger.info(f"Sender Email: {config.sender_email}")
            logger.info(f"Recipients: {len(config.recipient_emails)} configured")
            logger.info(f"Rate Limit: {config.rate_limit_per_hour} emails/hour")

            return True

        except Exception as e:
            logger.error(f"❌ Failed to create email service: {e}")
            return False

    except Exception as e:
        logger.error(f"❌ Configuration validation failed: {e}")
        return False


async def test_smtp_connection(logger: logging.Logger) -> bool:
    """Test SMTP connection without sending emails."""
    logger.info("🌐 Testing SMTP connection...")

    try:
        config_provider = EnvironmentConfigProvider()

        # Check if email is enabled
        if not config_provider.get_typed("email.enabled", bool, False):
            logger.warning("⚠️ Email service is disabled, skipping connection test")
            return False

        email_service = EmailReportService(config_provider)

        # Test connection
        results = await email_service.test_connection()

        logger.info(f"Configuration Valid: {'✅' if results['configuration_valid'] else '❌'}")
        logger.info(f"SMTP Connection: {'✅' if results['smtp_connection'] else '❌'}")
        logger.info(f"Authentication: {'✅' if results['authentication'] else '❌'}")

        if results["warnings"]:
            for warning in results["warnings"]:
                logger.warning(f"⚠️ {warning}")

        if results["errors"]:
            for error in results["errors"]:
                logger.error(f"❌ {error}")
            return False

        logger.info("✅ SMTP connection test passed")
        return True

    except Exception as e:
        logger.error(f"❌ SMTP connection test failed: {e}")
        return False


async def validate_email_templates(logger: logging.Logger) -> bool:
    """Validate email template generation."""
    logger.info("📧 Validating email templates...")

    try:
        config_provider = EnvironmentConfigProvider()

        # Mock configuration for template testing
        config_provider.config = {
            "email": {
                "enabled": True,
                "smtp": {
                    "host": "smtp.example.com",
                    "port": 587,
                    "username": "test@example.com",
                    "password": "testpass",
                    "use_tls": True,
                    "use_ssl": False,
                },
                "sender": {"email": "sender@example.com", "name": "Phoenix Real Estate Test"},
                "recipients": "recipient@example.com",
                "rate_limit_per_hour": 100,
                "timeout": 30,
            }
        }

        email_service = EmailReportService(config_provider)

        # Create test data
        test_properties = [
            PropertyDetails(
                property_id="test_001",
                address="123 Test Street, Phoenix, AZ 85031",
                price=425000.0,
                bedrooms=3,
                bathrooms=2,
                square_feet=1850,
                property_type="single_family",
            ),
            PropertyDetails(
                property_id="test_002",
                address="456 Sample Ave, Phoenix, AZ 85033",
                price=375000.0,
                bedrooms=4,
                bathrooms=3,
                square_feet=2100,
                property_type="single_family",
            ),
        ]

        batch_result = BatchIntegrationResult(
            total_processed=10,
            successful=8,
            failed=2,
            processing_time=35.7,
            errors=["Sample error 1", "Sample error 2"],
        )

        # Test daily report template
        logger.info("Testing daily report template...")
        daily_report = ReportData(
            title="Test Daily Report",
            summary="This is a test of the daily report template generation",
            collection_results=batch_result,
            properties=test_properties,
            metrics={
                "collection_mode": "test",
                "zip_codes": ["85031", "85033"],
                "success_rate": 80.0,
            },
            errors=batch_result.errors,
            report_type="daily",
        )

        html_content = email_service._generate_daily_report_html(
            daily_report, include_properties=True
        )
        text_content = email_service._generate_daily_report_text(daily_report)

        # Validate HTML content
        assert "<!DOCTYPE html>" in html_content
        assert "Test Daily Report" in html_content
        assert "This is a test" in html_content
        assert "Total Processed: 10" in html_content or "10" in html_content
        logger.info("✅ Daily report HTML template generated successfully")

        # Validate text content
        assert "Phoenix Real Estate Daily Report" in text_content
        assert "Test Daily Report" in text_content or "This is a test" in text_content
        assert "Total Processed: 10" in text_content
        assert "Successful: 8" in text_content
        logger.info("✅ Daily report text template generated successfully")

        # Test error alert template
        logger.info("Testing error alert template...")
        error_report = ReportData(
            title="Test Error Alert",
            summary="This is a test error alert",
            errors=["Critical system failure", "Database connection lost"],
            report_type="error",
            metrics={"error_context": "test_validation"},
        )

        error_html = email_service._generate_error_alert_html(error_report)
        error_text = email_service._generate_error_alert_text(error_report)

        # Validate error templates
        assert "<!DOCTYPE html>" in error_html
        assert "ALERT" in error_html.upper()
        assert "Test Error Alert" in error_html
        logger.info("✅ Error alert HTML template generated successfully")

        assert "PHOENIX REAL ESTATE ALERT" in error_text.upper()
        assert "Test Error Alert" in error_text
        assert "Critical system failure" in error_text
        logger.info("✅ Error alert text template generated successfully")

        # Test success summary template
        logger.info("Testing success summary template...")
        success_html = email_service._generate_success_summary_html(daily_report)
        success_text = email_service._generate_success_summary_text(daily_report)

        assert "<!DOCTYPE html>" in success_html
        assert "Collection Successful" in success_html or "Success" in success_html
        logger.info("✅ Success summary HTML template generated successfully")

        assert (
            "Phoenix Real Estate Collection Complete" in success_text
            or "Collection Complete" in success_text
        )
        logger.info("✅ Success summary text template generated successfully")

        logger.info("✅ All email templates validated successfully")
        return True

    except Exception as e:
        logger.error(f"❌ Template validation failed: {e}")
        return False


async def send_test_email(logger: logging.Logger) -> bool:
    """Send actual test email."""
    logger.info("📬 Sending test email...")

    try:
        config_provider = EnvironmentConfigProvider()

        # Check if email is enabled
        if not config_provider.get_typed("email.enabled", bool, False):
            logger.error("❌ Email service is disabled, cannot send test email")
            return False

        email_service = EmailReportService(config_provider)

        # Send test email
        result = await email_service.send_test_email()

        if result:
            logger.info("✅ Test email sent successfully")

            # Show metrics
            metrics = email_service.get_metrics()
            logger.info(f"Email metrics: {metrics.total_sent} sent, {metrics.total_failed} failed")

            return True
        else:
            logger.error("❌ Failed to send test email")
            return False

    except Exception as e:
        logger.error(f"❌ Test email sending failed: {e}")
        return False


async def main():
    """Main validation function."""
    args = parse_arguments()
    logger = setup_logging(args.verbose)

    logger.info("🏠 Phoenix Real Estate Email Service Validation")
    logger.info("=" * 50)

    success_count = 0
    total_tests = 0

    # Determine which tests to run
    run_all = args.all
    tests_to_run = []

    if run_all or args.check_config:
        tests_to_run.append(("Configuration Check", validate_email_configuration))

    if run_all or args.test_connection:
        tests_to_run.append(("SMTP Connection Test", test_smtp_connection))

    if run_all or args.validate_templates:
        tests_to_run.append(("Template Validation", validate_email_templates))

    if args.send_test_email:  # Not included in --all for safety
        tests_to_run.append(("Test Email Send", send_test_email))

    if not tests_to_run:
        logger.info("No tests specified. Use --all or specific test flags.")
        logger.info("Use --help for available options.")
        return 1

    # Run selected tests
    for test_name, test_func in tests_to_run:
        logger.info(f"\n🧪 Running {test_name}...")
        total_tests += 1

        try:
            result = await test_func(logger)
            if result:
                success_count += 1
                logger.info(f"✅ {test_name} passed")
            else:
                logger.error(f"❌ {test_name} failed")
        except Exception as e:
            logger.error(f"❌ {test_name} failed with exception: {e}")

    # Summary
    logger.info("\n" + "=" * 50)
    logger.info(f"📊 Validation Summary: {success_count}/{total_tests} tests passed")

    if success_count == total_tests:
        logger.info("🎉 All validation checks passed!")
        return 0
    else:
        logger.warning(f"⚠️ {total_tests - success_count} validation checks failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
