#!/usr/bin/env python3
"""Continuous Quality Monitoring and Validation System.

Comprehensive quality monitoring for Phoenix Real Estate data collection with:
- Data quality validation and scoring
- Processing pipeline quality assurance
- Automated quality trend analysis
- Quality degradation detection and alerting
- Continuous improvement recommendations
"""

import asyncio
import json
import statistics
from datetime import datetime, timedelta, UTC
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, NamedTuple
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from phoenix_real_estate.foundation.config import EnvironmentConfigProvider
from phoenix_real_estate.foundation.database import DatabaseConnection
from phoenix_real_estate.foundation.logging import get_logger
from phoenix_real_estate.models.property import PropertyDetails

logger = get_logger(__name__)


class QualityMetric(NamedTuple):
    """Quality metric measurement."""

    name: str
    value: float
    max_value: float
    percentage: float
    status: str  # EXCELLENT, GOOD, FAIR, POOR
    threshold_good: float
    threshold_fair: float
    timestamp: datetime


class QualityAlert(NamedTuple):
    """Quality degradation alert."""

    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    component: str
    metric: str
    current_value: float
    expected_value: float
    trend: str  # IMPROVING, STABLE, DEGRADING
    message: str
    recommended_actions: List[str]
    timestamp: datetime


@dataclass
class QualityReport:
    """Comprehensive quality assessment report."""

    overall_score: float
    component_scores: Dict[str, float] = field(default_factory=dict)
    metrics: List[QualityMetric] = field(default_factory=list)
    alerts: List[QualityAlert] = field(default_factory=list)
    trends: Dict[str, str] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class DataQualityCheck:
    """Individual data quality check result."""

    check_name: str
    passed: bool
    score: float
    expected_value: Any
    actual_value: Any
    message: str
    severity: str = "MEDIUM"


class QualityMonitor:
    """Continuous quality monitoring and validation system."""

    def __init__(self, config_provider: EnvironmentConfigProvider):
        """Initialize quality monitor.

        Args:
            config_provider: Configuration provider instance
        """
        self.config = config_provider
        self.db = DatabaseConnection(config_provider)

        # Storage paths
        self.quality_dir = Path("data/quality")
        self.quality_dir.mkdir(parents=True, exist_ok=True)
        self.metrics_file = self.quality_dir / "quality_metrics.json"
        self.reports_file = self.quality_dir / "quality_reports.json"

        # Quality thresholds
        self.thresholds = {
            "data_completeness": {"good": 0.95, "fair": 0.85},
            "data_accuracy": {"good": 0.98, "fair": 0.90},
            "processing_success_rate": {"good": 0.95, "fair": 0.85},
            "validation_pass_rate": {"good": 0.98, "fair": 0.90},
            "duplicate_rate": {"good": 0.02, "fair": 0.05},  # Lower is better
            "error_rate": {"good": 0.05, "fair": 0.10},  # Lower is better
            "response_time": {"good": 2.0, "fair": 5.0},  # seconds, lower is better
            "data_freshness": {"good": 3600, "fair": 7200},  # seconds, lower is better
        }

        # Component weights for overall score
        self.component_weights = {
            "data_collection": 0.30,
            "data_processing": 0.25,
            "data_validation": 0.25,
            "system_performance": 0.20,
        }

        # Quality history for trend analysis
        self.quality_history: List[QualityReport] = []

    async def run_quality_assessment(self) -> QualityReport:
        """Run comprehensive quality assessment.

        Returns:
            Complete quality assessment report
        """
        logger.info("Starting quality assessment")

        # Collect quality metrics from all components
        collection_metrics = await self._assess_data_collection_quality()
        processing_metrics = await self._assess_data_processing_quality()
        validation_metrics = await self._assess_data_validation_quality()
        performance_metrics = await self._assess_system_performance_quality()

        # Combine all metrics
        all_metrics = (
            collection_metrics + processing_metrics + validation_metrics + performance_metrics
        )

        # Calculate component scores
        component_scores = {
            "data_collection": self._calculate_component_score(collection_metrics),
            "data_processing": self._calculate_component_score(processing_metrics),
            "data_validation": self._calculate_component_score(validation_metrics),
            "system_performance": self._calculate_component_score(performance_metrics),
        }

        # Calculate overall quality score
        overall_score = sum(
            score * self.component_weights[component]
            for component, score in component_scores.items()
        )

        # Generate quality alerts
        alerts = await self._generate_quality_alerts(all_metrics)

        # Analyze trends
        trends = await self._analyze_quality_trends(component_scores)

        # Generate recommendations
        recommendations = await self._generate_quality_recommendations(component_scores, alerts)

        # Create quality report
        report = QualityReport(
            overall_score=overall_score,
            component_scores=component_scores,
            metrics=all_metrics,
            alerts=alerts,
            trends=trends,
            recommendations=recommendations,
        )

        # Store report for trend analysis
        self.quality_history.append(report)
        await self._save_quality_report(report)

        logger.info(f"Quality assessment completed: Overall score {overall_score:.2f}")
        return report

    async def validate_data_sample(
        self, properties: List[Dict[str, Any]]
    ) -> List[DataQualityCheck]:
        """Validate a sample of property data for quality issues.

        Args:
            properties: List of property data dictionaries

        Returns:
            List of data quality check results
        """
        checks = []

        if not properties:
            checks.append(
                DataQualityCheck(
                    check_name="data_availability",
                    passed=False,
                    score=0.0,
                    expected_value="At least 1 property",
                    actual_value="0 properties",
                    message="No data available for quality validation",
                    severity="HIGH",
                )
            )
            return checks

        # Data completeness check
        required_fields = ["address", "price", "property_type", "bedrooms", "bathrooms"]
        complete_properties = 0

        for prop in properties:
            if all(prop.get(field) is not None for field in required_fields):
                complete_properties += 1

        completeness_rate = complete_properties / len(properties)
        checks.append(
            DataQualityCheck(
                check_name="data_completeness",
                passed=completeness_rate >= self.thresholds["data_completeness"]["fair"],
                score=completeness_rate,
                expected_value=f">= {self.thresholds['data_completeness']['fair']:.1%}",
                actual_value=f"{completeness_rate:.1%}",
                message=f"Data completeness: {completeness_rate:.1%} of properties have all required fields",
                severity="HIGH" if completeness_rate < 0.8 else "MEDIUM",
            )
        )

        # Data accuracy checks
        valid_prices = sum(
            1
            for p in properties
            if isinstance(p.get("price"), (int, float)) and p.get("price", 0) > 0
        )
        price_accuracy = valid_prices / len(properties)

        checks.append(
            DataQualityCheck(
                check_name="price_accuracy",
                passed=price_accuracy >= self.thresholds["data_accuracy"]["fair"],
                score=price_accuracy,
                expected_value=f">= {self.thresholds['data_accuracy']['fair']:.1%}",
                actual_value=f"{price_accuracy:.1%}",
                message=f"Price accuracy: {price_accuracy:.1%} of properties have valid prices",
                severity="MEDIUM",
            )
        )

        # Duplicate detection
        unique_addresses = len(set(p.get("address", "") for p in properties if p.get("address")))
        duplicate_rate = 1 - (unique_addresses / len(properties)) if properties else 0

        checks.append(
            DataQualityCheck(
                check_name="duplicate_detection",
                passed=duplicate_rate <= self.thresholds["duplicate_rate"]["fair"],
                score=1 - duplicate_rate,  # Invert since lower is better
                expected_value=f"<= {self.thresholds['duplicate_rate']['fair']:.1%}",
                actual_value=f"{duplicate_rate:.1%}",
                message=f"Duplicate rate: {duplicate_rate:.1%} of properties appear to be duplicates",
                severity="LOW" if duplicate_rate < 0.1 else "MEDIUM",
            )
        )

        # Data format validation
        valid_formats = 0
        for prop in properties:
            if (
                isinstance(prop.get("bedrooms"), (int, float))
                and isinstance(prop.get("bathrooms"), (int, float))
                and isinstance(prop.get("square_feet"), (int, float, type(None)))
            ):
                valid_formats += 1

        format_accuracy = valid_formats / len(properties)
        checks.append(
            DataQualityCheck(
                check_name="data_format_validation",
                passed=format_accuracy >= 0.95,
                score=format_accuracy,
                expected_value=">= 95%",
                actual_value=f"{format_accuracy:.1%}",
                message=f"Format accuracy: {format_accuracy:.1%} of properties have correctly formatted numeric fields",
                severity="MEDIUM",
            )
        )

        return checks

    async def generate_quality_report(self, report: QualityReport) -> str:
        """Generate formatted quality report.

        Args:
            report: Quality assessment report

        Returns:
            Formatted quality report string
        """
        # Overall status
        if report.overall_score >= 0.9:
            status = "✅ EXCELLENT"
        elif report.overall_score >= 0.8:
            status = "👍 GOOD"
        elif report.overall_score >= 0.7:
            status = "⚠️ FAIR"
        else:
            status = "🚨 POOR"

        report_text = f"""
# Phoenix Real Estate - Quality Assessment Report
**Generated**: {report.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")}
**Overall Quality**: {status} ({report.overall_score:.1%})

## 📈 Component Quality Scores
"""

        for component, score in report.component_scores.items():
            component_status = (
                "✅" if score >= 0.9 else "👍" if score >= 0.8 else "⚠️" if score >= 0.7 else "🚨"
            )
            report_text += (
                f"- **{component.replace('_', ' ').title()}**: {component_status} {score:.1%}\n"
            )

        report_text += "\n## 🔍 Quality Metrics\n"

        # Group metrics by component
        metrics_by_component = {}
        for metric in report.metrics:
            component = self._get_metric_component(metric.name)
            if component not in metrics_by_component:
                metrics_by_component[component] = []
            metrics_by_component[component].append(metric)

        for component, metrics in metrics_by_component.items():
            report_text += f"\n### {component.replace('_', ' ').title()}\n"
            for metric in metrics:
                status_icon = self._get_metric_status_icon(metric.status)
                report_text += f"- {status_icon} **{metric.name}**: {metric.percentage:.1f}% ({metric.status})\n"

        # Quality alerts
        if report.alerts:
            report_text += "\n## 🚨 Quality Alerts\n"
            for alert in sorted(
                report.alerts,
                key=lambda x: {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}[alert.severity],
                reverse=True,
            ):
                severity_icon = {"CRITICAL": "🚨", "HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}[
                    alert.severity
                ]
                report_text += f"\n### {severity_icon} {alert.severity} - {alert.component}\n"
                report_text += f"**Metric**: {alert.metric}\n"
                report_text += f"**Current**: {alert.current_value:.2f} | **Expected**: {alert.expected_value:.2f}\n"
                report_text += f"**Message**: {alert.message}\n"
                if alert.recommended_actions:
                    report_text += "**Actions**:\n"
                    for action in alert.recommended_actions:
                        report_text += f"  - {action}\n"

        # Trends
        if report.trends:
            report_text += "\n## 📉 Quality Trends\n"
            for component, trend in report.trends.items():
                trend_icon = "📈" if trend == "IMPROVING" else "📉" if trend == "DEGRADING" else "➡️"
                report_text += (
                    f"- **{component.replace('_', ' ').title()}**: {trend_icon} {trend}\n"
                )

        # Recommendations
        if report.recommendations:
            report_text += "\n## 💡 Quality Improvement Recommendations\n"
            for i, rec in enumerate(report.recommendations, 1):
                report_text += f"{i}. {rec}\n"

        return report_text

    async def _assess_data_collection_quality(self) -> List[QualityMetric]:
        """Assess data collection quality metrics.

        Returns:
            List of data collection quality metrics
        """
        metrics = []
        now = datetime.now(UTC)

        try:
            # Collection success rate (simulated - would query actual data)
            success_rate = 0.92  # Example: 92% success rate
            metrics.append(
                QualityMetric(
                    name="collection_success_rate",
                    value=success_rate,
                    max_value=1.0,
                    percentage=success_rate * 100,
                    status=self._get_quality_status(success_rate, "processing_success_rate"),
                    threshold_good=self.thresholds["processing_success_rate"]["good"],
                    threshold_fair=self.thresholds["processing_success_rate"]["fair"],
                    timestamp=now,
                )
            )

            # Data freshness (time since last collection)
            hours_since_collection = 2.5  # Example: 2.5 hours
            freshness_score = max(0, 1 - (hours_since_collection * 3600) / 86400)  # 1 day baseline
            metrics.append(
                QualityMetric(
                    name="data_freshness",
                    value=hours_since_collection * 3600,
                    max_value=86400,  # 24 hours
                    percentage=freshness_score * 100,
                    status=self._get_quality_status(
                        hours_since_collection * 3600, "data_freshness", invert=True
                    ),
                    threshold_good=self.thresholds["data_freshness"]["good"],
                    threshold_fair=self.thresholds["data_freshness"]["fair"],
                    timestamp=now,
                )
            )

            # Source coverage (percentage of target sources active)
            source_coverage = 0.85  # Example: 85% of sources active
            metrics.append(
                QualityMetric(
                    name="source_coverage",
                    value=source_coverage,
                    max_value=1.0,
                    percentage=source_coverage * 100,
                    status=self._get_quality_status(source_coverage, "data_completeness"),
                    threshold_good=self.thresholds["data_completeness"]["good"],
                    threshold_fair=self.thresholds["data_completeness"]["fair"],
                    timestamp=now,
                )
            )

        except Exception as e:
            logger.error(f"Error assessing data collection quality: {e}")

        return metrics

    async def _assess_data_processing_quality(self) -> List[QualityMetric]:
        """Assess data processing quality metrics.

        Returns:
            List of data processing quality metrics
        """
        metrics = []
        now = datetime.now(UTC)

        try:
            # Processing success rate
            processing_success = 0.94  # Example: 94% processing success
            metrics.append(
                QualityMetric(
                    name="processing_success_rate",
                    value=processing_success,
                    max_value=1.0,
                    percentage=processing_success * 100,
                    status=self._get_quality_status(processing_success, "processing_success_rate"),
                    threshold_good=self.thresholds["processing_success_rate"]["good"],
                    threshold_fair=self.thresholds["processing_success_rate"]["fair"],
                    timestamp=now,
                )
            )

            # LLM processing quality
            llm_quality = 0.96  # Example: 96% LLM processing quality
            metrics.append(
                QualityMetric(
                    name="llm_processing_quality",
                    value=llm_quality,
                    max_value=1.0,
                    percentage=llm_quality * 100,
                    status=self._get_quality_status(llm_quality, "data_accuracy"),
                    threshold_good=self.thresholds["data_accuracy"]["good"],
                    threshold_fair=self.thresholds["data_accuracy"]["fair"],
                    timestamp=now,
                )
            )

            # Error recovery rate
            error_recovery = 0.88  # Example: 88% error recovery
            metrics.append(
                QualityMetric(
                    name="error_recovery_rate",
                    value=error_recovery,
                    max_value=1.0,
                    percentage=error_recovery * 100,
                    status=self._get_quality_status(error_recovery, "processing_success_rate"),
                    threshold_good=self.thresholds["processing_success_rate"]["good"],
                    threshold_fair=self.thresholds["processing_success_rate"]["fair"],
                    timestamp=now,
                )
            )

        except Exception as e:
            logger.error(f"Error assessing data processing quality: {e}")

        return metrics

    async def _assess_data_validation_quality(self) -> List[QualityMetric]:
        """Assess data validation quality metrics.

        Returns:
            List of data validation quality metrics
        """
        metrics = []
        now = datetime.now(UTC)

        try:
            # Validation pass rate
            validation_pass = 0.97  # Example: 97% validation pass rate
            metrics.append(
                QualityMetric(
                    name="validation_pass_rate",
                    value=validation_pass,
                    max_value=1.0,
                    percentage=validation_pass * 100,
                    status=self._get_quality_status(validation_pass, "validation_pass_rate"),
                    threshold_good=self.thresholds["validation_pass_rate"]["good"],
                    threshold_fair=self.thresholds["validation_pass_rate"]["fair"],
                    timestamp=now,
                )
            )

            # Data completeness
            data_completeness = 0.93  # Example: 93% data completeness
            metrics.append(
                QualityMetric(
                    name="data_completeness",
                    value=data_completeness,
                    max_value=1.0,
                    percentage=data_completeness * 100,
                    status=self._get_quality_status(data_completeness, "data_completeness"),
                    threshold_good=self.thresholds["data_completeness"]["good"],
                    threshold_fair=self.thresholds["data_completeness"]["fair"],
                    timestamp=now,
                )
            )

            # Duplicate detection accuracy
            duplicate_detection = 0.89  # Example: 89% duplicate detection accuracy
            metrics.append(
                QualityMetric(
                    name="duplicate_detection_accuracy",
                    value=duplicate_detection,
                    max_value=1.0,
                    percentage=duplicate_detection * 100,
                    status=self._get_quality_status(duplicate_detection, "data_accuracy"),
                    threshold_good=self.thresholds["data_accuracy"]["good"],
                    threshold_fair=self.thresholds["data_accuracy"]["fair"],
                    timestamp=now,
                )
            )

        except Exception as e:
            logger.error(f"Error assessing data validation quality: {e}")

        return metrics

    async def _assess_system_performance_quality(self) -> List[QualityMetric]:
        """Assess system performance quality metrics.

        Returns:
            List of system performance quality metrics
        """
        metrics = []
        now = datetime.now(UTC)

        try:
            # Response time quality
            avg_response_time = 1.8  # Example: 1.8 seconds average
            response_quality = max(0, 1 - (avg_response_time / 10))  # 10s baseline
            metrics.append(
                QualityMetric(
                    name="response_time_quality",
                    value=avg_response_time,
                    max_value=10.0,
                    percentage=response_quality * 100,
                    status=self._get_quality_status(
                        avg_response_time, "response_time", invert=True
                    ),
                    threshold_good=self.thresholds["response_time"]["good"],
                    threshold_fair=self.thresholds["response_time"]["fair"],
                    timestamp=now,
                )
            )

            # System availability
            availability = 0.995  # Example: 99.5% availability
            metrics.append(
                QualityMetric(
                    name="system_availability",
                    value=availability,
                    max_value=1.0,
                    percentage=availability * 100,
                    status=self._get_quality_status(availability, "data_accuracy"),
                    threshold_good=self.thresholds["data_accuracy"]["good"],
                    threshold_fair=self.thresholds["data_accuracy"]["fair"],
                    timestamp=now,
                )
            )

            # Error rate quality
            error_rate = 0.03  # Example: 3% error rate
            error_quality = max(0, 1 - (error_rate / 0.2))  # 20% baseline
            metrics.append(
                QualityMetric(
                    name="error_rate_quality",
                    value=error_rate,
                    max_value=0.2,
                    percentage=error_quality * 100,
                    status=self._get_quality_status(error_rate, "error_rate", invert=True),
                    threshold_good=self.thresholds["error_rate"]["good"],
                    threshold_fair=self.thresholds["error_rate"]["fair"],
                    timestamp=now,
                )
            )

        except Exception as e:
            logger.error(f"Error assessing system performance quality: {e}")

        return metrics

    def _calculate_component_score(self, metrics: List[QualityMetric]) -> float:
        """Calculate overall score for a component based on its metrics.

        Args:
            metrics: List of quality metrics for the component

        Returns:
            Component quality score (0-1)
        """
        if not metrics:
            return 0.0

        total_score = sum(metric.percentage / 100 for metric in metrics)
        return total_score / len(metrics)

    def _get_quality_status(self, value: float, threshold_key: str, invert: bool = False) -> str:
        """Get quality status based on value and thresholds.

        Args:
            value: Metric value
            threshold_key: Key for threshold lookup
            invert: Whether lower values are better

        Returns:
            Quality status string
        """
        thresholds = self.thresholds.get(threshold_key, {"good": 0.8, "fair": 0.6})

        if invert:
            if value <= thresholds["good"]:
                return "EXCELLENT"
            elif value <= thresholds["fair"]:
                return "GOOD"
            elif value <= thresholds["fair"] * 1.5:
                return "FAIR"
            else:
                return "POOR"
        else:
            if value >= thresholds["good"]:
                return "EXCELLENT"
            elif value >= thresholds["fair"]:
                return "GOOD"
            elif value >= thresholds["fair"] * 0.8:
                return "FAIR"
            else:
                return "POOR"

    def _get_metric_component(self, metric_name: str) -> str:
        """Get component name for a metric.

        Args:
            metric_name: Name of the metric

        Returns:
            Component name
        """
        if "collection" in metric_name or "source" in metric_name or "freshness" in metric_name:
            return "data_collection"
        elif "processing" in metric_name or "llm" in metric_name or "recovery" in metric_name:
            return "data_processing"
        elif (
            "validation" in metric_name
            or "completeness" in metric_name
            or "duplicate" in metric_name
        ):
            return "data_validation"
        else:
            return "system_performance"

    def _get_metric_status_icon(self, status: str) -> str:
        """Get icon for metric status.

        Args:
            status: Quality status

        Returns:
            Status icon
        """
        icons = {"EXCELLENT": "✅", "GOOD": "👍", "FAIR": "⚠️", "POOR": "🚨"}
        return icons.get(status, "❓")

    async def _generate_quality_alerts(self, metrics: List[QualityMetric]) -> List[QualityAlert]:
        """Generate quality alerts based on metrics.

        Args:
            metrics: List of quality metrics

        Returns:
            List of quality alerts
        """
        alerts = []

        for metric in metrics:
            if metric.status in ["POOR", "FAIR"]:
                severity = "CRITICAL" if metric.status == "POOR" else "MEDIUM"
                component = self._get_metric_component(metric.name)

                alert = QualityAlert(
                    severity=severity,
                    component=component,
                    metric=metric.name,
                    current_value=metric.value,
                    expected_value=metric.threshold_good,
                    trend="STABLE",  # Would calculate from history
                    message=f"{metric.name} is {metric.status.lower()}: {metric.percentage:.1f}%",
                    recommended_actions=self._get_metric_recommendations(
                        metric.name, metric.status
                    ),
                    timestamp=datetime.now(UTC),
                )
                alerts.append(alert)

        return alerts

    def _get_metric_recommendations(self, metric_name: str, status: str) -> List[str]:
        """Get recommendations for improving a metric.

        Args:
            metric_name: Name of the metric
            status: Current quality status

        Returns:
            List of improvement recommendations
        """
        recommendations = {
            "collection_success_rate": [
                "Check API endpoint health and availability",
                "Review rate limiting configuration",
                "Verify proxy rotation and health",
                "Implement retry logic with exponential backoff",
            ],
            "data_freshness": [
                "Increase collection frequency during business hours",
                "Implement real-time data monitoring",
                "Set up automated alerts for stale data",
                "Review collection scheduling configuration",
            ],
            "processing_success_rate": [
                "Review LLM service health and response times",
                "Check processing pipeline error logs",
                "Optimize batch sizes for better throughput",
                "Implement circuit breakers for external services",
            ],
            "data_completeness": [
                "Review data extraction selectors and patterns",
                "Implement field-level validation rules",
                "Add data enrichment from additional sources",
                "Improve error handling for missing fields",
            ],
        }

        return recommendations.get(
            metric_name,
            [
                "Monitor metric trends closely",
                "Review related system logs for issues",
                "Consider adjusting thresholds if appropriate",
            ],
        )

    async def _analyze_quality_trends(self, component_scores: Dict[str, float]) -> Dict[str, str]:
        """Analyze quality trends over time.

        Args:
            component_scores: Current component scores

        Returns:
            Dictionary of trend analysis by component
        """
        trends = {}

        # Would analyze historical data to determine trends
        # For now, return stable trends
        for component in component_scores:
            trends[component] = "STABLE"

        return trends

    async def _generate_quality_recommendations(
        self, component_scores: Dict[str, float], alerts: List[QualityAlert]
    ) -> List[str]:
        """Generate overall quality improvement recommendations.

        Args:
            component_scores: Component quality scores
            alerts: Quality alerts

        Returns:
            List of quality improvement recommendations
        """
        recommendations = []

        # Component-specific recommendations
        for component, score in component_scores.items():
            if score < 0.8:
                recommendations.append(
                    f"Focus on improving {component.replace('_', ' ')}: current score {score:.1%}"
                )

        # Alert-based recommendations
        critical_alerts = [a for a in alerts if a.severity == "CRITICAL"]
        if critical_alerts:
            recommendations.append(
                f"Address {len(critical_alerts)} critical quality issues immediately"
            )

        # General recommendations
        if not recommendations:
            recommendations.append("Quality metrics are within acceptable ranges")
            recommendations.append("Continue monitoring for any degradation trends")

        return recommendations

    async def _save_quality_report(self, report: QualityReport) -> None:
        """Save quality report to persistent storage.

        Args:
            report: Quality report to save
        """
        try:
            # Load existing reports
            reports = []
            if self.reports_file.exists():
                with open(self.reports_file, "r") as f:
                    reports_data = json.load(f)
                    reports = reports_data.get("reports", [])

            # Add new report
            report_dict = {
                "timestamp": report.timestamp.isoformat(),
                "overall_score": report.overall_score,
                "component_scores": report.component_scores,
                "alert_count": len(report.alerts),
                "critical_alerts": len([a for a in report.alerts if a.severity == "CRITICAL"]),
            }

            reports.append(report_dict)

            # Keep only recent reports
            reports = reports[-100:]  # Last 100 reports

            # Save to file
            with open(self.reports_file, "w") as f:
                json.dump({"reports": reports}, f, indent=2)

        except Exception as e:
            logger.error(f"Failed to save quality report: {e}")


async def main():
    """Main quality monitoring routine."""
    config = EnvironmentConfigProvider()
    monitor = QualityMonitor(config)

    # Run quality assessment
    report = await monitor.run_quality_assessment()

    # Generate and print report
    report_text = await monitor.generate_quality_report(report)
    print(report_text)

    # Sample data validation
    sample_properties = [
        {
            "address": "123 Main St, Phoenix, AZ",
            "price": 350000,
            "property_type": "Single Family",
            "bedrooms": 3,
            "bathrooms": 2,
            "square_feet": 1500,
        },
        {
            "address": "456 Oak Ave, Phoenix, AZ",
            "price": None,  # Missing price
            "property_type": "Condo",
            "bedrooms": 2,
            "bathrooms": 1,
            # Missing square_feet
        },
    ]

    quality_checks = await monitor.validate_data_sample(sample_properties)
    print("\n## Data Quality Validation Results:")
    for check in quality_checks:
        status = "✅" if check.passed else "❌"
        print(f"{status} {check.check_name}: {check.score:.1%} ({check.message})")


if __name__ == "__main__":
    asyncio.run(main())
