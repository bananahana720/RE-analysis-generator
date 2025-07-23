# Captcha Detection and Handling

The Phoenix MLS scraper includes comprehensive captcha detection and handling capabilities to automatically bypass captcha challenges that may appear during scraping operations.

## Overview

The captcha handling system provides:

- **Automatic Detection**: Detects various types of captchas using CSS selectors, keywords, and response codes
- **Type Identification**: Identifies specific captcha types (reCAPTCHA v2/v3, image captchas, hCaptcha)
- **Service Integration**: Integrates with captcha solving services like 2captcha and Anti-Captcha
- **Solution Application**: Automatically applies solutions to bypass captchas
- **Error Handling**: Comprehensive error handling and retry logic
- **Statistics Tracking**: Detailed statistics about captcha encounters and success rates

## Supported Captcha Types

### reCAPTCHA v2
- **Detection**: iframe[src*='recaptcha'], .g-recaptcha, [data-sitekey]
- **Solving**: Extracts sitekey and submits to solving service
- **Application**: Injects solution token into g-recaptcha-response textarea

### reCAPTCHA v3
- **Detection**: Detects v3 script includes and render parameters
- **Solving**: Submits with action and minimum score parameters
- **Application**: Creates hidden form fields with solution token

### Image Captchas
- **Detection**: img[src*='captcha'], .captcha-image, #captchaImage
- **Solving**: Downloads image and submits for OCR solving
- **Application**: Fills solution into associated input field

### hCaptcha
- **Detection**: iframe[src*='hcaptcha'], .h-captcha, [data-hcaptcha-widget-id]
- **Solving**: Similar to reCAPTCHA v2 with hCaptcha-specific API
- **Application**: Injects solution token into appropriate response field

## Configuration

### Basic Configuration

Add to your configuration file (e.g., `config/base.yaml`):

```yaml
sources:
  phoenix_mls:
    captcha:
      enabled: true
      service: "2captcha"  # Options: 2captcha, anti-captcha
      timeout: 120  # Maximum seconds to wait for solution
      max_retries: 3
      screenshot_on_detection: true
      screenshot_dir: "data/captcha_screenshots"
```

### Environment Variables

Set your API key via environment variables:

```bash
# Required: API key for your chosen service
CAPTCHA_API_KEY=your_2captcha_api_key_here
CAPTCHA_SERVICE=2captcha

# Optional: Override default settings
PHOENIX_SOURCES_PHOENIX_MLS_CAPTCHA_ENABLED=true
PHOENIX_SOURCES_PHOENIX_MLS_CAPTCHA_TIMEOUT=180
```

### Detection Configuration

Customize detection parameters:

```yaml
sources:
  phoenix_mls:
    captcha:
      detection:
        # CSS selectors to detect captcha presence
        selectors:
          - "iframe[src*='recaptcha']"
          - ".g-recaptcha"
          - "[data-sitekey]"
          - "#captcha"
        
        # Keywords in page content that indicate captcha
        keywords:
          - "captcha"
          - "verification"
          - "verify you're human"
        
        # HTTP response codes that often indicate captcha
        response_codes:
          - 403
          - 429
```

## Usage

### Automatic Integration

Captcha handling is automatically integrated into the scraper:

```python
from phoenix_real_estate.collectors.phoenix_mls.scraper import PhoenixMLSScraper

# Configure scraper with captcha handling
config = {
    "base_url": "https://phoenixmlssearch.com",
    "captcha": {
        "enabled": True,
        "service": "2captcha",
        "api_key": "your_api_key_here"
    }
}

scraper = PhoenixMLSScraper(config)

# Scraping operations will automatically handle captchas
properties = await scraper.search_properties_by_zipcode("85001")
```

### Manual Captcha Handling

You can also manually check and handle captchas:

```python
from phoenix_real_estate.collectors.phoenix_mls.captcha_handler import CaptchaHandler

handler = CaptchaHandler(captcha_config)

# Check if captcha is present
if await handler.detect_captcha(page):
    print("Captcha detected!")
    
    # Handle the captcha
    success = await handler.handle_captcha(page)
    if success:
        print("Captcha solved successfully!")
```

### Custom Detection

Extend detection capabilities:

```python
# Add custom selectors
handler.detection_selectors.extend([
    ".custom-captcha",
    "#my-captcha-container"
])

# Add custom keywords
handler.detection_keywords.extend([
    "custom verification",
    "prove you're human"
])
```

## Service Setup

### 2captcha Setup

1. Register at [2captcha.com](https://2captcha.com)
2. Add funds to your account
3. Get your API key from the dashboard
4. Set the `CAPTCHA_API_KEY` environment variable

**Pricing**: ~$1-3 per 1000 captchas solved

### Anti-Captcha Setup

1. Register at [anti-captcha.com](https://anti-captcha.com)
2. Add funds to your account
3. Get your API key from the dashboard
4. Set `CAPTCHA_SERVICE=anti-captcha` and `CAPTCHA_API_KEY`

**Pricing**: ~$1-2 per 1000 captchas solved

## Error Handling

The system includes comprehensive error handling:

### Configuration Errors
```python
from phoenix_real_estate.foundation.utils.exceptions import ConfigurationError

try:
    handler = CaptchaHandler(config)
except ConfigurationError as e:
    print(f"Configuration error: {e}")
```

### Detection Errors
```python
from phoenix_real_estate.collectors.phoenix_mls.captcha_handler import CaptchaDetectionError

try:
    captcha_type, metadata = await handler.identify_captcha_type(page)
except CaptchaDetectionError as e:
    print(f"Could not identify captcha: {e}")
```

### Solving Errors
```python
from phoenix_real_estate.collectors.phoenix_mls.captcha_handler import CaptchaSolvingError

try:
    solution = await handler.solve_captcha(page, captcha_type, metadata)
except CaptchaSolvingError as e:
    print(f"Failed to solve captcha: {e}")
    # Retry logic or fallback handling
```

## Statistics and Monitoring

### Access Statistics

```python
# Get captcha handling statistics
stats = handler.get_statistics()
print(f"Captchas detected: {stats['captchas_detected']}")
print(f"Success rate: {stats['success_rate']:.1f}%")
print(f"Average solve time: {stats['average_solve_time']:.2f}s")
```

### Monitor Performance

```python
# Check type breakdown
captcha_types = stats['captcha_types']
print(f"reCAPTCHA v2: {captcha_types['recaptcha_v2']}")
print(f"Image captchas: {captcha_types['image']}")
```

### Screenshot Analysis

When `screenshot_on_detection` is enabled, screenshots are saved to help with debugging:

```
data/captcha_screenshots/
├── captcha_selector_iframe_20250121_143022.png
├── captcha_keyword_verification_20250121_143155.png
└── captcha_response_code_403_20250121_143301.png
```

## Best Practices

### 1. Cost Management
- Monitor your solving service usage and costs
- Set reasonable timeouts to avoid excessive API calls
- Use retry limits to prevent infinite loops

### 2. Performance Optimization
- Enable screenshot capture only during development/debugging
- Adjust detection selectors based on target sites
- Use appropriate solving service for your volume

### 3. Error Recovery
- Implement fallback handling for solving failures
- Log captcha encounters for analysis
- Monitor success rates and adjust configuration

### 4. Rate Limiting Integration
```python
# Captcha solving respects rate limits
await handler.handle_captcha(page)  # Includes appropriate delays
```

### 5. Session Management
- Solved captchas may affect session validity
- Consider session refresh after multiple solves
- Monitor for unusual captcha frequency (may indicate blocking)

## Troubleshooting

### Common Issues

**1. API Key Invalid**
```
ConfigurationError: Captcha handling enabled but API key not provided
```
*Solution*: Set `CAPTCHA_API_KEY` environment variable

**2. Service Timeout**
```
CaptchaSolvingError: Captcha solving timeout after 120s
```
*Solutions*: 
- Increase timeout in configuration
- Check service status and account balance
- Verify API key is correct

**3. Detection Not Working**
```
No captcha detected but manual inspection shows captcha
```
*Solutions*:
- Add custom detection selectors
- Enable debug logging to see what's being checked
- Capture screenshots to analyze page structure

**4. High Solving Costs**
*Solutions*:
- Review detection sensitivity settings
- Check for captcha loops (failed solutions causing more captchas)
- Monitor proxy health (blocked IPs may trigger more captchas)

### Debug Logging

Enable detailed logging for troubleshooting:

```python
import logging
logging.getLogger('phoenix_real_estate.collectors.phoenix_mls.captcha_handler').setLevel(logging.DEBUG)
```

### Test Configuration

Test your captcha handling setup:

```python
# Test with a known captcha page
test_url = "https://example.com/captcha-test-page"
await scraper.page.goto(test_url)

# Check detection
detected = await handler.detect_captcha(scraper.page)
print(f"Captcha detected: {detected}")

# Check type identification  
if detected:
    captcha_type, metadata = await handler.identify_captcha_type(scraper.page)
    print(f"Type: {captcha_type}, Metadata: {metadata}")
```

## Security Considerations

- **API Key Protection**: Store API keys securely, never commit to version control
- **Rate Limiting**: Respect service rate limits to avoid account suspension
- **Cost Controls**: Monitor usage to prevent unexpected charges
- **Legal Compliance**: Ensure captcha solving complies with target site's terms of service
- **Data Privacy**: Screenshots may contain sensitive information, handle appropriately

## Advanced Configuration

### Custom Service Integration

Extend support for additional services:

```python
class CustomCaptchaHandler(CaptchaHandler):
    async def _solve_custom_service(self, captcha_type, metadata):
        # Implement custom service integration
        pass
```

### Selective Captcha Handling

Handle only specific types:

```yaml
captcha:
  enabled: true
  handle_types:
    - "recaptcha_v2"
    - "image"
  # Skip v3 and hCaptcha
```

### Integration Hooks

Add custom logic around captcha handling:

```python
class CustomScraper(PhoenixMLSScraper):
    async def on_captcha_detected(self, captcha_type):
        # Custom logic when captcha is detected
        await self.notify_admin(f"Captcha detected: {captcha_type}")
    
    async def on_captcha_solved(self, solution):
        # Custom logic after successful solving
        await self.log_success(solution)
```