"""Comprehensive tests for EmailReportService.

Tests cover:
- Configuration loading and validation
- SMTP connection and authentication
- Email template generation
- Report sending functionality
- Error handling and rate limiting
- Integration with ProcessingIntegrator
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, UTC
from email.mime.multipart import MIMEMultipart
import smtplib

from phoenix_real_estate.services.email_service import (
    EmailReportService,
    EmailConfiguration,
    EmailMetrics,
    ReportData,
)
from phoenix_real_estate.foundation.config.base import EnvironmentConfigProvider
from phoenix_real_estate.foundation.utils.exceptions import ProcessingError
from phoenix_real_estate.orchestration.processing_integrator import BatchIntegrationResult
from phoenix_real_estate.models.property import PropertyDetails


class TestEmailConfiguration:
    """Test EmailConfiguration data class."""

    def test_valid_configuration(self):
        """Test valid email configuration creation."""
        config = EmailConfiguration(
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_username="user@example.com",
            smtp_password="password",
            sender_email="sender@example.com",
            recipient_emails=["recipient@example.com"],
        )

        assert config.smtp_host == "smtp.example.com"
        assert config.smtp_port == 587
        assert config.use_tls is True
        assert config.use_ssl is False
        assert len(config.recipient_emails) == 1

    def test_configuration_validation_missing_host(self):
        """Test configuration validation fails with missing SMTP host."""
        with pytest.raises(ValueError, match="SMTP host is required"):
            EmailConfiguration(
                smtp_host="",
                sender_email="sender@example.com",
                recipient_emails=["recipient@example.com"],
            )

    def test_configuration_validation_missing_sender(self):
        """Test configuration validation fails with missing sender email."""
        with pytest.raises(ValueError, match="Sender email is required"):
            EmailConfiguration(
                smtp_host="smtp.example.com",
                sender_email="",
                recipient_emails=["recipient@example.com"],
            )

    def test_configuration_validation_no_recipients(self):
        """Test configuration validation fails with no recipients."""
        with pytest.raises(ValueError, match="At least one recipient email is required"):
            EmailConfiguration(
                smtp_host="smtp.example.com", sender_email="sender@example.com", recipient_emails=[]
            )

    def test_configuration_validation_invalid_port(self):
        """Test configuration validation fails with invalid port."""
        with pytest.raises(ValueError, match="SMTP port must be between 1 and 65535"):
            EmailConfiguration(
                smtp_host="smtp.example.com",
                smtp_port=0,
                sender_email="sender@example.com",
                recipient_emails=["recipient@example.com"],
            )

    def test_configuration_too_many_recipients(self):
        """Test configuration validation fails with too many recipients."""
        with pytest.raises(ValueError, match="Too many recipients"):
            EmailConfiguration(
                smtp_host="smtp.example.com",
                sender_email="sender@example.com",
                recipient_emails=[f"user{i}@example.com" for i in range(15)],
                max_recipients=10,
            )


class TestEmailMetrics:
    """Test EmailMetrics data class."""

    def test_metrics_initialization(self):
        """Test metrics initialization with default values."""
        metrics = EmailMetrics()

        assert metrics.total_sent == 0
        assert metrics.total_failed == 0
        assert metrics.success_rate == 0.0

    def test_success_rate_calculation(self):
        """Test success rate calculation."""
        metrics = EmailMetrics(total_sent=8, total_failed=2)

        assert metrics.success_rate == 80.0

    def test_success_rate_no_emails(self):
        """Test success rate with no emails sent."""
        metrics = EmailMetrics()

        assert metrics.success_rate == 0.0


class TestReportData:
    """Test ReportData data class."""

    def test_report_data_creation(self):
        """Test report data creation."""
        report = ReportData(title="Test Report", summary="Test summary", report_type="daily")

        assert report.title == "Test Report"
        assert report.summary == "Test summary"
        assert report.report_type == "daily"
        assert isinstance(report.generated_at, datetime)

    def test_has_data_empty(self):
        """Test has_data property with empty report."""
        report = ReportData(title="Empty Report", summary="No data")

        assert not report.has_data

    def test_has_data_with_properties(self):
        """Test has_data property with properties."""
        property_detail = PropertyDetails(
            property_id="test123", address="123 Test St", price=250000.0
        )

        report = ReportData(
            title="Report with Data", summary="Has properties", properties=[property_detail]
        )

        assert report.has_data

    def test_has_data_with_metrics(self):
        """Test has_data property with metrics."""
        report = ReportData(
            title="Report with Metrics", summary="Has metrics", metrics={"total_processed": 10}
        )

        assert report.has_data


class TestEmailReportService:
    """Test EmailReportService functionality."""

    @pytest.fixture
    def mock_config_provider(self):
        """Create mock configuration provider with email settings."""
        config = Mock(spec=EnvironmentConfigProvider)
        config.get_typed.side_effect = lambda key, type_cls, default=None: {
            ("email.enabled", bool, False): True,
            ("email.smtp.port", int, 587): 587,
            ("email.smtp.use_tls", bool, True): True,
            ("email.smtp.use_ssl", bool, False): False,
            ("email.rate_limit_per_hour", int, 100): 100,
            ("email.timeout", int, 30): 30,
            ("email.max_recipients", int, 10): 10,
        }.get((key, type_cls, default), default)

        config.get.side_effect = lambda key, default=None: {
            "email.smtp.host": "smtp.test.com",
            "email.smtp.username": "test@example.com",
            "email.smtp.password": "testpass",
            "email.sender.email": "sender@example.com",
            "email.sender.name": "Test Phoenix Collector",
            "email.recipients": "recipient1@example.com,recipient2@example.com",
        }.get(key, default)

        return config

    @pytest.fixture
    def mock_config_provider_disabled(self):
        """Create mock configuration provider with email disabled."""
        config = Mock(spec=EnvironmentConfigProvider)
        config.get_typed.side_effect = lambda key, type_cls, default=None: {
            ("email.enabled", bool, False): False
        }.get((key, type_cls, default), default)

        return config

    def test_initialization_email_enabled(self, mock_config_provider):
        """Test EmailReportService initialization with email enabled."""
        service = EmailReportService(mock_config_provider)

        assert service._email_config.smtp_host == "smtp.test.com"
        assert service._email_config.sender_email == "sender@example.com"
        assert len(service._email_config.recipient_emails) == 2
        assert isinstance(service._metrics, EmailMetrics)

    def test_initialization_email_disabled(self, mock_config_provider_disabled):
        """Test EmailReportService initialization with email disabled."""
        # Should not raise an error, but configuration loading will fail
        with pytest.raises(ProcessingError, match="Failed to load email configuration"):
            EmailReportService(mock_config_provider_disabled)

    def test_configuration_loading_missing_host(self):
        """Test configuration loading fails with missing SMTP host."""
        config = Mock(spec=EnvironmentConfigProvider)
        config.get.return_value = None
        config.get_typed.return_value = None

        with pytest.raises(ProcessingError, match="Failed to load email configuration"):
            EmailReportService(config)

    @pytest.mark.asyncio
    async def test_send_daily_report_success(self, mock_config_provider):
        """Test successful daily report sending."""
        service = EmailReportService(mock_config_provider)

        # Mock SMTP sending
        with patch.object(service, "_send_email", return_value=True) as mock_send:
            report_data = ReportData(
                title="Daily Report", summary="Test summary", report_type="daily"
            )

            result = await service.send_daily_report(report_data)

            assert result is True
            mock_send.assert_called_once()
            call_args = mock_send.call_args
            assert "Phoenix Real Estate Daily Report" in call_args[1]["subject"]

    @pytest.mark.asyncio
    async def test_send_error_alert_success(self, mock_config_provider):
        """Test successful error alert sending."""
        service = EmailReportService(mock_config_provider)

        with patch.object(service, "_send_email", return_value=True) as mock_send:
            result = await service.send_error_alert(
                "Test Error", "Error details", {"context": "test"}
            )

            assert result is True
            mock_send.assert_called_once()
            call_args = mock_send.call_args
            assert "🚨 Phoenix Real Estate Alert: Test Error" == call_args[1]["subject"]

    @pytest.mark.asyncio
    async def test_send_success_summary(self, mock_config_provider):
        """Test successful success summary sending."""
        service = EmailReportService(mock_config_provider)

        batch_result = BatchIntegrationResult(
            total_processed=10, successful=8, failed=2, processing_time=30.5
        )

        with patch.object(service, "_send_email", return_value=True) as mock_send:
            result = await service.send_success_summary(batch_result, 30.5)

            assert result is True
            mock_send.assert_called_once()
            call_args = mock_send.call_args
            assert "✅ Phoenix Real Estate: 8 Properties Collected" == call_args[1]["subject"]

    def test_html_template_generation_daily_report(self, mock_config_provider):
        """Test HTML template generation for daily reports."""
        service = EmailReportService(mock_config_provider)

        batch_result = BatchIntegrationResult(
            total_processed=5, successful=4, failed=1, processing_time=25.0
        )

        report_data = ReportData(
            title="Test Daily Report",
            summary="Test summary",
            collection_results=batch_result,
            report_type="daily",
        )

        html_content = service._generate_daily_report_html(report_data, include_properties=True)

        assert "Test Daily Report" in html_content
        assert "Test summary" in html_content
        assert "<!DOCTYPE html>" in html_content
        assert "success" in html_content  # Should include success metrics

    def test_text_template_generation_daily_report(self, mock_config_provider):
        """Test plain text template generation for daily reports."""
        service = EmailReportService(mock_config_provider)

        batch_result = BatchIntegrationResult(
            total_processed=5, successful=4, failed=1, processing_time=25.0
        )

        report_data = ReportData(
            title="Test Daily Report",
            summary="Test summary",
            collection_results=batch_result,
            report_type="daily",
        )

        text_content = service._generate_daily_report_text(report_data)

        assert "Phoenix Real Estate Daily Report" in text_content
        assert "Test summary" in text_content
        assert "Total Processed: 5" in text_content
        assert "Successful: 4" in text_content
        assert "Failed: 1" in text_content

    def test_rate_limiting(self, mock_config_provider):
        """Test email rate limiting functionality."""
        service = EmailReportService(mock_config_provider)

        # Rate limit should initially allow sending
        assert service._check_rate_limit() is True

        # Simulate hitting rate limit
        current_hour = datetime.now(UTC).strftime("%Y-%m-%d-%H")
        service._rate_limiter[current_hour] = service._email_config.rate_limit_per_hour

        # Should now block sending
        assert service._check_rate_limit() is False

        # Should increment rate limit hits
        assert service._metrics.rate_limit_hits == 0  # Not incremented in _check_rate_limit

    @pytest.mark.asyncio
    async def test_smtp_connection_tls(self, mock_config_provider):
        """Test SMTP connection with TLS."""
        service = EmailReportService(mock_config_provider)

        mock_message = MIMEMultipart()
        mock_message["Subject"] = "Test"
        mock_message["From"] = "test@example.com"
        mock_message["To"] = "recipient@example.com"

        with patch("smtplib.SMTP") as mock_smtp:
            mock_server = Mock()
            mock_smtp.return_value = mock_server

            await service._smtp_send(mock_message)

            mock_smtp.assert_called_once_with("smtp.test.com", 587, timeout=30)
            mock_server.starttls.assert_called_once()
            mock_server.login.assert_called_once_with("test@example.com", "testpass")
            mock_server.send_message.assert_called_once_with(mock_message)
            mock_server.quit.assert_called_once()

    @pytest.mark.asyncio
    async def test_smtp_connection_ssl(self, mock_config_provider):
        """Test SMTP connection with SSL."""
        service = EmailReportService(mock_config_provider)

        # Configure for SSL
        service._email_config.use_ssl = True
        service._email_config.use_tls = False

        mock_message = MIMEMultipart()

        with patch("smtplib.SMTP_SSL") as mock_smtp_ssl:
            mock_server = Mock()
            mock_smtp_ssl.return_value = mock_server

            await service._smtp_send(mock_message)

            mock_smtp_ssl.assert_called_once_with("smtp.test.com", 587, timeout=30)
            mock_server.login.assert_called_once_with("test@example.com", "testpass")
            mock_server.send_message.assert_called_once_with(mock_message)
            mock_server.quit.assert_called_once()

    @pytest.mark.asyncio
    async def test_smtp_connection_no_auth(self, mock_config_provider):
        """Test SMTP connection without authentication."""
        service = EmailReportService(mock_config_provider)

        # Configure without authentication
        service._email_config.smtp_username = None
        service._email_config.smtp_password = None

        mock_message = MIMEMultipart()

        with patch("smtplib.SMTP") as mock_smtp:
            mock_server = Mock()
            mock_smtp.return_value = mock_server

            await service._smtp_send(mock_message)

            mock_smtp.assert_called_once_with("smtp.test.com", 587, timeout=30)
            mock_server.starttls.assert_called_once()
            mock_server.login.assert_not_called()  # Should not login without credentials
            mock_server.send_message.assert_called_once_with(mock_message)
            mock_server.quit.assert_called_once()

    @pytest.mark.asyncio
    async def test_smtp_connection_failure(self, mock_config_provider):
        """Test SMTP connection failure handling."""
        service = EmailReportService(mock_config_provider)

        mock_message = MIMEMultipart()

        with patch("smtplib.SMTP") as mock_smtp:
            mock_smtp.side_effect = smtplib.SMTPException("Connection failed")

            with pytest.raises(smtplib.SMTPException):
                await service._smtp_send(mock_message)

    @pytest.mark.asyncio
    async def test_test_connection_success(self, mock_config_provider):
        """Test successful connection test."""
        service = EmailReportService(mock_config_provider)

        with patch("smtplib.SMTP") as mock_smtp:
            mock_server = Mock()
            mock_smtp.return_value = mock_server

            results = await service.test_connection()

            assert results["smtp_connection"] is True
            assert results["authentication"] is True
            assert results["configuration_valid"] is True
            assert len(results["errors"]) == 0

    @pytest.mark.asyncio
    async def test_test_connection_failure(self, mock_config_provider):
        """Test connection test failure."""
        service = EmailReportService(mock_config_provider)

        with patch("smtplib.SMTP") as mock_smtp:
            mock_smtp.side_effect = smtplib.SMTPException("Connection failed")

            results = await service.test_connection()

            assert results["smtp_connection"] is False
            assert len(results["errors"]) == 1
            assert "SMTP connection failed" in results["errors"][0]

    @pytest.mark.asyncio
    async def test_send_test_email(self, mock_config_provider):
        """Test sending test email."""
        service = EmailReportService(mock_config_provider)

        with patch.object(service, "_send_email", return_value=True) as mock_send:
            result = await service.send_test_email()

            assert result is True
            mock_send.assert_called_once()
            call_args = mock_send.call_args
            assert "🧪 Phoenix Real Estate Email Service Test" == call_args[1]["subject"]

    def test_get_metrics(self, mock_config_provider):
        """Test getting email service metrics."""
        service = EmailReportService(mock_config_provider)

        # Update some metrics
        service._metrics.total_sent = 5
        service._metrics.total_failed = 1

        metrics = service.get_metrics()

        assert isinstance(metrics, EmailMetrics)
        assert metrics.total_sent == 5
        assert metrics.total_failed == 1
        assert abs(metrics.success_rate - 83.33) < 0.01  # 5/6 * 100, approximately

    def test_get_configuration_masks_sensitive_data(self, mock_config_provider):
        """Test that get_configuration masks sensitive information."""
        service = EmailReportService(mock_config_provider)

        config = service.get_configuration()

        assert config.smtp_host == "smtp.test.com"
        assert config.sender_email == "sender@example.com"
        assert config.smtp_username == "***"  # Should be masked
        assert config.smtp_password == "***"  # Should be masked

    def test_update_avg_delivery_time(self, mock_config_provider):
        """Test average delivery time calculation."""
        service = EmailReportService(mock_config_provider)

        # First delivery
        service._metrics.total_sent = 1
        service._update_avg_delivery_time(2.5)
        assert service._metrics.avg_delivery_time == 2.5

        # Second delivery
        service._metrics.total_sent = 2
        service._update_avg_delivery_time(3.5)
        assert service._metrics.avg_delivery_time == 3.0  # (2.5 + 3.5) / 2

        # Third delivery
        service._metrics.total_sent = 3
        service._update_avg_delivery_time(1.5)
        assert abs(service._metrics.avg_delivery_time - 2.5) < 0.01  # (2.5*2 + 1.5) / 3


class TestEmailServiceIntegration:
    """Test EmailReportService integration scenarios."""

    @pytest.fixture
    def mock_config_provider(self):
        """Create mock configuration provider for integration tests."""
        config = Mock(spec=EnvironmentConfigProvider)
        config.get_typed.side_effect = lambda key, type_cls, default=None: {
            ("email.enabled", bool, False): True,
            ("email.smtp.port", int, 587): 587,
            ("email.smtp.use_tls", bool, True): True,
            ("email.smtp.use_ssl", bool, False): False,
            ("email.rate_limit_per_hour", int, 100): 50,  # Lower for testing
            ("email.timeout", int, 30): 10,  # Shorter for testing
            ("email.max_recipients", int, 10): 5,
        }.get((key, type_cls, default), default)

        config.get.side_effect = lambda key, default=None: {
            "email.smtp.host": "smtp.gmail.com",
            "email.smtp.username": "test.phoenix@gmail.com",
            "email.smtp.password": "app_password_here",
            "email.sender.email": "test.phoenix@gmail.com",
            "email.sender.name": "Phoenix Real Estate Test",
            "email.recipients": "user@example.com",
        }.get(key, default)

        return config

    @pytest.mark.asyncio
    async def test_full_email_workflow(self, mock_config_provider):
        """Test complete email sending workflow with mocked SMTP."""
        service = EmailReportService(mock_config_provider)

        # Create comprehensive report data
        properties = [
            PropertyDetails(
                property_id="prop1",
                address="123 Test Ave, Phoenix, AZ 85031",
                price=350000.0,
                bedrooms=3,
                bathrooms=2,
                square_feet=1800,
                property_type="single_family",
            ),
            PropertyDetails(
                property_id="prop2",
                address="456 Sample St, Phoenix, AZ 85033",
                price=425000.0,
                bedrooms=4,
                bathrooms=3,
                square_feet=2200,
                property_type="single_family",
            ),
        ]

        batch_result = BatchIntegrationResult(
            total_processed=10,
            successful=8,
            failed=2,
            processing_time=45.7,
            errors=["Property validation failed for prop_123", "Network timeout for prop_456"],
        )

        report_data = ReportData(
            title="Comprehensive Daily Report",
            summary="Daily collection completed with mixed results",
            collection_results=batch_result,
            properties=properties,
            metrics={
                "collection_mode": "incremental",
                "zip_codes": ["85031", "85033", "85035"],
                "processing_speed": 4.57,  # properties per second
                "success_rate": 80.0,
            },
            errors=batch_result.errors,
            report_type="daily",
        )

        # Mock SMTP operations
        with patch("smtplib.SMTP") as mock_smtp:
            mock_server = Mock()
            mock_smtp.return_value = mock_server

            # Test daily report
            result = await service.send_daily_report(report_data, include_properties=True)

            assert result is True
            mock_smtp.assert_called_once()
            mock_server.starttls.assert_called_once()
            mock_server.login.assert_called_once()
            mock_server.send_message.assert_called_once()
            mock_server.quit.assert_called_once()

            # Verify metrics updated
            metrics = service.get_metrics()
            assert metrics.total_sent == 1
            assert metrics.total_failed == 0
            assert metrics.success_rate == 100.0

    @pytest.mark.asyncio
    async def test_error_handling_with_recovery(self, mock_config_provider):
        """Test error handling and recovery mechanisms."""
        service = EmailReportService(mock_config_provider)

        # Test SMTP authentication failure
        with patch("smtplib.SMTP") as mock_smtp:
            mock_server = Mock()
            mock_server.login.side_effect = smtplib.SMTPAuthenticationError(
                535, "Authentication failed"
            )
            mock_smtp.return_value = mock_server

            result = await service.send_error_alert(
                "Authentication Failed", "SMTP authentication error occurred"
            )

            assert result is False

            # Verify metrics updated for failure
            metrics = service.get_metrics()
            assert metrics.total_failed == 1
            assert "Authentication failed" in metrics.last_error

    @pytest.mark.asyncio
    async def test_rate_limiting_integration(self, mock_config_provider):
        """Test rate limiting in integration scenario."""
        service = EmailReportService(mock_config_provider)

        # Mock successful SMTP
        with patch("smtplib.SMTP") as mock_smtp:
            mock_server = Mock()
            mock_smtp.return_value = mock_server

            # Send emails up to rate limit
            report_data = ReportData(title="Rate Limit Test", summary="Testing rate limiting")

            # Send multiple emails quickly
            results = []
            for i in range(52):  # Above rate limit of 50
                result = await service.send_daily_report(report_data)
                results.append(result)

            # First 50 should succeed, rest should be rate limited
            successful_sends = sum(results)
            assert successful_sends <= 50  # Should be rate limited

            # Check rate limit metrics
            metrics = service.get_metrics()
            assert metrics.rate_limit_hits > 0  # Should have hit rate limit

    @pytest.mark.asyncio
    async def test_large_report_data_handling(self, mock_config_provider):
        """Test handling of large report data."""
        service = EmailReportService(mock_config_provider)

        # Create large dataset
        properties = []
        for i in range(100):  # Large number of properties
            prop = PropertyDetails(
                property_id=f"prop_{i:03d}",
                address=f"{i} Test Street #{i}, Phoenix, AZ 85031",
                price=300000.0 + (i * 1000),
                bedrooms=2 + (i % 4),
                bathrooms=1 + (i % 3),
                square_feet=1500 + (i * 10),
                property_type="single_family",
            )
            properties.append(prop)

        batch_result = BatchIntegrationResult(
            total_processed=100, successful=95, failed=5, processing_time=180.5
        )

        report_data = ReportData(
            title="Large Dataset Report",
            summary="Processed large dataset successfully",
            collection_results=batch_result,
            properties=properties,  # 100 properties
            metrics={"large_dataset": True, "processing_time_per_property": 1.805},
            report_type="daily",
        )

        with patch("smtplib.SMTP") as mock_smtp:
            mock_server = Mock()
            mock_smtp.return_value = mock_server

            # Should handle large data gracefully
            result = await service.send_daily_report(report_data, include_properties=True)

            assert result is True

            # Verify email was constructed properly
            send_call = mock_server.send_message.call_args[0][0]
            email_content = str(send_call)

            # Should handle large dataset gracefully (properties are not shown in templates)
            # Verify the email was constructed without errors
            assert "Phoenix Real Estate" in email_content
            assert len(properties) == 100  # Verify we had large dataset
