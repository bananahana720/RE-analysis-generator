# Quick Setup Guide for Proxy and Captcha Services

## Steps to Configure Services

### 1. Update .env File

Run this command to safely update your .env file:
```bash
python scripts/setup/update_env_safely.py
```

When prompted, enter:
- WebShare username: [your username]
- WebShare password: [your password]
- 2captcha API key: [your API key]
- Maricopa API key: [optional - press Enter to skip]

### 2. Test Services

After updating .env, test your services:
```bash
python scripts/setup/configure_services.py
```

This will:
- Test WebShare proxy connection
- Test 2captcha API access
- Create config/proxies.yaml automatically

### 3. Test Phoenix MLS Scraper

Once services are configured:
```bash
python scripts/testing/test_phoenix_mls_with_services.py
```

This will:
- Test proxy manager
- Test captcha handler
- Try to scrape Phoenix MLS with proxy
- Generate a test report

### 4. Update CSS Selectors (if needed)

If the scraper can't find listings:
```bash
python scripts/testing/discover_phoenix_mls_selectors.py --headless
```

This will help identify the correct CSS selectors for property listings.

## Manual .env Update (Alternative)

If you prefer to update .env manually, add these lines:

```env
# Proxy configuration
WEBSHARE_USERNAME=your_username_here
WEBSHARE_PASSWORD=your_password_here

# Captcha service
CAPTCHA_API_KEY=your_2captcha_api_key_here
CAPTCHA_SERVICE=2captcha

# Phoenix MLS settings
PHOENIX_SOURCES_PHOENIX_MLS_CAPTCHA_ENABLED=true
PHOENIX_SOURCES_PHOENIX_MLS_CAPTCHA_SERVICE=2captcha
PHOENIX_SOURCES_PHOENIX_MLS_CAPTCHA_TIMEOUT=180
PHOENIX_SOURCES_PHOENIX_MLS_CAPTCHA_MAX_RETRIES=3
PHOENIX_MLS_RATE_LIMIT=60
PHOENIX_MLS_CONCURRENT_LIMIT=1
```

## Troubleshooting

### WebShare Issues
- Verify your account is active at https://webshare.io
- Check if you have available proxy bandwidth
- Ensure your subscription includes residential proxies

### 2captcha Issues
- Check your balance at https://2captcha.com
- Minimum balance needed: $0.01
- Average cost per captcha: $0.003

### MongoDB Not Running
```bash
net start MongoDB  # Run as Administrator
```

## Test Data Collection

Once everything is configured:
```bash
# Quick test with one property
python src/main.py --test --limit 1

# Full test with 10 properties
python src/main.py --test --limit 10
```

## Success Indicators

✅ WebShare test shows "Proxy working!"
✅ 2captcha shows balance > $0
✅ Phoenix MLS page loads without errors
✅ Properties are found and saved to MongoDB

## Common Issues

1. **"No proxies loaded"**
   - Check WEBSHARE_USERNAME and WEBSHARE_PASSWORD in .env
   - Verify config/proxies.yaml was created

2. **"Captcha API key not configured"**
   - Add CAPTCHA_API_KEY to .env
   - Set CAPTCHA_SERVICE=2captcha

3. **"No property listings found"**
   - Run selector discovery script
   - Update config/selectors/phoenix_mls.yaml

4. **MongoDB connection refused**
   - Start MongoDB service (as Administrator)
   - Check if port 27017 is available