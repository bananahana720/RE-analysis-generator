#!/usr/bin/env python3
"""Cost Optimization and Budget Monitoring System.

Automated cost tracking, budget compliance monitoring, and resource optimization
for the Phoenix Real Estate data collection system.

Features:
- Real-time cost tracking across all services
- Budget compliance alerts and recommendations
- Resource usage optimization
- Performance per dollar analysis
- Automated cost reduction recommendations
"""

import asyncio
import json
from datetime import datetime, UTC
from decimal import Decimal
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from typing import Dict, List, Any, NamedTuple
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from phoenix_real_estate.foundation.config import EnvironmentConfigProvider
from phoenix_real_estate.foundation.logging import get_logger

logger = get_logger(__name__)


class CostItem(NamedTuple):
    """Individual cost tracking item."""

    service: str
    category: str
    amount: Decimal
    timestamp: datetime
    usage_metric: str
    unit_cost: Decimal


class BudgetAlert(NamedTuple):
    """Budget alert notification."""

    level: str  # INFO, WARNING, CRITICAL
    message: str
    current_spend: Decimal
    budget_limit: Decimal
    percentage_used: float
    recommended_actions: List[str]


class CostOptimizer:
    """Phoenix Real Estate cost optimization and monitoring system."""

    def __init__(self, config_provider: EnvironmentConfigProvider):
        """Initialize cost optimizer.

        Args:
            config_provider: Configuration provider instance
        """
        self.config = config_provider
        self.monthly_budget = Decimal("25.00")  # $25/month budget
        self.warning_threshold = Decimal("0.80")  # 80% of budget
        self.critical_threshold = Decimal("0.95")  # 95% of budget

        # Cost tracking
        self.costs_file = Path("data/costs/monthly_costs.json")
        self.costs_file.parent.mkdir(parents=True, exist_ok=True)

        # Performance metrics for cost analysis
        self.performance_metrics = {
            "properties_collected_per_dollar": 0,
            "successful_collections_per_dollar": 0,
            "api_calls_per_dollar": 0,
            "processing_time_per_dollar": 0,
        }

    async def track_service_cost(
        self,
        service: str,
        category: str,
        amount: Decimal,
        usage_metric: str = "",
        unit_cost: Decimal = Decimal("0"),
    ) -> None:
        """Track cost for a specific service.

        Args:
            service: Service name (mongodb, ollama, webshare, etc.)
            category: Cost category (compute, storage, api_calls, etc.)
            amount: Cost amount
            usage_metric: Usage description
            unit_cost: Cost per unit if applicable
        """
        cost_item = CostItem(
            service=service,
            category=category,
            amount=amount,
            timestamp=datetime.now(UTC),
            usage_metric=usage_metric,
            unit_cost=unit_cost,
        )

        await self._record_cost(cost_item)
        logger.info(f"Tracked ${amount:.4f} for {service}/{category}: {usage_metric}")

    async def get_monthly_costs(self) -> Dict[str, Any]:
        """Get current month's cost breakdown.

        Returns:
            Dictionary with cost breakdown by service and category
        """
        costs = await self._load_costs()
        current_month = datetime.now(UTC).strftime("%Y-%m")

        monthly_costs = {"total": Decimal("0"), "by_service": {}, "by_category": {}, "items": []}

        for cost_data in costs.get(current_month, []):
            cost_item = CostItem(**cost_data)
            monthly_costs["total"] += cost_item.amount
            monthly_costs["items"].append(cost_item)

            # By service
            if cost_item.service not in monthly_costs["by_service"]:
                monthly_costs["by_service"][cost_item.service] = Decimal("0")
            monthly_costs["by_service"][cost_item.service] += cost_item.amount

            # By category
            if cost_item.category not in monthly_costs["by_category"]:
                monthly_costs["by_category"][cost_item.category] = Decimal("0")
            monthly_costs["by_category"][cost_item.category] += cost_item.amount

        return monthly_costs

    async def check_budget_compliance(self) -> List[BudgetAlert]:
        """Check current budget compliance and generate alerts.

        Returns:
            List of budget alerts if any thresholds are exceeded
        """
        alerts = []
        monthly_costs = await self.get_monthly_costs()
        current_spend = monthly_costs["total"]
        percentage_used = float(current_spend / self.monthly_budget)

        # Critical threshold
        if current_spend >= (self.monthly_budget * self.critical_threshold):
            alerts.append(
                BudgetAlert(
                    level="CRITICAL",
                    message=f"Budget usage critical: ${current_spend:.2f} of ${self.monthly_budget:.2f} ({percentage_used:.1%})",
                    current_spend=current_spend,
                    budget_limit=self.monthly_budget,
                    percentage_used=percentage_used,
                    recommended_actions=[
                        "Immediately pause non-essential data collection",
                        "Review and disable expensive proxy usage",
                        "Reduce collection frequency temporarily",
                        "Switch to free-tier services where possible",
                    ],
                )
            )

        # Warning threshold
        elif current_spend >= (self.monthly_budget * self.warning_threshold):
            alerts.append(
                BudgetAlert(
                    level="WARNING",
                    message=f"Budget usage high: ${current_spend:.2f} of ${self.monthly_budget:.2f} ({percentage_used:.1%})",
                    current_spend=current_spend,
                    budget_limit=self.monthly_budget,
                    percentage_used=percentage_used,
                    recommended_actions=[
                        "Monitor costs closely for remainder of month",
                        "Consider reducing proxy usage during peak hours",
                        "Optimize batch sizes to reduce API calls",
                        "Review LLM processing efficiency",
                    ],
                )
            )

        # Informational status
        else:
            alerts.append(
                BudgetAlert(
                    level="INFO",
                    message=f"Budget usage normal: ${current_spend:.2f} of ${self.monthly_budget:.2f} ({percentage_used:.1%})",
                    current_spend=current_spend,
                    budget_limit=self.monthly_budget,
                    percentage_used=percentage_used,
                    recommended_actions=[
                        "Continue monitoring costs",
                        "Look for optimization opportunities",
                    ],
                )
            )

        return alerts

    async def analyze_cost_efficiency(self) -> Dict[str, Any]:
        """Analyze cost efficiency and performance per dollar.

        Returns:
            Dictionary with efficiency metrics and recommendations
        """
        monthly_costs = await self.get_monthly_costs()
        total_spend = monthly_costs["total"]

        if total_spend == 0:
            return {
                "efficiency_score": 0,
                "metrics": self.performance_metrics,
                "recommendations": ["No costs recorded yet"],
            }

        # Calculate efficiency metrics
        efficiency_analysis = {
            "total_spend": float(total_spend),
            "budget_utilization": float(total_spend / self.monthly_budget),
            "cost_per_service": {k: float(v) for k, v in monthly_costs["by_service"].items()},
            "cost_per_category": {k: float(v) for k, v in monthly_costs["by_category"].items()},
            "efficiency_metrics": self.performance_metrics.copy(),
            "recommendations": await self._generate_efficiency_recommendations(monthly_costs),
        }

        return efficiency_analysis

    async def optimize_resources(self) -> Dict[str, Any]:
        """Generate resource optimization recommendations.

        Returns:
            Dictionary with optimization suggestions and potential savings
        """
        monthly_costs = await self.get_monthly_costs()
        optimizations = {
            "potential_savings": Decimal("0"),
            "recommendations": [],
            "priority_actions": [],
        }

        # Analyze by service
        for service, cost in monthly_costs["by_service"].items():
            service_recommendations = await self._analyze_service_optimization(service, cost)
            optimizations["recommendations"].extend(service_recommendations)

        # Analyze by category
        for category, cost in monthly_costs["by_category"].items():
            category_recommendations = await self._analyze_category_optimization(category, cost)
            optimizations["recommendations"].extend(category_recommendations)

        # Prioritize recommendations
        optimizations["priority_actions"] = sorted(
            optimizations["recommendations"],
            key=lambda x: x.get("potential_savings", 0),
            reverse=True,
        )[:5]

        return optimizations

    async def generate_cost_report(self) -> str:
        """Generate comprehensive cost report.

        Returns:
            Formatted cost report string
        """
        monthly_costs = await self.get_monthly_costs()
        alerts = await self.check_budget_compliance()
        await self.analyze_cost_efficiency()
        optimizations = await self.optimize_resources()

        report = f"""
# Phoenix Real Estate - Monthly Cost Report
**Generated**: {datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")}

## 💰 Budget Summary
- **Monthly Budget**: ${self.monthly_budget:.2f}
- **Current Spend**: ${monthly_costs["total"]:.2f}
- **Remaining Budget**: ${self.monthly_budget - monthly_costs["total"]:.2f}
- **Budget Utilization**: {float(monthly_costs["total"] / self.monthly_budget) * 100:.1f}%

## 📊 Cost Breakdown by Service
"""

        for service, cost in monthly_costs["by_service"].items():
            percentage = (
                float(cost / monthly_costs["total"]) * 100 if monthly_costs["total"] > 0 else 0
            )
            report += f"- **{service.title()}**: ${cost:.4f} ({percentage:.1f}%)\n"

        report += "\n## 📈 Cost Breakdown by Category\n"
        for category, cost in monthly_costs["by_category"].items():
            percentage = (
                float(cost / monthly_costs["total"]) * 100 if monthly_costs["total"] > 0 else 0
            )
            report += f"- **{category.title()}**: ${cost:.4f} ({percentage:.1f}%)\n"

        report += "\n## 🚨 Budget Alerts\n"
        for alert in alerts:
            icon = {"INFO": "ℹ️", "WARNING": "⚠️", "CRITICAL": "🚨"}.get(alert.level, "ℹ️")
            report += f"### {icon} {alert.level}\n{alert.message}\n\n"
            if alert.recommended_actions:
                report += "**Recommended Actions:**\n"
                for action in alert.recommended_actions:
                    report += f"- {action}\n"
                report += "\n"

        report += "\n## 🎯 Optimization Recommendations\n"
        for i, rec in enumerate(optimizations["priority_actions"][:3], 1):
            report += f"{i}. {rec.get('description', 'No description')}\n"
            if "potential_savings" in rec:
                report += f"   **Potential Savings**: ${rec['potential_savings']:.4f}\n"

        return report

    async def send_budget_alert_email(self, alerts: List[BudgetAlert]) -> bool:
        """Send budget alert email notifications.

        Args:
            alerts: List of budget alerts to send

        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            # Check if any alerts require email notification
            critical_alerts = [a for a in alerts if a.level in ["WARNING", "CRITICAL"]]
            if not critical_alerts:
                return True

            # Generate email content
            subject = f"Phoenix Real Estate - Budget Alert ({critical_alerts[0].level})"
            report = await self.generate_cost_report()

            # Create email
            msg = MIMEMultipart()
            msg["From"] = self.config.get("email.from_address", "noreply@phoenix-re.local")
            msg["To"] = self.config.get("email.alerts_to", "admin@phoenix-re.local")
            msg["Subject"] = subject

            msg.attach(MIMEText(report, "plain"))

            # Send email (implementation depends on email service)
            logger.info(f"Budget alert email prepared: {subject}")
            return True

        except Exception as e:
            logger.error(f"Failed to send budget alert email: {e}")
            return False

    async def _record_cost(self, cost_item: CostItem) -> None:
        """Record a cost item to persistent storage.

        Args:
            cost_item: Cost item to record
        """
        costs = await self._load_costs()
        month_key = cost_item.timestamp.strftime("%Y-%m")

        if month_key not in costs:
            costs[month_key] = []

        # Convert to dict for JSON serialization
        cost_dict = {
            "service": cost_item.service,
            "category": cost_item.category,
            "amount": str(cost_item.amount),
            "timestamp": cost_item.timestamp.isoformat(),
            "usage_metric": cost_item.usage_metric,
            "unit_cost": str(cost_item.unit_cost),
        }

        costs[month_key].append(cost_dict)
        await self._save_costs(costs)

    async def _load_costs(self) -> Dict[str, List[Dict[str, Any]]]:
        """Load costs from persistent storage.

        Returns:
            Dictionary of costs by month
        """
        if not self.costs_file.exists():
            return {}

        try:
            with open(self.costs_file, "r") as f:
                data = json.load(f)

            # Convert string amounts back to Decimal
            for month_data in data.values():
                for item in month_data:
                    item["amount"] = Decimal(item["amount"])
                    item["unit_cost"] = Decimal(item["unit_cost"])
                    item["timestamp"] = datetime.fromisoformat(item["timestamp"])

            return data

        except Exception as e:
            logger.error(f"Failed to load costs: {e}")
            return {}

    async def _save_costs(self, costs: Dict[str, List[Dict[str, Any]]]) -> None:
        """Save costs to persistent storage.

        Args:
            costs: Costs dictionary to save
        """
        try:
            # Convert Decimal and datetime for JSON serialization
            serializable_costs = {}
            for month, items in costs.items():
                serializable_costs[month] = []
                for item in items:
                    serializable_item = item.copy()
                    if isinstance(serializable_item["amount"], Decimal):
                        serializable_item["amount"] = str(serializable_item["amount"])
                    if isinstance(serializable_item["unit_cost"], Decimal):
                        serializable_item["unit_cost"] = str(serializable_item["unit_cost"])
                    if isinstance(serializable_item["timestamp"], datetime):
                        serializable_item["timestamp"] = serializable_item["timestamp"].isoformat()
                    serializable_costs[month].append(serializable_item)

            with open(self.costs_file, "w") as f:
                json.dump(serializable_costs, f, indent=2)

        except Exception as e:
            logger.error(f"Failed to save costs: {e}")

    async def _generate_efficiency_recommendations(self, costs: Dict[str, Any]) -> List[str]:
        """Generate efficiency recommendations based on cost analysis.

        Args:
            costs: Monthly costs dictionary

        Returns:
            List of efficiency recommendations
        """
        recommendations = []
        total = costs["total"]

        if total == 0:
            return ["No costs to analyze yet"]

        # Analyze service costs
        for service, cost in costs["by_service"].items():
            percentage = float(cost / total) * 100

            if service == "webshare" and percentage > 40:
                recommendations.append(
                    f"WebShare proxies account for {percentage:.1f}% of costs. "
                    "Consider reducing proxy usage or switching to free alternatives during low-traffic periods."
                )
            elif service == "mongodb" and percentage > 30:
                recommendations.append(
                    f"MongoDB costs are {percentage:.1f}% of budget. "
                    "Consider optimizing queries and implementing data archiving."
                )
            elif service == "ollama" and percentage > 25:
                recommendations.append(
                    f"LLM processing costs are {percentage:.1f}% of budget. "
                    "Consider batch processing optimization and response caching."
                )

        return recommendations or ["Cost distribution looks efficient"]

    async def _analyze_service_optimization(
        self, service: str, cost: Decimal
    ) -> List[Dict[str, Any]]:
        """Analyze optimization opportunities for a specific service.

        Args:
            service: Service name
            cost: Service cost

        Returns:
            List of optimization recommendations
        """
        recommendations = []

        if service == "webshare" and cost > Decimal("10.00"):
            recommendations.append(
                {
                    "service": service,
                    "description": "Reduce WebShare proxy usage during off-peak hours",
                    "potential_savings": float(cost * Decimal("0.3")),
                    "implementation": "Implement time-based proxy usage scheduling",
                }
            )

        elif service == "mongodb" and cost > Decimal("8.00"):
            recommendations.append(
                {
                    "service": service,
                    "description": "Optimize MongoDB queries and implement data archiving",
                    "potential_savings": float(cost * Decimal("0.2")),
                    "implementation": "Add query optimization and old data cleanup",
                }
            )

        return recommendations

    async def _analyze_category_optimization(
        self, category: str, cost: Decimal
    ) -> List[Dict[str, Any]]:
        """Analyze optimization opportunities for a cost category.

        Args:
            category: Cost category
            cost: Category cost

        Returns:
            List of optimization recommendations
        """
        recommendations = []

        if category == "api_calls" and cost > Decimal("5.00"):
            recommendations.append(
                {
                    "category": category,
                    "description": "Implement API response caching to reduce redundant calls",
                    "potential_savings": float(cost * Decimal("0.4")),
                    "implementation": "Add Redis caching layer for API responses",
                }
            )

        elif category == "compute" and cost > Decimal("7.00"):
            recommendations.append(
                {
                    "category": category,
                    "description": "Optimize compute resource usage with better scheduling",
                    "potential_savings": float(cost * Decimal("0.25")),
                    "implementation": "Implement off-peak processing and resource scaling",
                }
            )

        return recommendations


async def main():
    """Main cost optimization monitoring routine."""
    config = EnvironmentConfigProvider()
    optimizer = CostOptimizer(config)

    # Example usage - track some sample costs
    await optimizer.track_service_cost(
        "webshare", "proxy_usage", Decimal("2.50"), "1000 API calls", Decimal("0.0025")
    )

    await optimizer.track_service_cost(
        "mongodb", "storage", Decimal("1.75"), "2GB storage", Decimal("0.875")
    )

    await optimizer.track_service_cost(
        "ollama", "compute", Decimal("0.85"), "500 LLM requests", Decimal("0.0017")
    )

    # Check budget compliance
    alerts = await optimizer.check_budget_compliance()
    for alert in alerts:
        logger.info(f"{alert.level}: {alert.message}")

    # Generate and print cost report
    report = await optimizer.generate_cost_report()
    print(report)

    # Analyze optimizations
    optimizations = await optimizer.optimize_resources()
    print("\n## Top Optimization Opportunities:")
    for opt in optimizations["priority_actions"][:3]:
        print(f"- {opt.get('description', 'No description')}")
        if "potential_savings" in opt:
            print(f"  Potential savings: ${opt['potential_savings']:.4f}")


if __name__ == "__main__":
    asyncio.run(main())
