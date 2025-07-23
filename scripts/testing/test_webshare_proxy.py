#!/usr/bin/env python3
"""Test WebShare.io proxy service API and connectivity.

This script demonstrates the correct usage of WebShare.io API:
1. Authentication using Token header
2. Retrieving proxy list
3. Testing proxy connectivity
"""

import os
import sys
from pathlib import Path
import requests
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv
import logging
from urllib.parse import urlparse

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class WebShareClient:
    """Client for interacting with WebShare.io API."""
    
    BASE_URL = "https://proxy.webshare.io/api/v2"
    
    def __init__(self, api_key: str):
        """Initialize the WebShare client.
        
        Args:
            api_key: Your WebShare.io API key
        """
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "application/json"
        })
    
    def get_profile(self) -> Optional[Dict]:
        """Get account profile information.
        
        Returns:
            Profile data or None if request fails
        """
        try:
            response = self.session.get(f"{self.BASE_URL}/profile/")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get profile: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response body: {e.response.text}")
            return None
    
    def get_subscription(self) -> Optional[Dict]:
        """Get subscription information.
        
        Returns:
            Subscription data or None if request fails
        """
        try:
            response = self.session.get(f"{self.BASE_URL}/subscription/")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get subscription: {e}")
            return None
    
    def get_proxy_list(self, page: int = 1, page_size: int = 10) -> Optional[Dict]:
        """Get list of available proxies.
        
        Args:
            page: Page number (default: 1)
            page_size: Number of proxies per page (default: 10)
            
        Returns:
            Proxy list data or None if request fails
        """
        try:
            params = {
                "page": page,
                "page_size": page_size
            }
            response = self.session.get(
                f"{self.BASE_URL}/proxy/list/", 
                params=params
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get proxy list: {e}")
            return None
    
    def test_proxy(self, proxy_data: Dict) -> bool:
        """Test if a proxy is working.
        
        Args:
            proxy_data: Proxy information from the API
            
        Returns:
            True if proxy works, False otherwise
        """
        try:
            # WebShare API typically returns proxy data with these fields:
            # - proxy_address or address: The proxy hostname/IP
            # - ports: Dictionary with protocol:port mappings
            # - username: Authentication username
            # - password: Authentication password
            
            # Try different field names that WebShare might use
            proxy_host = (
                proxy_data.get("proxy_address") or 
                proxy_data.get("address") or 
                proxy_data.get("host", "")
            )
            
            # Extract port - WebShare often uses 'ports' dict or direct 'port' field
            if "ports" in proxy_data and isinstance(proxy_data["ports"], dict):
                # Get HTTP port from ports dictionary
                proxy_port = proxy_data["ports"].get("http", proxy_data["ports"].get("socks5", ""))
            else:
                proxy_port = proxy_data.get("port", "")
            
            # Extract authentication
            username = proxy_data.get("username", "")
            password = proxy_data.get("password", "")
            
            # If no direct auth fields, check for 'credentials'
            if not username and "credentials" in proxy_data:
                username = proxy_data["credentials"].get("username", "")
                password = proxy_data["credentials"].get("password", "")
            
            if not all([proxy_host, proxy_port, username, password]):
                logger.warning(f"Incomplete proxy data: host={proxy_host}, port={proxy_port}, auth={bool(username)}")
                logger.debug(f"Full proxy data: {proxy_data}")
                return False
            
            # Format proxy URL
            proxy_url = f"http://{username}:{password}@{proxy_host}:{proxy_port}"
            
            # Test the proxy
            test_url = "http://httpbin.org/ip"
            proxies = {
                "http": proxy_url,
                "https": proxy_url
            }
            
            response = requests.get(
                test_url, 
                proxies=proxies,
                timeout=10
            )
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"Proxy test successful. IP: {result.get('origin', 'Unknown')}")
            return True
            
        except Exception as e:
            logger.error(f"Proxy test failed: {e}")
            return False
    
    def convert_to_proxy_config(self, proxy_data: Dict) -> Dict[str, Any]:
        """Convert WebShare proxy data to project proxy configuration format.
        
        Args:
            proxy_data: Proxy data from WebShare API
            
        Returns:
            Dictionary in project proxy configuration format
        """
        # Extract fields using same logic as test_proxy
        proxy_host = (
            proxy_data.get("proxy_address") or 
            proxy_data.get("address") or 
            proxy_data.get("host", "")
        )
        
        if "ports" in proxy_data and isinstance(proxy_data["ports"], dict):
            proxy_port = proxy_data["ports"].get("http", proxy_data["ports"].get("socks5", ""))
        else:
            proxy_port = proxy_data.get("port", "")
        
        username = proxy_data.get("username", "")
        password = proxy_data.get("password", "")
        
        if not username and "credentials" in proxy_data:
            username = proxy_data["credentials"].get("username", "")
            password = proxy_data["credentials"].get("password", "")
        
        # Convert to project format
        return {
            "host": proxy_host,
            "port": int(proxy_port) if proxy_port else 80,
            "username": username,
            "password": password,
            "type": "http"  # Default to HTTP
        }


def main():
    """Main function to test WebShare.io API."""
    # Get API key from environment
    api_key = os.getenv("WEBSHARE_API_KEY")
    
    if not api_key:
        logger.error("WEBSHARE_API_KEY not found in environment variables")
        logger.info("Please set it in your .env file or environment")
        return
    
    # Initialize client
    client = WebShareClient(api_key)
    
    # Test 1: Get profile information
    logger.info("Testing profile endpoint...")
    profile = client.get_profile()
    if profile:
        logger.info("Profile retrieved successfully:")
        logger.info(f"  Email: {profile.get('email', 'N/A')}")
        if 'subscription' in profile:
            sub = profile['subscription']
            logger.info(f"  Plan: {sub.get('plan', 'N/A')}")
            logger.info(f"  Status: {sub.get('status', 'N/A')}")
    else:
        logger.error("Failed to retrieve profile")
    
    # Test 1.5: Get subscription details
    logger.info("\nTesting subscription endpoint...")
    subscription = client.get_subscription()
    if subscription:
        logger.info("Subscription retrieved successfully:")
        logger.info(f"  Proxy count: {subscription.get('proxy_count', 'N/A')}")
        logger.info(f"  Bandwidth: {subscription.get('bandwidth_limit', 'N/A')}")
    else:
        logger.debug("Subscription endpoint might not be available")
    
    # Test 2: Get proxy list
    logger.info("\nTesting proxy list endpoint...")
    proxy_list = client.get_proxy_list(page=1, page_size=5)
    if proxy_list:
        logger.info(f"Retrieved {proxy_list.get('count', 0)} total proxies")
        logger.info(f"Showing first {len(proxy_list.get('results', []))} proxies")
        
        # Test first proxy if available
        results = proxy_list.get("results", [])
        if results:
            logger.info("\nTesting first proxy...")
            first_proxy = results[0]
            logger.info(f"Proxy details: {first_proxy}")
            
            # Test the proxy
            if client.test_proxy(first_proxy):
                logger.info("✓ Proxy is working!")
            else:
                logger.error("✗ Proxy test failed")
    else:
        logger.error("Failed to retrieve proxy list")
    
    # Display rate limit information
    logger.info("\nRate Limits:")
    logger.info("  - General API: 180 requests/minute")
    logger.info("  - Proxy download links: 20 requests/minute")
    
    # Show how to generate proxies.yaml configuration
    if proxy_list and proxy_list.get("results"):
        logger.info("\n" + "="*60)
        logger.info("Sample proxies.yaml configuration:")
        logger.info("="*60)
        
        print("\nwebshare:")
        print("  enabled: true")
        print(f"  api_key: \"{api_key}\"")
        
        # Get first proxy for auth details
        first_proxy = proxy_list["results"][0]
        config = client.convert_to_proxy_config(first_proxy)
        print(f"  username: \"{config['username']}\"")
        print(f"  password: \"{config['password']}\"")
        print("  proxy_list:")
        
        # Show up to 5 proxies
        for i, proxy_data in enumerate(proxy_list["results"][:5]):
            config = client.convert_to_proxy_config(proxy_data)
            print(f"    - host: \"{config['host']}\"")
            print(f"      port: {config['port']}")
        
        if len(proxy_list["results"]) > 5:
            print(f"    # ... and {len(proxy_list['results']) - 5} more proxies")
        
        print("\n# Add this configuration to config/proxies.yaml")


if __name__ == "__main__":
    main()