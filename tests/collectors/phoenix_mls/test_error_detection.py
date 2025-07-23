"""Test suite for Phoenix MLS error pattern detection.

Tests for site-specific error detection patterns including rate limiting,
blocked IPs, session expiration, and other common scenarios.
"""

import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime, UTC
from playwright.async_api import Page, Response

from phoenix_real_estate.collectors.phoenix_mls.error_detection import (
    ErrorDetector,
    ErrorPattern,
    ErrorType,
    DetectedError,
    RateLimitDetectedError,
    BlockedIPDetectedError,
    SessionExpiredDetectedError,
    CaptchaDetectedError,
    MaintenanceDetectedError,
)


class TestErrorPattern:
    """Test cases for ErrorPattern class."""

    def test_error_pattern_creation(self):
        """Test creating an error pattern."""
        pattern = ErrorPattern(
            error_type=ErrorType.RATE_LIMIT,
            name="rate_limit_429",
            patterns={
                "status_code": [429],
                "response_headers": {"x-ratelimit-remaining": "0"},
                "body_text": ["rate limit exceeded", "too many requests"],
            },
            confidence=0.95,
        )

        assert pattern.error_type == ErrorType.RATE_LIMIT
        assert pattern.name == "rate_limit_429"
        assert 429 in pattern.patterns["status_code"]
        assert pattern.confidence == 0.95

    def test_error_pattern_match_status_code(self):
        """Test matching error pattern by status code."""
        pattern = ErrorPattern(
            error_type=ErrorType.RATE_LIMIT,
            name="rate_limit_429",
            patterns={"status_code": [429]},
            confidence=1.0,
        )

        response_data = {"status_code": 429}
        assert pattern.matches(response_data) is True

        response_data = {"status_code": 200}
        assert pattern.matches(response_data) is False

    def test_error_pattern_match_headers(self):
        """Test matching error pattern by headers."""
        pattern = ErrorPattern(
            error_type=ErrorType.RATE_LIMIT,
            name="rate_limit_headers",
            patterns={
                "response_headers": {
                    "x-ratelimit-remaining": "0",
                    "retry-after": lambda v: int(v) > 0,
                }
            },
            confidence=0.9,
        )

        response_data = {"response_headers": {"x-ratelimit-remaining": "0", "retry-after": "60"}}
        assert pattern.matches(response_data) is True

        response_data = {"response_headers": {"x-ratelimit-remaining": "100", "retry-after": "0"}}
        assert pattern.matches(response_data) is False

    def test_error_pattern_match_body_text(self):
        """Test matching error pattern by body text."""
        pattern = ErrorPattern(
            error_type=ErrorType.BLOCKED_IP,
            name="cloudflare_block",
            patterns={"body_text": ["cloudflare", "access denied", "blocked"]},
            confidence=0.85,
        )

        response_data = {"body_text": "You have been blocked by Cloudflare protection"}
        assert pattern.matches(response_data) is True

        response_data = {"body_text": "Welcome to Phoenix MLS"}
        assert pattern.matches(response_data) is False

    def test_error_pattern_match_selectors(self):
        """Test matching error pattern by CSS selectors."""
        pattern = ErrorPattern(
            error_type=ErrorType.CAPTCHA,
            name="recaptcha_challenge",
            patterns={"css_selectors": [".g-recaptcha", "#recaptcha", "iframe[src*='recaptcha']"]},
            confidence=0.95,
        )

        response_data = {"found_selectors": [".g-recaptcha", ".captcha-container"]}
        assert pattern.matches(response_data) is True

        response_data = {"found_selectors": [".property-list", ".search-form"]}
        assert pattern.matches(response_data) is False

    def test_error_pattern_match_url(self):
        """Test matching error pattern by URL."""
        pattern = ErrorPattern(
            error_type=ErrorType.SESSION_EXPIRED,
            name="login_redirect",
            patterns={"url_patterns": ["/login", "/signin", "/auth/expired"]},
            confidence=0.9,
        )

        response_data = {"current_url": "https://www.phoenixmlssearch.com/login?return_to=/search"}
        assert pattern.matches(response_data) is True

        response_data = {"current_url": "https://www.phoenixmlssearch.com/search/results"}
        assert pattern.matches(response_data) is False

    def test_error_pattern_combined_conditions(self):
        """Test matching with multiple conditions."""
        pattern = ErrorPattern(
            error_type=ErrorType.RATE_LIMIT,
            name="rate_limit_combined",
            patterns={
                "status_code": [429, 503],
                "body_text": ["rate limit", "too many requests"],
                "response_headers": {"retry-after": lambda v: True},
            },
            confidence=0.95,
        )

        # All conditions match
        response_data = {
            "status_code": 429,
            "body_text": "Rate limit exceeded",
            "response_headers": {"retry-after": "60"},
        }
        assert pattern.matches(response_data) is True

        # Only some conditions match
        response_data = {
            "status_code": 429,
            "body_text": "Error occurred",
            "response_headers": {"content-type": "text/html"},
        }
        assert pattern.matches(response_data) is False


class TestDetectedError:
    """Test cases for DetectedError classes."""

    def test_detected_error_creation(self):
        """Test creating a detected error."""
        error = DetectedError(
            error_type=ErrorType.RATE_LIMIT,
            pattern_name="rate_limit_429",
            confidence=0.95,
            context={
                "status_code": 429,
                "retry_after": 60,
                "url": "https://www.phoenixmlssearch.com/api/search",
            },
            timestamp=datetime.now(UTC),
        )

        assert error.error_type == ErrorType.RATE_LIMIT
        assert error.pattern_name == "rate_limit_429"
        assert error.confidence == 0.95
        assert error.context["retry_after"] == 60
        assert error.timestamp is not None

    def test_rate_limit_detected_error(self):
        """Test RateLimitDetectedError specific functionality."""
        error = RateLimitDetectedError(
            pattern_name="rate_limit_headers",
            confidence=0.9,
            context={"retry_after": "300", "rate_limit": "1000", "rate_remaining": "0"},
        )

        assert error.error_type == ErrorType.RATE_LIMIT
        assert error.retry_after == 300
        assert error.suggested_action == "wait"
        assert error.wait_seconds == 300

    def test_blocked_ip_detected_error(self):
        """Test BlockedIPDetectedError specific functionality."""
        error = BlockedIPDetectedError(
            pattern_name="cloudflare_block",
            confidence=0.85,
            context={"block_type": "cloudflare", "proxy_used": "proxy1.example.com"},
        )

        assert error.error_type == ErrorType.BLOCKED_IP
        assert error.block_type == "cloudflare"
        assert error.suggested_action == "switch_proxy"
        assert error.requires_proxy_switch is True

    def test_session_expired_detected_error(self):
        """Test SessionExpiredDetectedError specific functionality."""
        error = SessionExpiredDetectedError(
            pattern_name="login_redirect",
            confidence=0.9,
            context={"redirect_url": "/login", "original_url": "/search"},
        )

        assert error.error_type == ErrorType.SESSION_EXPIRED
        assert error.redirect_url == "/login"
        assert error.suggested_action == "re_authenticate"
        assert error.requires_new_session is True

    def test_captcha_detected_error(self):
        """Test CaptchaDetectedError specific functionality."""
        error = CaptchaDetectedError(
            pattern_name="recaptcha_v2",
            confidence=0.95,
            context={"captcha_type": "recaptcha_v2", "selector": ".g-recaptcha"},
        )

        assert error.error_type == ErrorType.CAPTCHA
        assert error.captcha_type == "recaptcha_v2"
        assert error.suggested_action == "solve_captcha"
        assert error.requires_human_intervention is True

    def test_maintenance_detected_error(self):
        """Test MaintenanceDetectedError specific functionality."""
        error = MaintenanceDetectedError(
            pattern_name="scheduled_maintenance",
            confidence=0.8,
            context={"maintenance_message": "Site under maintenance", "estimated_time": "2 hours"},
        )

        assert error.error_type == ErrorType.MAINTENANCE
        assert error.maintenance_message == "Site under maintenance"
        assert error.suggested_action == "wait_long"
        assert error.estimated_wait_minutes == 120


class TestErrorDetector:
    """Test cases for ErrorDetector class."""

    @pytest.fixture
    def error_detector(self):
        """Create an ErrorDetector instance."""
        return ErrorDetector()

    @pytest.fixture
    def mock_page(self):
        """Create a mock Playwright page."""
        page = Mock(spec=Page)
        page.url = "https://www.phoenixmlssearch.com/search"
        page.content = AsyncMock(return_value="<html><body>Welcome</body></html>")
        page.query_selector = AsyncMock(return_value=None)
        page.query_selector_all = AsyncMock(return_value=[])
        return page

    @pytest.fixture
    def mock_response(self):
        """Create a mock Playwright response."""
        response = Mock(spec=Response)
        response.status = 200
        response.headers = {"content-type": "text/html"}
        response.url = "https://www.phoenixmlssearch.com"
        response.text = AsyncMock(return_value="Welcome to Phoenix MLS")
        return response

    @pytest.mark.asyncio
    async def test_detect_from_response_rate_limit(self, error_detector, mock_response):
        """Test detecting rate limit from response."""
        mock_response.status = 429
        mock_response.headers = {"x-ratelimit-remaining": "0", "retry-after": "60"}
        mock_response.text = AsyncMock(return_value="Rate limit exceeded")

        errors = await error_detector.detect_from_response(mock_response)

        assert len(errors) > 0
        rate_limit_error = next((e for e in errors if e.error_type == ErrorType.RATE_LIMIT), None)
        assert rate_limit_error is not None
        assert rate_limit_error.retry_after == 60

    @pytest.mark.asyncio
    async def test_detect_from_response_cloudflare(self, error_detector, mock_response):
        """Test detecting Cloudflare block from response."""
        mock_response.status = 403
        mock_response.text = AsyncMock(
            return_value="<html><head><title>Access denied | www.phoenixmlssearch.com used Cloudflare to restrict access</title></head></html>"
        )

        errors = await error_detector.detect_from_response(mock_response)

        assert len(errors) > 0
        blocked_error = next((e for e in errors if e.error_type == ErrorType.BLOCKED_IP), None)
        assert blocked_error is not None
        assert blocked_error.block_type == "cloudflare"

    @pytest.mark.asyncio
    async def test_detect_from_page_captcha(self, error_detector, mock_page):
        """Test detecting CAPTCHA from page."""

        def query_selector_side_effect(selector):
            if selector == ".g-recaptcha":
                return Mock()  # Found .g-recaptcha
            return None  # No other selectors

        mock_page.query_selector = AsyncMock(side_effect=query_selector_side_effect)
        mock_page.content = AsyncMock(
            return_value='<html><body><div class="g-recaptcha"></div></body></html>'
        )

        errors = await error_detector.detect_from_page(mock_page)

        assert len(errors) > 0
        captcha_error = next((e for e in errors if e.error_type == ErrorType.CAPTCHA), None)
        assert captcha_error is not None
        assert captcha_error.captcha_type == "recaptcha"

    @pytest.mark.asyncio
    async def test_detect_from_page_session_expired(self, error_detector, mock_page):
        """Test detecting session expiration from page."""
        mock_page.url = "https://www.phoenixmlssearch.com/login?return_to=/search"

        def query_selector_side_effect(selector):
            if selector == ".login-form":
                return Mock()  # Found .login-form
            return None  # No other selectors

        mock_page.query_selector = AsyncMock(side_effect=query_selector_side_effect)

        errors = await error_detector.detect_from_page(mock_page)

        assert len(errors) > 0
        session_error = next((e for e in errors if e.error_type == ErrorType.SESSION_EXPIRED), None)
        assert session_error is not None
        assert "/login" in session_error.redirect_url

    @pytest.mark.asyncio
    async def test_detect_maintenance(self, error_detector, mock_response):
        """Test detecting maintenance mode."""
        mock_response.status = 503
        mock_response.headers = {"content-type": "text/html"}
        mock_response.url = "https://www.phoenixmlssearch.com"
        mock_response.text = AsyncMock(
            return_value="<html><body><h1>Site Maintenance</h1><p>We'll be back in 2 hours</p></body></html>"
        )

        errors = await error_detector.detect_from_response(mock_response)

        assert len(errors) > 0
        maintenance_error = next((e for e in errors if e.error_type == ErrorType.MAINTENANCE), None)
        assert maintenance_error is not None
        assert "maintenance" in maintenance_error.maintenance_message.lower()

    @pytest.mark.asyncio
    async def test_detect_multiple_errors(self, error_detector, mock_response):
        """Test detecting multiple error patterns."""
        mock_response.status = 429
        mock_response.headers = {
            "x-ratelimit-remaining": "0",
            "retry-after": "300",
            "cf-ray": "123456789",  # Cloudflare header
        }
        mock_response.text = AsyncMock(return_value="Rate limit exceeded. Protected by Cloudflare.")

        errors = await error_detector.detect_from_response(mock_response)

        assert len(errors) >= 2
        error_types = {e.error_type for e in errors}
        assert ErrorType.RATE_LIMIT in error_types
        assert ErrorType.BLOCKED_IP in error_types

    @pytest.mark.asyncio
    async def test_detect_no_errors(self, error_detector, mock_response):
        """Test normal response with no errors."""
        mock_response.status = 200
        mock_response.text = AsyncMock(
            return_value="<html><body><div class='property-list'>Properties found</div></body></html>"
        )

        errors = await error_detector.detect_from_response(mock_response)

        assert len(errors) == 0

    def test_add_custom_pattern(self, error_detector):
        """Test adding custom error pattern."""
        custom_pattern = ErrorPattern(
            error_type=ErrorType.BLOCKED_IP,
            name="custom_block",
            patterns={"body_text": ["custom block message"], "status_code": [451]},
            confidence=0.8,
        )

        error_detector.add_pattern(custom_pattern)

        # Verify pattern was added
        patterns = error_detector.get_patterns_by_type(ErrorType.BLOCKED_IP)
        assert any(p.name == "custom_block" for p in patterns)

    def test_remove_pattern(self, error_detector):
        """Test removing an error pattern."""
        # First add a custom pattern
        custom_pattern = ErrorPattern(
            error_type=ErrorType.BLOCKED_IP,
            name="temp_pattern",
            patterns={"status_code": [999]},
            confidence=0.5,
        )
        error_detector.add_pattern(custom_pattern)

        # Then remove it
        removed = error_detector.remove_pattern("temp_pattern")
        assert removed is True

        # Verify it was removed
        patterns = error_detector.get_patterns_by_type(ErrorType.BLOCKED_IP)
        assert not any(p.name == "temp_pattern" for p in patterns)

    def test_get_suggested_action(self, error_detector):
        """Test getting suggested action for detected errors."""
        errors = [
            RateLimitDetectedError(
                pattern_name="rate_limit", confidence=0.9, context={"retry_after": "60"}
            ),
            BlockedIPDetectedError(
                pattern_name="cloudflare", confidence=0.8, context={"block_type": "cloudflare"}
            ),
        ]

        action = error_detector.get_suggested_action(errors)

        # Should prioritize rate limit wait over proxy switch
        assert action["action"] == "wait"
        assert action["wait_seconds"] == 60
        assert action["reason"] == "rate_limit"
