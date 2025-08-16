# Unit tests for cost tracking module
import pytest

# Import cost tracking classes
try:
    from src.phoenix_real_estate.foundation.monitoring.cost_tracking import CostTracker
except ImportError:
    pytest.skip('CostTracker not available', allow_module_level=True)


class TestCostTracker:
    """Test suite for CostTracker."""
    
    def test_cost_tracker_initialization(self):
        """Test CostTracker initialization."""
        pricing_config = {
            'cpu_cost_per_second': 0.0001,
            'memory_cost_per_mb_second': 0.000001,
            'storage_cost_per_gb_second': 0.00001,
            'network_cost_per_gb': 0.09,
            'api_cost_per_request': 0.001
        }
        cost_tracker = CostTracker(pricing_config)
        assert cost_tracker.pricing_config['cpu_cost_per_second'] == 0.0001
        assert cost_tracker.pricing_config['api_cost_per_request'] == 0.001
        
    def test_basic_functionality(self):
        """Test basic cost tracking functionality."""
        pricing_config = {
            'cpu_cost_per_second': 0.0001,
            'memory_cost_per_mb_second': 0.000001,
            'api_cost_per_request': 0.001
        }
        cost_tracker = CostTracker(pricing_config)
        
        # Test that the tracker exists and has required methods
        assert hasattr(cost_tracker, 'pricing_config')
        assert isinstance(cost_tracker.pricing_config, dict)
