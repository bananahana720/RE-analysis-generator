"""
Phoenix Real Estate System - Epic 4 Quality Assurance Interfaces

This module defines the interfaces and contracts for comprehensive quality assurance
across the entire Phoenix Real Estate system. These interfaces provide testing,
monitoring, validation, and compliance capabilities that span all epics while
building on the foundation services and monitoring the collection, automation layers.

Key Design Principles:
- Observer pattern for system-wide quality monitoring
- Chain of responsibility for validation pipeline
- Strategy pattern for different testing approaches
- Template method for quality assessment workflows
- Comprehensive integration with all epic interfaces
"""

from abc import ABC, abstractmethod
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Protocol,
    runtime_checkable,
    Awaitable,
    Callable,
    Tuple,
)
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field

# Import all epic interfaces for comprehensive monitoring
from .epic_1_foundation_interfaces import BasePhoenixException, HealthCheckResult

# ==============================================================================
# Core Types and Enumerations
# ==============================================================================


class QualityLevel(Enum):
    """Quality assessment levels."""

    EXCELLENT = "excellent"  # >95% score
    GOOD = "good"  # 85-95% score
    FAIR = "fair"  # 70-85% score
    POOR = "poor"  # 50-70% score
    CRITICAL = "critical"  # <50% score


class TestType(Enum):
    """Types of quality tests."""

    UNIT = "unit"  # Unit testing
    INTEGRATION = "integration"  # Integration testing
    END_TO_END = "end_to_end"  # E2E workflow testing
    PERFORMANCE = "performance"  # Performance testing
    SECURITY = "security"  # Security testing
    COMPLIANCE = "compliance"  # Legal compliance testing
    DATA_QUALITY = "data_quality"  # Data quality validation


class AlertSeverity(Enum):
    """Alert severity levels."""

    INFO = "info"  # Informational
    WARNING = "warning"  # Warning condition
    ERROR = "error"  # Error condition
    CRITICAL = "critical"  # Critical system issue


class ComplianceRule(Enum):
    """Compliance validation rules."""

    RATE_LIMITING = "rate_limiting"  # API rate limit compliance
    ROBOTS_TXT = "robots_txt"  # robots.txt adherence
    PERSONAL_USE = "personal_use"  # Personal use only restriction
    DATA_PRIVACY = "data_privacy"  # No PII collection
    BUDGET_COMPLIANCE = "budget_compliance"  # Budget constraint adherence


@dataclass
class QualityReport:
    """Comprehensive quality assessment report."""

    epic: str
    component: str
    timestamp: datetime
    overall_score: float
    quality_level: QualityLevel
    test_results: Dict[str, Any] = field(default_factory=dict)
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    compliance_status: Dict[str, bool] = field(default_factory=dict)
    issues_found: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    trends: Dict[str, float] = field(default_factory=dict)


@dataclass
class TestResult:
    """Individual test execution result."""

    test_name: str
    test_type: TestType
    passed: bool
    score: float
    execution_time_ms: float
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class QualityAlert:
    """Quality monitoring alert."""

    alert_id: str
    severity: AlertSeverity
    epic: str
    component: str
    message: str
    context: Dict[str, Any]
    timestamp: datetime
    resolved: bool = False
    resolution_time: Optional[datetime] = None


# ==============================================================================
# Quality Assessment and Testing Interfaces
# ==============================================================================


@runtime_checkable
class QualityAssessor(Protocol):
    """
    Interface for quality assessment across system components.

    Provides comprehensive quality evaluation capabilities that span
    all epics and provide actionable insights for system improvement.
    """

    async def assess_component_quality(self, epic: str, component: str) -> QualityReport:
        """
        Assess quality of specific component.

        Args:
            epic: Epic name (foundation, collection, automation, quality)
            component: Component name within epic

        Returns:
            Comprehensive quality report for component
        """
        ...

    async def assess_system_quality(self) -> Dict[str, QualityReport]:
        """
        Assess quality across entire system.

        Returns:
            Dictionary mapping epic names to quality reports
        """
        ...

    async def assess_integration_quality(self) -> QualityReport:
        """
        Assess quality of cross-epic integration.

        Returns:
            Quality report for system integration
        """
        ...

    async def get_quality_trends(
        self, start_date: datetime, end_date: datetime
    ) -> Dict[str, List[float]]:
        """
        Get quality score trends over time period.

        Args:
            start_date: Start of analysis period
            end_date: End of analysis period

        Returns:
            Dictionary mapping metrics to time series data
        """
        ...


@runtime_checkable
class TestExecutor(Protocol):
    """
    Interface for executing different types of quality tests.

    Provides standardized test execution across unit, integration,
    performance, security, and compliance testing scenarios.
    """

    async def execute_test_suite(
        self, test_type: TestType, target_component: Optional[str] = None
    ) -> List[TestResult]:
        """
        Execute test suite of specified type.

        Args:
            test_type: Type of tests to execute
            target_component: Optional specific component to test

        Returns:
            List of test results
        """
        ...

    async def execute_single_test(self, test_name: str, test_config: Dict[str, Any]) -> TestResult:
        """
        Execute single test with configuration.

        Args:
            test_name: Name of test to execute
            test_config: Test configuration parameters

        Returns:
            Test execution result
        """
        ...

    async def get_test_coverage(self, epic: str) -> Dict[str, float]:
        """
        Get test coverage metrics for epic.

        Args:
            epic: Epic to analyze coverage for

        Returns:
            Coverage metrics by test type
        """
        ...

    async def schedule_recurring_tests(self, test_schedule: Dict[str, str]) -> bool:
        """
        Schedule recurring test execution.

        Args:
            test_schedule: Mapping of test names to cron schedules

        Returns:
            True if scheduling successful
        """
        ...


# ==============================================================================
# Monitoring and Observability Interfaces
# ==============================================================================


@runtime_checkable
class QualityMonitor(Protocol):
    """
    Interface for real-time quality monitoring.

    Provides continuous monitoring of system quality metrics with
    alerting capabilities for proactive issue detection and resolution.
    """

    async def start_monitoring(self) -> None:
        """Start continuous quality monitoring."""
        ...

    async def stop_monitoring(self) -> None:
        """Stop quality monitoring gracefully."""
        ...

    async def record_quality_event(
        self, epic: str, component: str, event_type: str, event_data: Dict[str, Any]
    ) -> None:
        """
        Record quality-related event for monitoring.

        Args:
            epic: Epic where event occurred
            component: Component where event occurred
            event_type: Type of quality event
            event_data: Event-specific data
        """
        ...

    async def get_current_quality_status(self) -> Dict[str, Any]:
        """
        Get current system-wide quality status.

        Returns:
            Current quality metrics and status across all epics
        """
        ...

    async def get_quality_alerts(
        self, severity: Optional[AlertSeverity] = None, unresolved_only: bool = True
    ) -> List[QualityAlert]:
        """
        Get quality alerts with optional filtering.

        Args:
            severity: Optional severity filter
            unresolved_only: Whether to return only unresolved alerts

        Returns:
            List of quality alerts
        """
        ...

    async def acknowledge_alert(self, alert_id: str, resolution: str) -> bool:
        """
        Acknowledge and resolve quality alert.

        Args:
            alert_id: ID of alert to acknowledge
            resolution: Resolution description

        Returns:
            True if acknowledgment successful
        """
        ...


@runtime_checkable
class SystemHealthMonitor(Protocol):
    """
    Interface for comprehensive system health monitoring.

    Monitors health across all epics and provides integrated health
    assessment with dependency tracking and failure impact analysis.
    """

    async def check_system_health(self) -> Dict[str, HealthCheckResult]:
        """
        Check health of all system components.

        Returns:
            Dictionary mapping component names to health results
        """
        ...

    async def check_epic_health(self, epic: str) -> HealthCheckResult:
        """
        Check health of specific epic.

        Args:
            epic: Epic to check health for

        Returns:
            Health check result for epic
        """
        ...

    async def check_integration_health(self) -> HealthCheckResult:
        """
        Check health of cross-epic integrations.

        Returns:
            Health check result for system integration
        """
        ...

    async def get_health_trends(
        self, component: str, hours: int = 24
    ) -> List[Tuple[datetime, bool]]:
        """
        Get health trends for component over time.

        Args:
            component: Component to get trends for
            hours: Number of hours to look back

        Returns:
            List of (timestamp, healthy) tuples
        """
        ...

    async def register_health_check(
        self, component: str, check_function: Callable[[], Awaitable[HealthCheckResult]]
    ) -> None:
        """
        Register custom health check for component.

        Args:
            component: Component name
            check_function: Async function returning health result
        """
        ...


# ==============================================================================
# Compliance and Validation Interfaces
# ==============================================================================


@runtime_checkable
class ComplianceValidator(Protocol):
    """
    Interface for legal and technical compliance validation.

    Ensures system operation complies with legal requirements,
    rate limiting constraints, and ethical usage guidelines.
    """

    async def validate_rate_limit_compliance(self, source: str, time_period: timedelta) -> bool:
        """
        Validate rate limit compliance for data source.

        Args:
            source: Data source to check
            time_period: Time period to analyze

        Returns:
            True if within rate limits
        """
        ...

    async def validate_robots_txt_compliance(self, url: str) -> bool:
        """
        Validate robots.txt compliance for web scraping.

        Args:
            url: URL to check robots.txt compliance for

        Returns:
            True if compliant with robots.txt
        """
        ...

    async def validate_personal_use_restriction(self) -> bool:
        """
        Validate system is properly marked for personal use only.

        Returns:
            True if personal use restrictions are properly implemented
        """
        ...

    async def validate_data_privacy_compliance(self) -> bool:
        """
        Validate no PII or sensitive data is collected or stored.

        Returns:
            True if data privacy compliant
        """
        ...

    async def validate_budget_compliance(self) -> Dict[str, Any]:
        """
        Validate system operation within budget constraints.

        Returns:
            Budget compliance status and usage metrics
        """
        ...

    async def generate_compliance_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive compliance validation report.

        Returns:
            Compliance report covering all validation areas
        """
        ...


@runtime_checkable
class SecurityValidator(Protocol):
    """
    Interface for security validation and audit.

    Provides security assessment capabilities including vulnerability
    scanning, configuration validation, and security best practices audit.
    """

    async def scan_for_vulnerabilities(self) -> List[Dict[str, Any]]:
        """
        Scan system for security vulnerabilities.

        Returns:
            List of identified vulnerabilities with details
        """
        ...

    async def validate_credential_security(self) -> bool:
        """
        Validate secure handling of credentials and secrets.

        Returns:
            True if credentials are handled securely
        """
        ...

    async def validate_network_security(self) -> bool:
        """
        Validate network communication security.

        Returns:
            True if network communications are secure
        """
        ...

    async def audit_access_controls(self) -> Dict[str, Any]:
        """
        Audit system access controls and permissions.

        Returns:
            Access control audit results
        """
        ...

    async def generate_security_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive security assessment report.

        Returns:
            Security report with findings and recommendations
        """
        ...


# ==============================================================================
# Performance and Optimization Interfaces
# ==============================================================================


@runtime_checkable
class PerformanceMonitor(Protocol):
    """
    Interface for system performance monitoring and optimization.

    Tracks performance metrics across all epics and provides
    optimization recommendations based on usage patterns and benchmarks.
    """

    async def measure_epic_performance(self, epic: str) -> Dict[str, float]:
        """
        Measure performance metrics for specific epic.

        Args:
            epic: Epic to measure performance for

        Returns:
            Performance metrics dictionary
        """
        ...

    async def measure_system_performance(self) -> Dict[str, Any]:
        """
        Measure overall system performance.

        Returns:
            System-wide performance metrics
        """
        ...

    async def benchmark_against_targets(self) -> Dict[str, bool]:
        """
        Compare current performance against defined targets.

        Returns:
            Dictionary of metrics and whether they meet targets
        """
        ...

    async def identify_performance_bottlenecks(self) -> List[Dict[str, Any]]:
        """
        Identify system performance bottlenecks.

        Returns:
            List of identified bottlenecks with details
        """
        ...

    async def get_optimization_recommendations(self) -> List[str]:
        """
        Get performance optimization recommendations.

        Returns:
            List of actionable optimization recommendations
        """
        ...

    async def track_resource_usage(self) -> Dict[str, Any]:
        """
        Track system resource usage patterns.

        Returns:
            Resource usage metrics and trends
        """
        ...


# ==============================================================================
# Quality Orchestration and Integration Interfaces
# ==============================================================================


class QualityAssuranceEngine(ABC):
    """
    Central quality assurance orchestrator for all system components.

    Coordinates quality assessment, monitoring, testing, and compliance
    validation across all four epics to provide comprehensive system
    quality oversight.
    """

    def __init__(
        self,
        foundation_provider: "Epic1ServiceProvider",
        collection_provider: "Epic2ServiceProvider",
        automation_provider: "Epic3ServiceProvider",
    ) -> None:
        self.foundation = foundation_provider
        self.collection = collection_provider
        self.automation = automation_provider
        self.logger = foundation_provider.get_logger("quality.engine")

        # Initialize quality components
        self._quality_assessor: Optional[QualityAssessor] = None
        self._test_executor: Optional[TestExecutor] = None
        self._quality_monitor: Optional[QualityMonitor] = None
        self._compliance_validator: Optional[ComplianceValidator] = None
        self._performance_monitor: Optional[PerformanceMonitor] = None

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize quality assurance engine with all components."""
        pass

    @abstractmethod
    async def run_comprehensive_quality_assessment(self) -> Dict[str, QualityReport]:
        """
        Execute comprehensive quality assessment across all epics.

        Returns:
            Quality reports for each epic and integration points
        """
        pass

    @abstractmethod
    async def monitor_system_quality(self) -> None:
        """Start continuous system quality monitoring."""
        pass

    @abstractmethod
    async def validate_system_compliance(self) -> Dict[str, bool]:
        """
        Validate system compliance with all requirements.

        Returns:
            Compliance status for each validation area
        """
        pass

    @abstractmethod
    async def generate_quality_dashboard(self) -> Dict[str, Any]:
        """
        Generate real-time quality dashboard data.

        Returns:
            Dashboard data for quality visualization
        """
        pass


# ==============================================================================
# Epic-Specific Quality Monitoring
# ==============================================================================


@runtime_checkable
class FoundationQualityMonitor(Protocol):
    """Quality monitoring specific to Epic 1 foundation components."""

    async def monitor_database_performance(self) -> Dict[str, float]:
        """Monitor database connection and query performance."""
        ...

    async def monitor_configuration_health(self) -> bool:
        """Monitor configuration loading and validation health."""
        ...

    async def monitor_logging_performance(self) -> Dict[str, float]:
        """Monitor logging system performance and throughput."""
        ...

    async def validate_foundation_contracts(self) -> List[str]:
        """Validate Epic 1 interface contracts and implementations."""
        ...


@runtime_checkable
class CollectionQualityMonitor(Protocol):
    """Quality monitoring specific to Epic 2 collection components."""

    async def monitor_collection_success_rates(self) -> Dict[str, float]:
        """Monitor success rates for each data collector."""
        ...

    async def monitor_data_quality_scores(self) -> Dict[str, float]:
        """Monitor data quality scores across all sources."""
        ...

    async def monitor_rate_limit_compliance(self) -> Dict[str, bool]:
        """Monitor rate limit compliance for all sources."""
        ...

    async def validate_collection_contracts(self) -> List[str]:
        """Validate Epic 2 collection interface contracts."""
        ...


@runtime_checkable
class AutomationQualityMonitor(Protocol):
    """Quality monitoring specific to Epic 3 automation components."""

    async def monitor_workflow_success_rates(self) -> Dict[str, float]:
        """Monitor success rates for automated workflows."""
        ...

    async def monitor_orchestration_performance(self) -> Dict[str, float]:
        """Monitor orchestration engine performance metrics."""
        ...

    async def monitor_deployment_health(self) -> Dict[str, bool]:
        """Monitor health of deployment environments."""
        ...

    async def validate_automation_contracts(self) -> List[str]:
        """Validate Epic 3 automation interface contracts."""
        ...


# ==============================================================================
# Exception Classes for Quality Assurance
# ==============================================================================


class QualityAssuranceError(BasePhoenixException):
    """Quality monitoring and validation errors."""

    def __init__(self, message: str, *, quality_check: Optional[str] = None, **kwargs):
        context = kwargs.get("context", {})
        if quality_check:
            context["quality_check"] = quality_check

        super().__init__(message, context=context, **kwargs)


class ValidationError(BasePhoenixException):
    """Data or system validation errors."""

    def __init__(
        self,
        message: str,
        *,
        validator: Optional[str] = None,
        validation_errors: Optional[List[str]] = None,
        **kwargs,
    ):
        context = kwargs.get("context", {})
        if validator:
            context["validator"] = validator
        if validation_errors:
            context["validation_errors"] = validation_errors

        super().__init__(message, context=context, **kwargs)


class ComplianceError(QualityAssuranceError):
    """Compliance validation errors."""

    def __init__(self, message: str, *, compliance_rule: Optional[str] = None, **kwargs):
        context = kwargs.get("context", {})
        if compliance_rule:
            context["compliance_rule"] = compliance_rule

        # Compliance errors are typically not recoverable
        kwargs.setdefault("recoverable", False)

        super().__init__(message, context=context, **kwargs)


class PerformanceError(QualityAssuranceError):
    """Performance monitoring and validation errors."""

    def __init__(
        self,
        message: str,
        *,
        metric: Optional[str] = None,
        threshold: Optional[float] = None,
        actual_value: Optional[float] = None,
        **kwargs,
    ):
        context = kwargs.get("context", {})
        if metric:
            context["metric"] = metric
        if threshold:
            context["threshold"] = threshold
        if actual_value:
            context["actual_value"] = actual_value

        super().__init__(message, context=context, **kwargs)


# ==============================================================================
# Integration Contracts for System Integration
# ==============================================================================


class Epic4ServiceProvider(ABC):
    """
    Service provider interface for Epic 4 quality assurance services.

    This interface defines the comprehensive quality services provided
    across the entire Phoenix Real Estate system for external monitoring
    and management tools.
    """

    @property
    @abstractmethod
    def quality_engine(self) -> QualityAssuranceEngine:
        """Quality assurance engine instance."""
        pass

    @property
    @abstractmethod
    def system_health_monitor(self) -> SystemHealthMonitor:
        """System health monitoring interface."""
        pass

    @property
    @abstractmethod
    def compliance_validator(self) -> ComplianceValidator:
        """Compliance validation interface."""
        pass

    @property
    @abstractmethod
    def performance_monitor(self) -> PerformanceMonitor:
        """Performance monitoring interface."""
        pass

    @abstractmethod
    async def get_system_quality_status(self) -> Dict[str, Any]:
        """Get comprehensive system quality status."""
        pass

    @abstractmethod
    async def execute_quality_audit(self) -> Dict[str, QualityReport]:
        """Execute comprehensive quality audit across all epics."""
        pass

    @abstractmethod
    async def generate_quality_insights(self) -> Dict[str, Any]:
        """Generate quality insights and recommendations."""
        pass


# ==============================================================================
# Usage Examples and Documentation
# ==============================================================================

"""
Example Implementation of Complete Quality Assessment:

```python
class PhoenixQualityAssuranceEngine(QualityAssuranceEngine):
    async def run_comprehensive_quality_assessment(self) -> Dict[str, QualityReport]:
        quality_reports = {}
        
        # Epic 1: Foundation Quality Assessment
        foundation_report = await self._assess_foundation_quality()
        quality_reports['foundation'] = foundation_report
        
        # Epic 2: Collection Quality Assessment  
        collection_report = await self._assess_collection_quality()
        quality_reports['collection'] = collection_report
        
        # Epic 3: Automation Quality Assessment
        automation_report = await self._assess_automation_quality()
        quality_reports['automation'] = automation_report
        
        # Cross-Epic Integration Assessment
        integration_report = await self._assess_integration_quality()
        quality_reports['integration'] = integration_report
        
        # Generate overall system quality score
        overall_score = self._calculate_overall_quality_score(quality_reports)
        quality_reports['overall'] = QualityReport(
            epic='system',
            component='overall',
            timestamp=datetime.now(UTC),
            overall_score=overall_score,
            quality_level=self._determine_quality_level(overall_score)
        )
        
        return quality_reports
    
    async def _assess_foundation_quality(self) -> QualityReport:
        # Database performance check
        db_health = await self.foundation.repository.health_check()
        
        # Configuration validation
        config_valid = await self._validate_all_configuration()
        
        # Logging performance measurement
        logging_metrics = await self._measure_logging_performance()
        
        # Calculate foundation quality score
        foundation_score = self._calculate_foundation_score(
            db_health, config_valid, logging_metrics
        )
        
        return QualityReport(
            epic='foundation',
            component='all',
            timestamp=datetime.now(UTC),
            overall_score=foundation_score,
            quality_level=self._determine_quality_level(foundation_score),
            performance_metrics=logging_metrics,
            compliance_status={'database_health': db_health.healthy}
        )
    
    async def _assess_collection_quality(self) -> QualityReport:
        # Collection success rates
        collection_metrics = await self.collection.collection_monitor.get_collection_summary(
            datetime.now(UTC) - timedelta(days=1),
            datetime.now(UTC)
        )
        
        # Data quality validation
        quality_score = collection_metrics.get('avg_quality_score', 0.0)
        
        # Rate limit compliance check
        rate_limit_compliance = await self._check_rate_limit_compliance()
        
        return QualityReport(
            epic='collection',
            component='all',
            timestamp=datetime.now(UTC),
            overall_score=quality_score,
            quality_level=self._determine_quality_level(quality_score),
            performance_metrics=collection_metrics,
            compliance_status={'rate_limits': rate_limit_compliance}
        )
    
    async def _assess_automation_quality(self) -> QualityReport:
        # Workflow success rates
        workflow_history = await self.automation.get_workflow_history(
            datetime.now(UTC) - timedelta(days=7),
            datetime.now(UTC)
        )
        
        success_rate = sum(
            1 for w in workflow_history 
            if w.status == WorkflowStatus.COMPLETED
        ) / len(workflow_history) if workflow_history else 0
        
        # Orchestration engine health
        engine_health = await self.automation.orchestration_engine.health_check()
        
        automation_score = (success_rate + (1.0 if engine_health.healthy else 0.0)) / 2
        
        return QualityReport(
            epic='automation',
            component='all',
            timestamp=datetime.now(UTC),
            overall_score=automation_score,
            quality_level=self._determine_quality_level(automation_score),
            performance_metrics={'workflow_success_rate': success_rate},
            compliance_status={'engine_health': engine_health.healthy}
        )
    
    async def _assess_integration_quality(self) -> QualityReport:
        # End-to-end workflow test
        integration_test_result = await self._run_integration_test()
        
        # Interface contract validation
        contract_validation = await self._validate_all_contracts()
        
        # Cross-epic communication test
        communication_test = await self._test_cross_epic_communication()
        
        integration_score = (
            integration_test_result.score + 
            contract_validation + 
            communication_test
        ) / 3
        
        return QualityReport(
            epic='integration',
            component='cross_epic',
            timestamp=datetime.now(UTC),
            overall_score=integration_score,
            quality_level=self._determine_quality_level(integration_score),
            test_results={'integration_test': integration_test_result.__dict__}
        )

# Example Usage for Real-time Quality Monitoring:
class RealTimeQualityMonitor:
    def __init__(self, quality_engine: QualityAssuranceEngine):
        self.quality_engine = quality_engine
        self.logger = quality_engine.logger
        self.alerts: List[QualityAlert] = []
        
    async def start_monitoring(self):
        # Start continuous monitoring loop
        while True:
            try:
                # Check system health every 5 minutes
                health_status = await self.quality_engine.check_system_health()
                
                # Generate alerts for unhealthy components
                for component, health in health_status.items():
                    if not health.healthy:
                        alert = QualityAlert(
                            alert_id=f"health_{component}_{datetime.now(UTC).timestamp()}",
                            severity=AlertSeverity.ERROR,
                            epic=self._determine_epic_from_component(component),
                            component=component,
                            message=f"Component {component} is unhealthy: {health.message}",
                            context=health.__dict__,
                            timestamp=datetime.now(UTC)
                        )
                        self.alerts.append(alert)
                        await self._send_alert(alert)
                
                # Sleep for 5 minutes
                await asyncio.sleep(300)
                
            except Exception as e:
                self.logger.error(f"Quality monitoring error: {e}")
                await asyncio.sleep(60)  # Shorter retry interval on error
```
"""
