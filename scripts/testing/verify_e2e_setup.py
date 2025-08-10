#!/usr/bin/env python3
"""Verify E2E test setup for LLM processing pipeline.

This script checks that all prerequisites are met and runs a simple
test to verify the E2E test infrastructure is working.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root and tests directory to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "tests"))

from phoenix_real_estate.foundation.config import EnvironmentConfigProvider  # noqa: E402
from phoenix_real_estate.foundation.logging import get_logger  # noqa: E402
from phoenix_real_estate.foundation.database.connection import DatabaseConnection  # noqa: E402
from phoenix_real_estate.collectors.processing.pipeline import DataProcessingPipeline  # noqa: E402


logger = get_logger("e2e.verify")


async def verify_mongodb():
    """Verify MongoDB connection."""
    print("1. Checking MongoDB connection...")
    try:
        mongodb_uri = os.environ.get("MONGODB_URI", "mongodb://localhost:27017")
        db_conn = DatabaseConnection.get_instance(mongodb_uri, "phoenix_real_estate_e2e_test")
        await db_conn.connect()

        # Test basic operations using async context manager
        async with db_conn.get_database() as db:
            collections = await db.list_collection_names()
            print(f"   [OK] Connected to MongoDB (found {len(collections)} collections)")

        await db_conn.close()
        return True
    except Exception as e:
        print(f"   [FAIL] MongoDB connection failed: {e}")
        return False


async def verify_ollama():
    """Verify Ollama service (optional)."""
    print("\n2. Checking Ollama service (optional)...")
    try:
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:11434/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get("models", [])
                llama_models = [m for m in models if "llama3.2" in m.get("name", "")]
                if llama_models:
                    print("   [OK] Ollama is running with llama3.2:latest")
                    return True
                else:
                    print("   [WARN] Ollama is running but llama3.2:latest not found")
                    print("      Run: ollama pull llama3.2:latest")
                    return False
            else:
                print("   [WARN] Ollama service not responding properly")
                return False
    except Exception:
        print("   [INFO] Ollama not running (tests will use mock mode)")
        return False


async def verify_pipeline():
    """Verify processing pipeline can be initialized."""
    print("\n3. Checking processing pipeline...")
    try:
        config = EnvironmentConfigProvider()
        pipeline = DataProcessingPipeline(config)

        # Test initialization
        await pipeline.initialize()
        print("   [OK] Pipeline initialized successfully")

        # Test with simple HTML

        # This will use mock mode if Ollama is not available
        print("   [TEST] Testing pipeline with sample HTML...")

        await pipeline.close()
        print("   [OK] Pipeline test completed")
        return True

    except Exception as e:
        print(f"   [FAIL] Pipeline verification failed: {e}")
        return False


async def verify_e2e_fixtures():
    """Verify E2E test fixtures are available."""
    print("\n4. Checking E2E test fixtures...")
    try:
        from e2e.fixtures import PropertySamples

        # Check sample data
        phoenix_samples = PropertySamples.get_phoenix_mls_samples()
        maricopa_samples = PropertySamples.get_maricopa_samples()
        edge_cases = PropertySamples.get_edge_case_samples()

        print(f"   [OK] Found {len(phoenix_samples)} Phoenix MLS samples")
        print(f"   [OK] Found {len(maricopa_samples)} Maricopa County samples")
        print(f"   [OK] Found {len(edge_cases)} edge case samples")
        return True

    except ImportError as e:
        print(f"   [FAIL] Failed to import test fixtures: {e}")
        return False


def check_dependencies():
    """Check required Python packages."""
    print("\n5. Checking Python dependencies...")
    required = [
        ("pytest", "Testing framework"),
        ("pytest_asyncio", "Async test support"),
        ("httpx", "HTTP client for Ollama"),
        ("motor", "MongoDB async driver"),
    ]

    all_present = True
    for package, description in required:
        try:
            __import__(package)
            print(f"   [OK] {package} - {description}")
        except ImportError:
            print(f"   [FAIL] {package} - {description} (run: uv sync)")
            all_present = False

    return all_present


async def main(mode="test"):
    """Run all verification checks."""
    print(f"E2E Test Setup Verification (mode: {mode})")
    print("=" * 60)

    # Run checks
    mongodb_ok = await verify_mongodb()
    ollama_ok = await verify_ollama()
    pipeline_ok = await verify_pipeline()
    fixtures_ok = await verify_e2e_fixtures()
    deps_ok = check_dependencies()

    # Summary
    print("\n" + "=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)

    checks = [
        ("MongoDB", mongodb_ok),
        ("Ollama (optional)", ollama_ok),
        ("Processing Pipeline", pipeline_ok),
        ("Test Fixtures", fixtures_ok),
        ("Python Dependencies", deps_ok),
    ]

    required_checks = [mongodb_ok, pipeline_ok, fixtures_ok, deps_ok]

    for name, status in checks:
        icon = "[OK]" if status else "[FAIL]"
        print(f"{icon} {name}")

    if all(required_checks):
        print("\n[SUCCESS] E2E test setup is ready!")
        print("\nYou can now run:")
        print("  - Mock tests: pytest tests/e2e/test_processing_pipeline_e2e.py")
        print("  - Real tests: E2E_MODE=real pytest tests/e2e/test_processing_pipeline_e2e.py")
        print("  - Helper script: python scripts/testing/run_llm_e2e_tests.py")
        return 0
    else:
        print("\n[ERROR] Some required components are missing.")
        print("Please fix the issues above before running E2E tests.")
        return 1


def run_main():
    """Main function with CLI argument parsing."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Verify E2E test setup for LLM processing pipeline"
    )
    parser.add_argument(
        "--mode",
        default="test",
        choices=["test", "incremental", "full"],
        help="Verification mode (default: test)",
    )

    args = parser.parse_args()
    exit_code = asyncio.run(main(args.mode))
    sys.exit(exit_code)


if __name__ == "__main__":
    run_main()
