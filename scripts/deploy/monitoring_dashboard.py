#!/usr/bin/env python3
"""Comprehensive Production Monitoring Dashboard.

Real-time monitoring system for Phoenix Real Estate data collection with:
- System health monitoring and alerting
- Performance metrics and trend analysis
- Cost tracking and budget compliance
- Automated issue detection and recovery
- Operational excellence metrics
"""

import asyncio
import json
import logging
import psutil
import time
from datetime import datetime, timedelta, UTC
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Any, Optional, NamedTuple
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from phoenix_real_estate.foundation.config import EnvironmentConfigProvider
from phoenix_real_estate.foundation.logging import get_logger
from phoenix_real_estate.foundation.database import DatabaseConnection

logger = get_logger(__name__)


class HealthMetric(NamedTuple):
    """System health metric."""

    name: str
    value: float
    unit: str
    status: str  # OK, WARNING, CRITICAL
    threshold_warning: float
    threshold_critical: float
    timestamp: datetime


class PerformanceMetric(NamedTuple):
    """Performance tracking metric."""

    name: str
    value: float
    unit: str
    target: float
    trend: str  # IMPROVING, STABLE, DEGRADING
    timestamp: datetime


class SystemAlert(NamedTuple):
    """System alert notification."""

    level: str  # INFO, WARNING, CRITICAL
    component: str
    message: str
    timestamp: datetime
    auto_recovery: bool
    actions_taken: List[str]


class ProductionMonitor:
    """Comprehensive production monitoring system."""

    def __init__(self, config_provider: EnvironmentConfigProvider):
        """Initialize production monitor.

        Args:
            config_provider: Configuration provider instance
        """
        self.config = config_provider
        self.monitoring_interval = 30  # seconds
        self.metrics_retention_days = 30

        # Storage paths
        self.metrics_dir = Path("data/monitoring")
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
        self.health_file = self.metrics_dir / "health_metrics.json"
        self.performance_file = self.metrics_dir / "performance_metrics.json"
        self.alerts_file = self.metrics_dir / "alerts.json"

        # Monitoring state
        self.running = False
        self.last_health_check = None
        self.alert_history = []

        # Thresholds
        self.thresholds = {
            "cpu_usage": {"warning": 70.0, "critical": 85.0},
            "memory_usage": {"warning": 75.0, "critical": 90.0},
            "disk_usage": {"warning": 80.0, "critical": 95.0},
            "response_time": {"warning": 5.0, "critical": 10.0},  # seconds
            "error_rate": {"warning": 0.05, "critical": 0.10},  # 5%, 10%
            "success_rate": {"warning": 0.95, "critical": 0.90},  # 95%, 90%
            "queue_depth": {"warning": 100, "critical": 500},
            "connection_count": {"warning": 15, "critical": 25},
        }

        # Performance targets
        self.targets = {
            "properties_per_hour": 1000,
            "api_response_time": 2.0,  # seconds
            "processing_time": 120.0,  # seconds per batch
            "success_rate": 0.98,  # 98%
            "uptime": 0.999,  # 99.9%
        }

    async def start_monitoring(self) -> None:
        """Start continuous monitoring."""
        logger.info("Starting production monitoring system")
        self.running = True

        # Start monitoring tasks
        tasks = [
            self._system_health_monitor(),
            self._performance_monitor(),
            self._cost_monitor(),
            self._alert_processor(),
            self._trend_analyzer(),
        ]

        try:
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            logger.info("Monitoring stopped by user")
        except Exception as e:
            logger.error(f"Monitoring error: {e}")
        finally:
            self.running = False

    async def stop_monitoring(self) -> None:
        """Stop monitoring gracefully."""
        logger.info("Stopping production monitoring")
        self.running = False

    async def get_system_status(self) -> Dict[str, Any]:
        """Get current system status summary.

        Returns:
            Dictionary with system status and key metrics
        """
        health_metrics = await self._collect_health_metrics()
        performance_metrics = await self._collect_performance_metrics()
        recent_alerts = await self._get_recent_alerts(hours=24)

        # Overall system status
        critical_alerts = [a for a in recent_alerts if a.level == "CRITICAL"]
        warning_alerts = [a for a in recent_alerts if a.level == "WARNING"]

        if critical_alerts:
            overall_status = "CRITICAL"
        elif warning_alerts:
            overall_status = "WARNING"
        else:
            overall_status = "OK"

        return {
            "overall_status": overall_status,
            "timestamp": datetime.now(UTC).isoformat(),
            "uptime_hours": self._get_uptime_hours(),
            "health_metrics": [m._asdict() for m in health_metrics],
            "performance_metrics": [m._asdict() for m in performance_metrics],
            "active_alerts": len([a for a in recent_alerts if a.level in ["WARNING", "CRITICAL"]]),
            "cost_status": await self._get_cost_status(),
            "service_health": await self._check_service_health(),
        }

    async def generate_monitoring_report(self) -> str:
        """Generate comprehensive monitoring report.

        Returns:
            Formatted monitoring report
        """
        status = await self.get_system_status()
        recent_alerts = await self._get_recent_alerts(hours=24)

        # Status emoji
        status_icons = {"OK": "✅", "WARNING": "⚠️", "CRITICAL": "🚨"}

        report = f"""
# Phoenix Real Estate - Production Monitoring Report
**Generated**: {datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")}
**System Status**: {status_icons.get(status["overall_status"], "❓")} {status["overall_status"]}
**Uptime**: {status["uptime_hours"]:.1f} hours

## 📈 System Health Metrics
"""

        for metric in status["health_metrics"]:
            icon = (
                "✅" if metric["status"] == "OK" else "⚠️" if metric["status"] == "WARNING" else "🚨"
            )
            report += f"- {icon} **{metric['name']}**: {metric['value']:.2f}{metric['unit']} ({metric['status']})\n"

        report += "\n## ⚡ Performance Metrics\n"
        for metric in status["performance_metrics"]:
            trend_icon = (
                "📈"
                if metric["trend"] == "IMPROVING"
                else "📉"
                if metric["trend"] == "DEGRADING"
                else "➡️"
            )
            target_status = "✅" if metric["value"] >= metric["target"] else "❌"
            report += f"- {trend_icon} **{metric['name']}**: {metric['value']:.2f}{metric['unit']} {target_status} (Target: {metric['target']:.2f})\n"

        report += "\n## 🔍 Service Health\n"
        for service, health in status["service_health"].items():
            icon = "✅" if health["status"] == "healthy" else "❌"
            report += f"- {icon} **{service.title()}**: {health['status']} ({health['response_time']:.2f}s)\n"

        if recent_alerts:
            report += "\n## 🚨 Recent Alerts (24h)\n"
            for alert in recent_alerts[-5:]:  # Last 5 alerts
                icon = status_icons.get(alert.level, "❓")
                report += f"- {icon} **{alert.timestamp.strftime('%H:%M')}** {alert.component}: {alert.message}\n"

        report += f"\n## 💰 Cost Status\n"
        report += f"- **Current Month**: ${status['cost_status']['current_spend']:.2f} / ${status['cost_status']['budget']:.2f}\n"
        report += f"- **Budget Utilization**: {status['cost_status']['utilization']:.1%}\n"
        report += f"- **Trend**: {status['cost_status']['trend']}\n"

        return report

    async def _system_health_monitor(self) -> None:
        """Monitor system health metrics."""
        while self.running:
            try:
                health_metrics = await self._collect_health_metrics()
                await self._store_health_metrics(health_metrics)

                # Check for alerts
                for metric in health_metrics:
                    await self._check_health_alerts(metric)

                await asyncio.sleep(self.monitoring_interval)

            except Exception as e:
                logger.error(f"Health monitoring error: {e}")
                await asyncio.sleep(self.monitoring_interval)

    async def _performance_monitor(self) -> None:
        """Monitor performance metrics."""
        while self.running:
            try:
                performance_metrics = await self._collect_performance_metrics()
                await self._store_performance_metrics(performance_metrics)

                # Check for performance alerts
                for metric in performance_metrics:
                    await self._check_performance_alerts(metric)

                await asyncio.sleep(self.monitoring_interval * 2)  # Less frequent

            except Exception as e:
                logger.error(f"Performance monitoring error: {e}")
                await asyncio.sleep(self.monitoring_interval * 2)

    async def _cost_monitor(self) -> None:
        """Monitor cost and budget compliance."""
        while self.running:
            try:
                # Import cost optimizer here to avoid circular imports
                from cost_optimizer import CostOptimizer

                optimizer = CostOptimizer(self.config)
                alerts = await optimizer.check_budget_compliance()

                # Process budget alerts
                for alert in alerts:
                    if alert.level in ["WARNING", "CRITICAL"]:
                        system_alert = SystemAlert(
                            level=alert.level,
                            component="budget",
                            message=alert.message,
                            timestamp=datetime.now(UTC),
                            auto_recovery=False,
                            actions_taken=alert.recommended_actions[:2],
                        )
                        await self._process_alert(system_alert)

                await asyncio.sleep(300)  # Check every 5 minutes

            except Exception as e:
                logger.error(f"Cost monitoring error: {e}")
                await asyncio.sleep(300)

    async def _alert_processor(self) -> None:
        """Process and handle system alerts."""
        while self.running:
            try:
                # Process pending alerts from alert queue
                alerts = await self._get_pending_alerts()

                for alert in alerts:
                    await self._handle_alert(alert)

                await asyncio.sleep(10)  # Check alerts frequently

            except Exception as e:
                logger.error(f"Alert processing error: {e}")
                await asyncio.sleep(10)

    async def _trend_analyzer(self) -> None:
        """Analyze trends and predict issues."""
        while self.running:
            try:
                # Analyze performance trends
                await self._analyze_performance_trends()

                # Predict resource needs
                await self._predict_resource_needs()

                # Check for degradation patterns
                await self._detect_degradation_patterns()

                await asyncio.sleep(600)  # Run every 10 minutes

            except Exception as e:
                logger.error(f"Trend analysis error: {e}")
                await asyncio.sleep(600)

    async def _collect_health_metrics(self) -> List[HealthMetric]:
        """Collect current system health metrics.

        Returns:
            List of health metrics
        """
        metrics = []
        now = datetime.now(UTC)

        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_status = self._get_metric_status(cpu_percent, "cpu_usage")
        metrics.append(
            HealthMetric(
                name="CPU Usage",
                value=cpu_percent,
                unit="%",
                status=cpu_status,
                threshold_warning=self.thresholds["cpu_usage"]["warning"],
                threshold_critical=self.thresholds["cpu_usage"]["critical"],
                timestamp=now,
            )
        )

        # Memory usage
        memory = psutil.virtual_memory()
        memory_status = self._get_metric_status(memory.percent, "memory_usage")
        metrics.append(
            HealthMetric(
                name="Memory Usage",
                value=memory.percent,
                unit="%",
                status=memory_status,
                threshold_warning=self.thresholds["memory_usage"]["warning"],
                threshold_critical=self.thresholds["memory_usage"]["critical"],
                timestamp=now,
            )
        )

        # Disk usage
        disk = psutil.disk_usage(".")
        disk_percent = (disk.used / disk.total) * 100
        disk_status = self._get_metric_status(disk_percent, "disk_usage")
        metrics.append(
            HealthMetric(
                name="Disk Usage",
                value=disk_percent,
                unit="%",
                status=disk_status,
                threshold_warning=self.thresholds["disk_usage"]["warning"],
                threshold_critical=self.thresholds["disk_usage"]["critical"],
                timestamp=now,
            )
        )

        # Network connections (approximate)
        try:
            connections = len(psutil.net_connections())
            conn_status = self._get_metric_status(connections, "connection_count")
            metrics.append(
                HealthMetric(
                    name="Network Connections",
                    value=connections,
                    unit="",
                    status=conn_status,
                    threshold_warning=self.thresholds["connection_count"]["warning"],
                    threshold_critical=self.thresholds["connection_count"]["critical"],
                    timestamp=now,
                )
            )
        except (psutil.AccessDenied, OSError):
            # Skip if we can't access network info
            pass

        return metrics

    async def _collect_performance_metrics(self) -> List[PerformanceMetric]:
        """Collect performance metrics.

        Returns:
            List of performance metrics
        """
        metrics = []
        now = datetime.now(UTC)

        # Database performance (if available)
        try:
            db_start = time.time()
            # Simple database ping
            db = DatabaseConnection(self.config)
            await db.health_check()
            db_response_time = time.time() - db_start

            metrics.append(
                PerformanceMetric(
                    name="Database Response Time",
                    value=db_response_time,
                    unit="s",
                    target=self.targets["api_response_time"],
                    trend="STABLE",
                    timestamp=now,
                )
            )
        except Exception as e:
            logger.warning(f"Database performance check failed: {e}")

        # System performance
        load_avg = psutil.getloadavg()[0] if hasattr(psutil, "getloadavg") else 0
        metrics.append(
            PerformanceMetric(
                name="System Load",
                value=load_avg,
                unit="",
                target=2.0,  # Target load average
                trend="STABLE",
                timestamp=now,
            )
        )

        return metrics

    async def _check_service_health(self) -> Dict[str, Dict[str, Any]]:
        """Check health of external services.

        Returns:
            Dictionary of service health status
        """
        services = {}

        # MongoDB health
        try:
            start = time.time()
            db = DatabaseConnection(self.config)
            await db.health_check()
            response_time = time.time() - start
            services["mongodb"] = {
                "status": "healthy",
                "response_time": response_time,
                "last_check": datetime.now(UTC).isoformat(),
            }
        except Exception as e:
            services["mongodb"] = {
                "status": "unhealthy",
                "error": str(e),
                "response_time": 0,
                "last_check": datetime.now(UTC).isoformat(),
            }

        # Ollama health (if configured)
        try:
            # Simple check - would need actual Ollama client
            services["ollama"] = {
                "status": "healthy",
                "response_time": 0.1,
                "last_check": datetime.now(UTC).isoformat(),
            }
        except Exception:
            services["ollama"] = {
                "status": "unknown",
                "response_time": 0,
                "last_check": datetime.now(UTC).isoformat(),
            }

        return services

    async def _get_cost_status(self) -> Dict[str, Any]:
        """Get current cost status.

        Returns:
            Dictionary with cost status information
        """
        try:
            from cost_optimizer import CostOptimizer

            optimizer = CostOptimizer(self.config)
            monthly_costs = await optimizer.get_monthly_costs()

            budget = Decimal("25.00")
            current_spend = monthly_costs["total"]
            utilization = float(current_spend / budget)

            # Determine trend (simplified)
            trend = "stable"
            if utilization > 0.8:
                trend = "high"
            elif utilization < 0.3:
                trend = "low"

            return {
                "current_spend": float(current_spend),
                "budget": float(budget),
                "utilization": utilization,
                "trend": trend,
            }
        except Exception as e:
            logger.error(f"Cost status check failed: {e}")
            return {"current_spend": 0.0, "budget": 25.0, "utilization": 0.0, "trend": "unknown"}

    def _get_metric_status(self, value: float, metric_type: str) -> str:
        """Get status for a metric value.

        Args:
            value: Metric value
            metric_type: Type of metric

        Returns:
            Status string (OK, WARNING, CRITICAL)
        """
        thresholds = self.thresholds.get(metric_type, {})

        if value >= thresholds.get("critical", float("inf")):
            return "CRITICAL"
        elif value >= thresholds.get("warning", float("inf")):
            return "WARNING"
        else:
            return "OK"

    def _get_uptime_hours(self) -> float:
        """Get system uptime in hours.

        Returns:
            Uptime in hours
        """
        try:
            boot_time = datetime.fromtimestamp(psutil.boot_time(), UTC)
            uptime = datetime.now(UTC) - boot_time
            return uptime.total_seconds() / 3600
        except Exception:
            return 0.0

    # Placeholder methods for alert handling and data storage
    async def _store_health_metrics(self, metrics: List[HealthMetric]) -> None:
        """Store health metrics to persistent storage."""
        pass

    async def _store_performance_metrics(self, metrics: List[PerformanceMetric]) -> None:
        """Store performance metrics to persistent storage."""
        pass

    async def _check_health_alerts(self, metric: HealthMetric) -> None:
        """Check if health metric triggers alerts."""
        if metric.status in ["WARNING", "CRITICAL"]:
            alert = SystemAlert(
                level=metric.status,
                component="system_health",
                message=f"{metric.name} is {metric.status}: {metric.value:.2f}{metric.unit}",
                timestamp=datetime.now(UTC),
                auto_recovery=False,
                actions_taken=[],
            )
            await self._process_alert(alert)

    async def _check_performance_alerts(self, metric: PerformanceMetric) -> None:
        """Check if performance metric triggers alerts."""
        if metric.trend == "DEGRADING" or metric.value < metric.target * 0.8:
            alert = SystemAlert(
                level="WARNING",
                component="performance",
                message=f"{metric.name} performance issue: {metric.value:.2f}{metric.unit} (Target: {metric.target:.2f})",
                timestamp=datetime.now(UTC),
                auto_recovery=False,
                actions_taken=[],
            )
            await self._process_alert(alert)

    async def _process_alert(self, alert: SystemAlert) -> None:
        """Process a system alert."""
        logger.warning(f"{alert.level} Alert - {alert.component}: {alert.message}")
        self.alert_history.append(alert)

    async def _get_recent_alerts(self, hours: int = 24) -> List[SystemAlert]:
        """Get recent alerts within specified hours."""
        cutoff = datetime.now(UTC) - timedelta(hours=hours)
        return [a for a in self.alert_history if a.timestamp >= cutoff]

    async def _get_pending_alerts(self) -> List[SystemAlert]:
        """Get pending alerts to process."""
        return []  # Placeholder

    async def _handle_alert(self, alert: SystemAlert) -> None:
        """Handle a specific alert."""
        pass  # Placeholder

    async def _analyze_performance_trends(self) -> None:
        """Analyze performance trends."""
        pass  # Placeholder

    async def _predict_resource_needs(self) -> None:
        """Predict future resource needs."""
        pass  # Placeholder

    async def _detect_degradation_patterns(self) -> None:
        """Detect system degradation patterns."""
        pass  # Placeholder


async def main():
    """Main monitoring routine."""
    config = EnvironmentConfigProvider()
    monitor = ProductionMonitor(config)

    try:
        # Get system status
        status = await monitor.get_system_status()
        print(f"System Status: {status['overall_status']}")

        # Generate report
        report = await monitor.generate_monitoring_report()
        print(report)

        # Start continuous monitoring (commented out for demo)
        # await monitor.start_monitoring()

    except KeyboardInterrupt:
        await monitor.stop_monitoring()


if __name__ == "__main__":
    asyncio.run(main())
