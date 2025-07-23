#!/usr/bin/env python3
"""
Automatically configure proxy and captcha services from environment variables.

This script reads credentials from .env and sets up the services.
"""

import os
import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv
import yaml
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Load environment variables
load_dotenv()


class AutoServiceConfigurator:
    """Automatically configure services from environment."""
    
    def __init__(self):
        self.webshare_user = os.getenv("WEBSHARE_USERNAME")
        self.webshare_pass = os.getenv("WEBSHARE_PASSWORD")
        self.captcha_key = os.getenv("CAPTCHA_API_KEY")
        self.proxies_yaml_path = Path("config/proxies.yaml")
    
    def check_credentials(self):
        """Check if all credentials are available."""
        print("[CHECK] Checking environment variables...")
        
        missing = []
        if not self.webshare_user:
            missing.append("WEBSHARE_USERNAME")
        if not self.webshare_pass:
            missing.append("WEBSHARE_PASSWORD")
        if not self.captcha_key:
            missing.append("CAPTCHA_API_KEY")
        
        if missing:
            print(f"[ERROR] Missing environment variables: {', '.join(missing)}")
            print("[ACTION] Please update your .env file with the required credentials")
            return False
        
        print("[OK] All credentials found in environment")
        return True
    
    def create_proxy_config(self):
        """Create proxy configuration file."""
        print("\n[CONFIG] Creating proxy configuration...")
        
        # Ensure config directory exists
        config_dir = Path("config")
        config_dir.mkdir(exist_ok=True)
        
        # Proxy configuration
        proxy_config = {
            'webshare': {
                'enabled': True,
                'api_key': self.webshare_pass,  # WebShare uses password as API key
                'username': self.webshare_user,
                'password': self.webshare_pass,
                'endpoint': 'proxy.webshare.io',
                'port': 80,
                'proxy_list': [
                    {'host': 'proxy.webshare.io', 'port': 80}
                ],
                'rotation_strategy': 'round_robin'
            },
            'smartproxy': {
                'enabled': False,
                'username': 'YOUR_SMARTPROXY_USERNAME',
                'password': 'YOUR_SMARTPROXY_PASSWORD',
                'endpoint': 'gate.smartproxy.com',
                'port': 10000
            },
            'generic': {
                'enabled': False,
                'proxies': []
            },
            'settings': {
                'timeout': 30,
                'max_retries': 3,
                'verify_ssl': False,
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            },
            'rate_limits': {
                'requests_per_minute': 20,
                'requests_per_hour': 500,
                'cooldown_period': 60
            },
            'validation': {
                'check_on_startup': True,
                'check_interval': 300,
                'remove_failed_proxies': True,
                'min_success_rate': 0.8
            }
        }
        
        # Write configuration
        with open(self.proxies_yaml_path, 'w') as f:
            yaml.dump(proxy_config, f, default_flow_style=False, sort_keys=False)
        
        print(f"[OK] Proxy configuration saved to: {self.proxies_yaml_path}")
        return True
    
    async def test_services(self):
        """Quick test of services."""
        print("\n[TEST] Testing services...")
        
        # Import test functions
        from scripts.setup.configure_services import ServiceConfigurator
        
        configurator = ServiceConfigurator()
        
        # Test WebShare
        print("\n1. Testing WebShare proxy...")
        try:
            webshare_ok = await configurator.test_webshare_proxy(
                self.webshare_user, self.webshare_pass
            )
        except Exception as e:
            print(f"[ERROR] WebShare test failed: {e}")
            webshare_ok = False
        
        # Test 2captcha
        print("\n2. Testing 2captcha service...")
        try:
            captcha_ok = await configurator.test_2captcha_service(self.captcha_key)
        except Exception as e:
            print(f"[ERROR] 2captcha test failed: {e}")
            captcha_ok = False
        
        return webshare_ok, captcha_ok
    
    def create_summary_report(self, webshare_ok, captcha_ok):
        """Create configuration summary."""
        print("\n" + "=" * 60)
        print("CONFIGURATION SUMMARY")
        print("=" * 60)
        
        print(f"\nWebShare Proxy: {'[OK]' if webshare_ok else '[FAILED]'}")
        print(f"2captcha Service: {'[OK]' if captcha_ok else '[FAILED]'}")
        print(f"Proxy Config File: [OK] Created at {self.proxies_yaml_path}")
        
        if webshare_ok and captcha_ok:
            print("\n[SUCCESS] All services configured successfully!")
            print("\nNext steps:")
            print("1. Start MongoDB: net start MongoDB (as Administrator)")
            print("2. Test Phoenix MLS: python scripts/testing/test_phoenix_mls_with_services.py")
            print("3. Update selectors: python scripts/testing/discover_phoenix_mls_selectors.py")
        else:
            print("\n[WARNING] Some services failed configuration")
            if not webshare_ok:
                print("\nWebShare troubleshooting:")
                print("- Verify your WebShare account is active")
                print("- Check username and password in .env")
                print("- Ensure you have proxy bandwidth available")
            
            if not captcha_ok:
                print("\n2captcha troubleshooting:")
                print("- Verify your API key is correct")
                print("- Check your account balance")
                print("- Ensure service is not blocked")
    
    async def run(self):
        """Run automatic configuration."""
        print("Phoenix MLS Automatic Service Configuration")
        print("=" * 60)
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Check credentials
        if not self.check_credentials():
            return False
        
        # Create proxy config
        if not self.create_proxy_config():
            return False
        
        # Test services
        webshare_ok, captcha_ok = await self.test_services()
        
        # Create summary
        self.create_summary_report(webshare_ok, captcha_ok)
        
        return webshare_ok and captcha_ok


async def main():
    """Main entry point."""
    configurator = AutoServiceConfigurator()
    success = await configurator.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())