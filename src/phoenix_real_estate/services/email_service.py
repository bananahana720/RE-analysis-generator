"""Email reporting service for Phoenix Real Estate system.

This module provides comprehensive email capabilities including:
- SMTP connectivity with authentication and security
- HTML email template system for reports and alerts
- Integration with data collection and processing pipeline
- Report generation with market insights and metrics
- Rate limiting and delivery optimization
"""

import asyncio
import smtplib
import ssl
from dataclasses import dataclass, field
from datetime import datetime, UTC
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, TYPE_CHECKING
import logging
import json

if TYPE_CHECKING:
    from phoenix_real_estate.orchestration.processing_integrator import BatchIntegrationResult

from phoenix_real_estate.foundation import ConfigProvider, get_logger
from phoenix_real_estate.foundation.utils.exceptions import ProcessingError
from phoenix_real_estate.models.property import PropertyDetails


logger = get_logger(__name__)


@dataclass
class EmailConfiguration:
    """Configuration for email service."""
    
    smtp_host: str
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    use_tls: bool = True
    use_ssl: bool = False
    sender_email: str = ""
    sender_name: str = "Phoenix Real Estate Collector"
    recipient_emails: List[str] = field(default_factory=list)
    max_recipients: int = 10
    timeout: int = 30
    rate_limit_per_hour: int = 100
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        if not self.smtp_host:
            raise ValueError("SMTP host is required")
        if not self.sender_email:
            raise ValueError("Sender email is required")
        if not self.recipient_emails:
            raise ValueError("At least one recipient email is required")
        if self.smtp_port not in range(1, 65536):
            raise ValueError("SMTP port must be between 1 and 65535")
        if len(self.recipient_emails) > self.max_recipients:
            raise ValueError(f"Too many recipients: {len(self.recipient_emails)} > {self.max_recipients}")


@dataclass
class EmailMetrics:
    """Email delivery metrics."""
    
    total_sent: int = 0
    total_failed: int = 0
    total_queued: int = 0
    last_sent: Optional[datetime] = None
    last_error: Optional[str] = None
    rate_limit_hits: int = 0
    avg_delivery_time: float = 0.0
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        total = self.total_sent + self.total_failed
        return (self.total_sent / total * 100) if total > 0 else 0.0


@dataclass 
class ReportData:
    """Data structure for email reports."""
    
    title: str
    summary: str
    collection_results: Optional[Any] = None  # BatchIntegrationResult, using Any to avoid circular import
    properties: List[PropertyDetails] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    report_type: str = "daily"  # daily, weekly, error, success
    
    @property
    def has_data(self) -> bool:
        """Check if report contains meaningful data."""
        return bool(self.properties or self.metrics or (self.collection_results and hasattr(self.collection_results, 'total_processed') and self.collection_results.total_processed > 0))


class EmailReportService:
    """Comprehensive email reporting service for Phoenix Real Estate system.
    
    Features:
    - SMTP connectivity with proper authentication and security
    - Professional HTML email templates with responsive design
    - Integration with ProcessingIntegrator for automated reports
    - Rate limiting and delivery optimization
    - Comprehensive error handling and monitoring
    - Support for both text and HTML email formats
    """
    
    def __init__(self, config: ConfigProvider):
        """Initialize email service with configuration.
        
        Args:
            config: Configuration provider with email settings
        """
        self.config = config
        self.logger = logger
        self._email_config = self._load_email_configuration()
        self._metrics = EmailMetrics()
        self._rate_limiter = {}  # Simple in-memory rate limiting
        self._templates_cache = {}
        
        self.logger.info(
            "EmailReportService initialized",
            extra={
                "smtp_host": self._email_config.smtp_host,
                "smtp_port": self._email_config.smtp_port,
                "sender": self._email_config.sender_email,
                "recipients": len(self._email_config.recipient_emails),
                "rate_limit": self._email_config.rate_limit_per_hour,
            }
        )
    
    def _load_email_configuration(self) -> EmailConfiguration:
        """Load email configuration from config provider.
        
        Returns:
            EmailConfiguration instance
            
        Raises:
            ProcessingError: If configuration is invalid
        """
        try:
            # SMTP Configuration
            smtp_host = self.config.get("email.smtp.host") or self.config.get("smtp_host")
            if not smtp_host:
                raise ValueError("Email SMTP host not configured")
            
            smtp_port = self.config.get_typed("email.smtp.port", int, 587)
            smtp_username = self.config.get("email.smtp.username") or self.config.get("smtp_username")
            smtp_password = self.config.get("email.smtp.password") or self.config.get("smtp_password")
            
            # Security settings
            use_tls = self.config.get_typed("email.smtp.use_tls", bool, True)
            use_ssl = self.config.get_typed("email.smtp.use_ssl", bool, False)
            
            # Sender configuration
            sender_email = self.config.get("email.sender.email") or self.config.get("sender_email")
            sender_name = self.config.get("email.sender.name", "Phoenix Real Estate Collector")
            
            # Recipients
            recipients_str = self.config.get("email.recipients") or self.config.get("recipient_emails", "")
            if isinstance(recipients_str, str):
                recipient_emails = [email.strip() for email in recipients_str.split(",") if email.strip()]
            elif isinstance(recipients_str, list):
                recipient_emails = recipients_str
            else:
                recipient_emails = []
            
            # Rate limiting and timeouts
            rate_limit = self.config.get_typed("email.rate_limit_per_hour", int, 100)
            timeout = self.config.get_typed("email.timeout", int, 30)
            max_recipients = self.config.get_typed("email.max_recipients", int, 10)
            
            return EmailConfiguration(
                smtp_host=smtp_host,
                smtp_port=smtp_port,
                smtp_username=smtp_username,
                smtp_password=smtp_password,
                use_tls=use_tls,
                use_ssl=use_ssl,
                sender_email=sender_email,
                sender_name=sender_name,
                recipient_emails=recipient_emails,
                rate_limit_per_hour=rate_limit,
                timeout=timeout,
                max_recipients=max_recipients,
            )
            
        except Exception as e:
            raise ProcessingError(f"Failed to load email configuration: {str(e)}") from e
    
    async def send_daily_report(
        self, 
        report_data: ReportData,
        include_properties: bool = True,
        include_charts: bool = False
    ) -> bool:
        """Send daily collection report via email.
        
        Args:
            report_data: Report data to include in email
            include_properties: Whether to include property details
            include_charts: Whether to include charts (future enhancement)
            
        Returns:
            True if email sent successfully
        """
        try:
            self.logger.info("Generating daily report email")
            
            # Generate email content
            subject = f"Phoenix Real Estate Daily Report - {report_data.generated_at.strftime('%Y-%m-%d')}"
            html_content = self._generate_daily_report_html(report_data, include_properties)
            text_content = self._generate_daily_report_text(report_data)
            
            # Send email
            success = await self._send_email(
                subject=subject,
                html_content=html_content,
                text_content=text_content,
                report_data=report_data
            )
            
            if success:
                self.logger.info(f"Daily report sent successfully to {len(self._email_config.recipient_emails)} recipients")
            else:
                self.logger.error("Failed to send daily report")
                
            return success
            
        except Exception as e:
            self.logger.error(f"Error sending daily report: {e}")
            self._metrics.total_failed += 1
            self._metrics.last_error = str(e)
            return False
    
    async def send_error_alert(
        self,
        error_title: str,
        error_details: str,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Send immediate error alert via email.
        
        Args:
            error_title: Brief error description
            error_details: Detailed error information
            context: Additional context information
            
        Returns:
            True if alert sent successfully
        """
        try:
            self.logger.info(f"Sending error alert: {error_title}")
            
            # Create report data for error
            report_data = ReportData(
                title=f"🚨 ALERT: {error_title}",
                summary=error_details,
                errors=[error_details],
                report_type="error",
                metrics=context or {}
            )
            
            # Generate email content
            subject = f"🚨 Phoenix Real Estate Alert: {error_title}"
            html_content = self._generate_error_alert_html(report_data)
            text_content = self._generate_error_alert_text(report_data)
            
            # Send with high priority
            success = await self._send_email(
                subject=subject,
                html_content=html_content,
                text_content=text_content,
                report_data=report_data,
                priority="high"
            )
            
            if success:
                self.logger.info("Error alert sent successfully")
            else:
                self.logger.error("Failed to send error alert")
                
            return success
            
        except Exception as e:
            self.logger.error(f"Error sending alert: {e}")
            return False
    
    async def send_success_summary(
        self,
        batch_result: Any,  # BatchIntegrationResult
        processing_time: float
    ) -> bool:
        """Send successful collection summary.
        
        Args:
            batch_result: Results from batch processing
            processing_time: Total processing time in seconds
            
        Returns:
            True if summary sent successfully
        """
        try:
            # Create report data
            report_data = ReportData(
                title="✅ Collection Completed Successfully",
                summary=f"Successfully processed {batch_result.successful} properties in {processing_time:.1f}s",
                collection_results=batch_result,
                report_type="success",
                metrics={
                    "processing_time": processing_time,
                    "success_rate": (batch_result.successful / batch_result.total_processed * 100) if batch_result.total_processed > 0 else 0,
                    "avg_time_per_property": processing_time / batch_result.total_processed if batch_result.total_processed > 0 else 0
                }
            )
            
            subject = f"✅ Phoenix Real Estate: {batch_result.successful} Properties Collected"
            html_content = self._generate_success_summary_html(report_data)
            text_content = self._generate_success_summary_text(report_data)
            
            return await self._send_email(
                subject=subject,
                html_content=html_content,
                text_content=text_content,
                report_data=report_data
            )
            
        except Exception as e:
            self.logger.error(f"Error sending success summary: {e}")
            return False
    
    def _generate_daily_report_html(self, report_data: ReportData, include_properties: bool = True) -> str:
        """Generate HTML content for daily report.
        
        Args:
            report_data: Report data to format
            include_properties: Whether to include property listings
            
        Returns:
            HTML string for email body
        """
        # Get or generate template
        template = self._get_template("daily_report")
        
        # Prepare template variables
        template_vars = {
            "title": report_data.title,
            "summary": report_data.summary,
            "generated_at": report_data.generated_at.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "has_collection_results": report_data.collection_results is not None,
            "collection_results": report_data.collection_results,
            "metrics": report_data.metrics,
            "has_properties": bool(report_data.properties) and include_properties,
            "properties": report_data.properties[:10] if include_properties else [],  # Limit to first 10
            "property_count": len(report_data.properties),
            "has_errors": bool(report_data.errors),
            "errors": report_data.errors[:5],  # Limit to first 5 errors
            "error_count": len(report_data.errors),
        }
        
        # Add collection metrics if available
        if report_data.collection_results:
            results = report_data.collection_results
            template_vars.update({
                "total_processed": results.total_processed,
                "successful": results.successful,
                "failed": results.failed,
                "success_rate": (results.successful / results.total_processed * 100) if results.total_processed > 0 else 0,
                "processing_time": f"{results.processing_time:.1f}",
            })
        
        # Use simple string replacement to avoid template formatting conflicts
        html_content = template
        for key, value in template_vars.items():
            placeholder = "{" + key + "}"
            html_content = html_content.replace(placeholder, str(value))
        
        return html_content
    
    def _generate_daily_report_text(self, report_data: ReportData) -> str:
        """Generate plain text content for daily report.
        
        Args:
            report_data: Report data to format
            
        Returns:
            Plain text string for email body
        """
        lines = [
            f"Phoenix Real Estate Daily Report",
            f"Generated: {report_data.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}",
            f"",
            f"SUMMARY",
            f"-------",
            f"{report_data.summary}",
            f"",
        ]
        
        # Add collection results if available
        if report_data.collection_results:
            results = report_data.collection_results
            lines.extend([
                f"COLLECTION RESULTS",
                f"-----------------",
                f"Total Processed: {results.total_processed}",
                f"Successful: {results.successful}",
                f"Failed: {results.failed}",
                f"Success Rate: {(results.successful / results.total_processed * 100):.1f}%" if results.total_processed > 0 else "Success Rate: N/A",
                f"Processing Time: {results.processing_time:.1f} seconds",
                f"",
            ])
        
        # Add property count
        if report_data.properties:
            lines.extend([
                f"PROPERTIES",
                f"----------",
                f"Total Properties: {len(report_data.properties)}",
                f"",
            ])
            
            # Add sample properties (first 3)
            for i, prop in enumerate(report_data.properties[:3], 1):
                lines.extend([
                    f"{i}. {prop.address or 'Unknown Address'}",
                    f"   Price: ${prop.price:,.2f}" if prop.price else "   Price: N/A",
                    f"   Type: {prop.property_type or 'Unknown'}",
                    f"   Beds/Baths: {prop.bedrooms or 'N/A'}/{prop.bathrooms or 'N/A'}",
                    f"",
                ])
        
        # Add errors if any
        if report_data.errors:
            lines.extend([
                f"ERRORS ({len(report_data.errors)})",
                f"------",
            ])
            for i, error in enumerate(report_data.errors[:5], 1):
                lines.append(f"{i}. {error}")
            
            if len(report_data.errors) > 5:
                lines.append(f"... and {len(report_data.errors) - 5} more errors")
            
            lines.append("")
        
        # Add metrics
        if report_data.metrics:
            lines.extend([
                f"METRICS",
                f"-------",
            ])
            for key, value in report_data.metrics.items():
                lines.append(f"{key.replace('_', ' ').title()}: {value}")
        
        return "\n".join(lines)
    
    def _generate_error_alert_html(self, report_data: ReportData) -> str:
        """Generate HTML content for error alert."""
        template = self._get_template("error_alert")
        
        template_vars = {
            "title": report_data.title,
            "summary": report_data.summary,
            "generated_at": report_data.generated_at.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "errors": report_data.errors,
            "error_count": len(report_data.errors),
            "metrics": report_data.metrics,
            "has_metrics": bool(report_data.metrics),
        }
        
        # Use simple string replacement to avoid template formatting conflicts
        html_content = template
        for key, value in template_vars.items():
            placeholder = "{" + key + "}"
            html_content = html_content.replace(placeholder, str(value))
        
        return html_content
    
    def _generate_error_alert_text(self, report_data: ReportData) -> str:
        """Generate plain text content for error alert."""
        lines = [
            f"🚨 PHOENIX REAL ESTATE ALERT 🚨",
            f"Generated: {report_data.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}",
            f"",
            f"ERROR: {report_data.title}",
            f"",
            f"DETAILS",
            f"-------",
            f"{report_data.summary}",
            f"",
        ]
        
        if report_data.errors:
            lines.extend([
                f"ADDITIONAL ERRORS",
                f"----------------",
            ])
            for i, error in enumerate(report_data.errors, 1):
                lines.append(f"{i}. {error}")
            lines.append("")
        
        if report_data.metrics:
            lines.extend([
                f"CONTEXT",
                f"-------",
            ])
            for key, value in report_data.metrics.items():
                lines.append(f"{key.replace('_', ' ').title()}: {value}")
        
        lines.extend([
            f"",
            f"Please investigate this issue immediately.",
            f"",
            f"--",
            f"Phoenix Real Estate Data Collector",
        ])
        
        return "\n".join(lines)
    
    def _generate_success_summary_html(self, report_data: ReportData) -> str:
        """Generate HTML content for success summary."""
        template = self._get_template("success_summary")
        
        results = report_data.collection_results
        template_vars = {
            "title": report_data.title,
            "summary": report_data.summary,
            "generated_at": report_data.generated_at.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "total_processed": results.total_processed if results else 0,
            "successful": results.successful if results else 0,
            "failed": results.failed if results else 0,
            "success_rate": report_data.metrics.get("success_rate", 0),
            "processing_time": report_data.metrics.get("processing_time", 0),
            "avg_time_per_property": report_data.metrics.get("avg_time_per_property", 0),
        }
        
        # Use simple string replacement to avoid template formatting conflicts
        html_content = template
        for key, value in template_vars.items():
            placeholder = "{" + key + "}"
            html_content = html_content.replace(placeholder, str(value))
        
        return html_content
    
    def _generate_success_summary_text(self, report_data: ReportData) -> str:
        """Generate plain text content for success summary."""
        results = report_data.collection_results
        
        lines = [
            f"✅ Phoenix Real Estate Collection Complete",
            f"Generated: {report_data.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}",
            f"",
            f"SUMMARY",
            f"-------",
            f"{report_data.summary}",
            f"",
        ]
        
        if results:
            lines.extend([
                f"RESULTS",
                f"-------",
                f"Total Processed: {results.total_processed}",
                f"Successful: {results.successful}",
                f"Failed: {results.failed}",
                f"Success Rate: {report_data.metrics.get('success_rate', 0):.1f}%",
                f"Processing Time: {report_data.metrics.get('processing_time', 0):.1f} seconds",
                f"Avg Time per Property: {report_data.metrics.get('avg_time_per_property', 0):.2f} seconds",
                f"",
            ])
        
        return "\n".join(lines)
    
    def _get_template(self, template_name: str) -> str:
        """Get HTML email template, using cache if available.
        
        Args:
            template_name: Name of template to retrieve
            
        Returns:
            HTML template string
        """
        if template_name in self._templates_cache:
            return self._templates_cache[template_name]
        
        # Generate template based on name
        if template_name == "daily_report":
            template = self._create_daily_report_template()
        elif template_name == "error_alert": 
            template = self._create_error_alert_template()
        elif template_name == "success_summary":
            template = self._create_success_summary_template()
        else:
            template = self._create_basic_template()
        
        # Cache template
        self._templates_cache[template_name] = template
        return template
    
    def _create_daily_report_template(self) -> str:
        """Create HTML template for daily reports."""
        return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Phoenix Real Estate Daily Report</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 20px; background-color: #f4f4f4; }
        .container { max-width: 800px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
        .header { background: #2c3e50; color: white; padding: 20px; margin: -20px -20px 20px -20px; border-radius: 8px 8px 0 0; }
        .header h1 { margin: 0; font-size: 24px; }
        .summary { background: #ecf0f1; padding: 15px; border-radius: 5px; margin: 20px 0; }
        .metrics { display: flex; flex-wrap: wrap; gap: 15px; margin: 20px 0; }
        .metric { background: #3498db; color: white; padding: 15px; border-radius: 5px; text-align: center; flex: 1; min-width: 120px; }
        .metric .value { font-size: 24px; font-weight: bold; display: block; }
        .metric .label { font-size: 12px; opacity: 0.9; }
        .success { background: #27ae60; }
        .warning { background: #f39c12; }
        .error { background: #e74c3c; }
        .footer { margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; color: #666; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏠 {title}</h1>
            <p>Generated: {generated_at}</p>
        </div>
        
        <div class="summary">
            <h2>Summary</h2>
            <p>{summary}</p>
        </div>
        
        <div class="metrics">
            <div class="metric success">
                <span class="value">{successful}</span>
                <span class="label">Successful</span>
            </div>
            <div class="metric">
                <span class="value">{failed}</span>
                <span class="label">Failed</span>
            </div>
            <div class="metric">
                <span class="value">{total_processed}</span>
                <span class="label">Total</span>
            </div>
            <div class="metric">
                <span class="value">{success_rate}%</span>
                <span class="label">Success Rate</span>
            </div>
            <div class="metric">
                <span class="value">{processing_time}s</span>
                <span class="label">Processing Time</span>
            </div>
        </div>
        
        <div class="footer">
            <p>Phoenix Real Estate Data Collector | Generated automatically</p>
        </div>
    </div>
</body>
</html>
        """.strip()
    
    def _create_error_alert_template(self) -> str:
        """Create HTML template for error alerts."""
        return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Phoenix Real Estate Alert</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 20px; background-color: #fef2f2; }
        .container { max-width: 600px; margin: 0 auto; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 0 20px rgba(0,0,0,0.1); }
        .header { background: #dc2626; color: white; padding: 20px; text-align: center; }
        .header h1 { margin: 0; font-size: 24px; }
        .content { padding: 20px; }
        .alert-icon { font-size: 48px; text-align: center; margin: 20px 0; }
        .summary { background: #fef2f2; border: 1px solid #fecaca; padding: 15px; border-radius: 5px; margin: 20px 0; }
        .urgent { color: #dc2626; font-weight: bold; }
        .footer { background: #f3f4f6; padding: 15px; text-align: center; color: #666; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚨 SYSTEM ALERT</h1>
            <p>Phoenix Real Estate Data Collector</p>
        </div>
        
        <div class="content">
            <div class="alert-icon">⚠️</div>
            
            <h2 class="urgent">{title}</h2>
            
            <div class="summary">
                <h3>Error Details</h3>
                <p>{summary}</p>
            </div>
            
            <p><strong>Time:</strong> {generated_at}</p>
            <p class="urgent">⚠️ Please investigate this issue immediately.</p>
        </div>
        
        <div class="footer">
            <p>This is an automated alert from Phoenix Real Estate Data Collector</p>
        </div>
    </div>
</body>
</html>
        """.strip()
    
    def _create_success_summary_template(self) -> str:
        """Create HTML template for success summaries."""
        return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Phoenix Real Estate Success</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 20px; background-color: #f0fdf4; }
        .container { max-width: 600px; margin: 0 auto; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
        .header { background: #16a34a; color: white; padding: 20px; text-align: center; }
        .header h1 { margin: 0; font-size: 24px; }
        .content { padding: 20px; }
        .success-icon { font-size: 48px; text-align: center; margin: 20px 0; color: #16a34a; }
        .summary { background: #f0fdf4; border: 1px solid #bbf7d0; padding: 15px; border-radius: 5px; margin: 20px 0; }
        .metrics { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin: 20px 0; }
        .metric { background: #16a34a; color: white; padding: 15px; border-radius: 5px; text-align: center; }
        .metric .value { font-size: 20px; font-weight: bold; display: block; }
        .metric .label { font-size: 12px; opacity: 0.9; }
        .footer { background: #f3f4f6; padding: 15px; text-align: center; color: #666; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>✅ Collection Successful</h1>
            <p>Phoenix Real Estate Data Collector</p>
        </div>
        
        <div class="content">
            <div class="success-icon">🎉</div>
            
            <h2>{title}</h2>
            
            <div class="summary">
                <p>{summary}</p>
            </div>
            
            <div class="metrics">
                <div class="metric">
                    <span class="value">{successful}</span>
                    <span class="label">Properties Collected</span>
                </div>
                <div class="metric">
                    <span class="value">{success_rate}%</span>
                    <span class="label">Success Rate</span>
                </div>
                <div class="metric">
                    <span class="value">{processing_time}s</span>
                    <span class="label">Processing Time</span>
                </div>
                <div class="metric">
                    <span class="value">{avg_time_per_property}s</span>
                    <span class="label">Avg per Property</span>
                </div>
            </div>
            
            <p><strong>Completed:</strong> {generated_at}</p>
        </div>
        
        <div class="footer">
            <p>Phoenix Real Estate Data Collector | Automated Collection Complete</p>
        </div>
    </div>
</body>
</html>
        """.strip()
    
    def _create_basic_template(self) -> str:
        """Create basic HTML template for generic emails."""
        return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Phoenix Real Estate</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 20px; background-color: #f4f4f4; }}
        .container {{ max-width: 600px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }}
        .header {{ border-bottom: 2px solid #2c3e50; padding-bottom: 10px; margin-bottom: 20px; }}
        .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; color: #666; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏠 Phoenix Real Estate</h1>
        </div>
        
        <div class="content">
            {content}
        </div>
        
        <div class="footer">
            <p>Phoenix Real Estate Data Collector | {generated_at}</p>
        </div>
    </div>
</body>
</html>
        """.strip()
    
    async def _send_email(
        self,
        subject: str,
        html_content: str,
        text_content: str,
        report_data: ReportData,
        priority: str = "normal"
    ) -> bool:
        """Send email using SMTP with proper error handling.
        
        Args:
            subject: Email subject line
            html_content: HTML email body
            text_content: Plain text email body
            report_data: Report data for context
            priority: Email priority (high, normal, low)
            
        Returns:
            True if email sent successfully
        """
        start_time = datetime.now(UTC)
        
        try:
            # Check rate limiting
            if not self._check_rate_limit():
                self.logger.warning("Email rate limit exceeded, queuing email")
                self._metrics.total_queued += 1
                self._metrics.rate_limit_hits += 1
                return False
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{self._email_config.sender_name} <{self._email_config.sender_email}>"
            msg['To'] = ", ".join(self._email_config.recipient_emails)
            
            # Set priority
            if priority == "high":
                msg['X-Priority'] = '1'
                msg['X-MSMail-Priority'] = 'High'
                msg['Importance'] = 'High'
            
            # Attach text and HTML parts
            text_part = MIMEText(text_content, 'plain')
            html_part = MIMEText(html_content, 'html')
            
            msg.attach(text_part)
            msg.attach(html_part)
            
            # Send email
            await self._smtp_send(msg)
            
            # Update metrics
            delivery_time = (datetime.now(UTC) - start_time).total_seconds()
            self._metrics.total_sent += 1
            self._metrics.last_sent = datetime.now(UTC)
            self._update_avg_delivery_time(delivery_time)
            
            self.logger.info(
                f"Email sent successfully: {subject}",
                extra={
                    "recipients": len(self._email_config.recipient_emails),
                    "delivery_time": f"{delivery_time:.2f}s",
                    "priority": priority,
                }
            )
            
            return True
            
        except Exception as e:
            self._metrics.total_failed += 1
            self._metrics.last_error = str(e)
            self.logger.error(f"Failed to send email: {e}")
            return False
    
    async def _smtp_send(self, message: MIMEMultipart) -> None:
        """Send email via SMTP with proper connection handling.
        
        Args:
            message: MIME message to send
            
        Raises:
            Exception: If SMTP sending fails
        """
        # Use asyncio.to_thread for SMTP operations (blocking)
        def _sync_smtp_send():
            if self._email_config.use_ssl:
                # Use SSL from the start
                server = smtplib.SMTP_SSL(
                    self._email_config.smtp_host,
                    self._email_config.smtp_port,
                    timeout=self._email_config.timeout
                )
            else:
                # Use regular SMTP, possibly with STARTTLS
                server = smtplib.SMTP(
                    self._email_config.smtp_host,
                    self._email_config.smtp_port,
                    timeout=self._email_config.timeout
                )
                
                if self._email_config.use_tls:
                    server.starttls(context=ssl.create_default_context())
            
            try:
                # Authenticate if credentials provided
                if self._email_config.smtp_username and self._email_config.smtp_password:
                    server.login(self._email_config.smtp_username, self._email_config.smtp_password)
                
                # Send email
                server.send_message(message)
                
            finally:
                server.quit()
        
        # Run SMTP operations in thread pool
        await asyncio.to_thread(_sync_smtp_send)
    
    def _check_rate_limit(self) -> bool:
        """Check if email sending is within rate limits.
        
        Returns:
            True if sending is allowed
        """
        now = datetime.now(UTC)
        hour_key = now.strftime("%Y-%m-%d-%H")
        
        # Clean old entries (keep last 2 hours)
        old_keys = [key for key in self._rate_limiter.keys() if key < hour_key]
        for key in old_keys:
            del self._rate_limiter[key]
        
        # Check current hour limit
        current_count = self._rate_limiter.get(hour_key, 0)
        if current_count >= self._email_config.rate_limit_per_hour:
            return False
        
        # Update count
        self._rate_limiter[hour_key] = current_count + 1
        return True
    
    def _update_avg_delivery_time(self, delivery_time: float) -> None:
        """Update average delivery time metric.
        
        Args:
            delivery_time: Time taken to deliver email in seconds
        """
        if self._metrics.avg_delivery_time == 0:
            self._metrics.avg_delivery_time = delivery_time
        else:
            # Simple moving average
            total_sent = self._metrics.total_sent
            self._metrics.avg_delivery_time = (
                (self._metrics.avg_delivery_time * (total_sent - 1) + delivery_time) / total_sent
            )
    
    def get_metrics(self) -> EmailMetrics:
        """Get current email service metrics.
        
        Returns:
            EmailMetrics with current statistics
        """
        return self._metrics
    
    def get_configuration(self) -> EmailConfiguration:
        """Get current email configuration (excluding sensitive data).
        
        Returns:
            EmailConfiguration with sensitive data masked
        """
        config_copy = EmailConfiguration(
            smtp_host=self._email_config.smtp_host,
            smtp_port=self._email_config.smtp_port,
            smtp_username="***" if self._email_config.smtp_username else None,
            smtp_password="***" if self._email_config.smtp_password else None,
            use_tls=self._email_config.use_tls,
            use_ssl=self._email_config.use_ssl,
            sender_email=self._email_config.sender_email,
            sender_name=self._email_config.sender_name,
            recipient_emails=self._email_config.recipient_emails,
            rate_limit_per_hour=self._email_config.rate_limit_per_hour,
            timeout=self._email_config.timeout,
            max_recipients=self._email_config.max_recipients,
        )
        return config_copy
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test SMTP connection and configuration.
        
        Returns:
            Dictionary with test results
        """
        results = {
            "smtp_connection": False,
            "authentication": False,
            "configuration_valid": False,
            "errors": [],
            "warnings": [],
        }
        
        try:
            # Test configuration validity
            if not self._email_config.smtp_host:
                results["errors"].append("SMTP host not configured")
            elif not self._email_config.sender_email:
                results["errors"].append("Sender email not configured")
            elif not self._email_config.recipient_emails:
                results["errors"].append("No recipient emails configured")
            else:
                results["configuration_valid"] = True
            
            if not results["configuration_valid"]:
                return results
            
            # Test SMTP connection
            def _test_smtp():
                if self._email_config.use_ssl:
                    server = smtplib.SMTP_SSL(
                        self._email_config.smtp_host,
                        self._email_config.smtp_port,
                        timeout=10
                    )
                else:
                    server = smtplib.SMTP(
                        self._email_config.smtp_host,
                        self._email_config.smtp_port,
                        timeout=10
                    )
                    if self._email_config.use_tls:
                        server.starttls(context=ssl.create_default_context())
                
                try:
                    # Test authentication if credentials provided
                    if self._email_config.smtp_username and self._email_config.smtp_password:
                        server.login(self._email_config.smtp_username, self._email_config.smtp_password)
                        results["authentication"] = True
                    else:
                        results["warnings"].append("No SMTP authentication configured")
                    
                    results["smtp_connection"] = True
                    
                finally:
                    server.quit()
            
            # Run SMTP test in thread pool
            await asyncio.to_thread(_test_smtp)
            
        except Exception as e:
            results["errors"].append(f"SMTP connection failed: {str(e)}")
        
        return results

    async def send_test_email(self) -> bool:
        """Send a test email to verify configuration.
        
        Returns:
            True if test email sent successfully
        """
        try:
            test_report = ReportData(
                title="📧 Email Service Test",
                summary="This is a test email to verify the Phoenix Real Estate email service configuration.",
                report_type="test",
                metrics={
                    "test_time": datetime.now(UTC).isoformat(),
                    "configuration_valid": True,
                    "smtp_host": self._email_config.smtp_host,
                    "smtp_port": self._email_config.smtp_port,
                }
            )
            
            subject = "🧪 Phoenix Real Estate Email Service Test"
            html_content = self._get_template("basic").format(
                content="<h2>Email Service Test</h2><p>If you receive this email, the Phoenix Real Estate email service is configured correctly!</p>",
                generated_at=datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
            )
            text_content = "Phoenix Real Estate Email Service Test\n\nIf you receive this email, the service is configured correctly!"
            
            return await self._send_email(
                subject=subject,
                html_content=html_content,
                text_content=text_content,
                report_data=test_report
            )
            
        except Exception as e:
            self.logger.error(f"Failed to send test email: {e}")
            return False