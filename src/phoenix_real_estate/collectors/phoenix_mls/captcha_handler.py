"""Captcha detection and handling for Phoenix MLS scraper.

This module provides captcha detection, identification, and solving capabilities
for the Phoenix MLS scraper. It supports multiple captcha types including
reCAPTCHA v2/v3 and image captchas, with integration to captcha solving services.
"""

import asyncio
import time
from enum import Enum
from typing import Dict, Optional, Any, Tuple, TypedDict
from datetime import datetime, UTC
from pathlib import Path
import base64
import re
from dataclasses import dataclass
from urllib.parse import urljoin

import aiohttp
from playwright.async_api import Page

from phoenix_real_estate.foundation.logging import get_logger
from phoenix_real_estate.foundation.utils.exceptions import (
    ConfigurationError,
    CaptchaError,
    CaptchaDetectionError,
    CaptchaSolvingError,
)

logger = get_logger(__name__)


class CaptchaType(Enum):
    """Supported captcha types."""

    RECAPTCHA_V2 = "recaptcha_v2"
    RECAPTCHA_V3 = "recaptcha_v3"
    IMAGE = "image"
    HCAPTCHA = "hcaptcha"
    FUNCAPTCHA = "funcaptcha"
    UNKNOWN = "unknown"


class CaptchaConfig(TypedDict, total=False):
    """Type definition for captcha configuration."""

    enabled: bool
    service: str
    api_key: str
    timeout: int
    max_retries: int
    detection: Dict[str, Any]
    screenshot_on_detection: bool
    screenshot_dir: str


@dataclass
class CaptchaSolution:
    """Container for captcha solution data."""

    captcha_type: CaptchaType
    token: str
    metadata: Dict[str, Any]
    solved_at: datetime
    solve_duration: Optional[float] = None
    service_used: Optional[str] = None


class CaptchaHandler:
    """Handles captcha detection, solving, and application for Phoenix MLS scraper.

    This handler provides:
    - Automatic captcha detection on pages
    - Captcha type identification (reCAPTCHA v2/v3, image, etc.)
    - Integration with captcha solving services (2captcha, Anti-Captcha, etc.)
    - Solution application to bypass captchas
    - Statistics tracking and error handling

    Attributes:
        enabled: Whether captcha handling is enabled.
        service: Captcha solving service to use.
        api_key: API key for the solving service.
        timeout: Maximum time to wait for captcha solution.
        max_retries: Maximum retry attempts for solving.
        stats: Statistics about captcha encounters and solutions.
    """

    # Default detection selectors for common captcha implementations
    DEFAULT_DETECTION_SELECTORS = [
        # reCAPTCHA
        "iframe[src*='recaptcha']",
        ".g-recaptcha",
        "#g-recaptcha",
        "[data-sitekey]",
        # hCaptcha
        "iframe[src*='hcaptcha']",
        ".h-captcha",
        "[data-hcaptcha-widget-id]",
        # General captcha indicators
        "#captcha",
        ".captcha",
        "[class*='captcha']",
        "[id*='captcha']",
        "img[src*='captcha']",
        "input[name*='captcha']",
        "[data-captcha]",
    ]

    # Keywords that indicate captcha presence
    DEFAULT_DETECTION_KEYWORDS = [
        "captcha",
        "verification",
        "verify you're human",
        "i'm not a robot",
        "security check",
        "human verification",
    ]

    def __init__(self, config: CaptchaConfig):
        """Initialize the captcha handler with configuration.

        Args:
            config: Captcha handler configuration including:
                - enabled: Whether to enable captcha handling
                - service: Captcha solving service (2captcha, anti-captcha, etc.)
                - api_key: API key for the service
                - timeout: Solution timeout in seconds
                - max_retries: Maximum solving attempts
                - detection: Detection configuration with selectors and keywords

        Raises:
            ConfigurationError: If required configuration is missing.
        """
        # Initialize statistics first
        self.stats = {
            "captchas_detected": 0,
            "captchas_solved": 0,
            "captcha_failures": 0,
            "total_solve_time": 0.0,
            "recaptcha_v2_count": 0,
            "recaptcha_v3_count": 0,
            "image_captcha_count": 0,
            "hcaptcha_count": 0,
            "unknown_count": 0,
        }

        self.enabled = config.get("enabled", False)
        self.service = config.get("service") if self.enabled else None
        self.api_key = config.get("api_key") if self.enabled else None
        self.timeout = config.get("timeout", 120)
        self.max_retries = config.get("max_retries", 3)

        # Validate configuration if enabled
        if self.enabled:
            if not self.api_key:
                raise ConfigurationError(
                    "Captcha handling enabled but API key not provided",
                    context={"service": self.service},
                )
            if not self.service:
                raise ConfigurationError("Captcha handling enabled but service not specified")

        # Detection configuration
        detection_config = config.get("detection", {})
        self.detection_selectors = detection_config.get(
            "selectors", self.DEFAULT_DETECTION_SELECTORS
        )
        self.detection_keywords = detection_config.get("keywords", self.DEFAULT_DETECTION_KEYWORDS)
        self.detection_response_codes = detection_config.get("response_codes", [403, 429])

        # Screenshot configuration
        self.capture_screenshots = config.get("screenshot_on_detection", False)
        self.screenshot_dir = Path(config.get("screenshot_dir", "data/captcha_screenshots"))
        if self.capture_screenshots:
            self.screenshot_dir.mkdir(parents=True, exist_ok=True)

        # Service-specific configuration
        self.service_endpoints = {
            "2captcha": {
                "base_url": "https://2captcha.com",
                "in_endpoint": "/in.php",
                "res_endpoint": "/res.php",
            },
            "anti-captcha": {
                "base_url": "https://api.anti-captcha.com",
                "create_task": "/createTask",
                "get_result": "/getTaskResult",
            },
        }

        logger.info(f"CaptchaHandler initialized (enabled={self.enabled}, service={self.service})")

    async def detect_captcha(self, page: Page, response_code: Optional[int] = None) -> bool:
        """Detect if a captcha is present on the page.

        Args:
            page: Playwright page object to check.
            response_code: Optional HTTP response code that triggered the check.

        Returns:
            True if captcha is detected, False otherwise.
        """
        if not self.enabled:
            return False

        logger.debug(f"Checking for captcha on {page.url}")

        # Check response code if provided
        if response_code and response_code in self.detection_response_codes:
            logger.info(f"Captcha likely due to response code {response_code}")
            self.stats["captchas_detected"] += 1
            await self._capture_screenshot(page, "response_code_trigger")
            return True

        # Check for captcha elements using selectors
        for selector in self.detection_selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    logger.info(f"Captcha detected via selector: {selector}")
                    self.stats["captchas_detected"] += 1
                    await self._capture_screenshot(
                        page, f"selector_{selector.replace('[', '').replace(']', '')}"
                    )
                    return True
            except Exception as e:
                logger.debug(f"Error checking selector {selector}: {e}")
                continue

        # Check page content for captcha keywords
        try:
            content = await page.content()
            content_lower = content.lower()

            for keyword in self.detection_keywords:
                if keyword.lower() in content_lower:
                    logger.info(f"Captcha detected via keyword: {keyword}")
                    self.stats["captchas_detected"] += 1
                    await self._capture_screenshot(page, f"keyword_{keyword.replace(' ', '_')}")
                    return True
        except Exception as e:
            logger.warning(f"Error checking page content for captcha: {e}")

        logger.debug("No captcha detected")
        return False

    async def identify_captcha_type(self, page: Page) -> Tuple[CaptchaType, Dict[str, Any]]:
        """Identify the type of captcha on the page.

        Args:
            page: Playwright page object containing the captcha.

        Returns:
            Tuple of (CaptchaType, metadata dict with captcha-specific information).

        Raises:
            CaptchaDetectionError: If captcha type cannot be identified.
        """
        logger.info("Identifying captcha type")
        metadata = {"page_url": page.url}

        # Check for reCAPTCHA v2
        recaptcha_v2_selectors = ["iframe[src*='recaptcha']", ".g-recaptcha", "[data-sitekey]"]

        for selector in recaptcha_v2_selectors:
            element = await page.query_selector(selector)
            if element:
                # Extract sitekey
                sitekey = await self._extract_recaptcha_sitekey(page)
                if sitekey:
                    metadata["sitekey"] = sitekey
                    self.stats["recaptcha_v2_count"] += 1
                    logger.info(f"Identified reCAPTCHA v2 with sitekey: {sitekey}")
                    return CaptchaType.RECAPTCHA_V2, metadata

        # Check for reCAPTCHA v3
        recaptcha_v3_script = await page.evaluate("""
            () => {
                const scripts = Array.from(document.scripts);
                const v3Script = scripts.find(s => s.src && s.src.includes('recaptcha/api.js?render='));
                if (v3Script) {
                    const match = v3Script.src.match(/render=([^&]+)/);
                    return match ? match[1] : null;
                }
                return null;
            }
        """)

        if recaptcha_v3_script:
            metadata["sitekey"] = recaptcha_v3_script
            metadata["action"] = "submit"  # Default action, may need adjustment
            metadata["min_score"] = 0.7
            self.stats["recaptcha_v3_count"] += 1
            logger.info(f"Identified reCAPTCHA v3 with sitekey: {recaptcha_v3_script}")
            return CaptchaType.RECAPTCHA_V3, metadata

        # Check for hCaptcha
        hcaptcha_element = await page.query_selector(
            "[data-hcaptcha-widget-id], .h-captcha, iframe[src*='hcaptcha']"
        )
        if hcaptcha_element:
            sitekey = await page.evaluate(
                """
                (element) => element.getAttribute('data-sitekey') || 
                          document.querySelector('[data-sitekey]')?.getAttribute('data-sitekey'),
                """,
                hcaptcha_element,
            )
            if sitekey:
                metadata["sitekey"] = sitekey
                self.stats["hcaptcha_count"] += 1
                logger.info(f"Identified hCaptcha with sitekey: {sitekey}")
                return CaptchaType.HCAPTCHA, metadata

        # Check for image captcha
        image_captcha_selectors = [
            "img[src*='captcha']",
            "img[alt*='captcha']",
            "#captchaImage",
            ".captcha-image",
        ]

        for selector in image_captcha_selectors:
            img_element = await page.query_selector(selector)
            if img_element:
                img_src = await img_element.get_attribute("src")
                if img_src:
                    # Convert relative URLs to absolute
                    if not img_src.startswith("http"):
                        img_src = urljoin(page.url, img_src)
                    metadata["image_url"] = img_src

                    # Look for associated input field
                    input_element = await page.query_selector(
                        "input[name*='captcha'], input[placeholder*='captcha']"
                    )
                    if input_element:
                        input_name = await input_element.get_attribute("name") or "captcha"
                        metadata["input_name"] = input_name
                        metadata["input_selector"] = f"input[name='{input_name}']"

                    self.stats["image_captcha_count"] += 1
                    logger.info(f"Identified image captcha: {img_src}")
                    return CaptchaType.IMAGE, metadata

        # Unknown captcha type
        self.stats["unknown_count"] += 1
        logger.warning("Could not identify captcha type")
        raise CaptchaDetectionError(
            "Unable to identify captcha type",
            context={"url": page.url, "selectors_tried": len(self.detection_selectors)},
        )

    async def solve_captcha(
        self, page: Page, captcha_type: CaptchaType, metadata: Dict[str, Any]
    ) -> CaptchaSolution:
        """Solve the detected captcha using configured service.

        Args:
            page: Playwright page object containing the captcha.
            captcha_type: Type of captcha to solve.
            metadata: Captcha-specific metadata (sitekey, image URL, etc.).

        Returns:
            CaptchaSolution object with the solution token and metadata.

        Raises:
            CaptchaSolvingError: If captcha solving fails.
        """
        if not self.enabled:
            raise CaptchaSolvingError("Captcha handling is disabled")

        logger.info(f"Solving {captcha_type.value} captcha using {self.service}")
        start_time = time.time()

        # Retry logic for solving
        for attempt in range(self.max_retries):
            try:
                solution = await self._solve_captcha_api(captcha_type, metadata)

                # Track statistics
                solve_duration = time.time() - start_time
                self.stats["captchas_solved"] += 1
                self.stats["total_solve_time"] += solve_duration

                solution.solve_duration = solve_duration
                solution.service_used = self.service

                logger.info(f"Captcha solved successfully in {solve_duration:.2f}s")
                return solution

            except CaptchaSolvingError as e:
                logger.warning(f"Captcha solving attempt {attempt + 1} failed: {e}")
                if attempt == self.max_retries - 1:
                    self.stats["captcha_failures"] += 1
                    raise
                await asyncio.sleep(5)  # Wait before retry

    async def _solve_captcha_api(
        self, captcha_type: CaptchaType, metadata: Dict[str, Any]
    ) -> CaptchaSolution:
        """Internal method to solve captcha via API service.

        Args:
            captcha_type: Type of captcha to solve.
            metadata: Captcha-specific metadata.

        Returns:
            CaptchaSolution object.

        Raises:
            CaptchaSolvingError: If API request fails.
        """
        if self.service == "2captcha":
            return await self._solve_2captcha(captcha_type, metadata)
        elif self.service == "anti-captcha":
            return await self._solve_anticaptcha(captcha_type, metadata)
        else:
            raise CaptchaSolvingError(
                f"Unsupported captcha service: {self.service}", service=self.service
            )

    async def _solve_2captcha(
        self, captcha_type: CaptchaType, metadata: Dict[str, Any]
    ) -> CaptchaSolution:
        """Solve captcha using 2captcha service."""
        base_url = self.service_endpoints["2captcha"]["base_url"]

        async with aiohttp.ClientSession() as session:
            # Submit captcha for solving
            if captcha_type == CaptchaType.RECAPTCHA_V2:
                params = {
                    "key": self.api_key,
                    "method": "userrecaptcha",
                    "googlekey": metadata["sitekey"],
                    "pageurl": metadata["page_url"],
                    "json": 1,
                }
            elif captcha_type == CaptchaType.RECAPTCHA_V3:
                params = {
                    "key": self.api_key,
                    "method": "userrecaptcha",
                    "googlekey": metadata["sitekey"],
                    "pageurl": metadata["page_url"],
                    "version": "v3",
                    "action": metadata.get("action", "submit"),
                    "min_score": metadata.get("min_score", 0.7),
                    "json": 1,
                }
            elif captcha_type == CaptchaType.IMAGE:
                # For image captcha, we need to download and base64 encode the image
                image_data = await self._download_image(metadata["image_url"])
                params = {
                    "key": self.api_key,
                    "method": "base64",
                    "body": base64.b64encode(image_data).decode(),
                    "json": 1,
                }
            else:
                raise CaptchaSolvingError(
                    f"Unsupported captcha type for 2captcha: {captcha_type}",
                    service="2captcha",
                    captcha_type=captcha_type.value,
                )

            # Submit task
            async with session.post(
                f"{base_url}{self.service_endpoints['2captcha']['in_endpoint']}", data=params
            ) as response:
                if response.status != 200:
                    raise CaptchaSolvingError(
                        f"2captcha API error: status {response.status}",
                        service="2captcha",
                        context={"status_code": response.status},
                    )

                result = await response.json()
                if result.get("status") != 1:
                    raise CaptchaSolvingError(
                        f"2captcha error: {result.get('request', 'Unknown error')}",
                        service="2captcha",
                        error_code=result.get("request"),
                    )

                task_id = result["request"]
                logger.debug(f"2captcha task created: {task_id}")

            # Poll for result
            start_time = time.time()
            while time.time() - start_time < self.timeout:
                await asyncio.sleep(5)  # Wait before polling

                async with session.post(
                    f"{base_url}{self.service_endpoints['2captcha']['res_endpoint']}",
                    data={"key": self.api_key, "action": "get", "id": task_id, "json": 1},
                ) as response:
                    if response.status != 200:
                        continue

                    result = await response.json()
                    if result.get("status") == 1:
                        # Success!
                        token = result["request"]
                        return CaptchaSolution(
                            captcha_type=captcha_type,
                            token=token,
                            metadata={"task_id": task_id},
                            solved_at=datetime.now(UTC),
                        )
                    elif result.get("request") != "CAPCHA_NOT_READY":
                        # Error occurred
                        raise CaptchaSolvingError(
                            f"2captcha solving error: {result.get('request')}",
                            service="2captcha",
                            error_code=result.get("request"),
                        )

            # Timeout
            raise CaptchaSolvingError(
                f"Captcha solving timeout after {self.timeout}s",
                service="2captcha",
                context={"task_id": task_id, "timeout": self.timeout},
            )

    async def _solve_anticaptcha(
        self, captcha_type: CaptchaType, metadata: Dict[str, Any]
    ) -> CaptchaSolution:
        """Solve captcha using Anti-Captcha service."""
        # Implementation for Anti-Captcha API
        # Similar structure to 2captcha but with Anti-Captcha's API format
        raise NotImplementedError("Anti-Captcha integration not yet implemented")

    async def apply_captcha_solution(self, page: Page, solution: CaptchaSolution) -> None:
        """Apply the captcha solution to the page.

        Args:
            page: Playwright page object.
            solution: CaptchaSolution object with the token.

        Raises:
            CaptchaError: If solution application fails.
        """
        logger.info(f"Applying {solution.captcha_type.value} captcha solution")

        try:
            if solution.captcha_type == CaptchaType.RECAPTCHA_V2:
                await self._apply_recaptcha_v2_solution(page, solution.token)
            elif solution.captcha_type == CaptchaType.RECAPTCHA_V3:
                await self._apply_recaptcha_v3_solution(page, solution.token)
            elif solution.captcha_type == CaptchaType.IMAGE:
                await self._apply_image_captcha_solution(page, solution.token, solution.metadata)
            else:
                raise CaptchaError(
                    f"Cannot apply solution for captcha type: {solution.captcha_type}",
                    captcha_type=solution.captcha_type.value,
                )

            logger.info("Captcha solution applied successfully")

        except Exception as e:
            raise CaptchaError(
                "Failed to apply captcha solution",
                context={"captcha_type": solution.captcha_type.value},
                original_error=e,
            ) from e

    async def _apply_recaptcha_v2_solution(self, page: Page, token: str) -> None:
        """Apply reCAPTCHA v2 solution to the page."""
        # Inject the token into the g-recaptcha-response textarea
        await page.evaluate(f"""
            () => {{
                // Find all g-recaptcha-response textareas
                const textareas = document.querySelectorAll('textarea[name="g-recaptcha-response"]');
                textareas.forEach(textarea => {{
                    textarea.value = '{token}';
                    textarea.innerHTML = '{token}';
                }});
                
                // Also set on any element with id g-recaptcha-response
                const responseElement = document.getElementById('g-recaptcha-response');
                if (responseElement) {{
                    responseElement.value = '{token}';
                    responseElement.innerHTML = '{token}';
                }}
                
                // Try to find and call the callback function
                if (typeof ___grecaptcha_cfg !== 'undefined') {{
                    Object.entries(___grecaptcha_cfg.clients).forEach(([key, client]) => {{
                        if (client.callback) {{
                            client.callback('{token}');
                        }}
                    }});
                }}
                
                // Alternative: look for data-callback attribute
                const recaptchaElement = document.querySelector('[data-callback]');
                if (recaptchaElement) {{
                    const callbackName = recaptchaElement.getAttribute('data-callback');
                    if (callbackName && typeof window[callbackName] === 'function') {{
                        window[callbackName]('{token}');
                    }}
                }}
            }}
        """)

        # Small delay to let any callbacks process
        await asyncio.sleep(1)

    async def _apply_recaptcha_v3_solution(self, page: Page, token: str) -> None:
        """Apply reCAPTCHA v3 solution to the page."""
        # v3 tokens are typically submitted with the form
        # We need to find the right field or intercept the submission
        await page.evaluate(f"""
            () => {{
                // Common field names for v3 tokens
                const fieldNames = ['g-recaptcha-response', 'recaptcha-token', 'recaptcha_token'];
                
                fieldNames.forEach(name => {{
                    // Try input fields
                    const input = document.querySelector(`input[name="${{name}}"]`);
                    if (input) {{
                        input.value = '{token}';
                    }}
                    
                    // Try creating hidden input if not exists
                    if (!input) {{
                        const form = document.querySelector('form');
                        if (form) {{
                            const hiddenInput = document.createElement('input');
                            hiddenInput.type = 'hidden';
                            hiddenInput.name = name;
                            hiddenInput.value = '{token}';
                            form.appendChild(hiddenInput);
                        }}
                    }}
                }});
            }}
        """)

    async def _apply_image_captcha_solution(
        self, page: Page, solution: str, metadata: Dict[str, Any]
    ) -> None:
        """Apply image captcha solution to the page."""
        # Find the input field and enter the solution
        input_selector = metadata.get("input_selector", "input[name*='captcha']")

        input_element = await page.query_selector(input_selector)
        if not input_element:
            # Try common selectors
            for selector in ["input[type='text'][name*='captcha']", "#captcha", ".captcha-input"]:
                input_element = await page.query_selector(selector)
                if input_element:
                    break

        if input_element:
            await input_element.fill(solution)
            logger.debug(f"Filled captcha input with solution: {solution}")
        else:
            raise CaptchaError(
                "Could not find captcha input field", context={"tried_selectors": [input_selector]}
            )

    async def handle_captcha(self, page: Page, response_code: Optional[int] = None) -> bool:
        """Main method to handle captcha if present on page.

        This method orchestrates the full captcha handling flow:
        1. Detect if captcha is present
        2. Identify the captcha type
        3. Solve the captcha
        4. Apply the solution

        Args:
            page: Playwright page object.
            response_code: Optional HTTP response code.

        Returns:
            True if captcha was handled, False if no captcha was present.

        Raises:
            CaptchaError: If captcha handling fails at any step.
        """
        if not self.enabled:
            logger.debug("Captcha handling disabled")
            return False

        # Detect captcha
        if not await self.detect_captcha(page, response_code):
            return False

        logger.info("Captcha detected, starting handling process")

        try:
            # Identify captcha type
            captcha_type, metadata = await self.identify_captcha_type(page)

            # Solve captcha
            solution = await self.solve_captcha(page, captcha_type, metadata)

            # Apply solution
            await self.apply_captcha_solution(page, solution)

            # Wait a bit for the page to process the solution
            await asyncio.sleep(2)

            # Check if captcha is still present (validation)
            if await self.detect_captcha(page):
                logger.warning("Captcha still present after applying solution")
                # Don't throw error yet, let the scraper retry

            return True

        except Exception as e:
            logger.error(f"Captcha handling failed: {e}")
            raise

    async def _extract_recaptcha_sitekey(self, page: Page) -> Optional[str]:
        """Extract reCAPTCHA sitekey from the page."""
        # Try multiple methods to find sitekey
        sitekey = await page.evaluate("""
            () => {
                // Method 1: data-sitekey attribute
                const element = document.querySelector('[data-sitekey]');
                if (element) return element.getAttribute('data-sitekey');
                
                // Method 2: grecaptcha render parameters
                if (typeof grecaptcha !== 'undefined' && grecaptcha.render) {
                    // This is tricky as we can't easily intercept render calls
                    const scripts = Array.from(document.scripts);
                    for (const script of scripts) {
                        const match = script.textContent.match(/['"]sitekey['"]:\\s*['"]([^'"]+)['"]/);
                        if (match) return match[1];
                    }
                }
                
                // Method 3: iframe src
                const iframe = document.querySelector('iframe[src*="recaptcha"]');
                if (iframe) {
                    const match = iframe.src.match(/[?&]k=([^&]+)/);
                    if (match) return match[1];
                }
                
                return null;
            }
        """)

        return sitekey

    async def _download_image(self, image_url: str) -> bytes:
        """Download image from URL for captcha solving."""
        async with aiohttp.ClientSession() as session:
            async with session.get(image_url) as response:
                if response.status != 200:
                    raise CaptchaError(
                        f"Failed to download captcha image: status {response.status}",
                        context={"image_url": image_url, "status": response.status},
                    )
                return await response.read()

    async def _capture_screenshot(self, page: Page, reason: str) -> None:
        """Capture screenshot when captcha is detected."""
        if not self.capture_screenshots:
            return

        try:
            timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
            # Clean reason for filename
            clean_reason = re.sub(r"[^\w\-_]", "_", reason)
            filename = self.screenshot_dir / f"captcha_{clean_reason}_{timestamp}.png"
            await page.screenshot(path=str(filename))
            logger.debug(f"Captured captcha screenshot: {filename}")
        except Exception as e:
            logger.warning(f"Failed to capture screenshot: {e}")

    def get_statistics(self) -> Dict[str, Any]:
        """Get captcha handling statistics.

        Returns:
            Dictionary containing statistics about captcha encounters and solutions.
        """
        stats = self.stats.copy()

        # Calculate success rate
        total_attempts = stats["captchas_solved"] + stats["captcha_failures"]
        if total_attempts > 0:
            stats["success_rate"] = (stats["captchas_solved"] / total_attempts) * 100
        else:
            stats["success_rate"] = 0.0

        # Calculate average solve time
        if stats["captchas_solved"] > 0:
            stats["average_solve_time"] = stats["total_solve_time"] / stats["captchas_solved"]
        else:
            stats["average_solve_time"] = 0.0

        # Captcha type breakdown
        stats["captcha_types"] = {
            "recaptcha_v2": stats["recaptcha_v2_count"],
            "recaptcha_v3": stats["recaptcha_v3_count"],
            "image": stats["image_captcha_count"],
            "hcaptcha": stats["hcaptcha_count"],
            "unknown": stats["unknown_count"],
        }

        return stats

    def __repr__(self) -> str:
        """String representation of CaptchaHandler."""
        return (
            f"CaptchaHandler("
            f"enabled={self.enabled}, "
            f"service={self.service}, "
            f"detected={self.stats['captchas_detected']}, "
            f"solved={self.stats['captchas_solved']})"
        )
