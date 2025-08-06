"""Services layer for Phoenix Real Estate system.

This module provides business services that coordinate between
different components to provide higher-level functionality.

Services include:
- EmailReportService: Email delivery and report generation
"""

from phoenix_real_estate.services.email_service import EmailReportService, EmailConfiguration

__all__ = [
    "EmailReportService",
    "EmailConfiguration",
]