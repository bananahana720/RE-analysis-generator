#!/usr/bin/env python
"""
Run performance benchmarks for the Phoenix Real Estate configuration system.

Usage:
    python run_benchmarks.py

The benchmark results will be saved to the 'benchmark_results' directory.
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from tests.foundation.config.benchmarks import main

if __name__ == "__main__":
    print("Starting Phoenix Real Estate Configuration System Benchmarks...")
    print("-" * 70)
    main()
