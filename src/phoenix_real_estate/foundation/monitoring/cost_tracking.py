"""Cost tracking and budget monitoring for Phoenix Real Estate system.

Provides real-time cost tracking with budget compliance monitoring,
cost efficiency metrics, and automated alerts for production deployment.
"""

import time
from datetime import datetime
from typing import Dict, Optional, Any
from dataclasses import dataclass
from contextlib import asynccontextmanager

from prometheus_client import Counter, Gauge, Histogram
from phoenix_real_estate.foundation.logging import get_logger
from phoenix_real_estate.foundation.config import ConfigProvider

logger = get_logger(__name__)


@dataclass
class CostComponent:
    """Individual cost component tracking."""
    name: str
    cost_per_unit: float
    units_consumed: int
    total_cost: float
    category: str  # 'api_calls', 'proxy_usage', 'llm_processing', 'storage'


@dataclass
class BudgetThresholds:
    """Budget threshold configuration."""
    monthly_limit: float = 25.00  # $25/month budget
    daily_limit: float = 25.00 / 30  # ~$0.83/day
    warning_threshold: float = 0.90  # 90% of budget
    critical_threshold: float = 1.10  # 110% of budget


class CostTracker:
    """Real-time cost tracking with Prometheus metrics integration."""
    
    def __init__(self, registry, config: ConfigProvider):
        """Initialize cost tracking system.
        
        Args:
            registry: Prometheus collector registry
            config: Configuration provider
        """
        self.registry = registry
        self.config = config
        self.thresholds = BudgetThresholds()
        
        # Initialize cost tracking data
        self.daily_costs: Dict[str, Dict[str, float]] = {}
        self.monthly_costs: Dict[str, Dict[str, float]] = {}
        self.cost_components: Dict[str, CostComponent] = {}
        
        # Initialize Prometheus metrics
        self._initialize_metrics()
        
        # Load current costs from persistence (if available)
        self._load_cost_data()
        
        logger.info("Cost tracking system initialized with $25/month budget")
    
    def _initialize_metrics(self):
        """Initialize Prometheus cost tracking metrics."""
        # Total cost metrics
        self.daily_cost = Gauge(
            'phoenix_cost_tracking_daily_spend',
            'Total daily spending in USD',
            registry=self.registry
        )
        
        self.monthly_cost = Gauge(
            'phoenix_cost_tracking_monthly_spend',
            'Total monthly spending in USD',
            registry=self.registry
        )
        
        # Budget compliance metrics
        self.budget_utilization = Gauge(
            'phoenix_cost_budget_utilization_percent',
            'Percentage of monthly budget utilized',
            registry=self.registry
        )
        
        self.budget_remaining = Gauge(
            'phoenix_cost_budget_remaining',
            'Remaining budget in USD',
            registry=self.registry
        )
        
        # Cost component metrics
        self.api_costs = Counter(
            'phoenix_cost_api_calls_total',
            'Total API call costs',
            ['api_type'],
            registry=self.registry
        )
        
        self.proxy_costs = Counter(
            'phoenix_cost_proxy_usage_total',
            'Total proxy usage costs',
            registry=self.registry
        )
        
        self.llm_costs = Counter(
            'phoenix_cost_llm_processing_total',
            'Total LLM processing costs',
            registry=self.registry
        )
        
        self.storage_costs = Counter(
            'phoenix_cost_storage_total',
            'Total storage costs',
            registry=self.registry
        )
        
        # Cost efficiency metrics
        self.cost_per_property = Gauge(
            'phoenix_cost_efficiency_per_property',
            'Cost per property collected (USD)',
            registry=self.registry
        )
        
        self.cost_efficiency_target = Gauge(
            'phoenix_cost_efficiency_target',
            'Target cost efficiency (USD per property)',
            registry=self.registry
        )
        
        # Cost history tracking
        self.cost_history = Histogram(
            'phoenix_cost_daily_history',
            'Daily cost history for trending',
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 25.0],
            registry=self.registry
        )
        
        # Set initial target efficiency (assuming 500 properties/month)
        self.cost_efficiency_target.set(25.00 / 500)  # $0.05 per property
    
    def _load_cost_data(self):
        """Load existing cost data from persistence."""
        today = datetime.now().strftime('%Y-%m-%d')
        current_month = datetime.now().strftime('%Y-%m')
        
        # Initialize empty cost tracking if not exists
        if current_month not in self.monthly_costs:
            self.monthly_costs[current_month] = {
                'api_calls': 0.0,
                'proxy_usage': 0.0,
                'llm_processing': 0.0,
                'storage': 0.0,
                'total': 0.0
            }
        
        if today not in self.daily_costs:
            self.daily_costs[today] = {
                'api_calls': 0.0,
                'proxy_usage': 0.0,
                'llm_processing': 0.0,
                'storage': 0.0,
                'total': 0.0
            }
        
        # Update metrics with loaded data
        self._update_metrics()
    
    def record_api_cost(self, api_type: str, cost: float):
        """Record API call cost.
        
        Args:
            api_type: Type of API (maricopa, captcha, etc.)
            cost: Cost in USD
        """
        self._record_cost('api_calls', cost)
        self.api_costs.labels(api_type=api_type).inc(cost)
        logger.debug(f"Recorded API cost: {api_type} = ${cost:.4f}")
    
    def record_proxy_cost(self, cost: float):
        """Record proxy usage cost.
        
        Args:
            cost: Cost in USD
        """
        self._record_cost('proxy_usage', cost)
        self.proxy_costs.inc(cost)
        logger.debug(f"Recorded proxy cost: ${cost:.4f}")
    
    def record_llm_cost(self, tokens_processed: int, cost_per_token: float = 0.0001):
        """Record LLM processing cost.
        
        Args:
            tokens_processed: Number of tokens processed
            cost_per_token: Cost per token (default: $0.0001)
        """
        cost = tokens_processed * cost_per_token
        self._record_cost('llm_processing', cost)
        self.llm_costs.inc(cost)
        logger.debug(f"Recorded LLM cost: {tokens_processed} tokens = ${cost:.4f}")
    
    def record_storage_cost(self, cost: float):
        """Record storage cost.
        
        Args:
            cost: Cost in USD
        """
        self._record_cost('storage', cost)
        self.storage_costs.inc(cost)
        logger.debug(f"Recorded storage cost: ${cost:.4f}")
    
    def _record_cost(self, category: str, cost: float):
        """Internal method to record cost in tracking structures.
        
        Args:
            category: Cost category
            cost: Cost amount in USD
        """
        today = datetime.now().strftime('%Y-%m-%d')
        current_month = datetime.now().strftime('%Y-%m')
        
        # Update daily costs
        if today not in self.daily_costs:
            self.daily_costs[today] = {
                'api_calls': 0.0,
                'proxy_usage': 0.0,
                'llm_processing': 0.0,
                'storage': 0.0,
                'total': 0.0
            }
        
        self.daily_costs[today][category] += cost
        self.daily_costs[today]['total'] += cost
        
        # Update monthly costs
        if current_month not in self.monthly_costs:
            self.monthly_costs[current_month] = {
                'api_calls': 0.0,
                'proxy_usage': 0.0,
                'llm_processing': 0.0,
                'storage': 0.0,
                'total': 0.0
            }
        
        self.monthly_costs[current_month][category] += cost
        self.monthly_costs[current_month]['total'] += cost
        
        # Update Prometheus metrics
        self._update_metrics()
        
        # Check budget thresholds
        self._check_budget_alerts()
    
    def _update_metrics(self):
        """Update Prometheus metrics with current cost data."""
        today = datetime.now().strftime('%Y-%m-%d')
        current_month = datetime.now().strftime('%Y-%m')
        
        # Update cost metrics
        daily_total = self.daily_costs.get(today, {}).get('total', 0.0)
        monthly_total = self.monthly_costs.get(current_month, {}).get('total', 0.0)
        
        self.daily_cost.set(daily_total)
        self.monthly_cost.set(monthly_total)
        
        # Update budget metrics
        budget_utilization = (monthly_total / self.thresholds.monthly_limit) * 100
        budget_remaining = max(0, self.thresholds.monthly_limit - monthly_total)
        
        self.budget_utilization.set(budget_utilization)
        self.budget_remaining.set(budget_remaining)
        
        # Update cost history
        self.cost_history.observe(daily_total)
        
        logger.debug(f"Updated metrics: Daily=${daily_total:.4f}, Monthly=${monthly_total:.4f}, Budget={budget_utilization:.1f}%")
    
    def _check_budget_alerts(self):
        """Check budget thresholds and log warnings."""
        current_month = datetime.now().strftime('%Y-%m')
        monthly_total = self.monthly_costs.get(current_month, {}).get('total', 0.0)
        
        utilization = monthly_total / self.thresholds.monthly_limit
        
        if utilization >= self.thresholds.critical_threshold:
            logger.error(f"CRITICAL: Budget overrun detected! ${monthly_total:.2f} / ${self.thresholds.monthly_limit:.2f} ({utilization*100:.1f}%)")
        elif utilization >= self.thresholds.warning_threshold:
            logger.warning(f"WARNING: Budget approaching limit: ${monthly_total:.2f} / ${self.thresholds.monthly_limit:.2f} ({utilization*100:.1f}%)")
    
    def update_cost_efficiency(self, properties_collected: int):
        """Update cost efficiency metrics.
        
        Args:
            properties_collected: Number of properties collected today
        """
        today = datetime.now().strftime('%Y-%m-%d')
        daily_total = self.daily_costs.get(today, {}).get('total', 0.0)
        
        if properties_collected > 0:
            cost_per_prop = daily_total / properties_collected
            self.cost_per_property.set(cost_per_prop)
            logger.debug(f"Cost efficiency: ${cost_per_prop:.4f} per property ({properties_collected} properties)")
    
    def get_cost_summary(self) -> Dict[str, Any]:
        """Get comprehensive cost summary.
        
        Returns:
            Dictionary with cost summary data
        """
        today = datetime.now().strftime('%Y-%m-%d')
        current_month = datetime.now().strftime('%Y-%m')
        
        daily_costs = self.daily_costs.get(today, {})
        monthly_costs = self.monthly_costs.get(current_month, {})
        
        return {
            'daily': {
                'total': daily_costs.get('total', 0.0),
                'breakdown': {k: v for k, v in daily_costs.items() if k != 'total'}
            },
            'monthly': {
                'total': monthly_costs.get('total', 0.0),
                'breakdown': {k: v for k, v in monthly_costs.items() if k != 'total'},
                'budget_utilization': (monthly_costs.get('total', 0.0) / self.thresholds.monthly_limit) * 100,
                'budget_remaining': max(0, self.thresholds.monthly_limit - monthly_costs.get('total', 0.0))
            },
            'thresholds': {
                'monthly_limit': self.thresholds.monthly_limit,
                'daily_limit': self.thresholds.daily_limit,
                'warning_threshold': self.thresholds.warning_threshold * 100,
                'critical_threshold': self.thresholds.critical_threshold * 100
            }
        }
    
    @asynccontextmanager
    async def track_operation_cost(self, operation_type: str, base_cost: float = 0.001):
        """Context manager to track operation costs.
        
        Args:
            operation_type: Type of operation for categorization
            base_cost: Base cost for the operation
        """
        start_time = time.time()
        
        try:
            yield
        except Exception:
            # Still record cost even on failure
            raise
        finally:
            duration = time.time() - start_time
            
            # Simple cost model based on duration
            computed_cost = base_cost + (duration * 0.0001)  # $0.0001 per second
            
            if operation_type.startswith('api_'):
                self.record_api_cost(operation_type.replace('api_', ''), computed_cost)
            elif operation_type == 'llm_processing':
                self.record_llm_cost(int(duration * 100), 0.0001)  # Estimate tokens
            elif operation_type == 'proxy_usage':
                self.record_proxy_cost(computed_cost)
            else:
                self._record_cost('other', computed_cost)


# Global cost tracker instance
_cost_tracker: Optional[CostTracker] = None


def get_cost_tracker(registry=None, config: Optional[ConfigProvider] = None) -> CostTracker:
    """Get or create the global cost tracker instance.
    
    Args:
        registry: Prometheus collector registry
        config: Configuration provider
        
    Returns:
        Global cost tracker instance
    """
    global _cost_tracker
    
    if _cost_tracker is None:
        if registry is None or config is None:
            raise ValueError("Registry and config required for first initialization")
        _cost_tracker = CostTracker(registry, config)
    
    return _cost_tracker


def reset_cost_tracker():
    """Reset the global cost tracker (for testing)."""
    global _cost_tracker
    _cost_tracker = None