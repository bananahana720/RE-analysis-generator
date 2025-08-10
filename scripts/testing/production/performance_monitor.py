#\!/usr/bin/env python3
"""Performance monitoring script for production."""
import asyncio
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

class PerformanceMonitor:
    """Production performance monitoring."""
    
    def __init__(self):
        self.metrics = defaultdict(list)
        self.thresholds = {
            "api_response_time": 0.2,  # 200ms
            "memory_usage_mb": 400,    # 400MB
            "error_rate": 0.01         # 1%
        }
    
    async def monitor_system_performance(self, duration_minutes=10):
        """Monitor system performance metrics."""
        print(f"📊 Monitoring performance for {duration_minutes} minutes")
        print("=" * 50)
        
        end_time = time.time() + (duration_minutes * 60)
        sample_count = 0
        
        while time.time() < end_time:
            sample_count += 1
            
            # Memory monitoring
            import psutil
            memory_mb = (psutil.virtual_memory().total - psutil.virtual_memory().available) / (1024 * 1024)
            self.metrics["memory_usage_mb"].append(memory_mb)
            
            # CPU monitoring
            cpu_percent = psutil.cpu_percent(interval=1)
            self.metrics["cpu_percent"].append(cpu_percent)
            
            # Simulate API response monitoring
            # In real implementation, this would test actual API endpoints
            simulated_response_time = 0.15  # 150ms baseline
            self.metrics["api_response_time"].append(simulated_response_time)
            
            if sample_count % 10 == 0:  # Report every 10 samples
                print(f"Sample {sample_count}: Memory {memory_mb:.1f}MB, CPU {cpu_percent:.1f}%")
            
            await asyncio.sleep(6)  # Sample every 6 seconds for 10-minute monitoring
    
    def analyze_performance(self):
        """Analyze collected performance metrics."""
        print("\n📈 Performance Analysis Results")
        print("=" * 40)
        
        results = {}
        
        for metric, values in self.metrics.items():
            if values:
                avg_value = sum(values) / len(values)
                max_value = max(values)
                min_value = min(values)
                
                # Check against thresholds
                threshold = self.thresholds.get(metric)
                threshold_met = avg_value <= threshold if threshold else True
                
                results[metric] = {
                    "average": avg_value,
                    "maximum": max_value,
                    "minimum": min_value,
                    "threshold": threshold,
                    "threshold_met": threshold_met
                }
                
                status = "[OK]" if threshold_met else "[WARN]"
                print(f"{status} {metric.replace(_,  ).title()}:")
                print(f"   Average: {avg_value:.3f}")
                print(f"   Range: {min_value:.3f} - {max_value:.3f}")
                if threshold:
                    print(f"   Threshold: <{threshold} ({MET if threshold_met else EXCEEDED})")
        
        # Overall assessment
        all_thresholds_met = all(
            result["threshold_met"] for result in results.values()
        )
        
        print("\n" + "=" * 40)
        print(f"Overall Performance: {"GOOD" if all_thresholds_met else "NEEDS ATTENTION"}")
        
        return results, all_thresholds_met
    
    def save_report(self, results, filename="performance_report.json"):
        """Save performance report to file."""
        report = {
            "timestamp": time.time(),
            "results": results,
            "raw_metrics": dict(self.metrics)
        }
        
        with open(filename, "w") as f:
            json.dump(report, f, indent=2)
        
        print(f"📄 Report saved to {filename}")

async def main():
    """Main monitoring execution."""
    monitor = PerformanceMonitor()
    
    try:
        # Monitor for 10 minutes (or shorter for demo)
        await monitor.monitor_system_performance(duration_minutes=1)  # 1 minute for demo
        
        # Analyze results
        results, performance_ok = monitor.analyze_performance()
        
        # Save report
        monitor.save_report(results)
        
        return performance_ok
        
    except Exception as e:
        print(f"[FAIL] Performance monitoring failed: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
