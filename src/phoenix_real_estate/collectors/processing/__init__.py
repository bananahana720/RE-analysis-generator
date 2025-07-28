"""LLM-powered data processing for property information."""

from .llm_client import OllamaClient
from .extractor import PropertyDataExtractor
from .validator import ProcessingValidator, ValidationResult, ValidationRule
from .pipeline import DataProcessingPipeline, ProcessingResult
from .cache import CacheManager, CacheConfig, CacheMetrics, LRUCache
from .monitoring import (
    ResourceMonitor, ResourceMetrics, ResourceLimits, 
    ResourceAlert, AlertLevel
)
from .performance import (
    PerformanceBenchmark, BenchmarkResult, PerformanceOptimizer,
    BatchSizeOptimizer, ConcurrencyOptimizer
)


__all__ = [
    # Core components
    "OllamaClient",
    "PropertyDataExtractor", 
    "ProcessingValidator",
    "ValidationResult",
    "ValidationRule",
    "DataProcessingPipeline",
    "ProcessingResult",
    # Caching
    "CacheManager",
    "CacheConfig", 
    "CacheMetrics",
    "LRUCache",
    # Monitoring
    "ResourceMonitor",
    "ResourceMetrics",
    "ResourceLimits",
    "ResourceAlert",
    "AlertLevel",
    # Performance
    "PerformanceBenchmark",
    "BenchmarkResult",
    "PerformanceOptimizer",
    "BatchSizeOptimizer",
    "ConcurrencyOptimizer"
]

# Add version info
__version__ = "0.2.0"  # Updated for performance features