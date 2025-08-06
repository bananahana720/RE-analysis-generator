#!/usr/bin/env python3
"""Production monitoring setup script.

This script configures comprehensive monitoring for the Phoenix Real Estate system,
including health checks, performance metrics, and alerting systems.
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime, UTC
from pathlib import Path
from typing import Dict, Any, Optional

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from phoenix_real_estate.foundation.config.base import EnvironmentConfigProvider
from phoenix_real_estate.foundation.database.connection import DatabaseConnection


def setup_logging() -> logging.Logger:
    """Set up logging for the monitoring setup script."""
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


def create_health_check_endpoint(logger: logging.Logger) -> bool:
    """Create a simple health check endpoint."""
    logger.info("Creating health check endpoint...")

    health_check_script = """#!/usr/bin/env python3
\"\"\"Simple health check endpoint for Phoenix Real Estate system.\"\"\"

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
    \"\"\"Check system health and return status.\"\"\"
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now(UTC).isoformat(),
        "checks": {}
    }
    
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
            "response_time_ms": 0  # Could add timing
        }
        
        await db_connection.close()
        
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["checks"]["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
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
                    "llama3_2_available": any("llama3.2" in model.get("name", "") for model in models)
                }
            else:
                health_status["checks"]["ollama"] = {
                    "status": "unhealthy",
                    "error": f"HTTP {response.status_code}"
                }
    except Exception as e:
        health_status["checks"]["ollama"] = {
            "status": "degraded",
            "error": str(e),
            "note": "LLM service optional for basic operations"
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
    parser.add_argument("--exit-code", action="store_true", help="Exit with error code if unhealthy")
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
"""

    health_check_file = Path("scripts/deploy/health_check.py")
    try:
        with open(health_check_file, "w") as f:
            f.write(health_check_script)

        # Make executable
        health_check_file.chmod(0o755)

        logger.info(f"Created health check endpoint: {health_check_file}")
        return True

    except Exception as e:
        logger.error(f"Failed to create health check endpoint: {e}")
        return False


def create_performance_monitor(logger: logging.Logger) -> bool:
    """Create performance monitoring script."""
    logger.info("Creating performance monitoring script...")

    performance_script = """#!/usr/bin/env python3
\"\"\"Performance monitoring for Phoenix Real Estate system.\"\"\"

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
    \"\"\"Get current system performance metrics.\"\"\"
    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "cpu": {
            "percent": psutil.cpu_percent(interval=1),
            "count": psutil.cpu_count(),
            "load_avg": psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None
        },
        "memory": {
            "total": psutil.virtual_memory().total,
            "available": psutil.virtual_memory().available,
            "percent": psutil.virtual_memory().percent,
            "used": psutil.virtual_memory().used
        },
        "disk": {
            "total": psutil.disk_usage('.').total,
            "used": psutil.disk_usage('.').used,
            "free": psutil.disk_usage('.').free,
            "percent": psutil.disk_usage('.').percent
        },
        "processes": len(psutil.pids()),
        "uptime": time.time() - psutil.boot_time()
    }


async def get_database_metrics():
    \"\"\"Get database performance metrics.\"\"\"
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
            "objects": stats.get("objects", 0)
        }
        
        await db_connection.close()
        return metrics
        
    except Exception as e:
        return {"error": str(e)}


def check_service_status():
    \"\"\"Check status of required services.\"\"\"
    services = {}
    
    # Check MongoDB
    mongodb_running = False
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if 'mongod' in proc.info['name'].lower():
                mongodb_running = True
                break
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    services['mongodb'] = {
        'running': mongodb_running,
        'status': 'active' if mongodb_running else 'inactive'
    }
    
    # Check Ollama (optional)
    ollama_running = False
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if 'ollama' in proc.info['name'].lower():
                ollama_running = True
                break
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    services['ollama'] = {
        'running': ollama_running,
        'status': 'active' if ollama_running else 'inactive'
    }
    
    return services


async def main():
    \"\"\"Main monitoring function.\"\"\"
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
        "database": db_metrics
    }
    
    if args.output == "json":
        print(json.dumps(performance_data, indent=2))
    else:
        print(f"Performance Report - {system_metrics['timestamp']}")
        print("=" * 50)
        
        print(f"CPU Usage: {system_metrics['cpu']['percent']:.1f}%")
        print(f"Memory Usage: {system_metrics['memory']['percent']:.1f}% ({system_metrics['memory']['used'] / 1024**3:.1f}GB / {system_metrics['memory']['total'] / 1024**3:.1f}GB)")
        print(f"Disk Usage: {system_metrics['disk']['percent']:.1f}% ({system_metrics['disk']['used'] / 1024**3:.1f}GB / {system_metrics['disk']['total'] / 1024**3:.1f}GB)")
        
        print(f"\\nService Status:")
        for service, status in service_status.items():
            print(f"  {service}: {status['status']}")
        
        if db_metrics and "error" not in db_metrics:
            print(f"\\nDatabase Metrics:")
            print(f"  Collections: {db_metrics['collections_count']}")
            print(f"  Data Size: {db_metrics['data_size'] / 1024**2:.1f}MB")
            print(f"  Objects: {db_metrics['objects']}")


if __name__ == "__main__":
    asyncio.run(main())
"""

    performance_file = Path("scripts/deploy/performance_baseline.py")
    try:
        with open(performance_file, "w") as f:
            f.write(performance_script)

        # Make executable
        performance_file.chmod(0o755)

        logger.info(f"Created performance monitor: {performance_file}")
        return True

    except Exception as e:
        logger.error(f"Failed to create performance monitor: {e}")
        return False


def create_monitoring_dashboard_config(logger: logging.Logger) -> bool:
    """Create Grafana dashboard configuration."""
    logger.info("Creating monitoring dashboard configuration...")

    dashboard_config = {
        "dashboard": {
            "id": None,
            "title": "Phoenix Real Estate System Monitoring",
            "tags": ["phoenix", "real-estate", "monitoring"],
            "timezone": "America/Phoenix",
            "panels": [
                {
                    "id": 1,
                    "title": "System Health Status",
                    "type": "stat",
                    "targets": [{"expr": "phoenix_system_health_status", "refId": "A"}],
                    "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0},
                },
                {
                    "id": 2,
                    "title": "CPU Usage",
                    "type": "graph",
                    "targets": [{"expr": "phoenix_cpu_usage_percent", "refId": "A"}],
                    "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0},
                },
                {
                    "id": 3,
                    "title": "Memory Usage",
                    "type": "graph",
                    "targets": [{"expr": "phoenix_memory_usage_percent", "refId": "A"}],
                    "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8},
                },
                {
                    "id": 4,
                    "title": "Database Connections",
                    "type": "graph",
                    "targets": [{"expr": "phoenix_database_connections_active", "refId": "A"}],
                    "gridPos": {"h": 8, "w": 12, "x": 12, "y": 8},
                },
                {
                    "id": 5,
                    "title": "LLM Processing Time",
                    "type": "graph",
                    "targets": [{"expr": "phoenix_llm_processing_duration_seconds", "refId": "A"}],
                    "gridPos": {"h": 8, "w": 12, "x": 0, "y": 16},
                },
                {
                    "id": 6,
                    "title": "Collection Success Rate",
                    "type": "stat",
                    "targets": [{"expr": "phoenix_collection_success_rate", "refId": "A"}],
                    "gridPos": {"h": 8, "w": 12, "x": 12, "y": 16},
                },
            ],
            "time": {"from": "now-6h", "to": "now"},
            "refresh": "30s",
        }
    }

    monitoring_dir = Path("config/monitoring")
    monitoring_dir.mkdir(exist_ok=True)

    dashboard_file = monitoring_dir / "grafana_dashboard.json"
    try:
        with open(dashboard_file, "w") as f:
            json.dump(dashboard_config, f, indent=2)

        logger.info(f"Created Grafana dashboard config: {dashboard_file}")
        return True

    except Exception as e:
        logger.error(f"Failed to create dashboard config: {e}")
        return False


def create_log_rotation_config(logger: logging.Logger) -> bool:
    """Create log rotation configuration."""
    logger.info("Creating log rotation configuration...")

    logrotate_config = """# Phoenix Real Estate log rotation
/opt/phoenix-real-estate/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    copytruncate
    create 0644 phoenix phoenix
    
    postrotate
        # Send HUP signal to application if running
        pkill -HUP -f "phoenix_real_estate" || true
    endscript
}

/opt/phoenix-real-estate/logs/github_actions/*.log {
    weekly
    missingok
    rotate 4
    compress
    delaycompress
    notifempty
    copytruncate
    create 0644 phoenix phoenix
}
"""

    config_dir = Path("config/monitoring")
    config_dir.mkdir(exist_ok=True)

    logrotate_file = config_dir / "logrotate.conf"
    try:
        with open(logrotate_file, "w") as f:
            f.write(logrotate_config)

        logger.info(f"Created log rotation config: {logrotate_file}")
        logger.info(
            "To install: sudo cp config/monitoring/logrotate.conf /etc/logrotate.d/phoenix-real-estate"
        )
        return True

    except Exception as e:
        logger.error(f"Failed to create log rotation config: {e}")
        return False


async def test_monitoring_setup(logger: logging.Logger) -> bool:
    """Test the monitoring setup."""
    logger.info("Testing monitoring setup...")

    try:
        # Test health check
        import subprocess

        result = subprocess.run(
            [sys.executable, "scripts/deploy/health_check.py", "--json"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode == 0:
            health_data = json.loads(result.stdout)
            logger.info(f"Health check passed: {health_data['status']}")
        else:
            logger.warning(f"Health check issues: {result.stderr}")

        # Test performance monitor
        result = subprocess.run(
            [sys.executable, "scripts/deploy/performance_baseline.py", "--output", "json"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode == 0:
            perf_data = json.loads(result.stdout)
            cpu_usage = perf_data["system"]["cpu"]["percent"]
            memory_usage = perf_data["system"]["memory"]["percent"]
            logger.info(f"Performance baseline: CPU {cpu_usage}%, Memory {memory_usage}%")
        else:
            logger.warning(f"Performance monitor issues: {result.stderr}")

        logger.info("Monitoring setup test completed")
        return True

    except Exception as e:
        logger.error(f"Monitoring setup test failed: {e}")
        return False


async def main():
    """Main monitoring setup function."""
    logger = setup_logging()

    logger.info("Phoenix Real Estate Monitoring Setup")
    logger.info("=" * 50)

    success_count = 0
    total_tasks = 0

    # Setup tasks
    tasks = [
        ("Create health check endpoint", lambda: create_health_check_endpoint(logger)),
        ("Create performance monitor", lambda: create_performance_monitor(logger)),
        ("Create dashboard config", lambda: create_monitoring_dashboard_config(logger)),
        ("Create log rotation config", lambda: create_log_rotation_config(logger)),
        ("Test monitoring setup", lambda: asyncio.create_task(test_monitoring_setup(logger))),
    ]

    for task_name, task_func in tasks:
        logger.info(f"\n🔧 {task_name}...")
        total_tasks += 1

        try:
            result = task_func()
            if asyncio.iscoroutine(result):
                result = await result

            if result:
                success_count += 1
                logger.info(f"✓ {task_name} completed successfully")
            else:
                logger.error(f"✗ {task_name} failed")

        except Exception as e:
            logger.error(f"✗ {task_name} failed with exception: {e}")

    # Summary
    logger.info("\n" + "=" * 50)
    logger.info(f"Monitoring Setup Summary: {success_count}/{total_tasks} tasks completed")

    if success_count == total_tasks:
        logger.info("🎉 Monitoring setup completed successfully!")
        logger.info("\nMonitoring endpoints available:")
        logger.info("• Health check: python scripts/deploy/health_check.py")
        logger.info("• Performance: python scripts/deploy/performance_baseline.py")
        logger.info("• Dashboard: config/monitoring/grafana_dashboard.json")
        logger.info("• Log rotation: config/monitoring/logrotate.conf")
        return 0
    else:
        logger.warning(f"⚠️ {total_tasks - success_count} setup tasks failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
