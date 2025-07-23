"""Error pattern detection for Phoenix MLS scraper.

This module provides site-specific error detection patterns for common
scenarios including rate limiting, blocked IPs, session expiration,
CAPTCHAs, and maintenance modes.
"""

import re
from enum import Enum
from typing import Dict, List, Any
from datetime import datetime, UTC
from dataclasses import dataclass, field

from playwright.async_api import Page, Response

from phoenix_real_estate.foundation.logging import get_logger
from phoenix_real_estate.foundation.utils.exceptions import DataCollectionError

logger = get_logger(__name__)


class ErrorType(Enum):
    """Types of errors that can be detected."""

    RATE_LIMIT = "rate_limit"
    BLOCKED_IP = "blocked_ip"
    SESSION_EXPIRED = "session_expired"
    CAPTCHA = "captcha"
    MAINTENANCE = "maintenance"
    AUTHENTICATION = "authentication"
    NOT_FOUND = "not_found"
    SERVER_ERROR = "server_error"
    UNKNOWN = "unknown"


@dataclass
class ErrorPattern:
    """Definition of an error pattern to detect.

    Attributes:
        error_type: The type of error this pattern detects
        name: Unique name for this pattern
        patterns: Dictionary of patterns to match against
        confidence: Confidence score (0-1) when this pattern matches
    """

    error_type: ErrorType
    name: str
    patterns: Dict[str, Any]
    confidence: float = 0.8

    def matches(self, response_data: Dict[str, Any]) -> bool:
        """Check if this pattern matches the response data.

        Args:
            response_data: Dictionary containing response information

        Returns:
            True if all pattern conditions match
        """
        for key, pattern in self.patterns.items():
            if key == "status_code":
                if key not in response_data or response_data.get(key) not in pattern:
                    return False

            elif key == "response_headers":
                if key not in response_data:
                    return False
                headers = response_data.get(key, {})
                for header_name, expected_value in pattern.items():
                    header_value = headers.get(header_name)
                    if header_value is None:
                        return False

                    if callable(expected_value):
                        if not expected_value(header_value):
                            return False
                    elif header_value != expected_value:
                        return False

            elif key == "body_text":
                if key not in response_data:
                    return False
                body = response_data.get(key, "").lower()
                if not any(text.lower() in body for text in pattern):
                    return False

            elif key == "css_selectors":
                # Look for found_selectors in response_data
                found_selectors = response_data.get("found_selectors", [])
                if not any(selector in found_selectors for selector in pattern):
                    return False

            elif key == "url_patterns":
                # Look for current_url in response_data
                current_url = response_data.get("current_url", "").lower()
                if not any(pattern_url.lower() in current_url for pattern_url in pattern):
                    return False

        return True


@dataclass
class DetectedError:
    """Base class for detected errors.

    Attributes:
        error_type: Type of error detected
        pattern_name: Name of the pattern that matched
        confidence: Confidence score of the detection
        context: Additional context about the error
        timestamp: When the error was detected
    """

    error_type: ErrorType
    pattern_name: str
    confidence: float
    context: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def suggested_action(self) -> str:
        """Get suggested action for this error."""
        return "retry"

    def to_exception(self) -> DataCollectionError:
        """Convert to a DataCollectionError exception."""
        return DataCollectionError(
            f"Phoenix MLS error detected: {self.error_type.value}",
            context={
                "error_type": self.error_type.value,
                "pattern": self.pattern_name,
                "confidence": self.confidence,
                **self.context,
            },
            source="phoenix_mls",
        )


@dataclass
class RateLimitDetectedError(DetectedError):
    """Rate limit error with retry information."""

    def __init__(self, pattern_name: str, confidence: float, context: Dict[str, Any]):
        super().__init__(ErrorType.RATE_LIMIT, pattern_name, confidence, context)

    @property
    def retry_after(self) -> int:
        """Get retry after seconds from context."""
        retry_after = self.context.get("retry_after", 60)
        if isinstance(retry_after, str):
            return int(retry_after)
        return retry_after

    @property
    def suggested_action(self) -> str:
        """Get suggested action for rate limit."""
        return "wait"

    @property
    def wait_seconds(self) -> int:
        """Get wait time in seconds."""
        return self.retry_after


@dataclass
class BlockedIPDetectedError(DetectedError):
    """Blocked IP error requiring proxy switch."""

    def __init__(self, pattern_name: str, confidence: float, context: Dict[str, Any]):
        super().__init__(ErrorType.BLOCKED_IP, pattern_name, confidence, context)

    @property
    def block_type(self) -> str:
        """Get type of block (e.g., cloudflare, waf)."""
        return self.context.get("block_type", "unknown")

    @property
    def suggested_action(self) -> str:
        """Get suggested action for blocked IP."""
        return "switch_proxy"

    @property
    def requires_proxy_switch(self) -> bool:
        """Check if proxy switch is required."""
        return True


@dataclass
class SessionExpiredDetectedError(DetectedError):
    """Session expiration error requiring re-authentication."""

    def __init__(self, pattern_name: str, confidence: float, context: Dict[str, Any]):
        super().__init__(ErrorType.SESSION_EXPIRED, pattern_name, confidence, context)

    @property
    def redirect_url(self) -> str:
        """Get redirect URL if available."""
        return self.context.get("redirect_url", "/login")

    @property
    def suggested_action(self) -> str:
        """Get suggested action for session expiration."""
        return "re_authenticate"

    @property
    def requires_new_session(self) -> bool:
        """Check if new session is required."""
        return True


@dataclass
class CaptchaDetectedError(DetectedError):
    """CAPTCHA challenge requiring solving."""

    def __init__(self, pattern_name: str, confidence: float, context: Dict[str, Any]):
        super().__init__(ErrorType.CAPTCHA, pattern_name, confidence, context)

    @property
    def captcha_type(self) -> str:
        """Get type of CAPTCHA (e.g., recaptcha_v2, hcaptcha)."""
        return self.context.get("captcha_type", "unknown")

    @property
    def suggested_action(self) -> str:
        """Get suggested action for CAPTCHA."""
        return "solve_captcha"

    @property
    def requires_human_intervention(self) -> bool:
        """Check if human intervention is required."""
        return True


@dataclass
class MaintenanceDetectedError(DetectedError):
    """Site maintenance error requiring long wait."""

    def __init__(self, pattern_name: str, confidence: float, context: Dict[str, Any]):
        super().__init__(ErrorType.MAINTENANCE, pattern_name, confidence, context)

    @property
    def maintenance_message(self) -> str:
        """Get maintenance message if available."""
        return self.context.get("maintenance_message", "Site under maintenance")

    @property
    def suggested_action(self) -> str:
        """Get suggested action for maintenance."""
        return "wait_long"

    @property
    def estimated_wait_minutes(self) -> int:
        """Get estimated wait time in minutes."""
        # Try to extract from context or default to 2 hours
        estimated = self.context.get("estimated_time", "120")
        if isinstance(estimated, str):
            # Try to parse hours from message
            if "hour" in estimated.lower():
                hours_match = re.search(r"(\d+)\s*hour", estimated.lower())
                if hours_match:
                    return int(hours_match.group(1)) * 60
            # Try to parse minutes
            minutes_match = re.search(r"(\d+)\s*min", estimated.lower())
            if minutes_match:
                return int(minutes_match.group(1))
        return 120  # Default 2 hours


class ErrorDetector:
    """Detects site-specific error patterns from responses and pages."""

    def __init__(self):
        """Initialize error detector with default patterns."""
        self.patterns: List[ErrorPattern] = []
        self._initialize_default_patterns()

    def _initialize_default_patterns(self):
        """Initialize default error patterns for Phoenix MLS."""
        # Rate limiting patterns
        self.patterns.extend(
            [
                ErrorPattern(
                    error_type=ErrorType.RATE_LIMIT,
                    name="rate_limit_429",
                    patterns={
                        "status_code": [429],
                        "body_text": ["rate limit", "too many requests", "exceeded the limit"],
                    },
                    confidence=0.95,
                ),
                ErrorPattern(
                    error_type=ErrorType.RATE_LIMIT,
                    name="rate_limit_headers",
                    patterns={"response_headers": {"x-ratelimit-remaining": "0"}},
                    confidence=0.9,
                ),
                ErrorPattern(
                    error_type=ErrorType.RATE_LIMIT,
                    name="rate_limit_503",
                    patterns={
                        "status_code": [503],
                        "body_text": ["temporarily unavailable", "please try again later"],
                        "response_headers": {"retry-after": lambda v: v is not None},
                    },
                    confidence=0.85,
                ),
            ]
        )

        # Blocked IP patterns
        self.patterns.extend(
            [
                ErrorPattern(
                    error_type=ErrorType.BLOCKED_IP,
                    name="cloudflare_block",
                    patterns={
                        "status_code": [403],
                        "body_text": ["cloudflare", "access denied", "ray id"],
                    },
                    confidence=0.9,
                ),
                ErrorPattern(
                    error_type=ErrorType.BLOCKED_IP,
                    name="cloudflare_challenge",
                    patterns={
                        "body_text": ["checking your browser", "cloudflare", "ddos protection"]
                    },
                    confidence=0.85,
                ),
                ErrorPattern(
                    error_type=ErrorType.BLOCKED_IP,
                    name="waf_block",
                    patterns={
                        "status_code": [403, 406],
                        "body_text": ["web application firewall", "waf", "blocked by security"],
                    },
                    confidence=0.85,
                ),
                ErrorPattern(
                    error_type=ErrorType.BLOCKED_IP,
                    name="ip_banned",
                    patterns={
                        "body_text": [
                            "your ip has been banned",
                            "ip address blocked",
                            "access forbidden",
                        ]
                    },
                    confidence=0.95,
                ),
            ]
        )

        # Session expiration patterns
        self.patterns.extend(
            [
                ErrorPattern(
                    error_type=ErrorType.SESSION_EXPIRED,
                    name="login_redirect",
                    patterns={
                        "url_patterns": ["/login", "/signin", "/auth"],
                        "css_selectors": [".login-form", "#login-form", ".signin-container"],
                    },
                    confidence=0.9,
                ),
                ErrorPattern(
                    error_type=ErrorType.SESSION_EXPIRED,
                    name="session_expired_message",
                    patterns={
                        "body_text": [
                            "session expired",
                            "please log in again",
                            "authentication required",
                        ]
                    },
                    confidence=0.95,
                ),
                ErrorPattern(
                    error_type=ErrorType.SESSION_EXPIRED,
                    name="unauthorized_401",
                    patterns={
                        "status_code": [401],
                        "body_text": ["unauthorized", "not authenticated"],
                    },
                    confidence=0.85,
                ),
            ]
        )

        # CAPTCHA patterns
        self.patterns.extend(
            [
                ErrorPattern(
                    error_type=ErrorType.CAPTCHA,
                    name="recaptcha_v2",
                    patterns={
                        "css_selectors": [".g-recaptcha", "#g-recaptcha", "[data-sitekey]"],
                        "body_text": ["recaptcha"],
                    },
                    confidence=0.95,
                ),
                ErrorPattern(
                    error_type=ErrorType.CAPTCHA,
                    name="recaptcha_v3",
                    patterns={"body_text": ["grecaptcha.execute", "recaptcha/api.js"]},
                    confidence=0.9,
                ),
                ErrorPattern(
                    error_type=ErrorType.CAPTCHA,
                    name="hcaptcha",
                    patterns={
                        "css_selectors": [".h-captcha", "[data-hcaptcha-sitekey]"],
                        "body_text": ["hcaptcha.com"],
                    },
                    confidence=0.95,
                ),
                ErrorPattern(
                    error_type=ErrorType.CAPTCHA,
                    name="generic_captcha",
                    patterns={
                        "css_selectors": [".captcha", "#captcha", "[data-captcha]"],
                        "body_text": [
                            "enter the characters",
                            "prove you're human",
                            "security check",
                        ],
                    },
                    confidence=0.8,
                ),
            ]
        )

        # Maintenance patterns
        self.patterns.extend(
            [
                ErrorPattern(
                    error_type=ErrorType.MAINTENANCE,
                    name="maintenance_503",
                    patterns={
                        "status_code": [503],
                        "body_text": ["maintenance", "be back soon", "temporarily down"],
                    },
                    confidence=0.9,
                ),
                ErrorPattern(
                    error_type=ErrorType.MAINTENANCE,
                    name="maintenance_page",
                    patterns={
                        "body_text": [
                            "site maintenance",
                            "scheduled maintenance",
                            "under construction",
                        ],
                        "css_selectors": [".maintenance-page", "#maintenance"],
                    },
                    confidence=0.85,
                ),
            ]
        )

        # Authentication errors
        self.patterns.extend(
            [
                ErrorPattern(
                    error_type=ErrorType.AUTHENTICATION,
                    name="invalid_credentials",
                    patterns={
                        "body_text": [
                            "invalid credentials",
                            "wrong password",
                            "authentication failed",
                        ]
                    },
                    confidence=0.95,
                ),
                ErrorPattern(
                    error_type=ErrorType.AUTHENTICATION,
                    name="account_locked",
                    patterns={
                        "body_text": [
                            "account locked",
                            "too many failed attempts",
                            "account suspended",
                        ]
                    },
                    confidence=0.9,
                ),
            ]
        )

        # Not found patterns
        self.patterns.extend(
            [
                ErrorPattern(
                    error_type=ErrorType.NOT_FOUND,
                    name="page_not_found",
                    patterns={
                        "status_code": [404],
                        "body_text": ["page not found", "404 error", "does not exist"],
                    },
                    confidence=0.95,
                ),
                ErrorPattern(
                    error_type=ErrorType.NOT_FOUND,
                    name="property_not_found",
                    patterns={
                        "body_text": [
                            "property not found",
                            "listing no longer available",
                            "removed from market",
                        ]
                    },
                    confidence=0.9,
                ),
            ]
        )

        # Server error patterns
        self.patterns.extend(
            [
                ErrorPattern(
                    error_type=ErrorType.SERVER_ERROR,
                    name="internal_server_error",
                    patterns={
                        "status_code": [500, 502, 504],
                        "body_text": [
                            "internal server error",
                            "something went wrong",
                            "technical difficulties",
                        ],
                    },
                    confidence=0.9,
                ),
            ]
        )

    async def detect_from_response(self, response: Response) -> List[DetectedError]:
        """Detect errors from a Playwright response.

        Args:
            response: Playwright response object

        Returns:
            List of detected errors
        """
        detected_errors = []

        try:
            # Extract response data
            response_data = {
                "status_code": response.status,
                "response_headers": dict(response.headers),
                "body_text": await response.text(),
                "current_url": response.url,
            }

            # Check each pattern
            for pattern in self.patterns:
                if pattern.matches(response_data):
                    # Create appropriate error instance
                    error = self._create_error_instance(pattern, response_data)
                    detected_errors.append(error)

                    logger.debug(
                        f"Detected {pattern.error_type.value} error: {pattern.name} "
                        f"(confidence: {pattern.confidence})"
                    )

        except Exception as e:
            logger.error(f"Error detecting patterns from response: {e}")

        return detected_errors

    async def detect_from_page(self, page: Page) -> List[DetectedError]:
        """Detect errors from current page state.

        Args:
            page: Playwright page object

        Returns:
            List of detected errors
        """
        detected_errors = []

        try:
            # Get page content and URL
            content = await page.content()
            current_url = page.url

            # Check for specific selectors
            found_selectors = []
            all_selectors = set()

            # Collect all selectors from patterns
            for pattern in self.patterns:
                if "css_selectors" in pattern.patterns:
                    all_selectors.update(pattern.patterns["css_selectors"])

            # Check which selectors exist on the page
            for selector in all_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        found_selectors.append(selector)
                except Exception:
                    continue

            # Build response data
            response_data = {
                "body_text": content,
                "current_url": current_url,
                "found_selectors": found_selectors,
            }

            # Check each pattern
            for pattern in self.patterns:
                if pattern.matches(response_data):
                    error = self._create_error_instance(pattern, response_data)
                    detected_errors.append(error)

                    logger.debug(
                        f"Detected {pattern.error_type.value} error on page: {pattern.name} "
                        f"(confidence: {pattern.confidence})"
                    )

        except Exception as e:
            logger.error(f"Error detecting patterns from page: {e}")

        return detected_errors

    def _create_error_instance(
        self, pattern: ErrorPattern, response_data: Dict[str, Any]
    ) -> DetectedError:
        """Create appropriate error instance based on pattern type.

        Args:
            pattern: The pattern that matched
            response_data: Response data used for matching

        Returns:
            Appropriate DetectedError subclass instance
        """
        context = {
            "status_code": response_data.get("status_code"),
            "url": response_data.get("current_url"),
        }

        # Add pattern-specific context
        if pattern.error_type == ErrorType.RATE_LIMIT:
            headers = response_data.get("response_headers", {})
            context.update(
                {
                    "retry_after": headers.get("retry-after", headers.get("Retry-After", "60")),
                    "rate_limit": headers.get("x-ratelimit-limit"),
                    "rate_remaining": headers.get("x-ratelimit-remaining"),
                }
            )
            return RateLimitDetectedError(pattern.name, pattern.confidence, context)

        elif pattern.error_type == ErrorType.BLOCKED_IP:
            # Determine block type from pattern name
            if "cloudflare" in pattern.name:
                context["block_type"] = "cloudflare"
            elif "waf" in pattern.name:
                context["block_type"] = "waf"
            else:
                context["block_type"] = "ip_ban"
            return BlockedIPDetectedError(pattern.name, pattern.confidence, context)

        elif pattern.error_type == ErrorType.SESSION_EXPIRED:
            context["redirect_url"] = response_data.get("current_url", "")
            return SessionExpiredDetectedError(pattern.name, pattern.confidence, context)

        elif pattern.error_type == ErrorType.CAPTCHA:
            # Determine CAPTCHA type from pattern name
            if "recaptcha" in pattern.name:
                context["captcha_type"] = "recaptcha"
            elif "hcaptcha" in pattern.name:
                context["captcha_type"] = "hcaptcha"
            else:
                context["captcha_type"] = "unknown"

            # Add selector info
            if response_data.get("found_selectors"):
                context["selector"] = response_data["found_selectors"][0]

            return CaptchaDetectedError(pattern.name, pattern.confidence, context)

        elif pattern.error_type == ErrorType.MAINTENANCE:
            # Try to extract maintenance message
            body_text = response_data.get("body_text", "")
            maintenance_match = re.search(
                r"(maintenance.*?(?:hours?|minutes?|soon))", body_text, re.IGNORECASE | re.DOTALL
            )
            if maintenance_match:
                context["maintenance_message"] = maintenance_match.group(1)

            # Try to extract estimated time
            time_match = re.search(r"(\d+)\s*(hours?|minutes?)", body_text, re.IGNORECASE)
            if time_match:
                context["estimated_time"] = time_match.group(0)

            return MaintenanceDetectedError(pattern.name, pattern.confidence, context)

        else:
            # Default DetectedError for other types
            return DetectedError(pattern.error_type, pattern.name, pattern.confidence, context)

    def add_pattern(self, pattern: ErrorPattern):
        """Add a custom error pattern.

        Args:
            pattern: ErrorPattern to add
        """
        self.patterns.append(pattern)
        logger.info(f"Added error pattern: {pattern.name}")

    def remove_pattern(self, pattern_name: str) -> bool:
        """Remove an error pattern by name.

        Args:
            pattern_name: Name of pattern to remove

        Returns:
            True if pattern was removed
        """
        original_count = len(self.patterns)
        self.patterns = [p for p in self.patterns if p.name != pattern_name]
        removed = len(self.patterns) < original_count

        if removed:
            logger.info(f"Removed error pattern: {pattern_name}")

        return removed

    def get_patterns_by_type(self, error_type: ErrorType) -> List[ErrorPattern]:
        """Get all patterns for a specific error type.

        Args:
            error_type: Type of error patterns to retrieve

        Returns:
            List of patterns for that error type
        """
        return [p for p in self.patterns if p.error_type == error_type]

    def get_suggested_action(self, errors: List[DetectedError]) -> Dict[str, Any]:
        """Get suggested action based on detected errors.

        Args:
            errors: List of detected errors

        Returns:
            Dictionary with suggested action and parameters
        """
        if not errors:
            return {"action": "proceed", "reason": "no_errors"}

        # Sort by confidence and priority
        priority_order = [
            ErrorType.CAPTCHA,  # Highest priority - requires human intervention
            ErrorType.RATE_LIMIT,  # Need to wait - handle before switching proxy
            ErrorType.BLOCKED_IP,  # Need proxy switch
            ErrorType.SESSION_EXPIRED,  # Need re-auth
            ErrorType.MAINTENANCE,  # Long wait
            ErrorType.AUTHENTICATION,  # Fix credentials
            ErrorType.SERVER_ERROR,  # Retry later
            ErrorType.NOT_FOUND,  # Skip
            ErrorType.UNKNOWN,  # Default retry
        ]

        sorted_errors = sorted(
            errors,
            key=lambda e: (
                priority_order.index(e.error_type) if e.error_type in priority_order else 999,
                -e.confidence,
            ),
        )

        # Get action from highest priority error
        top_error = sorted_errors[0]

        if isinstance(top_error, RateLimitDetectedError):
            return {
                "action": "wait",
                "wait_seconds": top_error.wait_seconds,
                "reason": "rate_limit",
                "error": top_error,
            }

        elif isinstance(top_error, BlockedIPDetectedError):
            return {
                "action": "switch_proxy",
                "reason": "blocked_ip",
                "block_type": top_error.block_type,
                "error": top_error,
            }

        elif isinstance(top_error, SessionExpiredDetectedError):
            return {
                "action": "re_authenticate",
                "reason": "session_expired",
                "redirect_url": top_error.redirect_url,
                "error": top_error,
            }

        elif isinstance(top_error, CaptchaDetectedError):
            return {
                "action": "solve_captcha",
                "reason": "captcha",
                "captcha_type": top_error.captcha_type,
                "error": top_error,
            }

        elif isinstance(top_error, MaintenanceDetectedError):
            return {
                "action": "wait_long",
                "wait_minutes": top_error.estimated_wait_minutes,
                "reason": "maintenance",
                "error": top_error,
            }

        else:
            return {"action": "retry", "reason": top_error.error_type.value, "error": top_error}
