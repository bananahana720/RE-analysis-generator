#!/usr/bin/env python3
"""Quick E2E test environment check."""

import subprocess
import sys
import os


def check_mongodb():
    """Check MongoDB status."""
    try:
        result = subprocess.run(
            ["mongosh", "--eval", "db.version()", "--quiet"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print("[OK] MongoDB is running")
            return True
    except:
        pass
    print("[FAIL] MongoDB is not running")
    print("      Run: net start MongoDB (as Administrator)")
    return False


def check_ollama():
    """Check Ollama status."""
    try:
        import requests
        response = requests.get("http://localhost:11434/api/version", timeout=2)
        if response.status_code == 200:
            print("[OK] Ollama is running")
            # Check for model
            response = requests.get("http://localhost:11434/api/tags", timeout=2)
            if response.status_code == 200:
                models = response.json().get("models", [])
                if any("llama3.2" in m.get("name", "") for m in models):
                    print("[OK] llama3.2:latest model is available")
                    return True
                else:
                    print("[WARN] llama3.2:latest model not found")
                    print("      Run: ollama pull llama3.2:latest")
    except:
        pass
    print("[INFO] Ollama not running (tests will use mock mode)")
    return False


def check_test_files():
    """Check if E2E test files exist."""
    test_files = [
        "tests/e2e/conftest.py",
        "tests/e2e/test_processing_pipeline_e2e.py",
        "tests/e2e/fixtures/__init__.py",
        "tests/e2e/fixtures/property_samples.py"
    ]
    
    all_exist = True
    for file in test_files:
        if os.path.exists(file):
            print(f"[OK] {file}")
        else:
            print(f"[FAIL] {file} not found")
            all_exist = False
    
    return all_exist


def main():
    """Run all checks."""
    print("E2E Test Quick Check")
    print("=" * 50)
    
    print("\n1. MongoDB Check:")
    mongodb_ok = check_mongodb()
    
    print("\n2. Ollama Check (optional):")
    check_ollama()
    
    print("\n3. Test Files Check:")
    files_ok = check_test_files()
    
    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    
    if mongodb_ok and files_ok:
        print("\n[SUCCESS] Ready to run E2E tests!")
        print("\nRun tests with:")
        print("  Mock mode: pytest tests/e2e/test_processing_pipeline_e2e.py -v")
        print("  Real mode: set E2E_MODE=real && pytest tests/e2e/test_processing_pipeline_e2e.py -v")
        return 0
    else:
        print("\n[ERROR] Fix the issues above before running E2E tests")
        return 1


if __name__ == "__main__":
    sys.exit(main())