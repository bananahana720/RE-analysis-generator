#!/usr/bin/env python3
"""
Configure proxy and captcha services for Phoenix MLS data collection.

This script helps set up WebShare proxy and 2captcha services
with proper validation and testing.
"""

import sys
import asyncio
import aiohttp
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.phoenix_real_estate.foundation.logging import get_logger

logger = get_logger(__name__)


class ServiceConfigurator:
    """Configure and test external services."""

    def __init__(self):
        self.env_path = Path(".env")
        self.env_sample_path = Path(".env.sample")
        self.proxies_yaml_path = Path("config/proxies.yaml")
        self.config_updated = False

    async def test_webshare_proxy(self, username: str, password: str) -> bool:
        """Test WebShare proxy connection."""
        print("\n[TEST] Testing WebShare proxy connection...")

        # WebShare API endpoint for getting proxy list
        api_url = "https://proxy.webshare.io/api/v2/proxy/list/"

        try:
            # Create basic auth
            auth = aiohttp.BasicAuth(username, password)

            async with aiohttp.ClientSession() as session:
                # Test API access
                async with session.get(api_url, auth=auth) as response:
                    if response.status == 200:
                        data = await response.json()
                        proxy_count = data.get("count", 0)
                        print(f"[OK] WebShare API accessible. Found {proxy_count} proxies.")

                        # Get first proxy for testing
                        if data.get("results"):
                            first_proxy = data["results"][0]
                            proxy_address = first_proxy.get("proxy_address")
                            proxy_port = first_proxy.get("port")
                            print(f"[OK] First proxy: {proxy_address}:{proxy_port}")

                            # Test actual proxy connection
                            await self._test_proxy_connection(
                                proxy_address, proxy_port, username, password
                            )

                        return True
                    else:
                        print(f"[ERROR] WebShare API returned status {response.status}")
                        error_text = await response.text()
                        print(f"[ERROR] Response: {error_text}")
                        return False

        except Exception as e:
            print(f"[ERROR] Failed to connect to WebShare: {e}")
            return False

    async def _test_proxy_connection(
        self, host: str, port: int, username: str, password: str
    ) -> bool:
        """Test actual proxy connection."""
        print(f"\n[TEST] Testing proxy connection through {host}:{port}...")

        proxy_url = f"http://{username}:{password}@{host}:{port}"
        test_url = "http://httpbin.org/ip"

        try:
            connector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(test_url, proxy=proxy_url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"[OK] Proxy working! Your IP through proxy: {data.get('origin')}")
                        return True
                    else:
                        print(f"[ERROR] Proxy test failed with status {response.status}")
                        return False

        except Exception as e:
            print(f"[ERROR] Proxy connection failed: {e}")
            return False

    async def test_2captcha_service(self, api_key: str) -> bool:
        """Test 2captcha service."""
        print("\n[TEST] Testing 2captcha service...")

        # 2captcha balance check endpoint
        balance_url = f"https://2captcha.com/res.php?key={api_key}&action=getbalance&json=1"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(balance_url) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get("status") == 1:
                            balance = data.get("request", 0)
                            print(f"[OK] 2captcha API working. Balance: ${balance}")

                            if float(balance) < 0.01:
                                print(
                                    "[WARNING] Low balance! Add funds to continue using the service."
                                )

                            return True
                        else:
                            error = data.get("request", "Unknown error")
                            print(f"[ERROR] 2captcha API error: {error}")
                            return False
                    else:
                        print(f"[ERROR] 2captcha API returned status {response.status}")
                        return False

        except Exception as e:
            print(f"[ERROR] Failed to connect to 2captcha: {e}")
            return False

    def update_proxy_config(self, username: str, password: str):
        """Update proxy configuration file."""
        print("\n[UPDATE] Updating proxy configuration...")

        # Create config directory if it doesn't exist
        config_dir = Path("config")
        config_dir.mkdir(exist_ok=True)

        # Read the example file
        example_path = Path("config/proxies.yaml.example")
        if not example_path.exists():
            print("[ERROR] proxies.yaml.example not found!")
            return False

        # Read example content
        with open(example_path, "r") as f:
            content = f.read()

        # Replace placeholders
        content = content.replace("YOUR_WEBSHARE_USERNAME", username)
        content = content.replace("YOUR_WEBSHARE_PASSWORD", password)
        content = content.replace(
            "YOUR_WEBSHARE_API_KEY_HERE", password
        )  # WebShare uses password as API key

        # Write to actual config file
        with open(self.proxies_yaml_path, "w") as f:
            f.write(content)

        print(f"[OK] Updated {self.proxies_yaml_path}")
        return True

    def create_env_reminder(self, webshare_user: str, webshare_pass: str, captcha_key: str):
        """Create a reminder file for env updates."""
        reminder_path = Path("config/.env_update_reminder.txt")

        with open(reminder_path, "w") as f:
            f.write(f"""Environment Variable Update Reminder
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

IMPORTANT: Update your .env file with these values:

# Proxy configuration
WEBSHARE_USERNAME={webshare_user}
WEBSHARE_PASSWORD={webshare_pass}

# Captcha service
CAPTCHA_API_KEY={captcha_key}
CAPTCHA_SERVICE=2captcha

# Optional: Phoenix MLS specific settings
PHOENIX_SOURCES_PHOENIX_MLS_CAPTCHA_ENABLED=true
PHOENIX_SOURCES_PHOENIX_MLS_CAPTCHA_SERVICE=2captcha

Remember to:
1. Copy these values to your .env file
2. Delete this reminder file after updating
3. Never commit .env to version control
""")

        print(f"\n[REMINDER] Created {reminder_path}")
        print("[ACTION] Please update your .env file with the credentials above")

    async def run_configuration(self):
        """Run the configuration process."""
        print("Phoenix MLS Service Configuration")
        print("=" * 50)

        # Check if .env exists
        if not self.env_path.exists():
            print("\n[WARNING] .env file not found!")
            print("[ACTION] Please copy .env.sample to .env first")
            return

        print("\n[INFO] This script will help configure and test your proxy and captcha services.")
        print("[INFO] Your credentials will be saved to configuration files.")

        # Get credentials
        print("\n" + "=" * 50)
        webshare_user = input("Enter WebShare username: ").strip()
        webshare_pass = input("Enter WebShare password: ").strip()
        captcha_key = input("Enter 2captcha API key: ").strip()

        if not all([webshare_user, webshare_pass, captcha_key]):
            print("\n[ERROR] All credentials are required!")
            return

        # Test services
        print("\n" + "=" * 50)
        print("Testing Services...")

        # Test WebShare
        webshare_ok = await self.test_webshare_proxy(webshare_user, webshare_pass)

        # Test 2captcha
        captcha_ok = await self.test_2captcha_service(captcha_key)

        # Update configurations if tests passed
        if webshare_ok:
            self.update_proxy_config(webshare_user, webshare_pass)
        else:
            print("\n[WARNING] WebShare test failed. Configuration not updated.")

        # Create reminder for .env updates
        self.create_env_reminder(webshare_user, webshare_pass, captcha_key)

        # Summary
        print("\n" + "=" * 50)
        print("Configuration Summary:")
        print(f"  WebShare Proxy: {'✓' if webshare_ok else '✗'}")
        print(f"  2captcha Service: {'✓' if captcha_ok else '✗'}")

        if webshare_ok:
            print(f"\n[OK] Proxy configuration saved to: {self.proxies_yaml_path}")

        print("\n[IMPORTANT] Next steps:")
        print("1. Update your .env file with the credentials")
        print("2. Run: python scripts/testing/discover_phoenix_mls_selectors.py")
        print("3. Run: python src/main.py --test")

        if not (webshare_ok and captcha_ok):
            print("\n[WARNING] Some services failed. Please check your credentials.")
            sys.exit(1)


if __name__ == "__main__":
    configurator = ServiceConfigurator()
    asyncio.run(configurator.run_configuration())
