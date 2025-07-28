# WebShare.io API Integration Guide

## API Documentation Summary

Based on the official WebShare.io API documentation at https://apidocs.webshare.io/, here are the key details:

### 1. Authentication

WebShare uses **Token-based authentication**:
- Format: `Authorization: Token YOUR_API_KEY`
- Get your API key from the WebShare dashboard
- Include this header in all API requests

### 2. Main API Endpoints

#### Profile Endpoint
- **URL**: `https://proxy.webshare.io/api/v2/profile/`
- **Method**: GET
- **Purpose**: Get account information including email and subscription details

#### Proxy List Endpoint
- **URL**: `https://proxy.webshare.io/api/v2/proxy/list/`
- **Method**: GET
- **Parameters**:
  - `page`: Page number (default: 1)
  - `page_size`: Results per page (default: 10, max: 100)
- **Purpose**: Retrieve your proxy list with credentials

### 3. Rate Limits
- **General API**: 180 requests per minute
- **Proxy download links**: 20 requests per minute

### 4. Response Format

All responses are JSON-encoded. The proxy list response includes:
```json
{
  "count": 100,
  "next": "https://proxy.webshare.io/api/v2/proxy/list/?page=2",
  "previous": null,
  "results": [
    {
      "proxy_address": "proxy.example.com",
      "port": 8080,
      "username": "user123",
      "password": "pass456",
      // Additional fields may vary
    }
  ]
}
```

## Testing the API

### 1. Set up your environment

First, add your API key to your `.env` file:
```
WEBSHARE_API_KEY=your_api_key_here
```

### 2. Run the test script

```bash
python scripts/testing/test_webshare_proxy.py
```

This script will:
1. Test the profile endpoint to verify authentication
2. Retrieve your proxy list
3. Test the first proxy to ensure it's working
4. Generate a sample `proxies.yaml` configuration

### 3. Configure proxies.yaml

After running the test script, you'll see output like:
```yaml
webshare:
  enabled: true
  api_key: "your_api_key"
  username: "proxy_username"
  password: "proxy_password"
  proxy_list:
    - host: "proxy1.webshare.io"
      port: 8080
    - host: "proxy2.webshare.io"
      port: 8080
    # ... more proxies
```

Copy this to `config/proxies.yaml` and adjust as needed.

## Integration with Phoenix MLS Scraper

The existing `ProxyManager` class expects proxies in this format:
```python
{
    "host": "proxy.example.com",
    "port": 8080,
    "username": "user123",
    "password": "pass456",
    "type": "http"
}
```

The test script includes a `convert_to_proxy_config()` method that converts WebShare API responses to this format automatically.

## Common Issues

1. **401 Unauthorized**: Check your API key is correct and properly formatted
2. **Rate limiting**: Stay within 180 requests/minute for general API calls
3. **Proxy format**: WebShare may return proxy data in different formats - the script handles common variations

## Next Steps

1. Sign up for WebShare.io (starts at $1/month)
2. Get your API key from the dashboard
3. Run the test script to verify everything works
4. Update `config/proxies.yaml` with your proxy details
5. The Phoenix MLS scraper will automatically use these proxies