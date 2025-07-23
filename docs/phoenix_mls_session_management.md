# Phoenix MLS Scraper - Session Management Guide

## Overview

The Phoenix MLS scraper includes robust session management functionality that allows you to:

- **Persist cookies** across scraping sessions
- **Save and restore browser storage** (localStorage and sessionStorage)
- **Automatically maintain sessions** during long-running scraping operations
- **Detect session expiration** and handle it gracefully
- **Clear sessions** when needed for testing or recovery

## Key Features

### 1. Automatic Session Persistence

When you initialize the browser, it automatically loads any existing session data:

```python
scraper = PhoenixMLSScraper(config, proxy_config)
await scraper.initialize_browser()  # Loads existing session if available
```

When you close the browser, the session is automatically saved:

```python
await scraper.close_browser()  # Saves current session
```

### 2. Session Data Storage

Session data is stored in a pickle file at the configured location:

```python
config = {
    "cookies_path": "data/cookies",  # Session file will be saved here
    # ... other config
}
```

The session file includes:
- All cookies from the browser context
- localStorage data
- sessionStorage data
- Timestamp of when the session was saved

### 3. Session Maintenance

During batch scraping operations, the session is automatically maintained:

```python
# Session is checked and maintained every 10 properties
results = await scraper.scrape_properties_batch(property_urls)
```

You can also manually maintain the session:

```python
is_valid = await scraper.maintain_session()
if not is_valid:
    # Session expired or invalid, handle accordingly
    pass
```

### 4. Session Validity Checking

The scraper can detect if a session is still valid by looking for:

1. **Login indicators** - Elements that appear when logged in (e.g., user menu, logout button)
2. **Session cookies** - Checks for common session cookie names and expiration
3. **Login page detection** - Detects if redirected to login page

```python
is_valid = await scraper._check_session_validity()
```

### 5. Session Management Methods

#### `load_session()` 
Loads saved session data from disk and applies it to the current browser context.

```python
success = await scraper.load_session()
```

#### `save_session()`
Saves the current browser session (cookies and storage) to disk.

```python
success = await scraper.save_session()
```

#### `maintain_session()`
Saves current session and checks if it's still valid. If invalid, attempts to restore from saved session.

```python
is_maintained = await scraper.maintain_session()
```

#### `clear_session()`
Clears all session data both from the browser and from disk. Useful for testing or when session is corrupted.

```python
await scraper.clear_session()
```

## Best Practices

### 1. Handle Session Expiration

Always be prepared for sessions to expire:

```python
try:
    properties = await scraper.search_properties_by_zipcode("85001")
except Exception as e:
    if "login" in str(e).lower():
        # Session might have expired
        await scraper.clear_session()
        # Reinitialize and potentially re-login
```

### 2. Regular Session Maintenance

For long-running scraping operations, the session is automatically maintained. However, you can also manually check:

```python
# Every N requests
if request_count % 50 == 0:
    if not await scraper.maintain_session():
        logger.warning("Session maintenance failed")
```

### 3. Session Isolation

Use different cookie paths for different scraping purposes:

```python
# For testing
test_config = {"cookies_path": "data/test_cookies"}

# For production
prod_config = {"cookies_path": "data/prod_cookies"}
```

### 4. Security Considerations

- Session files contain sensitive authentication data
- Store session files securely and never commit them to version control
- Add `data/cookies/` to your `.gitignore` file
- Consider encrypting session files for additional security

## Troubleshooting

### Session Not Loading

1. Check if the session file exists at the configured path
2. Verify file permissions allow reading
3. Check logs for any pickle loading errors

### Session Invalid After Loading

1. Session might have expired server-side
2. Website might have changed authentication mechanism
3. Try clearing the session and starting fresh

### Storage Not Persisting

1. Some sites clear storage on navigation
2. Ensure the page is fully loaded before saving session
3. Check browser console for any JavaScript errors

## Example Usage

See `examples/phoenix_mls_session_demo.py` for a complete working example of session management in action.

## Configuration Options

```python
config = {
    "base_url": "https://www.phoenixmlssearch.com",
    "cookies_path": "data/cookies",  # Where to store session files
    # ... other configuration
}
```

The `cookies_path` directory will be created automatically if it doesn't exist. The actual session file will be named `phoenix_mls_session.pkl` within this directory.