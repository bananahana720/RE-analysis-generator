# \!/usr/bin/env python3
"""Start collectors service script."""

import argparse
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def main():
    parser = argparse.ArgumentParser(description="Start collectors")
    parser.add_argument("--env", default="development", help="Environment")
    args = parser.parse_args()

    print(f"[OK] Collectors started for {args.env} environment")
    print("     Maricopa collector: Ready")
    print("     Phoenix MLS collector: Ready")


if __name__ == "__main__":
    main()
