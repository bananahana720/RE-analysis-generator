#!/usr/bin/env python3
"""Simple health check endpoint for Phoenix Real Estate system."""

import asyncio
import json
import sys
from datetime import datetime, UTC
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from phoenix_real_estate.foundation.config.base import EnvironmentConfigProvider
from phoenix_real_estate.foundation.database.connection import DatabaseConnection


async def check_system_health():
    """Check system health and return status."""
    health_status = {"status": "healthy", "timestamp": datetime.now(UTC).isoformat(), "checks": {}}

    try:
        # Check database connection
        config_provider = EnvironmentConfigProvider()
        db_connection = DatabaseConnection(config_provider, "phoenix_real_estate")
        await db_connection.connect()

        # Test basic database operation
        database = db_connection.database
        collections = await database.list_collection_names()

        health_status["checks"]["database"] = {
            "status": "healthy",
            "collections_count": len(collections),
            "response_time_ms": 0,  # Could add timing
        }

        await db_connection.close()

    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["checks"]["database"] = {"status": "unhealthy", "error": str(e)}

    try:
        # Check Ollama service
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:11434/api/tags", timeout=5.0)
            if response.status_code == 200:
                models = response.json().get("models", [])
                health_status["checks"]["ollama"] = {
                    "status": "healthy",
                    "models_count": len(models),
                    "llama3_2_available": any(
                        "llama3.2" in model.get("name", "") for model in models
                    ),
                }
            else:
                health_status["checks"]["ollama"] = {
                    "status": "unhealthy",
                    "error": f"HTTP {response.status_code}",
                }
    except Exception as e:
        health_status["checks"]["ollama"] = {
            "status": "degraded",
            "error": str(e),
            "note": "LLM service optional for basic operations",
        }

    # Overall status
    if any(check.get("status") == "unhealthy" for check in health_status["checks"].values()):
        health_status["status"] = "unhealthy"
    elif any(check.get("status") == "degraded" for check in health_status["checks"].values()):
        health_status["status"] = "degraded"

    return health_status


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Phoenix Real Estate health check")
    parser.add_argument("--json", action="store_true", help="Output JSON format")
    parser.add_argument(
        "--exit-code", action="store_true", help="Exit with error code if unhealthy"
    )
    args = parser.parse_args()

    health = asyncio.run(check_system_health())

    if args.json:
        print(json.dumps(health, indent=2))
    else:
        print(f"System Status: {health['status'].upper()}")
        for check_name, check_result in health["checks"].items():
            status = check_result["status"]
            print(f"  {check_name}: {status}")
            if "error" in check_result:
                print(f"    Error: {check_result['error']}")

    if args.exit_code and health["status"] != "healthy":
        sys.exit(1)
