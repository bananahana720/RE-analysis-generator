#!/usr/bin/env python3
"""
Final WebShare proxy test with correct API endpoints.

Based on WebShare.io API documentation.
"""

import asyncio
import aiohttp
import os
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()


async def test_webshare_proxies():
    """Test WebShare proxy list retrieval."""
    print("\n[TEST] WebShare Proxy API")
    print("-" * 40)
    
    # Get credentials
    username = os.getenv("WEBSHARE_USERNAME")
    api_key = os.getenv("WEBSHARE_PASSWORD")  # WebShare uses password as API key
    
    if not username or not api_key:
        print("[ERROR] WebShare credentials not found in .env")
        return False, []
    
    print(f"Username: {username}")
    print(f"API Key: {api_key[:10]}...")
    
    # WebShare proxy download endpoint
    proxy_url = f"https://proxy.webshare.io/api/proxy/list/download/{username}-residential-1/"
    
    # Try different authentication methods
    auth_methods = [
        ("API Key Header", {"Authorization": f"Token {api_key}"}),
        ("Bearer Token", {"Authorization": f"Bearer {api_key}"}),
        ("API Key Param", None),
    ]
    
    for method_name, headers in auth_methods:
        print(f"\nTrying {method_name}...")
        
        try:
            async with aiohttp.ClientSession() as session:
                # Build request
                if headers:
                    resp = await session.get(proxy_url, headers=headers)
                else:
                    # Try with API key as parameter
                    resp = await session.get(f"{proxy_url}?api_key={api_key}")
                
                if resp.status == 200:
                    content = await resp.text()
                    print(f"[OK] {method_name} successful!")
                    
                    # Parse proxy list (format: host:port:username:password)
                    proxies = []
                    lines = content.strip().split('\n')
                    for line in lines[:5]:  # Show first 5
                        if ':' in line:
                            parts = line.strip().split(':')
                            if len(parts) >= 4:
                                proxy = {
                                    'host': parts[0],
                                    'port': parts[1],
                                    'username': parts[2],
                                    'password': parts[3]
                                }
                                proxies.append(proxy)
                                print(f"  Proxy: {proxy['host']}:{proxy['port']}")
                    
                    return True, proxies
                else:
                    print(f"[FAILED] Status {resp.status}")
                    
        except Exception as e:
            print(f"[ERROR] {e}")
    
    # Try simple download format
    print("\nTrying simple proxy list download...")
    simple_url = f"https://{username}:{api_key}@proxy.webshare.io/proxy/list/download/"
    
    try:
        async with aiohttp.ClientSession() as session:
            resp = await session.get(simple_url)
            if resp.status == 200:
                content = await resp.text()
                print("[OK] Simple download successful!")
                
                # Parse proxies
                proxies = []
                lines = content.strip().split('\n')
                for line in lines[:5]:
                    if line.strip():
                        print(f"  Proxy line: {line.strip()}")
                        # Try to parse different formats
                        if '@' in line:
                            # Format: http://user:pass@host:port
                            import re
                            match = re.match(r'https?://([^:]+):([^@]+)@([^:]+):(\d+)', line)
                            if match:
                                proxies.append({
                                    'username': match.group(1),
                                    'password': match.group(2),
                                    'host': match.group(3),
                                    'port': match.group(4)
                                })
                
                return True, proxies
    except Exception as e:
        print(f"[ERROR] Simple download failed: {e}")
    
    return False, []


async def test_proxy_connection(proxy):
    """Test a single proxy connection."""
    print(f"\n[TEST] Testing proxy {proxy['host']}:{proxy['port']}")
    
    proxy_url = f"http://{proxy['username']}:{proxy['password']}@{proxy['host']}:{proxy['port']}"
    test_url = "http://httpbin.org/ip"
    
    try:
        timeout = aiohttp.ClientTimeout(total=20)
        connector = aiohttp.TCPConnector(ssl=False)
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            async with session.get(test_url, proxy=proxy_url) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"[OK] Proxy working! IP: {data.get('origin')}")
                    return True
                else:
                    print(f"[ERROR] Status {response.status}")
                    return False
                    
    except Exception as e:
        print(f"[ERROR] {e}")
        return False


async def create_working_config(proxies):
    """Create a working proxy configuration."""
    print("\n[CONFIG] Creating working proxy configuration...")
    
    import yaml
    
    config = {
        'webshare': {
            'enabled': True,
            'method': 'rotating',  # or 'sticky' for persistent sessions
            'proxies': []
        },
        'settings': {
            'timeout': 30,
            'max_retries': 3,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    }
    
    # Add working proxies
    for proxy in proxies[:10]:  # Use first 10
        config['webshare']['proxies'].append({
            'host': proxy['host'],
            'port': int(proxy['port']),
            'username': proxy['username'],
            'password': proxy['password']
        })
    
    # Save to file
    config_path = "config/proxies_working.yaml"
    with open(config_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False)
    
    print(f"[OK] Saved working configuration to {config_path}")
    print(f"[INFO] Added {len(config['webshare']['proxies'])} proxies")


async def main():
    """Run all tests."""
    print("WebShare Proxy Test - Final Version")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test proxy list retrieval
    success, proxies = await test_webshare_proxies()
    
    if success and proxies:
        print(f"\n[OK] Retrieved {len(proxies)} proxies")
        
        # Test first proxy
        if await test_proxy_connection(proxies[0]):
            print("\n[SUCCESS] WebShare proxies are working!")
            
            # Create working config
            await create_working_config(proxies)
            
            print("\n[NEXT STEPS]:")
            print("1. Copy config/proxies_working.yaml to config/proxies.yaml")
            print("2. Start MongoDB: net start MongoDB")
            print("3. Run: python scripts/testing/test_phoenix_mls_with_services.py")
        else:
            print("\n[WARNING] Could not verify proxy connection")
    else:
        print("\n[ERROR] Could not retrieve proxy list")
        print("\nPlease check:")
        print("1. Your WebShare account at https://proxy.webshare.io")
        print("2. Your subscription includes residential proxies")
        print("3. Your API credentials are correct")


if __name__ == "__main__":
    asyncio.run(main())