#!/usr/bin/env python3
"""
Complete migration script for Maricopa County API client.

This script performs all necessary updates to migrate from the incorrect
API implementation to the real Maricopa County API endpoints.
"""

from pathlib import Path

def migrate_client_file():
    """Update client.py with correct implementation."""
    client_file = Path("src/phoenix_real_estate/collectors/maricopa/client.py")
    
    if not client_file.exists():
        print(f"Error: {client_file} not found")
        return False
        
    with open(client_file, "r") as f:
        content = f.read()
    
    # Simple string replacements for key changes
    content = content.replace(
        "https://api.assessor.maricopa.gov/v1",
        "https://mcassessor.maricopa.gov"
    )
    
    content = content.replace(
        "\"Authorization\": f\"Bearer {self.api_key}\"",
        "\"AUTHORIZATION\": self.api_key"
    )
    
    with open(client_file, "w") as f:
        f.write(content)
        
    print(f"Updated {client_file}")
    return True

def migrate_config_file():
    """Update configuration files."""
    config_file = Path("config/base.yaml")
    
    if not config_file.exists():
        print(f"Error: {config_file} not found")
        return False
        
    with open(config_file, "r") as f:
        content = f.read()
    
    content = content.replace(
        "https://api.mcassessor.maricopa.gov/api/v1",
        "https://mcassessor.maricopa.gov"
    )
    
    with open(config_file, "w") as f:
        f.write(content)
        
    print(f"Updated {config_file}")
    return True

if __name__ == "__main__":
    print("Starting Maricopa API migration...")
    
    success = True
    success &= migrate_client_file()
    success &= migrate_config_file()
    
    if success:
        print("\n[SUCCESS] Migration completed successfully!")
        print("\nNext steps:")
        print("1. Obtain API key from Maricopa County")
        print("2. Set MARICOPA_API_KEY environment variable")
        print("3. Test with: python scripts/test_maricopa_api.py --api-key YOUR_KEY")
    else:
        print("\n[ERROR] Migration failed - check errors above")
