"""Demonstration of Phoenix MLS error detection system.

This example shows how the error detection system identifies and handles
common error scenarios like rate limiting, blocked IPs, and session expiration.
"""

import asyncio
from unittest.mock import Mock, AsyncMock

# Import our error detection classes
from phoenix_real_estate.collectors.phoenix_mls.error_detection import (
    ErrorDetector,
    RateLimitDetectedError,
    BlockedIPDetectedError,
    CaptchaDetectedError,
)
from phoenix_real_estate.foundation.logging import get_logger

logger = get_logger(__name__)


async def demo_rate_limit_detection():
    """Demonstrate rate limit error detection."""
    print("\n=== Rate Limit Detection Demo ===")

    detector = ErrorDetector()

    # Create a mock response with rate limit indicators
    mock_response = Mock()
    mock_response.status = 429
    mock_response.headers = {"x-ratelimit-remaining": "0", "retry-after": "60"}
    mock_response.url = "https://www.phoenixmlssearch.com/search"
    mock_response.text = AsyncMock(return_value="Rate limit exceeded. Try again later.")

    # Detect errors
    errors = await detector.detect_from_response(mock_response)

    print(f"Detected {len(errors)} error(s)")
    for error in errors:
        print(f"  - Type: {error.error_type.value}")
        print(f"  - Pattern: {error.pattern_name}")
        print(f"  - Confidence: {error.confidence}")
        if isinstance(error, RateLimitDetectedError):
            print(f"  - Retry after: {error.retry_after} seconds")
        print()


async def demo_blocked_ip_detection():
    """Demonstrate blocked IP error detection."""
    print("\n=== Blocked IP Detection Demo ===")

    detector = ErrorDetector()

    # Create a mock response with Cloudflare block indicators
    mock_response = Mock()
    mock_response.status = 403
    mock_response.headers = {"cf-ray": "123456789abcdef"}
    mock_response.url = "https://www.phoenixmlssearch.com/property/123"
    mock_response.text = AsyncMock(
        return_value="<html><head><title>Access denied | Cloudflare</title></head></html>"
    )

    # Detect errors
    errors = await detector.detect_from_response(mock_response)

    print(f"Detected {len(errors)} error(s)")
    for error in errors:
        print(f"  - Type: {error.error_type.value}")
        print(f"  - Pattern: {error.pattern_name}")
        print(f"  - Confidence: {error.confidence}")
        if isinstance(error, BlockedIPDetectedError):
            print(f"  - Block type: {error.block_type}")
            print(f"  - Requires proxy switch: {error.requires_proxy_switch}")
        print()


async def demo_captcha_detection():
    """Demonstrate CAPTCHA error detection."""
    print("\n=== CAPTCHA Detection Demo ===")

    detector = ErrorDetector()

    # Create a mock page with CAPTCHA present
    mock_page = Mock()
    mock_page.url = "https://www.phoenixmlssearch.com/search"
    mock_page.content = AsyncMock(
        return_value='<html><body><div class="g-recaptcha" data-sitekey="xyz123"></div></body></html>'
    )

    # Mock query_selector to return element for .g-recaptcha
    def query_selector_mock(selector):
        if selector == ".g-recaptcha":
            return Mock()  # Found element
        return None

    mock_page.query_selector = AsyncMock(side_effect=query_selector_mock)

    # Detect errors
    errors = await detector.detect_from_page(mock_page)

    print(f"Detected {len(errors)} error(s)")
    for error in errors:
        print(f"  - Type: {error.error_type.value}")
        print(f"  - Pattern: {error.pattern_name}")
        print(f"  - Confidence: {error.confidence}")
        if isinstance(error, CaptchaDetectedError):
            print(f"  - CAPTCHA type: {error.captcha_type}")
            print(f"  - Requires human intervention: {error.requires_human_intervention}")
        print()


async def demo_action_suggestions():
    """Demonstrate action suggestion system."""
    print("\n=== Action Suggestion Demo ===")

    detector = ErrorDetector()

    # Create multiple error types
    errors = [
        RateLimitDetectedError(
            pattern_name="rate_limit_429", confidence=0.95, context={"retry_after": "120"}
        ),
        BlockedIPDetectedError(
            pattern_name="cloudflare_block", confidence=0.85, context={"block_type": "cloudflare"}
        ),
    ]

    # Get suggested action
    action = detector.get_suggested_action(errors)

    print(f"Primary error: {errors[0].error_type.value}")
    print(f"Suggested action: {action['action']}")
    print(f"Reason: {action['reason']}")

    if action["action"] == "wait":
        print(f"Wait time: {action['wait_seconds']} seconds")
    elif action["action"] == "switch_proxy":
        print(f"Block type: {action['block_type']}")


def demo_error_patterns():
    """Demonstrate the different error patterns available."""
    print("\n=== Available Error Patterns ===")

    detector = ErrorDetector()

    error_types = {}
    for pattern in detector.patterns:
        error_type = pattern.error_type.value
        if error_type not in error_types:
            error_types[error_type] = []
        error_types[error_type].append(pattern.name)

    for error_type, patterns in error_types.items():
        print(f"\n{error_type.upper()} patterns:")
        for pattern_name in patterns:
            print(f"  - {pattern_name}")

    print(f"\nTotal patterns: {len(detector.patterns)}")


async def main():
    """Run all demonstrations."""
    print("Phoenix MLS Error Detection System Demo")
    print("=" * 50)

    # Show available patterns
    demo_error_patterns()

    # Run error detection demos
    await demo_rate_limit_detection()
    await demo_blocked_ip_detection()
    await demo_captcha_detection()
    await demo_action_suggestions()

    print("\nDemo completed! The error detection system can:")
    print("✓ Detect rate limits from HTTP status codes and headers")
    print("✓ Identify blocked IPs from Cloudflare and WAF responses")
    print("✓ Find CAPTCHAs in page content")
    print("✓ Suggest appropriate recovery actions")
    print("✓ Handle session expiration and maintenance modes")


if __name__ == "__main__":
    asyncio.run(main())
