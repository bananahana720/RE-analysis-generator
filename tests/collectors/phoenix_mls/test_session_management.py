"""Test session management functionality for PhoenixMLSScraper."""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from pathlib import Path
from datetime import datetime, UTC

from phoenix_real_estate.collectors.phoenix_mls.scraper import PhoenixMLSScraper


@pytest.fixture
def valid_proxy_config():
    """Provide a valid proxy configuration."""
    return {
        "proxies": [
            {"host": "proxy1.test.com", "port": 8080, "username": "user", "password": "pass"}
        ]
    }


@pytest.mark.asyncio
async def test_session_initialization(valid_proxy_config):
    """Test that session management is properly initialized."""
    config = {"base_url": "https://www.phoenixmlssearch.com", "cookies_path": "test_data/cookies"}

    scraper = PhoenixMLSScraper(config, valid_proxy_config)

    assert scraper.cookies_path == Path("test_data/cookies")
    assert scraper.session_file == Path("test_data/cookies/phoenix_mls_session.pkl")
    assert scraper.cookies == []
    assert scraper.local_storage == {}
    assert scraper.session_storage == {}


@pytest.mark.asyncio
async def test_save_session(valid_proxy_config):
    """Test saving session data to file."""
    config = {"base_url": "https://test.com"}

    scraper = PhoenixMLSScraper(config, valid_proxy_config)

    # Mock browser context
    mock_context = AsyncMock()
    mock_cookies = [
        {"name": "session_id", "value": "abc123", "domain": ".test.com"},
        {"name": "auth_token", "value": "xyz789", "domain": ".test.com"},
    ]
    mock_context.cookies = AsyncMock(return_value=mock_cookies)
    scraper.context = mock_context

    # Mock page
    mock_page = AsyncMock()
    mock_page.evaluate = AsyncMock(
        side_effect=[
            {"key1": "value1", "key2": "value2"},  # local storage
            {"session1": "data1"},  # session storage
        ]
    )
    scraper.page = mock_page

    # Save session
    with patch("pickle.dump") as mock_pickle_dump:
        result = await scraper.save_session()

        assert result is True
        mock_context.cookies.assert_called_once()
        assert mock_page.evaluate.call_count == 2

        # Verify pickle.dump was called
        mock_pickle_dump.assert_called_once()


@pytest.mark.asyncio
async def test_load_session(valid_proxy_config):
    """Test loading session data from file."""
    config = {"base_url": "https://test.com"}

    scraper = PhoenixMLSScraper(config, valid_proxy_config)

    # Create mock session data
    session_data = {
        "cookies": [{"name": "session_id", "value": "abc123", "domain": ".test.com"}],
        "local_storage": {"key1": "value1"},
        "session_storage": {"session1": "data1"},
        "saved_at": datetime.now(UTC).isoformat(),
    }

    # Mock file existence and reading
    with patch.object(Path, "exists", return_value=True):
        with patch("builtins.open", create=True) as mock_open:
            with patch("pickle.load", return_value=session_data):
                # Mock browser context
                mock_context = AsyncMock()
                mock_context.add_cookies = AsyncMock()
                scraper.context = mock_context

                result = await scraper.load_session()

                assert result is True
                assert scraper.cookies == session_data["cookies"]
                assert scraper.local_storage == session_data["local_storage"]
                assert scraper.session_storage == session_data["session_storage"]

                # Verify cookies were added to context
                mock_context.add_cookies.assert_called_once_with(session_data["cookies"])


@pytest.mark.asyncio
async def test_maintain_session(valid_proxy_config):
    """Test session maintenance functionality."""
    config = {"base_url": "https://test.com"}

    scraper = PhoenixMLSScraper(config, valid_proxy_config)

    # Mock browser state
    scraper.context = AsyncMock()
    scraper.page = AsyncMock()

    # Mock internal methods
    scraper.save_session = AsyncMock(return_value=True)
    scraper._check_session_validity = AsyncMock(return_value=True)

    result = await scraper.maintain_session()

    assert result is True
    scraper.save_session.assert_called_once()
    scraper._check_session_validity.assert_called_once()


@pytest.mark.asyncio
async def test_maintain_session_invalid(valid_proxy_config):
    """Test session maintenance when session is invalid."""
    config = {"base_url": "https://test.com"}

    scraper = PhoenixMLSScraper(config, valid_proxy_config)

    # Mock browser state
    scraper.context = AsyncMock()
    scraper.page = AsyncMock()

    # Mock internal methods
    scraper.save_session = AsyncMock(return_value=True)
    scraper._check_session_validity = AsyncMock(side_effect=[False, True])  # Invalid then valid
    scraper.load_session = AsyncMock(return_value=True)

    result = await scraper.maintain_session()

    assert result is True
    scraper.save_session.assert_called_once()
    assert scraper._check_session_validity.call_count == 2
    scraper.load_session.assert_called_once()


@pytest.mark.asyncio
async def test_check_session_validity_with_indicators(valid_proxy_config):
    """Test session validity check with page indicators."""
    config = {"base_url": "https://test.com"}

    scraper = PhoenixMLSScraper(config, valid_proxy_config)

    # Mock page with user menu (logged in indicator)
    mock_page = AsyncMock()
    mock_element = AsyncMock()
    mock_page.query_selector = AsyncMock(
        side_effect=lambda s: mock_element if s == ".user-menu" else None
    )
    scraper.page = mock_page

    result = await scraper._check_session_validity()

    assert result is True


@pytest.mark.asyncio
async def test_check_session_validity_with_cookies(valid_proxy_config):
    """Test session validity check using cookies."""
    config = {"base_url": "https://test.com"}

    scraper = PhoenixMLSScraper(config, valid_proxy_config)

    # Mock page without indicators
    mock_page = AsyncMock()
    mock_page.query_selector = AsyncMock(return_value=None)
    scraper.page = mock_page

    # Mock context with valid session cookie
    mock_context = AsyncMock()
    future_timestamp = datetime.now(UTC).timestamp() + 3600  # 1 hour from now
    mock_cookies = [{"name": "PHPSESSID", "value": "abc123", "expires": future_timestamp}]
    mock_context.cookies = AsyncMock(return_value=mock_cookies)
    scraper.context = mock_context

    result = await scraper._check_session_validity()

    assert result is True


@pytest.mark.asyncio
async def test_clear_session(valid_proxy_config):
    """Test clearing session data."""
    config = {"base_url": "https://test.com"}

    scraper = PhoenixMLSScraper(config, valid_proxy_config)

    # Set some session data
    scraper.cookies = [{"name": "test"}]
    scraper.local_storage = {"key": "value"}
    scraper.session_storage = {"session": "data"}

    # Mock browser components
    mock_context = AsyncMock()
    mock_context.clear_cookies = AsyncMock()
    scraper.context = mock_context

    mock_page = AsyncMock()
    mock_page.evaluate = AsyncMock()
    scraper.page = mock_page

    # Mock file deletion
    with patch.object(Path, "exists", return_value=True):
        with patch.object(Path, "unlink") as mock_unlink:
            await scraper.clear_session()

            # Verify session data cleared
            assert scraper.cookies == []
            assert scraper.local_storage == {}
            assert scraper.session_storage == {}

            # Verify browser methods called
            mock_context.clear_cookies.assert_called_once()
            mock_page.evaluate.assert_called_once()
            mock_unlink.assert_called_once()


@pytest.mark.asyncio
async def test_browser_initialization_loads_session(valid_proxy_config):
    """Test that browser initialization loads existing session."""
    config = {"base_url": "https://test.com"}

    scraper = PhoenixMLSScraper(config, valid_proxy_config)

    # Mock the load_session method
    scraper.load_session = AsyncMock(return_value=True)

    # Mock playwright and browser components
    with patch(
        "phoenix_real_estate.collectors.phoenix_mls.scraper.async_playwright"
    ) as mock_playwright:
        mock_pw_instance = AsyncMock()
        mock_chromium = AsyncMock()
        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()

        # Set up the chain
        mock_async_pw = Mock()
        mock_playwright.return_value = mock_async_pw
        mock_async_pw.start = AsyncMock(return_value=mock_pw_instance)

        mock_pw_instance.chromium = mock_chromium
        mock_chromium.launch = AsyncMock(return_value=mock_browser)
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_context.add_init_script = AsyncMock()
        mock_page.set_default_timeout = Mock()

        # Mock proxy manager
        scraper.proxy_manager.get_next_proxy = AsyncMock(
            return_value={"host": "proxy.test.com", "port": 8080}
        )
        scraper.proxy_manager.format_proxy_url = Mock(return_value="http://proxy.test.com:8080")

        # Mock anti-detection
        scraper.anti_detection.get_viewport = Mock(return_value=(1920, 1080))
        scraper.anti_detection.get_user_agent = Mock(return_value="Mozilla/5.0")
        scraper.anti_detection.get_random_headers = Mock(return_value={})

        await scraper.initialize_browser()

        # Verify load_session was called
        scraper.load_session.assert_called_once()


@pytest.mark.asyncio
async def test_browser_close_saves_session(valid_proxy_config):
    """Test that closing browser saves session."""
    config = {"base_url": "https://test.com"}

    scraper = PhoenixMLSScraper(config, valid_proxy_config)

    # Mock browser components
    scraper.page = AsyncMock()
    scraper.context = AsyncMock()
    scraper.browser = AsyncMock()

    # Mock save_session
    scraper.save_session = AsyncMock(return_value=True)

    await scraper.close_browser()

    # Verify save_session was called
    scraper.save_session.assert_called_once()

    # Verify browser components were closed
    scraper.page.close.assert_called_once()
    scraper.context.close.assert_called_once()
    scraper.browser.close.assert_called_once()
