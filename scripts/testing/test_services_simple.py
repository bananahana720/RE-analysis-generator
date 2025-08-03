#!/usr/bin/env python3
"""
Simple test script for WebShare proxy and 2captcha services.

Tests the services without complex dependencies.
"""

import asyncio
import aiohttp
import os
from pathlib import Path
from dotenv import load_dotenv
import yaml
from datetime import datetime

# Load environment variables
load_dotenv()


async def test_webshare_api():
    """Test WebShare API access."""
    print("\n[TEST] WebShare API")
    print("-" * 40)

    username = os.getenv("WEBSHARE_USERNAME")
    password = os.getenv("WEBSHARE_PASSWORD")

    if not username or not password:
        print("[ERROR] WebShare credentials not found in .env")
        return False

    print(f"Username: {username}")

    # WebShare API endpoint
    api_url = "https://proxy.webshare.io/api/v2/proxy/list/"

    try:
        auth = aiohttp.BasicAuth(username, password)

        async with aiohttp.ClientSession() as session:
            async with session.get(api_url, auth=auth) as response:
                if response.status == 200:
                    data = await response.json()
                    proxy_count = data.get("count", 0)
                    print("[OK] API Access successful!")
                    print(f"[OK] Found {proxy_count} proxies in your account")

                    if proxy_count > 0 and data.get("results"):
                        first_proxy = data["results"][0]
                        print("\nFirst proxy details:")
                        print(f"  Address: {first_proxy.get('proxy_address')}")
                        print(f"  Port: {first_proxy.get('port')}")
                        print(f"  Country: {first_proxy.get('country_code')}")
                        print(f"  Valid: {first_proxy.get('valid', True)}")

                    return True
                else:
                    print(f"[ERROR] API returned status {response.status}")
                    error_text = await response.text()
                    print(f"[ERROR] {error_text}")
                    return False

    except Exception as e:
        print(f"[ERROR] Connection failed: {e}")
        return False


async def test_proxy_connection():
    """Test actual proxy connection."""
    print("\n[TEST] Proxy Connection")
    print("-" * 40)

    # Load proxy config
    proxy_config_path = Path("config/proxies.yaml")
    if not proxy_config_path.exists():
        print("[ERROR] config/proxies.yaml not found")
        return False

    with open(proxy_config_path, "r") as f:
        config = yaml.safe_load(f)

    webshare = config.get("webshare", {})
    if not webshare.get("enabled"):
        print("[ERROR] WebShare not enabled in config")
        return False

    username = webshare.get("username")
    password = webshare.get("password")

    # Get proxy list from API first
    api_url = "https://proxy.webshare.io/api/v2/proxy/list/"

    try:
        auth = aiohttp.BasicAuth(username, password)

        async with aiohttp.ClientSession() as session:
            # Get proxy list
            async with session.get(api_url, auth=auth) as response:
                if response.status != 200:
                    print("[ERROR] Failed to get proxy list")
                    return False

                data = await response.json()
                if not data.get("results"):
                    print("[ERROR] No proxies available")
                    return False

                # Use first proxy
                proxy_info = data["results"][0]
                proxy_host = proxy_info.get("proxy_address")
                proxy_port = proxy_info.get("port")

                print(f"Testing proxy: {proxy_host}:{proxy_port}")

                # Test proxy
                proxy_url = f"http://{username}:{password}@{proxy_host}:{proxy_port}"
                test_url = "http://httpbin.org/ip"

                async with session.get(test_url, proxy=proxy_url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        print("[OK] Proxy working!")
                        print(f"[OK] Your IP through proxy: {data.get('origin')}")
                        return True
                    else:
                        print(f"[ERROR] Proxy test failed with status {response.status}")
                        return False

    except Exception as e:
        print(f"[ERROR] Proxy test failed: {e}")
        return False


async def test_2captcha():
    """Test 2captcha service."""
    print("\n[TEST] 2captcha Service")
    print("-" * 40)

    api_key = os.getenv("CAPTCHA_API_KEY")

    if not api_key:
        print("[ERROR] CAPTCHA_API_KEY not found in .env")
        return False

    print(f"API Key: {api_key[:10]}...")

    # 2captcha balance check
    balance_url = f"https://2captcha.com/res.php?key={api_key}&action=getbalance&json=1"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(balance_url) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("status") == 1:
                        balance = float(data.get("request", 0))
                        print("[OK] 2captcha API working!")
                        print(f"[OK] Account balance: ${balance:.3f}")

                        if balance < 0.01:
                            print("[WARNING] Low balance! Add funds to use the service.")
                        elif balance < 1.0:
                            print(
                                "[INFO] Balance is sufficient for ~{:.0f} captchas".format(
                                    balance / 0.003
                                )
                            )
                        else:
                            print("[INFO] Balance is good")

                        return True
                    else:
                        error = data.get("request", "Unknown error")
                        print(f"[ERROR] API error: {error}")
                        if error == "ERROR_WRONG_USER_KEY":
                            print("[INFO] Check your API key in .env")
                        return False
                else:
                    print(f"[ERROR] HTTP status {response.status}")
                    return False

    except Exception as e:
        print(f"[ERROR] Connection failed: {e}")
        return False


async def main():
    """Run all tests."""
    print("Phoenix MLS Service Tests")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    results = {"webshare_api": False, "proxy_connection": False, "captcha": False}

    # Test WebShare API
    results["webshare_api"] = await test_webshare_api()

    # Test proxy connection if API works
    if results["webshare_api"]:
        results["proxy_connection"] = await test_proxy_connection()

    # Test 2captcha
    results["captcha"] = await test_2captcha()

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    all_passed = True
    for service, passed in results.items():
        status = "[OK]" if passed else "[FAILED]"
        print(f"{service.replace('_', ' ').title()}: {status}")
        if not passed:
            all_passed = False

    if all_passed:
        print("\n[SUCCESS] All services are working!")
        print("\nNext steps:")
        print("1. Start MongoDB: net start MongoDB (as Administrator)")
        print("2. Update selectors: python scripts/testing/discover_phoenix_mls_selectors.py")
        print("3. Test scraper: python scripts/testing/test_phoenix_mls_with_services.py")
    else:
        print("\n[WARNING] Some services failed. Check the errors above.")

    return all_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
