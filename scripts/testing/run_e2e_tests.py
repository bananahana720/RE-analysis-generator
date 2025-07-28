#!/usr/bin/env python3
"""
Run E2E tests with Playwright browser automation.

This script ensures Playwright browsers are installed and runs
the E2E test suite with appropriate configuration.
"""

import subprocess
import sys
import os
import argparse
from pathlib import Path


def install_playwright_browsers():
    """Install Playwright browsers if not already installed."""
    print("Checking Playwright browser installation...")
    try:
        # Check if browsers are installed
        result = subprocess.run(
            [sys.executable, "-m", "playwright", "install", "--dry-run"],
            capture_output=True,
            text=True
        )
        
        if "chromium" not in result.stdout.lower():
            print("Installing Playwright browsers...")
            subprocess.run(
                [sys.executable, "-m", "playwright", "install", "chromium"],
                check=True
            )
            print("[OK] Playwright browsers installed successfully")
        else:
            print("[OK] Playwright browsers already installed")
            
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Failed to install Playwright browsers: {e}")
        sys.exit(1)


def check_mongodb():
    """Check if MongoDB is running."""
    print("\nChecking MongoDB connection...")
    script_path = Path(__file__).parent / "test_mongodb_connection.py"
    
    result = subprocess.run(
        [sys.executable, str(script_path)],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print("[ERROR] MongoDB is not running or not accessible")
        print("Please start MongoDB with: net start MongoDB (as Administrator)")
        return False
    
    print("[OK] MongoDB is running and accessible")
    return True


def run_e2e_tests(args):
    """Run the E2E test suite."""
    print("\nRunning E2E tests...")
    
    # Build pytest command
    pytest_args = [
        sys.executable, "-m", "pytest",
        "tests/e2e/test_phoenix_mls_real.py",
        "-v",
        "--tb=short"
    ]
    
    # Add markers
    if not args.all:
        pytest_args.extend(["-m", "e2e and not slow"])
    else:
        pytest_args.extend(["-m", "e2e"])
    
    # Add coverage if requested
    if args.coverage:
        pytest_args.extend([
            "--cov=src",
            "--cov-report=html",
            "--cov-report=term-missing"
        ])
    
    # Run in headed mode if requested
    if not args.headless:
        os.environ["HEADLESS"] = "false"
    
    # Fix failing tests if requested
    if args.fix:
        print("Running tests with auto-fix enabled...")
        # First run to identify failures
        result = subprocess.run(pytest_args, capture_output=True, text=True)
        
        if result.returncode != 0:
            print("\n[WARNING] Some tests failed. Attempting to fix...")
            # Analyze failures and suggest fixes
            analyze_test_failures(result.stdout + result.stderr)
    else:
        # Normal test run
        result = subprocess.run(pytest_args)
        return result.returncode


def analyze_test_failures(output: str):
    """Analyze test failures and suggest fixes."""
    fixes_suggested = []
    
    # Check for common issues
    if "Failed to navigate to Phoenix MLS" in output:
        fixes_suggested.append(
            "- Phoenix MLS URL may have changed. Update the URL in test_phoenix_mls_real.py"
        )
    
    if "No property listings found" in output:
        fixes_suggested.append(
            "- CSS selectors may be outdated. Run discover_phoenix_mls_selectors.py to update"
        )
    
    if "MongoDB" in output and "connection" in output:
        fixes_suggested.append(
            "- MongoDB connection failed. Ensure MongoDB is running: net start MongoDB"
        )
    
    if "timeout" in output.lower():
        fixes_suggested.append(
            "- Page load timeout. Consider increasing timeout or checking internet connection"
        )
    
    if fixes_suggested:
        print("\nSuggested fixes:")
        for fix in fixes_suggested:
            print(fix)
        
        # Offer to run selector discovery
        if any("selector" in fix.lower() for fix in fixes_suggested):
            response = input("\nWould you like to run selector discovery? (y/n): ")
            if response.lower() == 'y':
                subprocess.run([
                    sys.executable,
                    "scripts/testing/discover_phoenix_mls_selectors.py",
                    "--headless"
                ])
    else:
        print("\n[INFO] Unable to automatically determine fixes. Please review the error output above.")


def main():
    parser = argparse.ArgumentParser(description="Run E2E tests for Phoenix MLS scraper")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode (default)")
    parser.add_argument("--headed", dest="headless", action="store_false", help="Run browser in headed mode")
    parser.add_argument("--all", action="store_true", help="Run all tests including slow ones")
    parser.add_argument("--coverage", action="store_true", help="Generate coverage report")
    parser.add_argument("--fix", action="store_true", help="Attempt to fix failing tests")
    parser.add_argument("--skip-mongo-check", action="store_true", help="Skip MongoDB check")
    
    args = parser.parse_args()
    
    print("Phoenix MLS E2E Test Runner")
    print("=" * 50)
    
    # Install Playwright browsers if needed
    install_playwright_browsers()
    
    # Check MongoDB (unless skipped)
    if not args.skip_mongo_check:
        if not check_mongodb():
            response = input("\nContinue without MongoDB? (y/n): ")
            if response.lower() != 'y':
                sys.exit(1)
    
    # Run tests
    exit_code = run_e2e_tests(args)
    
    if exit_code == 0:
        print("\n[SUCCESS] All E2E tests passed!")
    else:
        print(f"\n[FAILED] E2E tests failed with exit code: {exit_code}")
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()