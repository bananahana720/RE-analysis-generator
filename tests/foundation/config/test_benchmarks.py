"""
Pytest wrapper for running comprehensive benchmarks.

This allows the benchmark suite to be run as part of the test suite
with proper pytest integration.
"""

import pytest
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from tests.foundation.config.benchmarks import BenchmarkSuite


@pytest.mark.benchmark
@pytest.mark.slow
class TestBenchmarkSuite:
    """Run comprehensive benchmarks via pytest."""
    
    def test_run_full_benchmark_suite(self, tmp_path):
        """Run the complete benchmark suite."""
        # Use temp directory for output to avoid cluttering project
        output_dir = tmp_path / "benchmark_results"
        output_dir.mkdir()
        
        # Create and run benchmark suite
        suite = BenchmarkSuite(output_dir)
        suite.run_all_benchmarks()
        
        # Verify outputs were created
        json_files = list(output_dir.glob("*.json"))
        md_files = list(output_dir.glob("*.md"))
        
        assert len(json_files) > 0, "No JSON report generated"
        assert len(md_files) > 0, "No Markdown report generated"
        
        # Verify benchmark results were collected
        assert len(suite.results) > 0, "No benchmark results collected"
        
        # Check for critical performance issues
        critical_issues = []
        for result in suite.results:
            if 'cold_start' in result.name and result.mean > 0.2:  # 200ms
                critical_issues.append(f"Cold start too slow: {result.mean*1000:.0f}ms")
            elif 'warm_cache' in result.name and result.mean > 0.001:  # 1ms
                critical_issues.append(f"Warm cache too slow: {result.mean*1000:.0f}ms")
        
        # Report but don't fail on performance issues (they're informational)
        if critical_issues:
            print("\nPerformance concerns detected:")
            for issue in critical_issues:
                print(f"  - {issue}")
        
        print(f"\nBenchmark reports saved to: {output_dir}")
    
    @pytest.mark.parametrize("benchmark_category", [
        "configuration_load_time",
        "validation_performance",
        "concurrent_access",
        "memory_usage",
        "secret_access",
        "environment_processing",
        "yaml_parsing",
        "cache_efficiency",
        "thread_contention"
    ])
    def test_individual_benchmark_category(self, benchmark_category, tmp_path):
        """Run individual benchmark categories."""
        output_dir = tmp_path / "benchmark_results"
        output_dir.mkdir()
        
        suite = BenchmarkSuite(output_dir)
        
        # Run specific benchmark method
        method_name = f"_benchmark_{benchmark_category}"
        if hasattr(suite, method_name):
            print(f"\nRunning {benchmark_category} benchmarks...")
            getattr(suite, method_name)()
            
            # Verify some results were collected
            assert len(suite.results) > 0, f"No results for {benchmark_category}"
            
            # Print summary
            print(f"\nCollected {len(suite.results)} benchmarks for {benchmark_category}")
            for result in suite.results:
                print(f"  - {result.name}: {result.mean*1000:.2f}ms mean")
        else:
            pytest.skip(f"Benchmark category {benchmark_category} not found")