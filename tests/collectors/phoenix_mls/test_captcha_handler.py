"""Tests for Phoenix MLS captcha detection and handling functionality.

This module tests the captcha detection, handling, and resolution mechanisms
for the Phoenix MLS scraper, including integration with captcha solving services.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, UTC

from phoenix_real_estate.collectors.phoenix_mls.captcha_handler import (
    CaptchaHandler,
    CaptchaSolvingError,
    CaptchaType,
    CaptchaSolution,
)
from phoenix_real_estate.foundation.utils.exceptions import ConfigurationError


class TestCaptchaHandler:
    """Test suite for CaptchaHandler functionality."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration for testing."""
        return {
            "enabled": True,
            "service": "2captcha",
            "api_key": "test_api_key_123",
            "timeout": 120,
            "max_retries": 3,
            "detection": {
                "selectors": [
                    "iframe[src*='recaptcha']",
                    ".g-recaptcha",
                    "#recaptcha",
                    "div[data-captcha]",
                    ".captcha-container",
                ],
                "keywords": ["captcha", "verification", "human"],
                "response_codes": [403, 429],
            },
        }

    @pytest.fixture
    def captcha_handler(self, mock_config):
        """Create a CaptchaHandler instance for testing."""
        return CaptchaHandler(mock_config)

    @pytest.fixture
    def mock_page(self):
        """Create a mock Playwright page object."""
        page = AsyncMock()
        page.url = "https://phoenixmlssearch.com/search"
        page.query_selector = AsyncMock()
        page.query_selector_all = AsyncMock()
        page.content = AsyncMock()
        page.evaluate = AsyncMock()
        page.wait_for_selector = AsyncMock()
        page.click = AsyncMock()
        page.fill = AsyncMock()
        page.screenshot = AsyncMock()
        return page

    @pytest.mark.asyncio
    async def test_initialization_with_valid_config(self, mock_config):
        """Test CaptchaHandler initialization with valid configuration."""
        handler = CaptchaHandler(mock_config)

        assert handler.enabled is True
        assert handler.service == "2captcha"
        assert handler.api_key == "test_api_key_123"
        assert handler.timeout == 120
        assert handler.max_retries == 3
        assert len(handler.detection_selectors) == 5
        assert len(handler.detection_keywords) == 3
        assert 403 in handler.detection_response_codes

    def test_initialization_disabled(self):
        """Test CaptchaHandler initialization when disabled."""
        config = {"enabled": False}
        handler = CaptchaHandler(config)

        assert handler.enabled is False
        assert handler.service is None
        assert handler.api_key is None

    def test_initialization_missing_api_key(self):
        """Test initialization fails with missing API key when enabled."""
        config = {"enabled": True, "service": "2captcha"}

        with pytest.raises(ConfigurationError, match="API key not provided"):
            CaptchaHandler(config)

    @pytest.mark.asyncio
    async def test_detect_captcha_by_selector(self, captcha_handler, mock_page):
        """Test captcha detection by selector match."""
        # Mock finding a reCAPTCHA iframe
        mock_page.query_selector.return_value = MagicMock()

        detected = await captcha_handler.detect_captcha(mock_page)

        assert detected is True
        assert captcha_handler.stats["captchas_detected"] == 1
        mock_page.query_selector.assert_called()

    @pytest.mark.asyncio
    async def test_detect_captcha_by_keyword(self, captcha_handler, mock_page):
        """Test captcha detection by keyword in page content."""
        # No selector matches
        mock_page.query_selector.return_value = None

        # But page content contains captcha keyword
        mock_page.content.return_value = """
        <html>
            <body>
                <div>Please complete the captcha verification</div>
            </body>
        </html>
        """

        detected = await captcha_handler.detect_captcha(mock_page)

        assert detected is True
        assert captcha_handler.stats["captchas_detected"] == 1

    @pytest.mark.asyncio
    async def test_detect_no_captcha(self, captcha_handler, mock_page):
        """Test when no captcha is detected."""
        # No selector matches
        mock_page.query_selector.return_value = None

        # Page content doesn't contain keywords
        mock_page.content.return_value = """
        <html>
            <body>
                <div>Property listings</div>
            </body>
        </html>
        """

        detected = await captcha_handler.detect_captcha(mock_page)

        assert detected is False
        assert captcha_handler.stats["captchas_detected"] == 0

    @pytest.mark.asyncio
    async def test_identify_captcha_type_recaptcha_v2(self, captcha_handler, mock_page):
        """Test identification of reCAPTCHA v2."""
        # Mock finding reCAPTCHA v2 elements - return element for first selector
        async def query_selector_side_effect(selector):
            if "iframe" in selector and "recaptcha" in selector:
                return MagicMock()  # Found iframe
            return None

        mock_page.query_selector.side_effect = query_selector_side_effect
        mock_page.evaluate.return_value = "test-site-key-123"

        captcha_type, metadata = await captcha_handler.identify_captcha_type(mock_page)

        assert captcha_type == CaptchaType.RECAPTCHA_V2
        assert metadata["sitekey"] == "test-site-key-123"
        assert metadata["page_url"] == "https://phoenixmlssearch.com/search"

    @pytest.mark.asyncio
    async def test_identify_captcha_type_recaptcha_v3(self, captcha_handler, mock_page):
        """Test identification of reCAPTCHA v3."""

        # No v2 elements found
        async def query_selector_side_effect(selector):
            if "recaptcha" in selector and "iframe" not in selector:
                return None
            return None

        mock_page.query_selector.side_effect = query_selector_side_effect

        # Mock the evaluate call to return the v3 script sitekey
        mock_page.evaluate.return_value = "test-v3-key-456"

        captcha_type, metadata = await captcha_handler.identify_captcha_type(mock_page)

        assert captcha_type == CaptchaType.RECAPTCHA_V3
        assert metadata["sitekey"] == "test-v3-key-456"
        assert metadata["action"] == "submit"
        assert metadata["min_score"] == 0.7

    @pytest.mark.asyncio
    async def test_identify_captcha_type_image(self, captcha_handler, mock_page):
        """Test identification of image captcha."""
        # No reCAPTCHA elements found in initial checks
        async def query_selector_side_effect(selector):
            # Return None for reCAPTCHA selectors
            if "recaptcha" in selector or "hcaptcha" in selector:
                return None
            # Return mock image element for image captcha selectors
            if "captcha" in selector and "img" in selector:
                mock_img_element = MagicMock()
                mock_img_element.get_attribute = AsyncMock(return_value="/captcha/image.png")
                return mock_img_element
            return None

        mock_page.query_selector.side_effect = query_selector_side_effect
        mock_page.evaluate.return_value = None  # No reCAPTCHA v3 script

        captcha_type, metadata = await captcha_handler.identify_captcha_type(mock_page)

        assert captcha_type == CaptchaType.IMAGE
        assert metadata["image_url"].endswith("/captcha/image.png")

    @pytest.mark.asyncio
    async def test_solve_recaptcha_v2_success(self, captcha_handler, mock_page):
        """Test successful reCAPTCHA v2 solving."""
        # Mock the entire _solve_2captcha method instead of trying to mock aiohttp
        async def mock_solve_2captcha(captcha_type, metadata):
            return CaptchaSolution(
                captcha_type=captcha_type,
                token="captcha-solution-token-456",
                metadata={"task_id": "task-id-123"},
                solved_at=datetime.now(UTC),
            )
        
        # Replace the method with our mock
        captcha_handler._solve_2captcha = mock_solve_2captcha

        # Solve captcha
        solution = await captcha_handler.solve_captcha(
            mock_page,
            CaptchaType.RECAPTCHA_V2,
            {"sitekey": "test-key", "page_url": "https://test.com"},
        )

        assert solution.token == "captcha-solution-token-456"
        assert solution.captcha_type == CaptchaType.RECAPTCHA_V2
        assert solution.solved_at is not None
        assert captcha_handler.stats["captchas_solved"] == 1

    @pytest.mark.asyncio
    async def test_solve_captcha_timeout(self, captcha_handler, mock_page):
        """Test captcha solving timeout."""
        # Mock the _solve_2captcha method to simulate timeout
        async def mock_solve_2captcha_timeout(captcha_type, metadata):
            raise CaptchaSolvingError(
                "Captcha solving timeout after 1s",
                service="2captcha",
                context={"task_id": "task-id-123", "timeout": 1}
            )
        
        # Replace the method with our mock
        captcha_handler._solve_2captcha = mock_solve_2captcha_timeout

        with pytest.raises(CaptchaSolvingError, match="timeout"):
            await captcha_handler.solve_captcha(
                mock_page,
                CaptchaType.RECAPTCHA_V2,
                {"sitekey": "test-key", "page_url": "https://test.com"},
            )

        assert captcha_handler.stats["captcha_failures"] == 1

    @pytest.mark.asyncio
    async def test_apply_captcha_solution_recaptcha_v2(self, captcha_handler, mock_page):
        """Test applying reCAPTCHA v2 solution to page."""
        solution = CaptchaSolution(
            captcha_type=CaptchaType.RECAPTCHA_V2,
            token="test-token-123",
            metadata={"callback": "onCaptchaSuccess"},
            solved_at=datetime.now(UTC),
        )

        # Apply solution
        await captcha_handler.apply_captcha_solution(mock_page, solution)

        # Verify JavaScript was executed to inject token
        mock_page.evaluate.assert_called()
        call_args = mock_page.evaluate.call_args[0][0]
        assert "test-token-123" in call_args
        assert "g-recaptcha-response" in call_args

    @pytest.mark.asyncio
    async def test_apply_captcha_solution_image(self, captcha_handler, mock_page):
        """Test applying image captcha solution."""
        solution = CaptchaSolution(
            captcha_type=CaptchaType.IMAGE,
            token="ABC123",
            metadata={"input_selector": "#captcha-input"},
            solved_at=datetime.now(UTC),
        )

        # Mock finding the input element
        mock_input = AsyncMock()
        mock_page.query_selector.return_value = mock_input

        # Apply solution
        await captcha_handler.apply_captcha_solution(mock_page, solution)

        # Verify solution was typed into input
        mock_input.fill.assert_called_with("ABC123")

    @pytest.mark.asyncio
    async def test_handle_captcha_complete_flow(self, captcha_handler, mock_page):
        """Test complete captcha handling flow."""
        # Mock captcha detection
        captcha_handler.detect_captcha = AsyncMock(return_value=True)

        # Mock captcha identification
        captcha_handler.identify_captcha_type = AsyncMock(
            return_value=(CaptchaType.RECAPTCHA_V2, {"sitekey": "test"})
        )

        # Mock solving
        mock_solution = CaptchaSolution(
            captcha_type=CaptchaType.RECAPTCHA_V2,
            token="solved-token",
            metadata={},
            solved_at=datetime.now(UTC),
        )
        captcha_handler.solve_captcha = AsyncMock(return_value=mock_solution)

        # Mock applying solution
        captcha_handler.apply_captcha_solution = AsyncMock()

        # Handle captcha
        result = await captcha_handler.handle_captcha(mock_page)

        assert result is True
        captcha_handler.detect_captcha.assert_called_once()
        captcha_handler.identify_captcha_type.assert_called_once()
        captcha_handler.solve_captcha.assert_called_once()
        captcha_handler.apply_captcha_solution.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_captcha_when_disabled(self, mock_page):
        """Test captcha handling when disabled."""
        config = {"enabled": False}
        handler = CaptchaHandler(config)

        result = await handler.handle_captcha(mock_page)

        assert result is False

    @pytest.mark.asyncio
    async def test_handle_captcha_not_detected(self, captcha_handler, mock_page):
        """Test handling when no captcha is detected."""
        captcha_handler.detect_captcha = AsyncMock(return_value=False)

        result = await captcha_handler.handle_captcha(mock_page)

        assert result is False
        captcha_handler.detect_captcha.assert_called_once()

    def test_get_statistics(self, captcha_handler):
        """Test getting captcha handler statistics."""
        # Set some stats directly on handler
        captcha_handler.stats.update({
            "captchas_detected": 10,
            "captchas_solved": 8,
            "captcha_failures": 2,
            "total_solve_time": 240.5,
            "recaptcha_v2_count": 5,
            "recaptcha_v3_count": 2,
            "image_captcha_count": 1,
            "hcaptcha_count": 0,
            "unknown_count": 0,
        })

        stats = captcha_handler.get_statistics()

        assert stats["captchas_detected"] == 10
        assert stats["captchas_solved"] == 8
        assert stats["captcha_failures"] == 2
        assert stats["success_rate"] == 80.0
        assert stats["average_solve_time"] == 30.0625
        assert stats["captcha_types"]["recaptcha_v2"] == 5

    @pytest.mark.asyncio
    async def test_solve_with_retry(self, captcha_handler, mock_page):
        """Test captcha solving with retry on failure."""
        # Mock first attempt fails, second succeeds
        captcha_handler._solve_captcha_api = AsyncMock()
        captcha_handler._solve_captcha_api.side_effect = [
            CaptchaSolvingError("API error"),
            CaptchaSolution(
                captcha_type=CaptchaType.RECAPTCHA_V2,
                token="success-token",
                metadata={},
                solved_at=datetime.now(UTC),
            ),
        ]

        solution = await captcha_handler.solve_captcha(
            mock_page, CaptchaType.RECAPTCHA_V2, {"sitekey": "test"}
        )

        assert solution.token == "success-token"
        assert captcha_handler._solve_captcha_api.call_count == 2

    @pytest.mark.asyncio
    async def test_screenshot_on_detection(self, captcha_handler, mock_page, tmp_path):
        """Test screenshot capture when captcha is detected."""
        # Enable screenshot capture
        captcha_handler.capture_screenshots = True
        captcha_handler.screenshot_dir = tmp_path

        # Mock screenshot
        mock_page.screenshot.return_value = b"fake-screenshot-data"

        # Mock finding captcha
        mock_page.query_selector.return_value = MagicMock()

        await captcha_handler.detect_captcha(mock_page)

        # Verify screenshot was taken
        mock_page.screenshot.assert_called_once()

        # Check screenshot file exists
        screenshots = list(tmp_path.glob("captcha_*.png"))
        assert len(screenshots) == 1
