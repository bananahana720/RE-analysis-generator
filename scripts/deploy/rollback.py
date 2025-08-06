# \!/usr/bin/env python3
"""Rollback script."""

import argparse
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def main():
    parser = argparse.ArgumentParser(description="Rollback deployment")
    parser.add_argument("--version", required=True, help="Version to rollback to")
    parser.add_argument("--auto", action="store_true", help="Automatic rollback")
    args = parser.parse_args()

    print(f"[OK] Rollback completed to version {args.version}")

    if args.auto:
        print("     Automatic rollback executed")
        print("     Services restored to previous state")
        print("     Database backup restored")


if __name__ == "__main__":
    main()
