#!/usr/bin/env python3
"""Email notification script for GitHub Actions data collection workflow.

This script sends email reports based on the results of the daily data collection
workflow. It integrates with the EmailReportService to deliver professional
reports directly to users.
"""

import argparse
import asyncio
import os
import sys
from datetime import datetime, UTC
from pathlib import Path
from typing import Dict, Any, List, Optional
import json
import logging

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from phoenix_real_estate.foundation.config.base import EnvironmentConfigProvider
from phoenix_real_estate.services.email_service import EmailReportService, ReportData
from phoenix_real_estate.orchestration.processing_integrator import BatchIntegrationResult


def setup_logging() -> logging.Logger:
    """Set up logging for the email script."""
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Send email notification from GitHub Actions workflow"
    )

    parser.add_argument(
        "--status",
        required=True,
        choices=["success", "partial", "failure"],
        help="Overall collection status",
    )

    parser.add_argument("--message", required=True, help="Status message")

    parser.add_argument(
        "--email-type",
        required=True,
        choices=["success", "warning", "error"],
        help="Type of email to send",
    )

    parser.add_argument(
        "--zip-codes", required=True, help="ZIP codes processed (JSON array string)"
    )

    parser.add_argument("--collection-mode", required=True, help="Collection mode used")

    parser.add_argument("--maricopa-result", required=True, help="Maricopa collection result")

    parser.add_argument("--phoenix-mls-result", required=True, help="Phoenix MLS collection result")

    parser.add_argument("--llm-result", required=True, help="LLM processing result")

    parser.add_argument("--validation-result", required=True, help="Data validation result")

    parser.add_argument("--github-run-url", required=True, help="GitHub Actions run URL")

    parser.add_argument(
        "--dry-run", action="store_true", help="Print email content without sending"
    )

    return parser.parse_args()


def create_email_configuration() -> Dict[str, str]:
    """Create email configuration from environment variables."""
    config = {}

    # Required email configuration
    required_vars = ["SMTP_HOST", "SENDER_EMAIL", "RECIPIENT_EMAILS"]

    for var in required_vars:
        value = os.getenv(var)
        if not value:
            raise ValueError(f"Required environment variable {var} not set")
        config[var.lower()] = value

    # Optional email configuration with defaults
    optional_vars = {
        "SMTP_PORT": "587",
        "SMTP_USERNAME": "",
        "SMTP_PASSWORD": "",
        "EMAIL_ENABLED": "true",
    }

    for var, default in optional_vars.items():
        config[var.lower()] = os.getenv(var, default)

    return config


def load_collection_data(args: argparse.Namespace) -> Dict[str, Any]:
    """Load collection data from artifacts and arguments."""
    logger = logging.getLogger(__name__)

    collection_data = {
        "status": args.status,
        "message": args.message,
        "email_type": args.email_type,
        "zip_codes": json.loads(args.zip_codes)
        if args.zip_codes.startswith("[")
        else args.zip_codes.split(","),
        "collection_mode": args.collection_mode,
        "component_results": {
            "maricopa": args.maricopa_result,
            "phoenix_mls": args.phoenix_mls_result,
            "llm_processing": args.llm_result,
            "validation": args.validation_result,
        },
        "github_run_url": args.github_run_url,
        "timestamp": datetime.now(UTC).isoformat(),
    }

    # Try to load processing results from artifacts
    processed_data_dir = Path("data/processed")
    reports_dir = Path("reports")

    properties_data = []
    metrics_data = {}

    # Load processed property data
    if processed_data_dir.exists():
        for json_file in processed_data_dir.glob("*.json"):
            try:
                with open(json_file, "r") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        properties_data.extend(data)
                    elif isinstance(data, dict) and "properties" in data:
                        properties_data.extend(data["properties"])
                logger.info(f"Loaded {len(properties_data)} properties from {json_file}")
            except Exception as e:
                logger.warning(f"Failed to load {json_file}: {e}")

    # Load report data
    if reports_dir.exists():
        for json_file in reports_dir.glob("*report*.json"):
            try:
                with open(json_file, "r") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        metrics_data.update(data)
                logger.info(f"Loaded metrics from {json_file}")
            except Exception as e:
                logger.warning(f"Failed to load {json_file}: {e}")

    # Create synthetic batch result
    total_processed = len(properties_data)
    successful = sum(1 for prop in properties_data if prop.get("valid", True))
    failed = total_processed - successful

    collection_data.update(
        {
            "properties_data": properties_data,
            "metrics_data": metrics_data,
            "batch_result": {
                "total_processed": total_processed,
                "successful": successful,
                "failed": failed,
                "processing_time": metrics_data.get("total_processing_time", 0),
                "errors": [],
            },
        }
    )

    logger.info(
        f"Loaded collection data: {total_processed} properties, {successful} successful, {failed} failed"
    )
    return collection_data


def create_report_data(collection_data: Dict[str, Any]) -> ReportData:
    """Create ReportData object from collection information."""

    # Determine report title based on status
    if collection_data["status"] == "success":
        title = "✅ Phoenix Real Estate Collection Completed Successfully"
    elif collection_data["status"] == "partial":
        title = "⚠️ Phoenix Real Estate Collection Completed with Issues"
    else:
        title = "🚨 Phoenix Real Estate Collection Failed"

    # Create summary
    batch_result = collection_data["batch_result"]
    summary_parts = [
        f"Collection Status: {collection_data['status'].upper()}",
        f"ZIP Codes: {', '.join(collection_data['zip_codes'])}",
        f"Collection Mode: {collection_data['collection_mode']}",
        f"Properties Processed: {batch_result['total_processed']}",
        f"Success Rate: {(batch_result['successful'] / batch_result['total_processed'] * 100):.1f}%"
        if batch_result["total_processed"] > 0
        else "Success Rate: N/A",
    ]

    summary = "\n".join(summary_parts)

    # Create batch integration result
    batch_result_obj = BatchIntegrationResult(
        total_processed=batch_result["total_processed"],
        successful=batch_result["successful"],
        failed=batch_result["failed"],
        processing_time=batch_result["processing_time"],
        errors=batch_result.get("errors", []),
    )

    # Add component status to metrics
    enhanced_metrics = dict(collection_data["metrics_data"])
    enhanced_metrics.update(
        {
            "component_results": collection_data["component_results"],
            "github_run_url": collection_data["github_run_url"],
            "collection_mode": collection_data["collection_mode"],
            "zip_codes": collection_data["zip_codes"],
            "workflow_timestamp": collection_data["timestamp"],
        }
    )

    # Create errors list if any components failed
    errors = []
    for component, result in collection_data["component_results"].items():
        if result in ["failure", "cancelled", "skipped"]:
            errors.append(f"{component.replace('_', ' ').title()} {result}")

    if collection_data["status"] == "failure":
        errors.append("Daily data collection workflow failed completely")
    elif collection_data["status"] == "partial":
        errors.append("Data collection completed with some component failures")

    return ReportData(
        title=title,
        summary=summary,
        collection_results=batch_result_obj,
        properties=[],  # Don't include actual property data in email for brevity
        metrics=enhanced_metrics,
        errors=errors,
        report_type="workflow",
    )


async def send_email_notification(
    email_config: Dict[str, str], report_data: ReportData, email_type: str, dry_run: bool = False
) -> bool:
    """Send email notification using EmailReportService."""
    logger = logging.getLogger(__name__)

    try:
        # Create configuration provider with email settings
        config_provider = EnvironmentConfigProvider()

        # Override email configuration from environment
        config_provider.config["email"] = {
            "enabled": email_config["email_enabled"].lower() == "true",
            "smtp": {
                "host": email_config["smtp_host"],
                "port": int(email_config["smtp_port"]),
                "username": email_config["smtp_username"],
                "password": email_config["smtp_password"],
                "use_tls": True,
                "use_ssl": False,
            },
            "sender": {
                "email": email_config["sender_email"],
                "name": "Phoenix Real Estate Collector",
            },
            "recipients": email_config["recipient_emails"],
            "rate_limit_per_hour": 100,
            "timeout": 30,
        }

        if dry_run:
            logger.info("DRY RUN: Would send email with following configuration:")
            logger.info(f"SMTP Host: {email_config['smtp_host']}")
            logger.info(f"Sender: {email_config['sender_email']}")
            logger.info(f"Recipients: {email_config['recipient_emails']}")
            logger.info(f"Email Type: {email_type}")
            logger.info(f"Report Title: {report_data.title}")
            logger.info(f"Report Summary: {report_data.summary}")
            return True

        # Create email service
        email_service = EmailReportService(config_provider)

        # Send appropriate email type
        if email_type == "success":
            success = await email_service.send_success_summary(
                report_data.collection_results, report_data.collection_results.processing_time
            )
        elif email_type == "error":
            success = await email_service.send_error_alert(
                "Daily Collection Failed", report_data.summary, report_data.metrics
            )
        else:  # warning or general
            success = await email_service.send_daily_report(
                report_data,
                include_properties=False,  # Don't include property details in workflow emails
            )

        if success:
            logger.info("Email notification sent successfully")

            # Log email metrics
            metrics = email_service.get_metrics()
            logger.info(
                f"Email service metrics: {metrics.total_sent} sent, {metrics.total_failed} failed, {metrics.success_rate:.1f}% success rate"
            )
        else:
            logger.error("Failed to send email notification")

        return success

    except Exception as e:
        logger.error(f"Error sending email notification: {e}")
        return False


async def main():
    """Main execution function."""
    logger = setup_logging()

    try:
        # Parse arguments
        args = parse_arguments()
        logger.info(f"Starting email notification for {args.email_type} email")

        # Check if email is enabled
        if os.getenv("EMAIL_ENABLED", "false").lower() != "true":
            logger.info("EMAIL_ENABLED is not set to true, skipping email notification")
            return 0

        # Create email configuration
        try:
            email_config = create_email_configuration()
            logger.info(f"Email configuration loaded: SMTP host {email_config['smtp_host']}")
        except ValueError as e:
            logger.error(f"Email configuration error: {e}")
            logger.info("Skipping email notification due to missing configuration")
            return 0

        # Load collection data
        collection_data = load_collection_data(args)

        # Create report data
        report_data = create_report_data(collection_data)

        # Send email notification
        success = await send_email_notification(
            email_config, report_data, args.email_type, dry_run=args.dry_run
        )

        if success:
            logger.info("Email notification workflow completed successfully")
            return 0
        else:
            logger.error("Email notification workflow failed")
            return 1

    except Exception as e:
        logger.error(f"Unexpected error in email notification workflow: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
