# Epic 3: Automation & Orchestration

## Executive Summary

### Purpose
Create a comprehensive automation and orchestration layer that seamlessly integrates Epic 1's foundation infrastructure and Epic 2's data collection engine to provide daily automated data collection, deployment management, and operational monitoring. This epic transforms the manual collection system into a fully automated, monitored, and deployable solution within strict budget constraints.

### Scope
- GitHub Actions workflows for daily automation and CI/CD
- Docker containerization using Epic 1's configuration patterns
- Orchestration engine that coordinates Epic 2's data collectors
- Monitoring and alerting extending Epic 1's framework
- Report generation using Epic 1's PropertyRepository
- Deployment strategies for development and production environments

### Dependencies
**Epic 1: Foundation Infrastructure** (REQUIRED)
- `phoenix_real_estate.foundation.config.base.ConfigProvider`
- `phoenix_real_estate.foundation.database.repositories.PropertyRepository`
- `phoenix_real_estate.foundation.logging.factory.get_logger`
- `phoenix_real_estate.foundation.monitoring.metrics.MetricsCollector`
- `phoenix_real_estate.foundation.utils.exceptions.*`

**Epic 2: Data Collection Engine** (REQUIRED)  
- `phoenix_real_estate.collectors.base.DataCollector`
- `phoenix_real_estate.collectors.maricopa.MaricopaAPICollector`
- `phoenix_real_estate.collectors.phoenix_mls.PhoenixMLSCollector`
- `phoenix_real_estate.collectors.combined.CombinedCollector`
- `phoenix_real_estate.collectors.monitoring.CollectionMetrics`

### Budget Alignment
- GitHub Actions: $0/month (2000 minutes free tier, ~200 minutes/month usage)
- Docker Hub: $0/month (1 free private repository)
- MongoDB Atlas: $0/month (Epic 1's free tier)
- Monitoring/Alerting: $0/month (using Epic 1's logging framework)
- Total: $0/month (Epic 2's $5/month proxy cost maintained)

## Technical Architecture

### Core Design Patterns

#### Command Pattern for Workflow Execution
```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from phoenix_real_estate.foundation.config.base import ConfigProvider
from phoenix_real_estate.foundation.logging.factory import get_logger
from phoenix_real_estate.foundation.database.repositories import PropertyRepository

class WorkflowCommand(ABC):
    """Base command for workflow operations."""
    
    def __init__(
        self, 
        config: ConfigProvider,
        repository: PropertyRepository,
        logger_name: str
    ) -> None:
        self.config = config
        self.repository = repository
        self.logger = get_logger(logger_name)
        self._metrics: Dict[str, Any] = {}
    
    @abstractmethod
    async def execute(self) -> bool:
        """Execute the workflow command."""
        pass
    
    @abstractmethod
    async def rollback(self) -> bool:
        """Rollback changes if execution fails."""
        pass
    
    @abstractmethod
    def get_command_name(self) -> str:
        """Return human-readable command name."""
        pass
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Return execution metrics."""
        return self._metrics.copy()

class DailyCollectionCommand(WorkflowCommand):
    """Command for daily data collection workflow."""
    
    def __init__(
        self,
        config: ConfigProvider,
        repository: PropertyRepository,
        collectors: List[DataCollector]
    ) -> None:
        super().__init__(config, repository, "workflow.daily_collection")
        self.collectors = collectors
        self._start_time: Optional[datetime] = None
    
    async def execute(self) -> bool:
        """Execute daily collection across all configured collectors."""
        try:
            self._start_time = datetime.utcnow()
            
            # Use Epic 1's configuration for target ZIP codes
            target_zips = self.config.get_required("TARGET_ZIP_CODES").split(",")
            total_collected = 0
            
            self.logger.info(
                "Starting daily collection workflow",
                extra={
                    "command": self.get_command_name(),
                    "target_zip_count": len(target_zips),
                    "collector_count": len(self.collectors)
                }
            )
            
            # Orchestrate Epic 2's collectors
            for collector in self.collectors:
                collector_total = 0
                
                for zipcode in target_zips:
                    try:
                        # Use Epic 2's collection interface
                        count = await self._collect_and_store(collector, zipcode)
                        collector_total += count
                        
                    except Exception as e:
                        self.logger.error(
                            "Collection failed for zipcode",
                            extra={
                                "collector": collector.get_source_name(),
                                "zipcode": zipcode,
                                "error": str(e)
                            }
                        )
                        # Continue with other ZIP codes
                        continue
                
                total_collected += collector_total
                self.logger.info(
                    "Collector completed",
                    extra={
                        "collector": collector.get_source_name(),
                        "properties_collected": collector_total
                    }
                )
            
            duration = (datetime.utcnow() - self._start_time).total_seconds()
            self._metrics = {
                "total_properties": total_collected,
                "duration_seconds": duration,
                "zip_codes_processed": len(target_zips),
                "collectors_used": len(self.collectors),
                "properties_per_minute": (total_collected / max(duration / 60, 0.1))
            }
            
            self.logger.info(
                "Daily collection completed successfully",
                extra={
                    "command": self.get_command_name(),
                    **self._metrics
                }
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                "Daily collection workflow failed",
                extra={
                    "command": self.get_command_name(),
                    "error": str(e)
                }
            )
            await self.rollback()
            raise WorkflowExecutionError(
                "Daily collection workflow failed",
                context={"command": self.get_command_name()},
                cause=e
            ) from e
    
    async def _collect_and_store(self, collector: DataCollector, zipcode: str) -> int:
        """Collect properties and store using Epic 1's repository."""
        # Use Epic 2's collection strategy
        raw_properties = await collector.collect_zipcode(zipcode)
        
        stored_count = 0
        for raw_property in raw_properties:
            try:
                # Epic 2's adapter converts to Epic 1's Property schema
                property_data = await collector.adapt_property(raw_property)
                
                # Store using Epic 1's repository pattern
                property_id = await self.repository.create(property_data.model_dump())
                stored_count += 1
                
            except Exception as e:
                self.logger.warning(
                    "Failed to store individual property",
                    extra={
                        "zipcode": zipcode,
                        "collector": collector.get_source_name(),
                        "error": str(e)
                    }
                )
                continue
        
        return stored_count
    
    async def rollback(self) -> bool:
        """Rollback any partial changes."""
        # For data collection, rollback might involve marking
        # incomplete collection runs for retry
        self.logger.warning(
            "Rolling back daily collection",
            extra={"command": self.get_command_name()}
        )
        return True
    
    def get_command_name(self) -> str:
        return "daily_collection"
```

#### Observer Pattern for Workflow Monitoring
```python
from typing import Protocol, List
from datetime import datetime
from phoenix_real_estate.foundation.monitoring.metrics import MetricsCollector

class WorkflowObserver(Protocol):
    """Observer for workflow execution events."""
    
    async def on_workflow_started(self, command_name: str, context: Dict[str, Any]) -> None:
        """Called when workflow starts."""
        ...
    
    async def on_workflow_completed(self, command_name: str, metrics: Dict[str, Any]) -> None:
        """Called when workflow completes successfully."""
        ...
    
    async def on_workflow_failed(self, command_name: str, error: str, context: Dict[str, Any]) -> None:
        """Called when workflow fails."""
        ...
    
    async def on_workflow_progress(self, command_name: str, progress: Dict[str, Any]) -> None:
        """Called during workflow execution for progress updates."""
        ...

class WorkflowMonitor(WorkflowObserver):
    """Workflow monitoring using Epic 1's metrics framework."""
    
    def __init__(self, metrics_collector: MetricsCollector, logger_name: str) -> None:
        self.metrics = metrics_collector
        self.logger = get_logger(logger_name)
    
    async def on_workflow_started(self, command_name: str, context: Dict[str, Any]) -> None:
        """Record workflow start metrics."""
        await self.metrics.record_counter(
            name="workflow_started",
            value=1,
            tags={"command": command_name}
        )
        
        self.logger.info(
            "Workflow started",
            extra={
                "event_type": "workflow_start",
                "command": command_name,
                "context": context,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    async def on_workflow_completed(self, command_name: str, metrics: Dict[str, Any]) -> None:
        """Record workflow completion metrics."""
        await self.metrics.record_counter(
            name="workflow_completed",
            value=1,
            tags={"command": command_name}
        )
        
        # Record workflow-specific metrics
        for metric_name, value in metrics.items():
            if isinstance(value, (int, float)):
                await self.metrics.record_gauge(
                    name=f"workflow_{command_name}_{metric_name}",
                    value=value
                )
        
        self.logger.info(
            "Workflow completed",
            extra={
                "event_type": "workflow_complete",
                "command": command_name,
                "metrics": metrics,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    async def on_workflow_failed(self, command_name: str, error: str, context: Dict[str, Any]) -> None:
        """Record workflow failure metrics."""
        await self.metrics.record_counter(
            name="workflow_failed",
            value=1,
            tags={"command": command_name}
        )
        
        self.logger.error(
            "Workflow failed",
            extra={
                "event_type": "workflow_failure",
                "command": command_name,
                "error": error,
                "context": context,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
```

#### Template Method for Deployment Workflows
```python
from abc import ABC, abstractmethod
from phoenix_real_estate.foundation.config.environment import Environment

class DeploymentWorkflow(ABC):
    """Template method for deployment workflows."""
    
    def __init__(
        self,
        config: ConfigProvider,
        environment: Environment,
        logger_name: str
    ) -> None:
        self.config = config
        self.environment = environment
        self.logger = get_logger(logger_name)
    
    async def deploy(self) -> bool:
        """Template method for deployment process."""
        try:
            self.logger.info(
                "Starting deployment",
                extra={
                    "environment": self.environment.value,
                    "deployment_type": self.get_deployment_type()
                }
            )
            
            # Template method steps
            await self.prepare_environment()
            await self.validate_configuration()
            await self.build_artifacts()
            await self.deploy_application()
            await self.run_health_checks()
            await self.cleanup()
            
            self.logger.info(
                "Deployment completed successfully",
                extra={
                    "environment": self.environment.value,
                    "deployment_type": self.get_deployment_type()
                }
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                "Deployment failed",
                extra={
                    "environment": self.environment.value,
                    "error": str(e)
                }
            )
            await self.rollback_deployment()
            raise DeploymentError(
                f"Deployment failed for {self.environment.value}",
                context={"environment": self.environment.value},
                cause=e
            ) from e
    
    @abstractmethod
    async def prepare_environment(self) -> None:
        """Prepare deployment environment."""
        pass
    
    @abstractmethod
    async def validate_configuration(self) -> None:
        """Validate configuration for target environment."""
        pass
    
    @abstractmethod
    async def build_artifacts(self) -> None:
        """Build deployment artifacts."""
        pass
    
    @abstractmethod
    async def deploy_application(self) -> None:
        """Deploy application components."""
        pass
    
    @abstractmethod
    async def run_health_checks(self) -> None:
        """Run post-deployment health checks."""
        pass
    
    @abstractmethod
    async def cleanup(self) -> None:
        """Clean up deployment resources."""
        pass
    
    @abstractmethod
    async def rollback_deployment(self) -> None:
        """Rollback failed deployment."""
        pass
    
    @abstractmethod
    def get_deployment_type(self) -> str:
        """Return deployment type name."""
        pass

class DockerDeployment(DeploymentWorkflow):
    """Docker-based deployment workflow."""
    
    async def prepare_environment(self) -> None:
        """Prepare Docker environment."""
        # Use Epic 1's configuration for Docker settings
        registry = self.config.get("DOCKER_REGISTRY", "docker.io")
        self.logger.info(
            "Preparing Docker environment",
            extra={"registry": registry, "environment": self.environment.value}
        )
    
    async def validate_configuration(self) -> None:
        """Validate Docker configuration."""
        required_configs = [
            "TARGET_ZIP_CODES",
            "MONGODB_CONNECTION_STRING",
            "MARICOPA_API_KEY"
        ]
        
        for config_key in required_configs:
            value = self.config.get_required(config_key)
            self.logger.debug(
                "Configuration validated",
                extra={"config_key": config_key, "has_value": bool(value)}
            )
    
    async def build_artifacts(self) -> None:
        """Build Docker image with Epic 1 & 2 dependencies."""
        self.logger.info("Building Docker artifacts")
        # Docker build process will be handled by GitHub Actions
    
    async def deploy_application(self) -> None:
        """Deploy Docker containers."""
        self.logger.info("Deploying Docker application")
        # Container deployment handled by orchestration engine
    
    async def run_health_checks(self) -> None:
        """Run health checks using Epic 1's monitoring."""
        # Health checks will verify Epic 1 database connection
        # and Epic 2 collector availability
        pass
    
    async def cleanup(self) -> None:
        """Clean up deployment resources."""
        self.logger.info("Cleaning up deployment resources")
    
    async def rollback_deployment(self) -> None:
        """Rollback Docker deployment."""
        self.logger.warning("Rolling back Docker deployment")
    
    def get_deployment_type(self) -> str:
        return "docker"
```

#### Strategy Pattern for Different Orchestration Modes
```python
from enum import Enum
from typing import List

class OrchestrationMode(Enum):
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    MIXED = "mixed"

class OrchestrationStrategy(ABC):
    """Strategy for orchestrating data collection."""
    
    def __init__(
        self,
        config: ConfigProvider,
        repository: PropertyRepository,
        logger_name: str
    ) -> None:
        self.config = config
        self.repository = repository
        self.logger = get_logger(logger_name)
    
    @abstractmethod
    async def orchestrate(self, collectors: List[DataCollector], zip_codes: List[str]) -> Dict[str, int]:
        """Orchestrate collection across collectors and ZIP codes."""
        pass

class SequentialOrchestration(OrchestrationStrategy):
    """Sequential collection strategy - one collector at a time."""
    
    async def orchestrate(self, collectors: List[DataCollector], zip_codes: List[str]) -> Dict[str, int]:
        """Run collectors sequentially to minimize load."""
        results = {}
        
        for collector in collectors:
            collector_name = collector.get_source_name()
            collector_total = 0
            
            self.logger.info(
                "Starting sequential collection",
                extra={"collector": collector_name, "zip_count": len(zip_codes)}
            )
            
            for zipcode in zip_codes:
                try:
                    # Use Epic 2's collection interface
                    count = await self._collect_zipcode(collector, zipcode)
                    collector_total += count
                    
                    # Respect rate limits between ZIP codes
                    await asyncio.sleep(self.config.get("INTER_ZIP_DELAY", 5.0))
                    
                except Exception as e:
                    self.logger.error(
                        "Sequential collection failed for zipcode",
                        extra={
                            "collector": collector_name,
                            "zipcode": zipcode,
                            "error": str(e)
                        }
                    )
                    continue
            
            results[collector_name] = collector_total
            
            # Delay between collectors to respect source limits
            await asyncio.sleep(self.config.get("INTER_COLLECTOR_DELAY", 30.0))
        
        return results

class ParallelOrchestration(OrchestrationStrategy):
    """Parallel collection strategy - multiple collectors simultaneously."""
    
    async def orchestrate(self, collectors: List[DataCollector], zip_codes: List[str]) -> Dict[str, int]:
        """Run collectors in parallel for faster completion."""
        results = {}
        
        # Create tasks for each collector
        tasks = []
        for collector in collectors:
            task = asyncio.create_task(
                self._collect_all_zips(collector, zip_codes)
            )
            tasks.append((collector.get_source_name(), task))
        
        # Wait for all collectors to complete
        for collector_name, task in tasks:
            try:
                count = await task
                results[collector_name] = count
                
            except Exception as e:
                self.logger.error(
                    "Parallel collection failed for collector",
                    extra={"collector": collector_name, "error": str(e)}
                )
                results[collector_name] = 0
        
        return results
    
    async def _collect_all_zips(self, collector: DataCollector, zip_codes: List[str]) -> int:
        """Collect all ZIP codes for a single collector."""
        total = 0
        
        for zipcode in zip_codes:
            try:
                count = await self._collect_zipcode(collector, zipcode)
                total += count
                
            except Exception as e:
                self.logger.error(
                    "Failed to collect zipcode in parallel mode",
                    extra={
                        "collector": collector.get_source_name(),
                        "zipcode": zipcode,
                        "error": str(e)
                    }
                )
                continue
        
        return total
```

### Module Organization

```
src/phoenix_real_estate/
├── automation/                   # Automation & Orchestration layer (Epic 3)
│   ├── __init__.py
│   ├── workflows/
│   │   ├── __init__.py
│   │   ├── base.py               # WorkflowCommand ABC
│   │   ├── daily_collection.py   # DailyCollectionCommand
│   │   ├── data_cleanup.py       # DataCleanupCommand
│   │   ├── report_generation.py  # ReportGenerationCommand
│   │   └── health_check.py       # HealthCheckCommand
│   ├── orchestration/
│   │   ├── __init__.py
│   │   ├── engine.py             # Main orchestration engine
│   │   ├── strategies.py         # Orchestration strategies
│   │   ├── scheduler.py          # Task scheduling
│   │   └── coordinator.py        # Multi-collector coordination
│   ├── deployment/
│   │   ├── __init__.py
│   │   ├── base.py               # DeploymentWorkflow ABC
│   │   ├── docker.py             # DockerDeployment implementation
│   │   ├── github_actions.py     # GitHub Actions integration
│   │   └── environment.py        # Environment-specific deployments
│   ├── monitoring/
│   │   ├── __init__.py
│   │   ├── workflow_monitor.py   # WorkflowMonitor implementation
│   │   ├── health.py             # System health monitoring
│   │   ├── alerts.py             # Alert management
│   │   └── dashboard.py          # Monitoring dashboard
│   └── reporting/
│       ├── __init__.py
│       ├── generators.py         # Report generation
│       ├── templates.py          # Report templates
│       ├── formatters.py         # Output formatters
│       └── exporters.py          # Export to various formats
```

### Integration with Epic 1 & Epic 2

#### Configuration Extension
```python
# Epic 3 extends Epic 1's configuration system
from phoenix_real_estate.foundation.config.base import ConfigProvider

class AutomationConfig:
    """Automation-specific configuration using Epic 1's ConfigProvider."""
    
    def __init__(self, config: ConfigProvider) -> None:
        self.config = config
    
    @property
    def orchestration_mode(self) -> OrchestrationMode:
        """Orchestration strategy."""
        mode_str = self.config.get("ORCHESTRATION_MODE", "sequential")
        return OrchestrationMode(mode_str)
    
    @property
    def daily_schedule_time(self) -> str:
        """Daily collection schedule (cron format)."""
        return self.config.get("DAILY_SCHEDULE", "0 10 * * *")  # 3 AM Phoenix time
    
    @property
    def max_concurrent_collectors(self) -> int:
        """Maximum concurrent collectors for parallel mode."""
        return self.config.get("MAX_CONCURRENT_COLLECTORS", 2)
    
    @property
    def workflow_timeout_minutes(self) -> int:
        """Workflow execution timeout."""
        return self.config.get("WORKFLOW_TIMEOUT_MINUTES", 120)
    
    @property
    def deployment_environment(self) -> Environment:
        """Target deployment environment."""
        env_str = self.config.get("DEPLOYMENT_ENVIRONMENT", "development")
        return Environment(env_str)
    
    @property
    def github_actions_enabled(self) -> bool:
        """Whether GitHub Actions automation is enabled."""
        return self.config.get("GITHUB_ACTIONS_ENABLED", True)
    
    @property
    def docker_registry(self) -> str:
        """Docker registry for container images."""
        return self.config.get("DOCKER_REGISTRY", "docker.io")
    
    @property
    def health_check_interval_minutes(self) -> int:
        """Health check interval in minutes."""
        return self.config.get("HEALTH_CHECK_INTERVAL", 15)
```

#### Orchestration Engine
```python
from phoenix_real_estate.foundation.database.repositories import PropertyRepository
from phoenix_real_estate.foundation.monitoring.metrics import MetricsCollector
from phoenix_real_estate.collectors.base import DataCollector
from phoenix_real_estate.collectors.factory import CollectorFactory, DataSourceType

class OrchestrationEngine:
    """Main orchestration engine integrating Epic 1 & 2 components."""
    
    def __init__(
        self,
        config: ConfigProvider,
        repository: PropertyRepository,
        metrics: MetricsCollector
    ) -> None:
        self.config = config
        self.repository = repository
        self.metrics = metrics
        self.logger = get_logger("automation.orchestration")
        
        # Epic 3 configuration
        self.automation_config = AutomationConfig(config)
        
        # Epic 2 collectors
        self.collectors: List[DataCollector] = []
        
        # Workflow monitoring
        self.monitor = WorkflowMonitor(metrics, "automation.monitor")
        
        # Orchestration strategy
        self.strategy = self._create_strategy()
    
    async def initialize(self) -> None:
        """Initialize orchestration engine with Epic 2 collectors."""
        try:
            self.logger.info("Initializing orchestration engine")
            
            # Create Epic 2 collectors using factory pattern
            source_types = [
                DataSourceType.MARICOPA_API,
                DataSourceType.PHOENIX_MLS
            ]
            
            for source_type in source_types:
                try:
                    collector = await CollectorFactory.create_collector(
                        source_type, self.config, self.repository
                    )
                    self.collectors.append(collector)
                    
                    self.logger.info(
                        "Collector initialized",
                        extra={"source": collector.get_source_name()}
                    )
                    
                except Exception as e:
                    self.logger.error(
                        "Failed to initialize collector",
                        extra={"source_type": source_type.value, "error": str(e)}
                    )
                    # Continue with other collectors
                    continue
            
            if not self.collectors:
                raise OrchestrationError("No collectors available for orchestration")
            
            self.logger.info(
                "Orchestration engine initialized",
                extra={"collector_count": len(self.collectors)}
            )
            
        except Exception as e:
            self.logger.error(
                "Failed to initialize orchestration engine",
                extra={"error": str(e)}
            )
            raise OrchestrationError(
                "Orchestration engine initialization failed",
                cause=e
            ) from e
    
    async def run_daily_workflow(self) -> Dict[str, Any]:
        """Run daily collection workflow orchestrating Epic 2 collectors."""
        workflow_context = {
            "workflow_type": "daily_collection",
            "collector_count": len(self.collectors),
            "orchestration_mode": self.automation_config.orchestration_mode.value
        }
        
        await self.monitor.on_workflow_started("daily_collection", workflow_context)
        
        try:
            # Get target ZIP codes from Epic 1 configuration
            zip_codes = self.automation_config.config.get_required("TARGET_ZIP_CODES").split(",")
            zip_codes = [z.strip() for z in zip_codes]
            
            # Orchestrate Epic 2 collectors using selected strategy
            collection_results = await self.strategy.orchestrate(self.collectors, zip_codes)
            
            # Generate daily report using Epic 1's repository
            report_data = await self._generate_daily_report(collection_results)
            
            # Record metrics
            total_collected = sum(collection_results.values())
            workflow_metrics = {
                "total_properties": total_collected,
                "zip_codes_processed": len(zip_codes),
                "collectors_used": len(self.collectors),
                "collection_results": collection_results,
                "report_generated": bool(report_data)
            }
            
            await self.monitor.on_workflow_completed("daily_collection", workflow_metrics)
            
            return {
                "success": True,
                "metrics": workflow_metrics,
                "report": report_data
            }
            
        except Exception as e:
            await self.monitor.on_workflow_failed(
                "daily_collection", 
                str(e), 
                workflow_context
            )
            raise
    
    async def _generate_daily_report(self, collection_results: Dict[str, int]) -> Dict[str, Any]:
        """Generate daily collection report using Epic 1's repository."""
        try:
            # Use Epic 1's repository to get recent data
            today = datetime.utcnow().date()
            
            # Get properties collected today (this would require enhancing PropertyRepository)
            # For now, use collection results
            report = {
                "date": today.isoformat(),
                "collection_summary": collection_results,
                "total_properties": sum(collection_results.values()),
                "sources_used": list(collection_results.keys()),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            self.logger.info(
                "Daily report generated",
                extra={"report_summary": report}
            )
            
            return report
            
        except Exception as e:
            self.logger.error(
                "Failed to generate daily report",
                extra={"error": str(e)}
            )
            # Return minimal report on failure
            return {
                "date": datetime.utcnow().date().isoformat(),
                "collection_summary": collection_results,
                "error": "Failed to generate full report"
            }
    
    def _create_strategy(self) -> OrchestrationStrategy:
        """Create orchestration strategy based on configuration."""
        mode = self.automation_config.orchestration_mode
        
        if mode == OrchestrationMode.SEQUENTIAL:
            return SequentialOrchestration(
                self.config, self.repository, "automation.sequential"
            )
        elif mode == OrchestrationMode.PARALLEL:
            return ParallelOrchestration(
                self.config, self.repository, "automation.parallel"
            )
        else:
            # Default to sequential for safety
            return SequentialOrchestration(
                self.config, self.repository, "automation.sequential"
            )
```

#### Report Generation Service
```python
from phoenix_real_estate.foundation.database.repositories import PropertyRepository

class ReportGenerator:
    """Report generation service using Epic 1's repository."""
    
    def __init__(
        self,
        repository: PropertyRepository,
        config: ConfigProvider
    ) -> None:
        self.repository = repository
        self.config = config
        self.logger = get_logger("automation.reporting")
    
    async def generate_daily_summary(self, date: datetime.date) -> Dict[str, Any]:
        """Generate daily collection summary."""
        try:
            # Use Epic 1's repository to query data
            # This would require enhancing PropertyRepository with date-based queries
            properties_count = await self._count_properties_by_date(date)
            
            report = {
                "report_type": "daily_summary",
                "date": date.isoformat(),
                "properties_collected": properties_count,
                "generated_at": datetime.utcnow().isoformat()
            }
            
            self.logger.info(
                "Daily summary generated",
                extra={"date": date.isoformat(), "count": properties_count}
            )
            
            return report
            
        except Exception as e:
            self.logger.error(
                "Failed to generate daily summary",
                extra={"date": date.isoformat(), "error": str(e)}
            )
            raise ReportGenerationError(
                "Daily summary generation failed",
                context={"date": date.isoformat()},
                cause=e
            ) from e
    
    async def generate_weekly_analysis(self, start_date: datetime.date) -> Dict[str, Any]:
        """Generate weekly analysis report."""
        try:
            end_date = start_date + timedelta(days=7)
            
            # Use Epic 1's repository for data analysis
            weekly_data = await self._analyze_weekly_trends(start_date, end_date)
            
            report = {
                "report_type": "weekly_analysis",
                "period": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat()
                },
                "analysis": weekly_data,
                "generated_at": datetime.utcnow().isoformat()
            }
            
            return report
            
        except Exception as e:
            self.logger.error(
                "Failed to generate weekly analysis",
                extra={"start_date": start_date.isoformat(), "error": str(e)}
            )
            raise ReportGenerationError(
                "Weekly analysis generation failed",
                context={"start_date": start_date.isoformat()},
                cause=e
            ) from e
    
    async def _count_properties_by_date(self, date: datetime.date) -> int:
        """Count properties collected on specific date."""
        # This would require Epic 1's PropertyRepository to support date-based queries
        # For now, return a placeholder
        return 0
    
    async def _analyze_weekly_trends(self, start_date: datetime.date, end_date: datetime.date) -> Dict[str, Any]:
        """Analyze weekly property collection trends."""
        # This would use Epic 1's repository for trend analysis
        return {
            "total_properties": 0,
            "daily_averages": {},
            "source_distribution": {},
            "quality_metrics": {}
        }
```

## Detailed Requirements

### Functional Requirements

#### FR-1: GitHub Actions Automation
- **Requirement**: Daily automated data collection via GitHub Actions
- **Acceptance Criteria**:
  - Scheduled workflow runs at 3 AM Phoenix time (10 AM UTC)
  - Uses Epic 1's configuration management for secrets
  - Orchestrates Epic 2's collectors in containerized environment
  - Generates execution reports and stores artifacts
  - Handles workflow failures with retry logic and notifications

#### FR-2: Docker Containerization
- **Requirement**: Containerized deployment of entire system
- **Acceptance Criteria**:
  - Multi-stage Docker build using Epic 1's foundation as base
  - Environment-specific configuration injection
  - Health checks using Epic 1's monitoring framework
  - Resource limits and security best practices
  - Container registry integration

#### FR-3: Orchestration Engine
- **Requirement**: Intelligent coordination of Epic 2's data collectors
- **Acceptance Criteria**:
  - Sequential and parallel orchestration strategies
  - Integration with Epic 1's configuration and logging
  - Error recovery and partial failure handling
  - Progress monitoring and metrics collection
  - Resource management and rate limit coordination

#### FR-4: Monitoring and Alerting
- **Requirement**: Comprehensive system monitoring extending Epic 1's framework
- **Acceptance Criteria**:
  - Workflow execution monitoring with Epic 1's MetricsCollector
  - Health checks for all system components
  - Alert generation for failures and anomalies
  - Performance metrics and optimization insights
  - Integration with Epic 1's structured logging

#### FR-5: Report Generation
- **Requirement**: Automated report generation using Epic 1's repository
- **Acceptance Criteria**:
  - Daily collection summaries with metrics and insights
  - Weekly trend analysis and data quality reports
  - Export to multiple formats (JSON, CSV, HTML)
  - Integration with Epic 1's PropertyRepository for data access
  - Automated report distribution

### Non-Functional Requirements

#### NFR-1: Performance
- **Workflow Execution**: Complete daily collection within 60 minutes
- **Container Startup**: < 30 seconds for full system initialization
- **Memory Usage**: < 500MB total for orchestration layer
- **GitHub Actions**: Stay within 200 minutes/month usage

#### NFR-2: Reliability
- **Workflow Success Rate**: 95% successful daily executions
- **Error Recovery**: Automatic retry for transient failures
- **Partial Failure Handling**: Continue operation despite individual component failures
- **Monitoring Uptime**: 99% availability for monitoring systems

#### NFR-3: Security
- **Credential Management**: Use Epic 1's configuration for all secrets
- **Container Security**: Non-root user, minimal attack surface
- **Network Security**: Encrypted connections for all external communications
- **Access Control**: Principle of least privilege for all components

#### NFR-4: Maintainability
- **Test Coverage**: 90%+ for all orchestration modules
- **Documentation**: Comprehensive deployment and operations guides
- **Configuration Management**: All settings externally configurable
- **Observability**: Complete audit trail using Epic 1's logging

## Implementation Tasks

### Task 7: GitHub Actions Workflow
**File**: `task-07-github-actions-workflow.md`
- Design daily automation workflow with Epic 1/2 integration
- Implement secret management using Epic 1's configuration patterns
- Create workflow for building and deploying Docker containers
- Add monitoring, alerting, and artifact management
- Integrate with Epic 2's collection orchestration

### Task 8: Orchestration Engine
**File**: `task-08-orchestration-engine.md`
- Build orchestration engine coordinating Epic 2's collectors
- Implement workflow command pattern with Epic 1 integration
- Create orchestration strategies (sequential, parallel, mixed)
- Add comprehensive monitoring using Epic 1's framework
- Integrate with Epic 1's repository for data persistence

### Task 9: Docker Deployment
**File**: `task-09-docker-deployment.md`
- Create multi-stage Docker builds with Epic 1/2 dependencies
- Implement environment-specific configuration injection
- Add health checks using Epic 1's monitoring
- Create deployment workflows for different environments
- Integrate with GitHub Actions for automated deployment

## Constraints & Limitations

### Technical Constraints
- **GitHub Actions**: 2000 minutes/month free tier limit
- **Docker Hub**: 1 free private repository
- **Container Resources**: Must operate within reasonable memory/CPU limits
- **Epic Dependencies**: Must use Epic 1/2 interfaces without duplication

### Budget Constraints
- **GitHub Actions**: $0/month (within free tier)
- **Docker Hub**: $0/month (free tier)
- **Monitoring**: $0/month (using Epic 1's framework)
- **Total Budget**: $0/month additional (Epic 2's $5/month maintained)

### Legal Constraints
- **Personal Use**: System clearly marked for personal use only
- **Automation Ethics**: Respectful automation without overwhelming sources
- **Data Handling**: No storage of sensitive information in CI/CD
- **Compliance**: All automation respects robots.txt and rate limits

### Performance Constraints
- **Execution Time**: Daily workflow completes within 60 minutes
- **Resource Usage**: Minimal impact on GitHub Actions runner resources
- **Network Usage**: Efficient use of bandwidth and API quotas
- **Storage**: Minimal artifact storage to stay within free tiers

## Risk Assessment

### High Risk Items

#### R-1: GitHub Actions Quota Exhaustion
- **Risk**: Exceeding 2000 minutes/month free tier limit
- **Impact**: Automation suspension, manual intervention required
- **Mitigation**:
  - Monitor usage with alerts at 75% and 90% thresholds
  - Optimize workflow efficiency to minimize execution time
  - Implement workflow scheduling to distribute load
  - Create fallback local execution capability
- **Owner**: DevOps Team

#### R-2: Epic 1/2 Integration Failures
- **Risk**: Breaking changes in Epic 1 or Epic 2 interfaces
- **Impact**: Orchestration failures, data collection outages
- **Mitigation**:
  - Comprehensive integration testing in CI/CD
  - Version pinning for Epic 1/2 dependencies
  - Interface compatibility monitoring
  - Rollback capabilities for failed deployments
- **Owner**: Integration Team

### Medium Risk Items

#### R-3: Container Registry Limitations
- **Risk**: Docker Hub rate limits or storage constraints
- **Impact**: Deployment failures, image pull errors
- **Mitigation**:
  - Monitor registry usage and implement caching
  - Consider alternative registries if needed
  - Optimize image sizes to reduce storage usage
  - Implement image cleanup policies
- **Owner**: DevOps Team

#### R-4: Workflow Complexity Management
- **Risk**: Orchestration workflows become too complex to maintain
- **Impact**: Debugging difficulties, maintenance overhead
- **Mitigation**:
  - Modular workflow design with clear interfaces
  - Comprehensive logging and monitoring
  - Regular workflow reviews and simplification
  - Documentation and runbooks for common issues
- **Owner**: Development Team

### Low Risk Items

#### R-5: Monitoring Data Overload
- **Risk**: Excessive monitoring data overwhelming logging systems
- **Impact**: Performance degradation, cost increases
- **Mitigation**:
  - Intelligent log level management
  - Monitoring data retention policies
  - Sampling strategies for high-volume metrics
  - Regular monitoring system optimization
- **Owner**: Operations Team

## Testing Strategy

### Unit Testing Framework
```python
# Example test structure for orchestration
import pytest
from unittest.mock import AsyncMock, patch
from phoenix_real_estate.automation.orchestration import OrchestrationEngine
from phoenix_real_estate.foundation.config.base import ConfigProvider

class TestOrchestrationEngine:
    @pytest.fixture
    async def engine(self):
        mock_config = AsyncMock(spec=ConfigProvider)
        mock_repository = AsyncMock()
        mock_metrics = AsyncMock()
        return OrchestrationEngine(mock_config, mock_repository, mock_metrics)
    
    async def test_daily_workflow_success(self, engine):
        # Test successful daily workflow execution
        with patch.object(engine, 'collectors', [AsyncMock(), AsyncMock()]):
            result = await engine.run_daily_workflow()
            
        assert result["success"] is True
        assert "metrics" in result
        assert "report" in result
    
    async def test_epic_integration(self, engine):
        # Test integration with Epic 1 and Epic 2 components
        await engine.initialize()
        assert len(engine.collectors) > 0
        assert engine.repository is not None
        assert engine.metrics is not None
```

### Integration Testing
- **Epic 1 Integration**: Test configuration, logging, and repository usage
- **Epic 2 Integration**: Test collector orchestration and data flow
- **Docker Integration**: Test containerized execution in different environments
- **GitHub Actions**: Test workflow execution with real CI/CD pipeline

### Performance Testing
- **Workflow Execution**: Measure daily workflow completion time
- **Resource Usage**: Profile memory and CPU usage during orchestration
- **Container Performance**: Test startup time and resource consumption
- **Scalability**: Test with increasing numbers of collectors and ZIP codes

### Acceptance Testing
- **End-to-End**: Complete daily workflow from trigger to report generation
- **Failure Scenarios**: Test error recovery and partial failure handling
- **Environment Deployment**: Validate deployment across dev/staging/prod
- **Monitoring Validation**: Verify all monitoring and alerting functions

## Success Metrics

### Key Performance Indicators

#### KPI-1: Automation Reliability
- **Metric**: Percentage of successful daily workflow executions
- **Target**: 95% success rate
- **Measurement**: GitHub Actions workflow success tracking

#### KPI-2: Orchestration Efficiency
- **Metric**: Average daily workflow execution time
- **Target**: < 60 minutes end-to-end
- **Measurement**: Workflow timing metrics and optimization

#### KPI-3: Resource Utilization
- **Metric**: GitHub Actions minutes usage per month
- **Target**: < 200 minutes/month (10% of free tier)
- **Measurement**: Monthly usage reports and optimization

#### KPI-4: Integration Quality
- **Metric**: Epic 1/2 interface compatibility score
- **Target**: 100% interface compatibility
- **Measurement**: Integration testing and monitoring

### Acceptance Criteria

#### Business Criteria
- [ ] Epic 4 can build quality assurance on automation interfaces
- [ ] Daily data collection runs automatically without manual intervention
- [ ] Comprehensive reporting provides actionable insights
- [ ] System operates within all budget constraints

#### Technical Criteria
- [ ] 90%+ test coverage for all automation modules
- [ ] Complete integration with Epic 1 foundation and Epic 2 collectors
- [ ] Performance targets met under realistic load
- [ ] Security standards maintained across all components

#### Quality Criteria
- [ ] Code passes all ruff formatting and linting checks
- [ ] Type hints pass mypy strict mode validation
- [ ] Security scan shows no vulnerabilities
- [ ] Documentation complete for operations and deployment

## Interface Definitions for Dependent Epics

### Epic 4: Quality Assurance & Analytics
```python
# Interfaces that Epic 4 will consume
from phoenix_real_estate.automation.workflows import WorkflowStatus, WorkflowMetrics
from phoenix_real_estate.automation.monitoring import AutomationHealth, WorkflowMonitor
from phoenix_real_estate.automation.reporting import ReportGenerator

class QualityAssuranceIntegration:
    """Interface for Epic 4 quality assurance integration."""
    
    def __init__(
        self,
        workflow_monitor: WorkflowMonitor,
        report_generator: ReportGenerator
    ) -> None:
        # Epic 4 will monitor Epic 3 automation quality
        pass
    
    async def analyze_automation_quality(self, timeframe: str) -> Dict[str, float]:
        """Analyze automation and orchestration quality metrics."""
        pass
    
    async def validate_workflow_integrity(self, workflow_name: str) -> bool:
        """Validate workflow execution integrity."""
        pass
    
    async def generate_quality_report(self) -> Dict[str, Any]:
        """Generate comprehensive quality assessment report."""
        pass
```

### Future Epic Dependencies
```python
# Epic 4 will depend on these Epic 3 interfaces
from phoenix_real_estate.automation.workflows.base import WorkflowCommand
from phoenix_real_estate.automation.orchestration.engine import OrchestrationEngine
from phoenix_real_estate.automation.monitoring.workflow_monitor import WorkflowMonitor
from phoenix_real_estate.automation.reporting.generators import ReportGenerator
from phoenix_real_estate.automation.deployment.base import DeploymentWorkflow
```

## Implementation Guidelines

### Code Quality Standards
- **Epic Integration**: All components must seamlessly integrate Epic 1 and Epic 2
- **Type Safety**: Complete type hints with mypy validation
- **Error Handling**: Use Epic 1's exception hierarchy consistently
- **Testing**: Test-driven development with comprehensive coverage
- **Documentation**: Clear integration examples and operational guides

### Security Guidelines
- **Credential Security**: Use Epic 1's configuration system exclusively
- **Container Security**: Non-root execution with minimal attack surface
- **Network Security**: Encrypted connections and secure defaults
- **Access Control**: Principle of least privilege throughout

### Performance Guidelines
- **Resource Efficiency**: Minimize GitHub Actions minutes usage
- **Orchestration Optimization**: Efficient coordination of Epic 2 collectors
- **Monitoring Efficiency**: Intelligent metrics collection and storage
- **Container Optimization**: Multi-stage builds and caching strategies

## Validation Checklist

### Pre-Implementation
- [ ] Epic 1 and Epic 2 interfaces fully understood and documented
- [ ] Integration patterns designed for seamless Epic coordination
- [ ] All task specifications created with explicit Epic dependencies
- [ ] Interface definitions complete for Epic 4 consumption

### Implementation Phase
- [ ] All components use Epic 1's foundation exclusively
- [ ] Orchestration coordinates Epic 2's collectors without duplication
- [ ] Configuration managed through Epic 1's ConfigProvider
- [ ] Monitoring extends Epic 1's MetricsCollector framework

### Post-Implementation
- [ ] Integration tests pass with Epic 1 and Epic 2 components
- [ ] Performance benchmarks meet targets within resource constraints
- [ ] Security scan shows no vulnerabilities
- [ ] Epic 4 interface contracts validated and ready

---

**Epic Owner**: DevOps Engineering Team  
**Created**: 2025-01-20  
**Status**: Planning  
**Estimated Effort**: 5-7 days  
**Dependencies**: Epic 1 (Foundation Infrastructure), Epic 2 (Data Collection Engine)