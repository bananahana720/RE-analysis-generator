#!/usr/bin/env python3
"""
Check the setup status of all Phoenix Real Estate Data Collection components.

This script verifies:
1. Environment configuration
2. MongoDB connection
3. Proxy service configuration
4. Captcha service configuration
5. Required files and directories
"""

import os
import sys
import asyncio
from pathlib import Path
from datetime import datetime
import yaml
import json

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class SetupChecker:
    """Check setup status of all components."""

    def __init__(self):
        self.status = {"timestamp": datetime.now().isoformat(), "components": {}, "ready": False}
        self.required_count = 0
        self.ready_count = 0

    def check_env_file(self):
        """Check .env file status."""
        print("\n[CHECK] Environment Configuration (.env)")
        print("-" * 40)

        env_path = Path(".env")
        if not env_path.exists():
            print("[X] .env file NOT FOUND")
            print("   ACTION: Copy .env.sample to .env")
            self.status["components"]["env_file"] = "MISSING"
            return False

        print("[OK] .env file exists")

        # Check for required variables
        required_vars = {
            "MONGODB_URI": False,
            "MONGODB_DATABASE": False,
            "ENVIRONMENT": False,
            "SECRET_KEY": False,
            "MARICOPA_API_KEY": False,
            "WEBSHARE_USERNAME": False,
            "WEBSHARE_PASSWORD": False,
            "CAPTCHA_API_KEY": False,
        }

        # Read .env content (safely)
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    if "=" in line:
                        key = line.split("=", 1)[0].strip()
                        value = line.split("=", 1)[1].strip()
                        if key in required_vars and value and value != "your_" + key.lower():
                            required_vars[key] = True

        # Report status
        configured = sum(required_vars.values())
        total = len(required_vars)

        print(f"\nRequired variables: {configured}/{total} configured")
        for var, status in required_vars.items():
            print(f"  {'[OK]' if status else '[X]'} {var}")

        self.status["components"]["env_file"] = {
            "status": "CONFIGURED" if configured == total else "PARTIAL",
            "configured": configured,
            "total": total,
            "missing": [k for k, v in required_vars.items() if not v],
        }

        return configured >= 6  # At least main services configured

    def check_mongodb(self):
        """Check MongoDB status."""
        print("\n[CHECK] MongoDB Connection")
        print("-" * 40)

        # Try to import and test
        try:
            import motor.motor_asyncio

            # Quick connection test
            client = motor.motor_asyncio.AsyncIOMotorClient(
                "mongodb://localhost:27017", serverSelectionTimeoutMS=2000
            )

            # Run async test
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            async def test():
                try:
                    await client.admin.command("ping")
                    return True
                except Exception:
                    return False

            connected = loop.run_until_complete(test())
            loop.close()

            if connected:
                print("[OK] MongoDB is RUNNING and accessible")
                self.status["components"]["mongodb"] = "RUNNING"
                return True
            else:
                print("[X] MongoDB is NOT RUNNING")
                print("   ACTION: Run 'net start MongoDB' as Administrator")
                self.status["components"]["mongodb"] = "STOPPED"
                return False

        except Exception as e:
            print(f"[X] MongoDB test failed: {e}")
            self.status["components"]["mongodb"] = "ERROR"
            return False

    def check_proxy_config(self):
        """Check proxy configuration."""
        print("\n[CHECK] Proxy Configuration")
        print("-" * 40)

        proxy_yaml = Path("config/proxies.yaml")
        proxy_example = Path("config/proxies.yaml.example")

        if not proxy_yaml.exists():
            print("[X] config/proxies.yaml NOT FOUND")
            if proxy_example.exists():
                print("   [i]  Example file exists: config/proxies.yaml.example")
                print("   ACTION: Run 'python scripts/setup/configure_services.py'")
            self.status["components"]["proxy_config"] = "MISSING"
            return False

        print("[OK] config/proxies.yaml exists")

        # Check content
        try:
            with open(proxy_yaml, "r") as f:
                config = yaml.safe_load(f)

            webshare = config.get("webshare", {})
            if webshare.get("enabled") and webshare.get("username") != "YOUR_WEBSHARE_USERNAME":
                print("[OK] WebShare proxy configured")
                self.status["components"]["proxy_config"] = "CONFIGURED"
                return True
            else:
                print("[!]  WebShare proxy not fully configured")
                self.status["components"]["proxy_config"] = "PARTIAL"
                return False

        except Exception as e:
            print(f"[X] Error reading proxy config: {e}")
            self.status["components"]["proxy_config"] = "ERROR"
            return False

    def check_selectors(self):
        """Check Phoenix MLS selectors."""
        print("\n[CHECK] Phoenix MLS Selectors")
        print("-" * 40)

        selectors_path = Path("config/selectors/phoenix_mls.yaml")

        if not selectors_path.exists():
            print("[X] config/selectors/phoenix_mls.yaml NOT FOUND")
            print("   ACTION: Run 'python scripts/testing/discover_phoenix_mls_selectors.py'")
            self.status["components"]["selectors"] = "MISSING"
            return False

        print("[OK] Selectors file exists")

        # Check if selectors are updated
        try:
            with open(selectors_path, "r") as f:
                selectors = yaml.safe_load(f)

            # Check for placeholder values
            listings = selectors.get("listings", {})
            if listings.get("container") == ".listing-results":
                print("[!]  Selectors appear to be default/outdated")
                print("   ACTION: Run selector discovery to update")
                self.status["components"]["selectors"] = "OUTDATED"
                return False
            else:
                print("[OK] Selectors appear to be customized")
                self.status["components"]["selectors"] = "CONFIGURED"
                return True

        except Exception as e:
            print(f"[X] Error reading selectors: {e}")
            self.status["components"]["selectors"] = "ERROR"
            return False

    def check_directories(self):
        """Check required directories."""
        print("\n[CHECK] Required Directories")
        print("-" * 40)

        required_dirs = ["data/raw", "data/processed", "logs", "config", "config/selectors"]

        all_exist = True
        for dir_path in required_dirs:
            path = Path(dir_path)
            if path.exists():
                print(f"[OK] {dir_path}")
            else:
                print(f"[X] {dir_path} (creating...)")
                path.mkdir(parents=True, exist_ok=True)
                all_exist = False

        self.status["components"]["directories"] = "READY" if all_exist else "CREATED"
        return True

    def generate_summary(self):
        """Generate setup summary."""
        print("\n" + "=" * 60)
        print("SETUP STATUS SUMMARY")
        print("=" * 60)

        # Component status
        components = [
            ("Environment (.env)", self.check_env_file(), True),
            ("MongoDB", self.check_mongodb(), True),
            ("Proxy Config", self.check_proxy_config(), True),
            ("CSS Selectors", self.check_selectors(), False),
            ("Directories", self.check_directories(), False),
        ]

        ready_count = 0
        required_count = 0

        print("\nComponent Status:")
        for name, ready, required in components:
            if required:
                required_count += 1
                if ready:
                    ready_count += 1
            status_icon = "[OK]" if ready else ("[X]" if required else "[!]")
            print(f"  {status_icon} {name}")

        # Overall readiness
        self.status["ready"] = ready_count == required_count

        print(f"\nRequired Components: {ready_count}/{required_count} ready")

        if self.status["ready"]:
            print("\n[SUCCESS] SYSTEM READY FOR DATA COLLECTION!")
            print("\nNext step: python src/main.py --test --limit 1")
        else:
            print("\n[!]  SYSTEM NOT READY")
            print("\nRequired actions:")

            if not self.status["components"].get("env_file"):
                print("1. Create .env file from .env.sample")
                print("2. Add your service credentials")
            elif isinstance(self.status["components"].get("env_file"), dict):
                missing = self.status["components"]["env_file"].get("missing", [])
                if missing:
                    print(f"1. Configure missing variables in .env: {', '.join(missing)}")

            if self.status["components"].get("mongodb") != "RUNNING":
                print("2. Start MongoDB: net start MongoDB (as Administrator)")

            if self.status["components"].get("proxy_config") != "CONFIGURED":
                print("3. Configure proxy: python scripts/setup/configure_services.py")

        # Save status report
        report_path = f"setup_status_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, "w") as f:
            json.dump(self.status, f, indent=2)
        print(f"\n[INFO] Detailed status saved to: {report_path}")


def main():
    """Run setup status check."""
    print("Phoenix Real Estate Data Collection - Setup Status Check")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    checker = SetupChecker()
    checker.generate_summary()


if __name__ == "__main__":
    os.chdir(Path(__file__).parent.parent.parent)  # Change to project root
    main()
