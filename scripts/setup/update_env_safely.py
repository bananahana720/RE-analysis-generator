#!/usr/bin/env python3
"""
Safely update .env file with new credentials.

This script helps update the .env file without exposing sensitive data.
"""

import os
from pathlib import Path
import re
from datetime import datetime


def update_env_file(updates: dict):
    """Safely update .env file with new values."""
    env_path = Path(".env")

    if not env_path.exists():
        print("[ERROR] .env file not found!")
        print("[ACTION] Copy .env.sample to .env first")
        return False

    # Read current content
    with open(env_path, "r") as f:
        content = f.read()

    # Backup current .env
    backup_path = env_path.with_suffix(f".backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    with open(backup_path, "w") as f:
        f.write(content)
    print(f"[OK] Created backup: {backup_path}")

    # Update each value
    updated_count = 0
    for key, value in updates.items():
        # Pattern to match the key with any value
        pattern = rf"^{re.escape(key)}=.*$"
        replacement = f"{key}={value}"

        # Check if key exists
        if re.search(pattern, content, re.MULTILINE):
            # Update existing key
            content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
            print(f"[UPDATE] {key}")
            updated_count += 1
        else:
            # Add new key at the end of file
            if not content.endswith("\n"):
                content += "\n"
            content += f"{key}={value}\n"
            print(f"[ADD] {key}")
            updated_count += 1

    # Write updated content
    with open(env_path, "w") as f:
        f.write(content)

    print(f"\n[OK] Updated {updated_count} values in .env")
    return True


def main():
    """Main function to get credentials and update .env."""
    print("Secure .env Update Tool")
    print("=" * 50)

    # Check if .env exists
    if not Path(".env").exists():
        # Create from sample
        print("[INFO] Creating .env from .env.sample...")
        sample_path = Path(".env.sample")
        if sample_path.exists():
            with open(sample_path, "r") as f:
                sample_content = f.read()
            with open(".env", "w") as f:
                f.write(sample_content)
            print("[OK] Created .env from sample")
        else:
            print("[ERROR] .env.sample not found!")
            return

    print("\nEnter your service credentials:")
    print("(Press Enter to skip any field)\n")

    # Collect updates
    updates = {}

    # WebShare credentials
    webshare_user = input("WebShare username: ").strip()
    if webshare_user:
        updates["WEBSHARE_USERNAME"] = webshare_user

    webshare_pass = input("WebShare password: ").strip()
    if webshare_pass:
        updates["WEBSHARE_PASSWORD"] = webshare_pass

    # Captcha service
    captcha_key = input("2captcha API key: ").strip()
    if captcha_key:
        updates["CAPTCHA_API_KEY"] = captcha_key
        updates["CAPTCHA_SERVICE"] = "2captcha"

    # Maricopa API key (if not already set)
    print("\nOptional - Maricopa County API:")
    maricopa_key = input("Maricopa API key (press Enter to skip): ").strip()
    if maricopa_key:
        updates["MARICOPA_API_KEY"] = maricopa_key

    # Apply updates
    if updates:
        print(f"\n[INFO] Updating {len(updates)} values...")
        if update_env_file(updates):
            print("\n[SUCCESS] .env file updated successfully!")

            # Additional Phoenix MLS settings
            print("\n[INFO] Adding recommended Phoenix MLS settings...")
            phoenix_settings = {
                "PHOENIX_SOURCES_PHOENIX_MLS_CAPTCHA_ENABLED": "true",
                "PHOENIX_SOURCES_PHOENIX_MLS_CAPTCHA_SERVICE": "2captcha",
                "PHOENIX_SOURCES_PHOENIX_MLS_CAPTCHA_TIMEOUT": "180",
                "PHOENIX_SOURCES_PHOENIX_MLS_CAPTCHA_MAX_RETRIES": "3",
                "PHOENIX_MLS_RATE_LIMIT": "60",
                "PHOENIX_MLS_CONCURRENT_LIMIT": "1",
            }
            update_env_file(phoenix_settings)

            print("\n[NEXT STEPS]:")
            print("1. Run: python scripts/setup/configure_services.py")
            print("   This will test your credentials and set up proxy config")
            print("2. Run: python scripts/testing/test_phoenix_mls_with_services.py")
            print("   This will test the complete setup")
            print("3. Run: python scripts/testing/discover_phoenix_mls_selectors.py")
            print("   This will help update the CSS selectors")
    else:
        print("\n[INFO] No updates provided.")


if __name__ == "__main__":
    os.chdir(Path(__file__).parent.parent.parent)  # Change to project root
    main()
