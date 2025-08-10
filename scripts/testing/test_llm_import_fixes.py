#\!/usr/bin/env python3
"""Test LLM Client import fixes and backward compatibility."""

import sys
import traceback
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def test_backward_compatibility_imports():
    """Test that both LLMClient and OllamaClient can be imported."""
    test_results = []
    
    # Test 1: Direct imports from module
    try:
        from phoenix_real_estate.collectors.processing.llm_client import OllamaClient, LLMClient
        test_results.append(("✅", "Direct import from llm_client module"))
        
        # Verify they are the same class
        if LLMClient is OllamaClient:
            test_results.append(("✅", "LLMClient is alias for OllamaClient"))
        else:
            test_results.append(("❌", "LLMClient alias is not working properly"))
            
    except ImportError as e:
        test_results.append(("❌", f"Direct import failed: {e}"))
        
    # Test 2: Import from package __init__
    try:
        from phoenix_real_estate.collectors.processing import LLMClient, OllamaClient
        test_results.append(("✅", "Package-level import successful"))
        
        # Verify classes are accessible
        if hasattr(LLMClient, '__init__') and hasattr(OllamaClient, '__init__'):
            test_results.append(("✅", "Both classes have constructor"))
        else:
            test_results.append(("❌", "Classes missing constructor"))
            
    except ImportError as e:
        test_results.append(("❌", f"Package import failed: {e}"))
        
    # Test 3: Test old import patterns (common in existing code)
    try:
        from phoenix_real_estate.collectors.processing import LLMClient
        # This should work for backward compatibility
        client_class = LLMClient
        test_results.append(("✅", "Legacy LLMClient import pattern works"))
        
    except ImportError as e:
        test_results.append(("❌", f"Legacy import pattern failed: {e}"))
        
    return test_results

def test_class_instantiation():
    """Test that classes can be instantiated."""
    test_results = []
    
    try:
        # Mock minimal config for testing
        class MockConfig:
            def get(self, key, default=None):
                if key == "llm.ollama.base_url":
                    return "http://localhost:11434"
                if key == "llm.ollama.model":
                    return "llama2"
                if key == "llm.ollama.timeout":
                    return 30
                return default
        
        mock_config = MockConfig()
        
        # Test OllamaClient instantiation
        from phoenix_real_estate.collectors.processing import OllamaClient
        ollama_client = OllamaClient(mock_config)
        test_results.append(("✅", "OllamaClient instantiated successfully"))
        
        # Test LLMClient instantiation (should be same as OllamaClient)
        from phoenix_real_estate.collectors.processing import LLMClient
        llm_client = LLMClient(mock_config)
        test_results.append(("✅", "LLMClient instantiated successfully"))
        
        # Verify they're the same type
        if type(ollama_client) == type(llm_client):
            test_results.append(("✅", "Both instances have same type"))
        else:
            test_results.append(("❌", "Instance types differ"))
            
    except Exception as e:
        test_results.append(("❌", f"Instantiation failed: {e}"))
        
    return test_results

def test_critical_methods_exist():
    """Test that critical methods exist on both class references."""
    test_results = []
    
    try:
        from phoenix_real_estate.collectors.processing import LLMClient, OllamaClient
        
        # Check critical methods exist
        critical_methods = ['process_property_data', 'extract_property_features']
        
        for method_name in critical_methods:
            if hasattr(OllamaClient, method_name) and hasattr(LLMClient, method_name):
                test_results.append(("✅", f"Method '{method_name}' exists on both classes"))
            else:
                test_results.append(("❌", f"Method '{method_name}' missing"))
                
        # Check they reference the same methods
        for method_name in critical_methods:
            if hasattr(OllamaClient, method_name) and hasattr(LLMClient, method_name):
                ollama_method = getattr(OllamaClient, method_name)
                llm_method = getattr(LLMClient, method_name)
                if ollama_method is llm_method:
                    test_results.append(("✅", f"Method '{method_name}' properly aliased"))
                else:
                    test_results.append(("⚠️", f"Method '{method_name}' not same reference"))
                    
    except Exception as e:
        test_results.append(("❌", f"Method check failed: {e}"))
        
    return test_results

def main():
    """Run all LLM client import tests."""
    print("Testing LLM Client Import Fixes and Backward Compatibility")
    print("=" * 65)
    
    all_results = []
    
    # Run all test suites
    test_suites = [
        ("Import Compatibility Tests", test_backward_compatibility_imports),
        ("Class Instantiation Tests", test_class_instantiation),
        ("Method Availability Tests", test_critical_methods_exist),
    ]
    
    total_tests = 0
    passed_tests = 0
    
    for suite_name, test_func in test_suites:
        print(f"\n{suite_name}")
        print("-" * len(suite_name))
        
        try:
            results = test_func()
            for status, message in results:
                print(f"{status} {message}")
                total_tests += 1
                if status == "✅":
                    passed_tests += 1
                    
            all_results.extend(results)
            
        except Exception as e:
            print(f"❌ Test suite failed: {e}")
            traceback.print_exc()
    
    # Summary
    print(f"\nTest Summary")
    print("=" * 15)
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {total_tests - passed_tests}")
    
    success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
    print(f"Success Rate: {success_rate:.1f}%")
    
    if success_rate >= 90:
        print("LLM Client import fixes are working correctly\!")
        return 0
    elif success_rate >= 70:
        print("LLM Client imports have some issues but basic functionality works")
        return 1
    else:
        print("LLM Client import fixes need attention")
        return 2

if __name__ == "__main__":
    sys.exit(main())
EOF < /dev/null
