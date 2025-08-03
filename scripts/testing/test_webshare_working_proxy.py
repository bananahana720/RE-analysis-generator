#!/usr/bin/env python3
"""Test WebShare proxy with provided working credentials."""

import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def test_direct_proxy():
    """Test the proxy using the provided working example."""
    print("Testing WebShare Proxy")
    print("=" * 50)

    # Direct proxy configuration from user
    proxy_config = {
        "http": "http://svcvoqpm:g2j2p2cv602u@23.95.150.145:6114/",
        "https": "http://svcvoqpm:g2j2p2cv602u@23.95.150.145:6114/",
    }

    try:
        # Test with ipv4.webshare.io
        print("\n[TEST] Testing proxy with ipv4.webshare.io...")
        response = requests.get("https://ipv4.webshare.io/", proxies=proxy_config, timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text.strip()}")
        print("[OK] Proxy is working!")

        # Test with httpbin to see headers
        print("\n[TEST] Testing proxy with httpbin.org...")
        response = requests.get("http://httpbin.org/ip", proxies=proxy_config, timeout=10)
        print(f"Your IP through proxy: {response.json().get('origin', 'Unknown')}")

        return True

    except Exception as e:
        print(f"[ERROR] Proxy test failed: {str(e)}")
        return False


def download_proxy_list():
    """Download the full proxy list from WebShare."""
    print("\n[TEST] Downloading proxy list...")

    # Download URL provided by user
    download_url = "https://proxy.webshare.io/api/v2/proxy/list/download/tagoovkuesfewwgoyhfkequxeznkuhyriiqckxto/-/any/username/direct/-/"

    try:
        response = requests.get(download_url, timeout=10)
        if response.status_code == 200:
            print("[OK] Proxy list downloaded successfully!")
            print("Content preview (first 500 chars):")
            print(response.text[:500])

            # Save to file for reference
            with open("webshare_proxy_list.txt", "w") as f:
                f.write(response.text)
            print("\nFull proxy list saved to: webshare_proxy_list.txt")

            # Parse first few proxies
            lines = response.text.strip().split("\n")
            print(f"\nFound {len(lines)} proxies in list")
            print("\nFirst 5 proxies:")
            for i, line in enumerate(lines[:5]):
                print(f"  {i + 1}. {line}")

        else:
            print(f"[ERROR] Failed to download proxy list: {response.status_code}")
            print(f"Response: {response.text}")

    except Exception as e:
        print(f"[ERROR] Error downloading proxy list: {str(e)}")


if __name__ == "__main__":
    # Test the working proxy
    proxy_works = test_direct_proxy()

    # Download proxy list
    download_proxy_list()

    print("\n" + "=" * 50)
    print("WebShare Proxy Test Complete")
    print(f"Proxy Status: {'Working' if proxy_works else 'Failed'}")
