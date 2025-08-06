#!/usr/bin/env python3
"""Performance monitoring for Phoenix Real Estate system."""

import asyncio
import json
import psutil
import time
from datetime import datetime, UTC
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


def get_system_metrics():
    """Get current system performance metrics."""
    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "cpu": {
            "percent": psutil.cpu_percent(interval=1),
            "count": psutil.cpu_count(),
            "load_avg": psutil.getloadavg() if hasattr(psutil, "getloadavg") else None,
        },
        "memory": {
            "total": psutil.virtual_memory().total,
            "available": psutil.virtual_memory().available,
            "percent": psutil.virtual_memory().percent,
            "used": psutil.virtual_memory().used,
        },
        "disk": {
            "total": psutil.disk_usage(".").total,
            "used": psutil.disk_usage(".").used,
            "free": psutil.disk_usage(".").free,
            "percent": psutil.disk_usage(".").percent,
        },
        "processes": len(psutil.pids()),
        "uptime": time.time() - psutil.boot_time(),
    }


async def get_database_metrics():
    """Get database performance metrics."""
    try:
        from phoenix_real_estate.foundation.config.base import EnvironmentConfigProvider
        from phoenix_real_estate.foundation.database.connection import DatabaseConnection

        config_provider = EnvironmentConfigProvider()
        db_connection = DatabaseConnection(config_provider, "phoenix_real_estate")
        await db_connection.connect()

        database = db_connection.database

        # Get database stats
        stats = await database.command("dbStats")
        collections = await database.list_collection_names()

        metrics = {
            "collections_count": len(collections),
            "data_size": stats.get("dataSize", 0),
            "storage_size": stats.get("storageSize", 0),
            "index_size": stats.get("indexSize", 0),
            "objects": stats.get("objects", 0),
        }

        await db_connection.close()
        return metrics

    except Exception as e:
        return {"error": str(e)}


def check_service_status():
    """Check status of required services."""
    services = {}

    # Check MongoDB
    mongodb_running = False
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            if "mongod" in proc.info["name"].lower():
                mongodb_running = True
                break
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    services["mongodb"] = {
        "running": mongodb_running,
        "status": "active" if mongodb_running else "inactive",
    }

    # Check Ollama (optional)
    ollama_running = False
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            if "ollama" in proc.info["name"].lower():
                ollama_running = True
                break
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    services["ollama"] = {
        "running": ollama_running,
        "status": "active" if ollama_running else "inactive",
    }

    return services


async def main():
    """Main monitoring function."""
    import argparse

    parser = argparse.ArgumentParser(description="Phoenix Real Estate performance monitor")
    parser.add_argument("--output", choices=["json", "human"], default="human")
    parser.add_argument("--include-db", action="store_true", help="Include database metrics")
    args = parser.parse_args()

    # Collect metrics
    system_metrics = get_system_metrics()
    service_status = check_service_status()

    db_metrics = None
    if args.include_db:
        db_metrics = await get_database_metrics()

    performance_data = {
        "system": system_metrics,
        "services": service_status,
        "database": db_metrics,
    }

    if args.output == "json":
        print(json.dumps(performance_data, indent=2))
    else:
        print(f"Performance Report - {system_metrics['timestamp']}")
        print("=" * 50)

        print(f"CPU Usage: {system_metrics['cpu']['percent']:.1f}%")
        print(
            f"Memory Usage: {system_metrics['memory']['percent']:.1f}% ({system_metrics['memory']['used'] / 1024**3:.1f}GB / {system_metrics['memory']['total'] / 1024**3:.1f}GB)"
        )
        print(
            f"Disk Usage: {system_metrics['disk']['percent']:.1f}% ({system_metrics['disk']['used'] / 1024**3:.1f}GB / {system_metrics['disk']['total'] / 1024**3:.1f}GB)"
        )

        print("\nService Status:")
        for service, status in service_status.items():
            print(f"  {service}: {status['status']}")

        if db_metrics and "error" not in db_metrics:
            print("\nDatabase Metrics:")
            print(f"  Collections: {db_metrics['collections_count']}")
            print(f"  Data Size: {db_metrics['data_size'] / 1024**2:.1f}MB")
            print(f"  Objects: {db_metrics['objects']}")


if __name__ == "__main__":
    asyncio.run(main())
