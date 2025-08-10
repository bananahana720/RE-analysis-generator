import asyncio
import sys
import os
import time
import psutil
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "..", "src"))

from phoenix_real_estate.foundation.config import EnvironmentConfigProvider
from phoenix_real_estate.foundation.database import DatabaseConnection

async def validate_production_environment():
    """Comprehensive validation of production environment readiness"""
    print("Phoenix Real Estate - Production Environment Validation")
    print("=" * 55)
    
    validations = {}
    config = EnvironmentConfigProvider()
    
    # Database connectivity test
    try:
        start_time = time.time()
        db = DatabaseConnection(
            uri=config.get("MONGODB_URI", "mongodb://localhost:27017"),
            database_name=config.get("MONGODB_DATABASE", "phoenix_real_estate")
        )
        await db.connect()
        await db.health_check()
        response_time = time.time() - start_time
        validations["database"] = response_time < 2.0
        print(f"[OK] Database: {response_time*1000:.1f}ms")
        await db.close()
    except Exception as e:
        validations["database"] = False
        print(f"[FAIL] Database: {e}")
    
    # Configuration validation (informational for test env)
    required_keys = ["MARICOPA_API_KEY", "WEBSHARE_API_KEY"]
    for key in required_keys:
        value = config.get(key)
        if value and value != "test_key":
            print(f"[OK] {key}: Configured")
        else:
            print(f"[INFO] {key}: Test value (OK for testing)")
    
    # Ollama connectivity test
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:11434/api/tags") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    models = [m["name"] for m in data.get("models", [])]
                    if "llama3.2:latest" in models:
                        print(f"[OK] Ollama LLM: llama3.2:latest available")
                        validations["ollama"] = True
                    else:
                        print(f"[WARN] Ollama LLM: llama3.2:latest not found. Available: {models}")
                        validations["ollama"] = False
                else:
                    print(f"[WARN] Ollama LLM: Status {resp.status}")
                    validations["ollama"] = False
    except Exception as e:
        print(f"[FAIL] Ollama LLM: {e}")
        validations["ollama"] = False
    
    # Resource validation
    memory_mb = psutil.virtual_memory().available / (1024 * 1024)
    memory_ok = memory_mb >= 512
    validations["resources"] = memory_ok
    
    if memory_ok:
        print(f"[OK] Memory: {memory_mb:.0f}MB available")
    else:
        print(f"[WARN] Memory: {memory_mb:.0f}MB (need 512MB)")
    
    # Overall result
    core_validations = {"database": validations["database"], 
                       "ollama": validations["ollama"], 
                       "resources": validations["resources"]}
    overall_valid = all(core_validations.values())
    print("=" * 50)
    print(f"Overall Status: {'READY' if overall_valid else 'NOT READY'}")
    
    # Print summary
    print(f"Database: {'PASS' if validations['database'] else 'FAIL'}")
    print(f"LLM (Ollama): {'PASS' if validations['ollama'] else 'FAIL'}") 
    print(f"Resources: {'PASS' if validations['resources'] else 'FAIL'}")
    
    return overall_valid

if __name__ == "__main__":
    result = asyncio.run(validate_production_environment())
    sys.exit(0 if result else 1)
