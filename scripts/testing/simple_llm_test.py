"""Simple direct LLM test"""
import asyncio
import aiohttp

async def test_ollama_direct():
    """Direct test of Ollama API"""
    print("Testing Ollama LLM directly...")
    
    # Test API is responding
    try:
        async with aiohttp.ClientSession() as session:
            # Check version
            async with session.get('http://localhost:11434/api/version') as resp:
                if resp.status == 200:
                    version_data = await resp.json()
                    print(f"[OK] Ollama version: {version_data.get('version', 'unknown')}")
                else:
                    print(f"[FAIL] Ollama API status: {resp.status}")
                    return False
            
            # Test simple completion
            print("[TEST] Generating simple completion...")
            payload = {
                "model": "llama3.2:latest",
                "prompt": "What is 2+2? Answer with just the number.",
                "stream": False,
                "options": {
                    "num_predict": 5,
                    "temperature": 0.1
                }
            }
            
            async with session.post('http://localhost:11434/api/generate', 
                                   json=payload,
                                   timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    response_text = data.get('response', '').strip()
                    print(f"[OK] LLM Response: '{response_text}'")
                    
                    if '4' in response_text:
                        print("[PASS] LLM generated correct answer")
                        return True
                    else:
                        print(f"[WARN] LLM response unexpected: '{response_text}'")
                        return False
                else:
                    error_text = await resp.text()
                    print(f"[FAIL] Generate API status: {resp.status}")
                    print(f"[FAIL] Error: {error_text}")
                    return False
                    
    except Exception as e:
        print(f"[FAIL] Exception: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_ollama_direct())
    print(f"\nResult: {'SUCCESS' if result else 'FAILED'}")
