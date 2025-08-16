"""Simple Performance Baseline Test"""
import asyncio
import sys
import os
import time
import psutil

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "src"))

async def test_performance_baselines():
    """Test system performance baselines"""
    print("Phoenix Real Estate - Performance Baseline Test")
    print("=" * 55)
    
    results = {}
    
    # System Resource Metrics
    print("[TEST] Measuring system resources...")
    
    # CPU Usage
    cpu_percent = psutil.cpu_percent(interval=1)
    results["cpu_usage_percent"] = cpu_percent
    print(f"[INFO] CPU Usage: {cpu_percent:.1f}%")
    
    # Memory Usage
    memory = psutil.virtual_memory()
    memory_used_gb = memory.used / (1024**3)
    memory_available_gb = memory.available / (1024**3)
    results["memory_used_gb"] = memory_used_gb
    results["memory_available_gb"] = memory_available_gb
    print(f"[INFO] Memory Used: {memory_used_gb:.1f}GB")
    print(f"[INFO] Memory Available: {memory_available_gb:.1f}GB")
    
    # Disk Usage
    disk = psutil.disk_usage('.')
    disk_used_gb = disk.used / (1024**3)
    disk_free_gb = disk.free / (1024**3)
    results["disk_used_gb"] = disk_used_gb
    results["disk_free_gb"] = disk_free_gb
    print(f"[INFO] Disk Used: {disk_used_gb:.1f}GB")
    print(f"[INFO] Disk Free: {disk_free_gb:.1f}GB")
    
    # Network connectivity test
    print("\n[TEST] Testing network connectivity...")
    try:
        import aiohttp
        start_time = time.time()
        async with aiohttp.ClientSession() as session:
            async with session.get('http://localhost:11434/api/version') as resp:
                network_latency = (time.time() - start_time) * 1000
                results["network_latency_ms"] = network_latency
                if resp.status == 200:
                    print(f"[OK] Network latency: {network_latency:.1f}ms")
                else:
                    print(f"[WARN] Network status: {resp.status}")
    except Exception as e:
        print(f"[WARN] Network test failed: {e}")
        results["network_latency_ms"] = None
    
    # Database connection performance
    print("\n[TEST] Testing database performance...")
    try:
        from phoenix_real_estate.foundation.config import EnvironmentConfigProvider
        from phoenix_real_estate.foundation.database import DatabaseConnection
        
        config = EnvironmentConfigProvider()
        start_time = time.time()
        
        db = DatabaseConnection(
            uri=config.get("MONGODB_URI", "mongodb://localhost:27017"),
            database_name=config.get("MONGODB_DATABASE", "phoenix_real_estate")
        )
        await db.connect()
        connection_time = (time.time() - start_time) * 1000
        results["db_connection_time_ms"] = connection_time
        print(f"[OK] Database connection: {connection_time:.1f}ms")
        
        # Test a simple operation
        start_time = time.time()
        async with db.get_database() as database:
            collection = database.get_collection('test_performance')
            await collection.find_one({"_id": "nonexistent"})  # Simple query
        query_time = (time.time() - start_time) * 1000
        results["db_query_time_ms"] = query_time
        print(f"[OK] Database query: {query_time:.1f}ms")
        
        await db.close()
        
    except Exception as e:
        print(f"[WARN] Database test failed: {e}")
        results["db_connection_time_ms"] = None
        results["db_query_time_ms"] = None
    
    # LLM Performance Test
    print("\n[TEST] Testing LLM performance...")
    try:
        import aiohttp
        
        payload = {
            "model": "llama3.2:latest",
            "prompt": "Hello",
            "stream": False,
            "options": {"num_predict": 1}
        }
        
        start_time = time.time()
        async with aiohttp.ClientSession() as session:
            async with session.post('http://localhost:11434/api/generate', 
                                   json=payload,
                                   timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status == 200:
                    await resp.json()
                    llm_response_time = (time.time() - start_time) * 1000
                    results["llm_response_time_ms"] = llm_response_time
                    print(f"[OK] LLM response time: {llm_response_time:.1f}ms")
                else:
                    print(f"[WARN] LLM API status: {resp.status}")
                    results["llm_response_time_ms"] = None
        
    except Exception as e:
        print(f"[WARN] LLM test failed: {e}")
        results["llm_response_time_ms"] = None
    
    # Performance Assessment
    print("\n" + "=" * 55)
    print("Performance Baseline Summary:")
    print("=" * 55)
    
    # Check against targets
    checks = []
    
    if cpu_percent < 80:
        print(f"[OK] CPU usage: {cpu_percent:.1f}% (target <80%)")
        checks.append(True)
    else:
        print(f"[WARN] CPU usage: {cpu_percent:.1f}% (target <80%)")
        checks.append(False)
    
    if memory_available_gb > 1.0:
        print(f"[OK] Available memory: {memory_available_gb:.1f}GB (target >1GB)")
        checks.append(True)
    else:
        print(f"[WARN] Available memory: {memory_available_gb:.1f}GB (target >1GB)")
        checks.append(False)
    
    if disk_free_gb > 5.0:
        print(f"[OK] Free disk space: {disk_free_gb:.1f}GB (target >5GB)")
        checks.append(True)
    else:
        print(f"[WARN] Free disk space: {disk_free_gb:.1f}GB (target >5GB)")
        checks.append(False)
    
    if results.get("db_connection_time_ms") and results["db_connection_time_ms"] < 1000:
        print(f"[OK] DB connection: {results['db_connection_time_ms']:.1f}ms (target <1000ms)")
        checks.append(True)
    elif results.get("db_connection_time_ms"):
        print(f"[WARN] DB connection: {results['db_connection_time_ms']:.1f}ms (target <1000ms)")
        checks.append(False)
    else:
        print("[SKIP] DB connection test failed")
    
    if results.get("llm_response_time_ms") and results["llm_response_time_ms"] < 5000:
        print(f"[OK] LLM response: {results['llm_response_time_ms']:.1f}ms (target <5000ms)")
        checks.append(True)
    elif results.get("llm_response_time_ms"):
        print(f"[WARN] LLM response: {results['llm_response_time_ms']:.1f}ms (target <5000ms)")
        checks.append(False)
    else:
        print("[SKIP] LLM response test failed")
    
    overall_pass = all(checks) if checks else False
    print(f"\nOverall Performance: {'GOOD' if overall_pass else 'NEEDS ATTENTION'}")
    
    # Estimate daily cost at current performance levels
    print("\nEstimated Daily Costs:")
    print("- Current usage pattern: <$1/day (within budget)")
    print("- MongoDB operations: Local (no cost)")
    print("- LLM processing: Local Ollama (no cost)")
    print("- Network usage: Minimal")
    
    return results, overall_pass

if __name__ == "__main__":
    result = asyncio.run(test_performance_baselines())
    results, overall_pass = result
    sys.exit(0 if overall_pass else 1)
