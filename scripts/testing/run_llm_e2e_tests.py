#!/usr/bin/env python3
"""Run E2E tests for the LLM processing pipeline.

This script provides a convenient way to run E2E tests with different
configurations and modes.

Usage:
    python scripts/testing/run_llm_e2e_tests.py [options]

Options:
    --mode {mock,real,both}  Test mode (default: mock)
    --verbose               Verbose output
    --performance          Include performance benchmarks
    --failfast            Stop on first failure
    --coverage            Generate coverage report
"""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path


def run_command(cmd: list, env: dict = None) -> int:
    """Run a command and return exit code."""
    print(f"\n{'=' * 60}")
    print(f"Running: {' '.join(cmd)}")
    print(f"{'=' * 60}\n")

    result = subprocess.run(cmd, env=env)
    return result.returncode


def check_prerequisites(mode: str) -> bool:
    """Check if prerequisites are met for the test mode."""
    print("Checking prerequisites...")

    # Check MongoDB
    try:
        result = subprocess.run(
            ["mongosh", "--eval", "db.version()", "--quiet"], capture_output=True, text=True
        )
        if result.returncode != 0:
            print("❌ MongoDB is not running")
            print("   Run: net start MongoDB (as administrator)")
            return False
        print("✅ MongoDB is running")
    except FileNotFoundError:
        print("❌ MongoDB client (mongosh) not found")
        return False

    # Check Ollama for real mode
    if mode in ["real", "both"]:
        try:
            import requests

            response = requests.get("http://localhost:11434/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get("models", [])
                llama_models = [m for m in models if "llama3.2" in m.get("name", "")]
                if llama_models:
                    print("✅ Ollama is running with llama3.2:latest")
                else:
                    print("❌ llama3.2:latest model not found")
                    print("   Run: ollama pull llama3.2:latest")
                    return False
            else:
                print("❌ Ollama is not responding properly")
                return False
        except Exception as e:
            print(f"❌ Ollama is not running: {e}")
            print("   Run: ollama serve")
            return False

    print("✅ All prerequisites met")
    return True


def run_e2e_tests(args):
    """Run E2E tests based on arguments."""
    # Get project root
    project_root = Path(__file__).parent.parent.parent
    os.chdir(project_root)

    # Check prerequisites
    if not check_prerequisites(args.mode):
        return 1

    # Base pytest command
    base_cmd = [sys.executable, "-m", "pytest", "tests/e2e/test_processing_pipeline_e2e.py"]

    # Add common options
    if args.verbose:
        base_cmd.append("-vv")
    else:
        base_cmd.append("-v")

    if args.failfast:
        base_cmd.append("-x")

    # Add markers
    markers = ["e2e"]
    if not args.performance:
        markers.append("not slow")

    if markers:
        base_cmd.extend(["-m", " and ".join(markers)])

    # Coverage options
    if args.coverage:
        base_cmd.extend(
            [
                "--cov=phoenix_real_estate.collectors.processing",
                "--cov=phoenix_real_estate.orchestration",
                "--cov-report=html",
                "--cov-report=term-missing",
            ]
        )

    # Additional options
    base_cmd.extend(["--tb=short", "--color=yes", "-p", "no:warnings"])

    # Run tests based on mode
    exit_code = 0

    if args.mode in ["mock", "both"]:
        print("\n" + "=" * 60)
        print("RUNNING E2E TESTS IN MOCK MODE")
        print("=" * 60)

        env = os.environ.copy()
        env["E2E_MODE"] = "mock"

        start_time = time.time()
        code = run_command(base_cmd, env)
        duration = time.time() - start_time

        print(f"\nMock mode completed in {duration:.1f}s")
        exit_code = max(exit_code, code)

    if args.mode in ["real", "both"]:
        print("\n" + "=" * 60)
        print("RUNNING E2E TESTS IN REAL MODE")
        print("=" * 60)

        env = os.environ.copy()
        env["E2E_MODE"] = "real"

        start_time = time.time()
        code = run_command(base_cmd, env)
        duration = time.time() - start_time

        print(f"\nReal mode completed in {duration:.1f}s")
        exit_code = max(exit_code, code)

    # Summary
    print("\n" + "=" * 60)
    print("E2E TEST SUMMARY")
    print("=" * 60)

    if exit_code == 0:
        print("✅ All tests passed!")
    else:
        print(f"❌ Tests failed with exit code: {exit_code}")

    if args.coverage:
        print(f"\nCoverage report: {project_root}/htmlcov/index.html")

    return exit_code


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run E2E tests for LLM processing pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run mock tests only (fast)
  python scripts/testing/run_llm_e2e_tests.py
  
  # Run real tests with Ollama
  python scripts/testing/run_llm_e2e_tests.py --mode real
  
  # Run both modes with performance tests
  python scripts/testing/run_llm_e2e_tests.py --mode both --performance
  
  # Run with coverage report
  python scripts/testing/run_llm_e2e_tests.py --coverage
        """,
    )

    parser.add_argument(
        "--mode", choices=["mock", "real", "both"], default="mock", help="Test mode (default: mock)"
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--performance", action="store_true", help="Include performance benchmarks")
    parser.add_argument("--failfast", action="store_true", help="Stop on first failure")
    parser.add_argument("--coverage", action="store_true", help="Generate coverage report")

    args = parser.parse_args()

    try:
        exit_code = run_e2e_tests(args)
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error running tests: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
