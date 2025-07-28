#!/usr/bin/env python3
"""
Test and fix WebShare proxy authentication.

WebShare uses API key authentication, not basic auth.
"""

import asyncio
import aiohttp
import os
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()


async def test_webshare_with_api_key():
    """Test WebShare using API key in header."""
    print("\n[TEST] WebShare API with API Key Authentication")
    print("-" * 40)
    
    # WebShare uses the password as API key
    api_key = os.getenv("WEBSHARE_PASSWORD")
    
    if not api_key:
        print("[ERROR] WEBSHARE_PASSWORD (API key) not found in .env")
        return False
    
    print(f"API Key: {api_key[:10]}...")
    
    # WebShare API endpoints
    endpoints = {
        "proxy_list": "https://proxy.webshare.io/api/v2/proxy/list/",
        "account": "https://proxy.webshare.io/api/v2/account/",
        "subscription": "https://proxy.webshare.io/api/v2/subscription/",
    }
    
    # Headers with API key
    headers = {
        "Authorization": f"Token {api_key}"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            # Test account endpoint first
            print("\n1. Testing account access...")
            async with session.get(endpoints["account"], headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"[OK] Account access successful!")
                    print(f"  Email: {data.get('email', 'N/A')}")
                    print(f"  ID: {data.get('id', 'N/A')}")
                else:
                    print(f"[ERROR] Account access failed: {response.status}")
                    error = await response.text()
                    print(f"[ERROR] {error}")
                    return False
            
            # Test proxy list
            print("\n2. Testing proxy list...")
            async with session.get(endpoints["proxy_list"], headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    proxy_count = data.get('count', 0)
                    print(f"[OK] Proxy list access successful!")
                    print(f"[OK] Total proxies: {proxy_count}")
                    
                    if proxy_count > 0 and data.get('results'):
                        print("\nProxy details:")
                        for i, proxy in enumerate(data['results'][:3], 1):
                            print(f"\n  Proxy {i}:")
                            print(f"    Address: {proxy.get('proxy_address')}:{proxy.get('port')}")
                            print(f"    Username: {proxy.get('username')}")
                            print(f"    Password: {proxy.get('password')}")
                            print(f"    Country: {proxy.get('country_code')}")
                            print(f"    Valid: {proxy.get('valid', True)}")
                    
                    return True, data.get('results', [])
                else:
                    print(f"[ERROR] Proxy list failed: {response.status}")
                    return False, []
                    
    except Exception as e:
        print(f"[ERROR] Connection failed: {e}")
        return False, []


async def test_proxy_connection(proxy_info):
    """Test actual proxy connection."""
    print("\n[TEST] Testing Proxy Connection")
    print("-" * 40)
    
    if not proxy_info:
        print("[ERROR] No proxy info provided")
        return False
    
    # Use first proxy
    proxy = proxy_info[0]
    proxy_address = proxy.get('proxy_address')
    proxy_port = proxy.get('port')
    proxy_username = proxy.get('username')
    proxy_password = proxy.get('password')
    
    print(f"Testing proxy: {proxy_address}:{proxy_port}")
    print(f"Proxy auth: {proxy_username}:{'*' * len(proxy_password)}")
    
    # Test URL
    test_url = "http://httpbin.org/ip"
    proxy_url = f"http://{proxy_username}:{proxy_password}@{proxy_address}:{proxy_port}"
    
    try:
        connector = aiohttp.TCPConnector(ssl=False)
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.get(test_url, proxy=proxy_url, timeout=15) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"[OK] Proxy connection successful!")
                    print(f"[OK] Your IP through proxy: {data.get('origin')}")
                    print(f"[OK] Proxy is working correctly!")
                    return True
                else:
                    print(f"[ERROR] Proxy test failed with status {response.status}")
                    return False
                    
    except asyncio.TimeoutError:
        print("[ERROR] Proxy connection timed out")
        return False
    except Exception as e:
        print(f"[ERROR] Proxy connection failed: {e}")
        return False


async def update_proxy_config(proxy_list):
    """Update proxy configuration with correct settings."""
    print("\n[UPDATE] Updating proxy configuration...")
    
    if not proxy_list:
        print("[ERROR] No proxies to configure")
        return
    
    # Get first proxy for config
    proxy = proxy_list[0]
    
    print(f"\nProxy configuration to add to config/proxies.yaml:")
    print("=" * 60)
    print("webshare:")
    print("  enabled: true")
    print(f"  api_key: {os.getenv('WEBSHARE_PASSWORD')}")
    print("  proxies:")
    
    for p in proxy_list[:3]:  # Show first 3
        print(f"    - host: {p.get('proxy_address')}")
        print(f"      port: {p.get('port')}")
        print(f"      username: {p.get('username')}")
        print(f"      password: {p.get('password')}")
    
    print("=" * 60)


async def main():
    """Run WebShare tests."""
    print("WebShare Proxy Authentication Test")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test API access
    success, proxy_list = await test_webshare_with_api_key()
    
    if success and proxy_list:
        # Test proxy connection
        proxy_works = await test_proxy_connection(proxy_list)
        
        if proxy_works:
            print("\n[SUCCESS] WebShare proxy is fully functional!")
            
            # Show config update
            await update_proxy_config(proxy_list)
        else:
            print("\n[WARNING] API works but proxy connection failed")
    else:
        print("\n[ERROR] WebShare API authentication failed")
        print("\nTroubleshooting:")
        print("1. Verify your API key (password) in .env")
        print("2. Check if your WebShare account is active")
        print("3. Try logging in at https://proxy.webshare.io")


if __name__ == "__main__":
    asyncio.run(main())