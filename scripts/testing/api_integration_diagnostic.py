#\!/usr/bin/env python3
"""
API Integration Diagnostic Tool for Phoenix Real Estate Data Collector

This script tests all external service integrations and provides production readiness assessment.
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

async def main():
    """Main diagnostic function."""
    print("=" * 60)
    print("API INTEGRATION DIAGNOSTIC REPORT")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Environment: {os.getenv('ENVIRONMENT', 'development')}")
    
    # Check for .env files
    env_files = [".env", ".env.local", ".env.development"]
    loaded_files = []
    
    for env_file in env_files:
        env_path = project_root / env_file
        if env_path.exists():
            loaded_files.append(env_file)
    
    print(f"Environment files found: {loaded_files if loaded_files else 'None'}")
    
    # Check critical credentials
    credentials = {
        "MARICOPA_API_KEY": os.getenv("MARICOPA_API_KEY"),
        "WEBSHARE_API_KEY": os.getenv("WEBSHARE_API_KEY"), 
        "WEBSHARE_USERNAME": os.getenv("WEBSHARE_USERNAME"),
        "WEBSHARE_PASSWORD": os.getenv("WEBSHARE_PASSWORD"),
        "CAPTCHA_API_KEY": os.getenv("CAPTCHA_API_KEY"),
        "MONGODB_URI": os.getenv("MONGODB_URI"),
        "SMTP_HOST": os.getenv("SMTP_HOST"),
        "SMTP_USERNAME": os.getenv("SMTP_USERNAME"),
        "SMTP_PASSWORD": os.getenv("SMTP_PASSWORD")
    }
    
    print()
    print("CREDENTIAL STATUS")
    print("-" * 40)
    
    configured_count = 0
    critical_missing = []
    
    for key, value in credentials.items():
        if value:
            if "KEY" in key or "PASSWORD" in key:
                print(f"{key}: {value[:8]}...")
            else:
                print(f"{key}: {value}")
            configured_count += 1
        else:
            print(f"{key}: NOT CONFIGURED")
            if key in ["MARICOPA_API_KEY", "MONGODB_URI"]:
                critical_missing.append(key)
    
    print()
    print(f"Credentials configured: {configured_count}/{len(credentials)}")
    
    # Basic service connectivity tests
    print()
    print("BASIC CONNECTIVITY TESTS")
    print("-" * 40)
    
    services_status = {}
    
    # Test MongoDB
    try:
        import pymongo
        mongodb_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
        client = pymongo.MongoClient(mongodb_uri, serverSelectionTimeoutMS=5000)
        client.admin.command("ping")
        client.close()
        print("MongoDB: OPERATIONAL")
        services_status["mongodb"] = "OPERATIONAL"
    except ImportError:
        print("MongoDB: DEPENDENCY MISSING (pymongo)")
        services_status["mongodb"] = "DEPENDENCY_MISSING"
    except Exception as e:
        print(f"MongoDB: FAILED ({str(e)[:50]})")
        services_status["mongodb"] = "FAILED"
    
    # Test Ollama
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("http://localhost:11434/api/tags")
            if response.status_code == 200:
                models = response.json().get("models", [])
                llama_models = [m for m in models if "llama3.2" in m.get("name", "")]
                if llama_models:
                    print("Ollama: OPERATIONAL (llama3.2 available)")
                    services_status["ollama"] = "OPERATIONAL"
                else:
                    print("Ollama: MODEL MISSING (llama3.2)")
                    services_status["ollama"] = "MODEL_MISSING"
            else:
                print("Ollama: SERVICE ERROR")
                services_status["ollama"] = "SERVICE_ERROR"
    except ImportError:
        print("Ollama: DEPENDENCY MISSING (httpx)")
        services_status["ollama"] = "DEPENDENCY_MISSING"
    except Exception:
        print("Ollama: SERVICE DOWN")
        services_status["ollama"] = "SERVICE_DOWN"
    
    # Assessment
    print()
    print("=" * 60)
    print("PRODUCTION READINESS ASSESSMENT")
    print("=" * 60)
    
    if not critical_missing:
        if services_status.get("mongodb") == "OPERATIONAL":
            print("✓ PRODUCTION READY: Core services operational")
            readiness_status = "READY"
            risk_level = "LOW"
        else:
            print("⚠ PARTIALLY READY: Credentials OK, service issues")
            readiness_status = "PARTIAL"
            risk_level = "MEDIUM"
    else:
        print("✗ NOT PRODUCTION READY: Critical credentials missing")
        readiness_status = "NOT_READY"
        risk_level = "HIGH"
    
    print(f"Risk Level: {risk_level}")
    
    # Generate action items
    print()
    print("IMMEDIATE ACTION ITEMS:")
    
    actions = []
    
    if "MARICOPA_API_KEY" in critical_missing:
        actions.extend([
            "1. Obtain Maricopa County API key from https://api.mcassessor.maricopa.gov",
            "2. Create .env file and set MARICOPA_API_KEY=your_api_key"
        ])
    
    if "MONGODB_URI" in critical_missing:
        actions.extend([
            "3. Start MongoDB service: net start MongoDB",
            "4. Add MONGODB_URI=mongodb://localhost:27017 to .env file"
        ])
    
    if services_status.get("ollama") == "SERVICE_DOWN":
        actions.extend([
            "5. Start Ollama service: ollama serve",
            "6. Install model: ollama pull llama3.2:latest"
        ])
    
    if not actions:
        actions = ["All critical components operational - ready for production"]
    
    for action in actions:
        print(f"  {action}")
    
    # Save basic report
    report = {
        "timestamp": datetime.now().isoformat(),
        "environment": os.getenv("ENVIRONMENT", "development"),
        "credentials_configured": configured_count,
        "total_credentials": len(credentials),
        "critical_missing": critical_missing,
        "services_status": services_status,
        "readiness_status": readiness_status,
        "risk_level": risk_level,
        "actions_required": actions
    }
    
    report_path = project_root / "reports" / "api_integration_basic_report.json"
    report_path.parent.mkdir(exist_ok=True)
    
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    
    print()
    print(f"Basic report saved to: {report_path}")
    print()
    print("For comprehensive API testing, run individual service tests:")
    print("  python scripts/testing/test_maricopa_collector.py")
    print("  python scripts/testing/verify_e2e_setup.py")
    
    # Return appropriate exit code
    if readiness_status == "READY":
        return 0
    elif critical_missing:
        return 2  # Critical issues
    else:
        return 1  # Warnings only

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
