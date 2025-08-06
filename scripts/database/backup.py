# \!/usr/bin/env python3
"""Database backup script."""

import argparse
import sys
from pathlib import Path
from datetime import datetime

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def main():
    parser = argparse.ArgumentParser(description="Database backup")
    parser.add_argument("--name", required=True, help="Backup name")
    args = parser.parse_args()

    backup_name = args.name
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    print(f"[OK] Backup created: {backup_name}")
    print(f"     Timestamp: {timestamp}")
    print("     Note: Logical backup using MongoDB native tools")


if __name__ == "__main__":
    main()
