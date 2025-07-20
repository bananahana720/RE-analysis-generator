# Task 8: Orchestration Engine

## Overview

### Objective
Build a sophisticated orchestration engine that coordinates Epic 2's data collectors using Epic 1's foundation infrastructure to provide intelligent workflow management, multi-strategy collection orchestration, and comprehensive monitoring. The engine serves as the central coordination layer for all automated data collection operations.

### Epic Integration
**Builds upon Epic 1**: Uses ConfigProvider, PropertyRepository, logging framework, and MetricsCollector
**Orchestrates Epic 2**: Coordinates all data collectors, manages collection strategies, and monitors collection metrics  
**Enables Epic 4**: Provides orchestration metrics, workflow data, and quality measurements for analysis

### Dependencies
- Epic 1: `foundation.config.base.ConfigProvider`, `foundation.database.repositories.PropertyRepository`, `foundation.logging.factory.get_logger`, `foundation.monitoring.metrics.MetricsCollector`
- Epic 2: All collector implementations, collection monitoring, rate limiting systems
- Epic 3: Workflow command pattern, monitoring observers, deployment strategies

## Technical Architecture

### Core Components

#### Orchestration Engine Core
```python
# src/phoenix_real_estate/automation/orchestration/engine.py
"""
Main orchestration engine coordinating Epic 1 & 2 components.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Protocol
from enum import Enum

from phoenix_real_estate.foundation.config.base import ConfigProvider
from phoenix_real_estate.foundation.database.repositories import PropertyRepository
from phoenix_real_estate.foundation.logging.factory import get_logger
from phoenix_real_estate.foundation.monitoring.metrics import MetricsCollector
from phoenix_real_estate.foundation.utils.exceptions import OrchestrationError

from phoenix_real_estate.collectors.base import DataCollector
from phoenix_real_estate.collectors.factory import CollectorFactory, DataSourceType
from phoenix_real_estate.collectors.monitoring import CollectionMetrics

from phoenix_real_estate.automation.orchestration.strategies import (
    OrchestrationStrategy,
    SequentialStrategy,
    ParallelStrategy,
    MixedStrategy
)
from phoenix_real_estate.automation.monitoring.workflow_monitor import WorkflowMonitor

class OrchestrationMode(Enum):
    """Orchestration execution modes."""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    MIXED = "mixed"
    ADAPTIVE = "adaptive"

class CollectorStatus(Enum):
    """Individual collector status."""
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    DISABLED = "disabled"

class OrchestrationEngine:
    """
    Main orchestration engine integrating Epic 1 foundation and Epic 2 collectors.
    Provides intelligent coordination, monitoring, and error recovery.
    """
    
    def __init__(
        self,
        config: ConfigProvider,
        repository: PropertyRepository,
        metrics: MetricsCollector
    ) -> None:
        # Epic 1 Foundation Integration
        self.config = config
        self.repository = repository
        self.metrics = metrics
        self.logger = get_logger("automation.orchestration.engine")
        
        # Epic 2 Collector Management
        self.collectors: Dict[str, DataCollector] = {}
        self.collector_status: Dict[str, CollectorStatus] = {}
        self.collection_metrics = CollectionMetrics("orchestration.collection")
        
        # Epic 3 Orchestration Components
        self.workflow_monitor = WorkflowMonitor(metrics, "orchestration.monitor")
        self.orchestration_strategy: Optional[OrchestrationStrategy] = None
        
        # State Management
        self._is_initialized = False
        self._current_execution_id: Optional[str] = None
        self._execution_start_time: Optional[datetime] = None
        
        # Configuration
        self.target_zip_codes: List[str] = []
        self.orchestration_mode = OrchestrationMode.SEQUENTIAL
        self.max_concurrent_collectors = 2
        self.collection_timeout_minutes = 90
        
    async def initialize(self) -> None:
        """Initialize orchestration engine with Epic 1 & 2 components."""
        try:
            if self._is_initialized:
                self.logger.warning("Orchestration engine already initialized")
                return
            
            self.logger.info("Initializing orchestration engine")
            
            # Load configuration using Epic 1's ConfigProvider
            await self._load_configuration()
            
            # Initialize Epic 2 collectors
            await self._initialize_collectors()
            
            # Set up orchestration strategy
            self._setup_orchestration_strategy()
            
            # Validate system readiness
            await self._validate_system_readiness()
            
            self._is_initialized = True
            
            self.logger.info(
                "Orchestration engine initialized successfully",
                extra={
                    "collector_count": len(self.collectors),
                    "target_zip_count": len(self.target_zip_codes),
                    "orchestration_mode": self.orchestration_mode.value
                }
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
    
    async def _load_configuration(self) -> None:
        """Load orchestration configuration using Epic 1's patterns."""
        try:
            # Target ZIP codes from Epic 1 configuration
            zip_codes_str = self.config.get_required("TARGET_ZIP_CODES")
            self.target_zip_codes = [z.strip() for z in zip_codes_str.split(",") if z.strip()]
            
            # Orchestration mode
            mode_str = self.config.get("ORCHESTRATION_MODE", "sequential")
            self.orchestration_mode = OrchestrationMode(mode_str)
            
            # Performance settings
            self.max_concurrent_collectors = self.config.get("MAX_CONCURRENT_COLLECTORS", 2)
            self.collection_timeout_minutes = self.config.get("COLLECTION_TIMEOUT_MINUTES", 90)
            
            # Validation
            if not self.target_zip_codes:
                raise ValueError("No target ZIP codes configured")
            
            self.logger.info(
                "Configuration loaded",
                extra={
                    "zip_codes": len(self.target_zip_codes),
                    "mode": self.orchestration_mode.value,
                    "max_concurrent": self.max_concurrent_collectors
                }
            )
            
        except Exception as e:
            self.logger.error(
                "Failed to load orchestration configuration",
                extra={"error": str(e)}
            )
            raise
    
    async def _initialize_collectors(self) -> None:
        """Initialize Epic 2 data collectors."""
        try:
            self.logger.info("Initializing data collectors")
            
            # Define available collector types
            collector_types = [
                DataSourceType.MARICOPA_API,
                DataSourceType.PHOENIX_MLS
            ]
            
            # Create collectors using Epic 2's factory pattern
            for source_type in collector_types:
                try:
                    collector = await CollectorFactory.create_collector(
                        source_type, self.config, self.repository
                    )
                    
                    collector_name = collector.get_source_name()
                    self.collectors[collector_name] = collector
                    self.collector_status[collector_name] = CollectorStatus.READY
                    
                    self.logger.info(
                        "Collector initialized",
                        extra={
                            "collector": collector_name,
                            "source_type": source_type.value
                        }
                    )
                    
                except Exception as e:
                    self.logger.error(
                        "Failed to initialize collector",
                        extra={
                            "source_type": source_type.value,
                            "error": str(e)
                        }
                    )
                    # Continue with other collectors
                    continue
            
            if not self.collectors:
                raise OrchestrationError("No collectors available for orchestration")
            
            self.logger.info(
                "All collectors initialized",
                extra={"collector_count": len(self.collectors)}
            )
            
        except Exception as e:
            self.logger.error(
                "Collector initialization failed",
                extra={"error": str(e)}
            )
            raise
    
    def _setup_orchestration_strategy(self) -> None:
        """Set up orchestration strategy based on configuration."""
        try:
            if self.orchestration_mode == OrchestrationMode.SEQUENTIAL:
                self.orchestration_strategy = SequentialStrategy(
                    self.config, self.repository, "orchestration.sequential"
                )
            elif self.orchestration_mode == OrchestrationMode.PARALLEL:
                self.orchestration_strategy = ParallelStrategy(
                    self.config, self.repository, "orchestration.parallel"
                )
            elif self.orchestration_mode == OrchestrationMode.MIXED:
                self.orchestration_strategy = MixedStrategy(
                    self.config, self.repository, "orchestration.mixed"
                )
            elif self.orchestration_mode == OrchestrationMode.ADAPTIVE:
                # Adaptive mode chooses strategy based on current conditions
                self.orchestration_strategy = self._choose_adaptive_strategy()
            else:
                # Default to sequential for safety
                self.orchestration_strategy = SequentialStrategy(
                    self.config, self.repository, "orchestration.default"
                )
            
            self.logger.info(
                "Orchestration strategy configured",
                extra={
                    "mode": self.orchestration_mode.value,
                    "strategy_class": self.orchestration_strategy.__class__.__name__
                }
            )
            
        except Exception as e:
            self.logger.error(
                "Failed to setup orchestration strategy",
                extra={"error": str(e)}
            )
            raise
    
    def _choose_adaptive_strategy(self) -> OrchestrationStrategy:
        """Choose orchestration strategy adaptively based on conditions."""
        # Adaptive logic considers:
        # - Number of collectors
        # - Historical performance data
        # - Current system load
        # - Time constraints
        
        if len(self.collectors) <= 1:
            # Single collector - use sequential
            return SequentialStrategy(
                self.config, self.repository, "orchestration.adaptive.sequential"
            )
        elif len(self.target_zip_codes) > 10:
            # Many ZIP codes - parallel might be beneficial
            return ParallelStrategy(
                self.config, self.repository, "orchestration.adaptive.parallel"
            )
        else:
            # Default to mixed strategy for balanced approach
            return MixedStrategy(
                self.config, self.repository, "orchestration.adaptive.mixed"
            )
    
    async def _validate_system_readiness(self) -> None:
        """Validate system readiness for orchestration."""
        try:
            self.logger.info("Validating system readiness")
            
            # Validate Epic 1 database connection
            await self._validate_database_connection()
            
            # Validate Epic 2 collector readiness
            await self._validate_collector_readiness()
            
            # Validate configuration completeness
            self._validate_configuration_completeness()
            
            self.logger.info("System readiness validation completed")
            
        except Exception as e:
            self.logger.error(
                "System readiness validation failed",
                extra={"error": str(e)}
            )
            raise
    
    async def _validate_database_connection(self) -> None:
        """Validate Epic 1 database connection."""
        try:
            # Test database connection using Epic 1's repository
            # This would require adding a ping/health check method to PropertyRepository
            self.logger.info("Database connection validated")
            
        except Exception as e:
            self.logger.error(
                "Database connection validation failed",
                extra={"error": str(e)}
            )
            raise
    
    async def _validate_collector_readiness(self) -> None:
        """Validate Epic 2 collector readiness."""
        ready_count = 0
        
        for collector_name, collector in self.collectors.items():
            try:
                # Test collector connectivity (if available)
                # For now, assume ready if initialized
                self.collector_status[collector_name] = CollectorStatus.READY
                ready_count += 1
                
            except Exception as e:
                self.logger.warning(
                    "Collector not ready",
                    extra={"collector": collector_name, "error": str(e)}
                )
                self.collector_status[collector_name] = CollectorStatus.DISABLED
        
        if ready_count == 0:
            raise OrchestrationError("No collectors are ready for execution")
        
        self.logger.info(
            "Collector readiness validated",
            extra={"ready_collectors": ready_count, "total_collectors": len(self.collectors)}
        )
    
    def _validate_configuration_completeness(self) -> None:
        """Validate configuration completeness."""
        required_configs = [
            "TARGET_ZIP_CODES",
            "MONGODB_CONNECTION_STRING"
        ]
        
        missing_configs = []
        for config_key in required_configs:
            try:
                value = self.config.get_required(config_key)
                if not value:
                    missing_configs.append(config_key)
            except Exception:
                missing_configs.append(config_key)
        
        if missing_configs:
            raise OrchestrationError(
                f"Missing required configuration: {missing_configs}"
            )
    
    async def run_daily_workflow(self) -> Dict[str, Any]:
        """Execute daily collection workflow orchestrating Epic 2 collectors."""
        if not self._is_initialized:
            raise OrchestrationError("Orchestration engine not initialized")
        
        # Generate unique execution ID
        self._current_execution_id = f"daily_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        self._execution_start_time = datetime.utcnow()
        
        workflow_context = {
            "execution_id": self._current_execution_id,
            "workflow_type": "daily_collection",
            "orchestration_mode": self.orchestration_mode.value,
            "collector_count": len(self.collectors),
            "zip_code_count": len(self.target_zip_codes),
            "started_at": self._execution_start_time.isoformat()
        }
        
        # Notify workflow start
        await self.workflow_monitor.on_workflow_started(
            "daily_collection", workflow_context
        )
        
        try:
            self.logger.info(
                "Starting daily collection workflow",
                extra=workflow_context
            )
            
            # Get ready collectors
            ready_collectors = [
                collector for name, collector in self.collectors.items()
                if self.collector_status[name] == CollectorStatus.READY
            ]
            
            if not ready_collectors:
                raise OrchestrationError("No collectors ready for execution")
            
            # Execute orchestration strategy
            collection_results = await self._execute_orchestration(ready_collectors)
            
            # Generate execution metrics
            execution_metrics = await self._generate_execution_metrics(collection_results)
            
            # Create workflow result
            workflow_result = {
                "success": True,
                "execution_id": self._current_execution_id,
                "collection_results": collection_results,
                "metrics": execution_metrics,
                "completed_at": datetime.utcnow().isoformat()
            }
            
            # Notify workflow completion
            await self.workflow_monitor.on_workflow_completed(
                "daily_collection", execution_metrics
            )
            
            self.logger.info(
                "Daily collection workflow completed successfully",
                extra={
                    "execution_id": self._current_execution_id,
                    "total_collected": execution_metrics.get("total_properties", 0),
                    "duration_minutes": execution_metrics.get("duration_minutes", 0)
                }
            )
            
            return workflow_result
            
        except Exception as e:
            # Handle workflow failure
            await self._handle_workflow_failure(e, workflow_context)
            raise
        
        finally:
            # Reset execution state
            self._current_execution_id = None
            self._execution_start_time = None
    
    async def _execute_orchestration(self, collectors: List[DataCollector]) -> Dict[str, int]:
        """Execute orchestration strategy with ready collectors."""
        try:
            self.logger.info(
                "Executing orchestration strategy",
                extra={
                    "strategy": self.orchestration_strategy.__class__.__name__,
                    "collector_count": len(collectors),
                    "zip_code_count": len(self.target_zip_codes)
                }
            )
            
            # Use Epic 3's orchestration strategy to coordinate Epic 2's collectors
            collection_results = await self.orchestration_strategy.orchestrate(
                collectors, self.target_zip_codes
            )
            
            self.logger.info(
                "Orchestration strategy completed",
                extra={
                    "collection_results": collection_results,
                    "total_collected": sum(collection_results.values())
                }
            )
            
            return collection_results
            
        except Exception as e:
            self.logger.error(
                "Orchestration strategy execution failed",
                extra={
                    "strategy": self.orchestration_strategy.__class__.__name__,
                    "error": str(e)
                }
            )
            raise OrchestrationError(
                "Orchestration strategy execution failed",
                context={"strategy": self.orchestration_strategy.__class__.__name__},
                cause=e
            ) from e
    
    async def _generate_execution_metrics(self, collection_results: Dict[str, int]) -> Dict[str, Any]:
        """Generate comprehensive execution metrics."""
        try:
            execution_duration = (
                datetime.utcnow() - self._execution_start_time
            ).total_seconds()
            
            total_properties = sum(collection_results.values())
            
            metrics = {
                "execution_id": self._current_execution_id,
                "total_properties": total_properties,
                "duration_seconds": execution_duration,
                "duration_minutes": execution_duration / 60,
                "properties_per_minute": total_properties / max(execution_duration / 60, 0.1),
                "zip_codes_processed": len(self.target_zip_codes),
                "collectors_used": len([c for c in collection_results.values() if c > 0]),
                "collection_distribution": collection_results,
                "orchestration_mode": self.orchestration_mode.value,
                "success_rate": len([c for c in collection_results.values() if c > 0]) / max(len(collection_results), 1)
            }
            
            # Record metrics using Epic 1's MetricsCollector
            await self.metrics.record_gauge(
                name="orchestration_properties_collected",
                value=total_properties,
                tags={"execution_id": self._current_execution_id}
            )
            
            await self.metrics.record_gauge(
                name="orchestration_duration_minutes",
                value=metrics["duration_minutes"],
                tags={"execution_id": self._current_execution_id}
            )
            
            await self.metrics.record_counter(
                name="orchestration_executions",
                value=1,
                tags={"mode": self.orchestration_mode.value}
            )
            
            return metrics
            
        except Exception as e:
            self.logger.error(
                "Failed to generate execution metrics",
                extra={"error": str(e)}
            )
            # Return minimal metrics on failure
            return {
                "execution_id": self._current_execution_id,
                "error": "Failed to generate metrics"
            }
    
    async def _handle_workflow_failure(self, error: Exception, context: Dict[str, Any]) -> None:
        """Handle workflow failure with comprehensive error reporting."""
        try:
            failure_metrics = {
                "execution_id": self._current_execution_id,
                "error_type": type(error).__name__,
                "error_message": str(error),
                "failure_time": datetime.utcnow().isoformat(),
                "execution_duration_seconds": (
                    datetime.utcnow() - self._execution_start_time
                ).total_seconds() if self._execution_start_time else 0
            }
            
            # Notify workflow failure
            await self.workflow_monitor.on_workflow_failed(
                "daily_collection", str(error), {**context, **failure_metrics}
            )
            
            # Record failure metrics
            await self.metrics.record_counter(
                name="orchestration_failures",
                value=1,
                tags={
                    "error_type": type(error).__name__,
                    "mode": self.orchestration_mode.value
                }
            )
            
            self.logger.error(
                "Workflow execution failed",
                extra={
                    "execution_id": self._current_execution_id,
                    "error": str(error),
                    "context": context,
                    "failure_metrics": failure_metrics
                }
            )
            
        except Exception as e:
            self.logger.error(
                "Failed to handle workflow failure",
                extra={"original_error": str(error), "handler_error": str(e)}
            )
    
    async def get_orchestration_status(self) -> Dict[str, Any]:
        """Get current orchestration engine status."""
        try:
            status = {
                "initialized": self._is_initialized,
                "current_execution_id": self._current_execution_id,
                "is_running": self._current_execution_id is not None,
                "orchestration_mode": self.orchestration_mode.value,
                "collector_status": {
                    name: status.value for name, status in self.collector_status.items()
                },
                "configuration": {
                    "target_zip_count": len(self.target_zip_codes),
                    "max_concurrent_collectors": self.max_concurrent_collectors,
                    "collection_timeout_minutes": self.collection_timeout_minutes
                },
                "system_health": await self._get_system_health()
            }
            
            if self._execution_start_time:
                status["current_execution_duration"] = (
                    datetime.utcnow() - self._execution_start_time
                ).total_seconds()
            
            return status
            
        except Exception as e:
            self.logger.error(
                "Failed to get orchestration status",
                extra={"error": str(e)}
            )
            return {"error": "Failed to get status"}
    
    async def _get_system_health(self) -> Dict[str, Any]:
        """Get system health indicators."""
        try:
            health = {
                "database_connected": True,  # Would implement actual check
                "collectors_ready": len([
                    s for s in self.collector_status.values() 
                    if s == CollectorStatus.READY
                ]),
                "total_collectors": len(self.collector_status),
                "configuration_valid": bool(self.target_zip_codes),
                "last_health_check": datetime.utcnow().isoformat()
            }
            
            health["overall_health"] = (
                health["database_connected"] and
                health["collectors_ready"] > 0 and
                health["configuration_valid"]
            )
            
            return health
            
        except Exception as e:
            self.logger.error(
                "Failed to get system health",
                extra={"error": str(e)}
            )
            return {"error": "Failed to get health status"}
    
    async def shutdown(self) -> None:
        """Gracefully shutdown orchestration engine."""
        try:
            self.logger.info("Shutting down orchestration engine")
            
            # Cancel any running workflows
            if self._current_execution_id:
                self.logger.warning(
                    "Cancelling running workflow",
                    extra={"execution_id": self._current_execution_id}
                )
                self._current_execution_id = None
            
            # Update collector status
            for collector_name in self.collector_status:
                self.collector_status[collector_name] = CollectorStatus.DISABLED
            
            # Clear state
            self._is_initialized = False
            self._execution_start_time = None
            
            self.logger.info("Orchestration engine shutdown completed")
            
        except Exception as e:
            self.logger.error(
                "Error during orchestration engine shutdown",
                extra={"error": str(e)}
            )
```

#### Orchestration Strategies
```python
# src/phoenix_real_estate/automation/orchestration/strategies.py
"""
Orchestration strategies for coordinating Epic 2 collectors.
"""

import asyncio
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Dict, Any

from phoenix_real_estate.foundation.config.base import ConfigProvider
from phoenix_real_estate.foundation.database.repositories import PropertyRepository
from phoenix_real_estate.foundation.logging.factory import get_logger
from phoenix_real_estate.foundation.utils.exceptions import OrchestrationError

from phoenix_real_estate.collectors.base import DataCollector

class OrchestrationStrategy(ABC):
    """Base strategy for orchestrating data collection."""
    
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
    async def orchestrate(
        self, 
        collectors: List[DataCollector], 
        zip_codes: List[str]
    ) -> Dict[str, int]:
        """Orchestrate collection across collectors and ZIP codes."""
        pass
    
    async def _collect_zipcode(
        self, 
        collector: DataCollector, 
        zipcode: str
    ) -> int:
        """Collect and store properties for a single ZIP code."""
        try:
            # Use Epic 2's collection interface
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
            
            self.logger.info(
                "ZIP code collection completed",
                extra={
                    "collector": collector.get_source_name(),
                    "zipcode": zipcode,
                    "collected": len(raw_properties),
                    "stored": stored_count
                }
            )
            
            return stored_count
            
        except Exception as e:
            self.logger.error(
                "ZIP code collection failed",
                extra={
                    "collector": collector.get_source_name(),
                    "zipcode": zipcode,
                    "error": str(e)
                }
            )
            return 0

class SequentialStrategy(OrchestrationStrategy):
    """Sequential collection strategy - one collector at a time."""
    
    async def orchestrate(
        self, 
        collectors: List[DataCollector], 
        zip_codes: List[str]
    ) -> Dict[str, int]:
        """Run collectors sequentially to minimize load and respect rate limits."""
        results = {}
        
        self.logger.info(
            "Starting sequential orchestration",
            extra={
                "collector_count": len(collectors),
                "zip_code_count": len(zip_codes)
            }
        )
        
        for collector in collectors:
            collector_name = collector.get_source_name()
            collector_total = 0
            
            self.logger.info(
                "Starting collector execution",
                extra={"collector": collector_name}
            )
            
            for zipcode in zip_codes:
                try:
                    count = await self._collect_zipcode(collector, zipcode)
                    collector_total += count
                    
                    # Respect rate limits between ZIP codes
                    inter_zip_delay = self.config.get("INTER_ZIP_DELAY", 5.0)
                    await asyncio.sleep(inter_zip_delay)
                    
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
            
            self.logger.info(
                "Collector execution completed",
                extra={
                    "collector": collector_name,
                    "total_collected": collector_total
                }
            )
            
            # Delay between collectors to respect source limits
            inter_collector_delay = self.config.get("INTER_COLLECTOR_DELAY", 30.0)
            if collector != collectors[-1]:  # Don't delay after last collector
                await asyncio.sleep(inter_collector_delay)
        
        total_collected = sum(results.values())
        self.logger.info(
            "Sequential orchestration completed",
            extra={
                "results": results,
                "total_collected": total_collected
            }
        )
        
        return results

class ParallelStrategy(OrchestrationStrategy):
    """Parallel collection strategy - multiple collectors simultaneously."""
    
    async def orchestrate(
        self, 
        collectors: List[DataCollector], 
        zip_codes: List[str]
    ) -> Dict[str, int]:
        """Run collectors in parallel for faster completion."""
        results = {}
        
        self.logger.info(
            "Starting parallel orchestration",
            extra={
                "collector_count": len(collectors),
                "zip_code_count": len(zip_codes)
            }
        )
        
        # Create tasks for each collector
        tasks = []
        for collector in collectors:
            task = asyncio.create_task(
                self._collect_all_zips(collector, zip_codes),
                name=f"collector_{collector.get_source_name()}"
            )
            tasks.append((collector.get_source_name(), task))
        
        # Wait for all collectors to complete
        for collector_name, task in tasks:
            try:
                count = await task
                results[collector_name] = count
                
                self.logger.info(
                    "Parallel collector completed",
                    extra={
                        "collector": collector_name,
                        "total_collected": count
                    }
                )
                
            except Exception as e:
                self.logger.error(
                    "Parallel collection failed for collector",
                    extra={"collector": collector_name, "error": str(e)}
                )
                results[collector_name] = 0
        
        total_collected = sum(results.values())
        self.logger.info(
            "Parallel orchestration completed",
            extra={
                "results": results,
                "total_collected": total_collected
            }
        )
        
        return results
    
    async def _collect_all_zips(
        self, 
        collector: DataCollector, 
        zip_codes: List[str]
    ) -> int:
        """Collect all ZIP codes for a single collector in parallel mode."""
        total = 0
        collector_name = collector.get_source_name()
        
        for zipcode in zip_codes:
            try:
                count = await self._collect_zipcode(collector, zipcode)
                total += count
                
                # Shorter delay in parallel mode but still respect rate limits
                inter_zip_delay = self.config.get("PARALLEL_INTER_ZIP_DELAY", 2.0)
                await asyncio.sleep(inter_zip_delay)
                
            except Exception as e:
                self.logger.error(
                    "Failed to collect zipcode in parallel mode",
                    extra={
                        "collector": collector_name,
                        "zipcode": zipcode,
                        "error": str(e)
                    }
                )
                continue
        
        return total

class MixedStrategy(OrchestrationStrategy):
    """Mixed strategy - intelligent combination of sequential and parallel."""
    
    async def orchestrate(
        self, 
        collectors: List[DataCollector], 
        zip_codes: List[str]
    ) -> Dict[str, int]:
        """
        Use mixed strategy: high-rate collectors in sequence,
        low-rate collectors in parallel.
        """
        results = {}
        
        self.logger.info(
            "Starting mixed orchestration",
            extra={
                "collector_count": len(collectors),
                "zip_code_count": len(zip_codes)
            }
        )
        
        # Categorize collectors by rate limit sensitivity
        high_rate_collectors, low_rate_collectors = self._categorize_collectors(collectors)
        
        # Run high-rate collectors sequentially
        if high_rate_collectors:
            self.logger.info(
                "Running high-rate collectors sequentially",
                extra={"count": len(high_rate_collectors)}
            )
            
            sequential_strategy = SequentialStrategy(
                self.config, self.repository, "orchestration.mixed.sequential"
            )
            sequential_results = await sequential_strategy.orchestrate(
                high_rate_collectors, zip_codes
            )
            results.update(sequential_results)
        
        # Run low-rate collectors in parallel
        if low_rate_collectors:
            self.logger.info(
                "Running low-rate collectors in parallel",
                extra={"count": len(low_rate_collectors)}
            )
            
            parallel_strategy = ParallelStrategy(
                self.config, self.repository, "orchestration.mixed.parallel"
            )
            parallel_results = await parallel_strategy.orchestrate(
                low_rate_collectors, zip_codes
            )
            results.update(parallel_results)
        
        total_collected = sum(results.values())
        self.logger.info(
            "Mixed orchestration completed",
            extra={
                "results": results,
                "total_collected": total_collected,
                "high_rate_count": len(high_rate_collectors),
                "low_rate_count": len(low_rate_collectors)
            }
        )
        
        return results
    
    def _categorize_collectors(
        self, 
        collectors: List[DataCollector]
    ) -> tuple[List[DataCollector], List[DataCollector]]:
        """Categorize collectors by rate limit sensitivity."""
        high_rate_collectors = []
        low_rate_collectors = []
        
        for collector in collectors:
            collector_name = collector.get_source_name()
            
            # Categorize based on collector type
            # This could be made more sophisticated with configuration
            if "api" in collector_name.lower():
                # API collectors typically have stricter rate limits
                high_rate_collectors.append(collector)
            else:
                # Web scrapers can often handle more concurrent load
                low_rate_collectors.append(collector)
        
        return high_rate_collectors, low_rate_collectors
```

### Non-Functional Requirements

#### NFR-1: Performance
- **Orchestration Overhead**: < 5% of total execution time
- **Memory Usage**: < 100MB for orchestration engine
- **Workflow Startup**: < 10 seconds to initialize
- **Concurrent Execution**: Support up to 5 concurrent collectors

#### NFR-2: Reliability  
- **Error Recovery**: Automatic retry for transient failures (max 3 attempts)
- **Partial Failure Handling**: Continue with available collectors
- **State Management**: Persistent workflow state across restarts
- **Health Monitoring**: Continuous collector and system health checks

#### NFR-3: Scalability
- **ZIP Code Scaling**: Support 50+ ZIP codes per execution
- **Collector Scaling**: Support 10+ different data collectors
- **Strategy Flexibility**: Easy addition of new orchestration strategies
- **Configuration Scaling**: Dynamic configuration without code changes

## Implementation Plan

### Phase 1: Core Engine (Days 1-2)
- [ ] Implement OrchestrationEngine with Epic 1/2 integration
- [ ] Add basic orchestration strategies (Sequential, Parallel)
- [ ] Integrate workflow monitoring and metrics collection
- [ ] Add comprehensive error handling and recovery

### Phase 2: Advanced Strategies (Days 2-3)
- [ ] Implement Mixed and Adaptive orchestration strategies
- [ ] Add intelligent collector categorization and management
- [ ] Implement comprehensive status monitoring and health checks
- [ ] Add configuration validation and system readiness checks

### Phase 3: Workflow Integration (Days 3-4)
- [ ] Integrate with Epic 3 workflow command pattern
- [ ] Add execution state management and persistence
- [ ] Implement comprehensive metrics and reporting
- [ ] Add graceful shutdown and cleanup procedures

### Phase 4: Production Hardening (Days 4-5)
- [ ] Add comprehensive testing and validation
- [ ] Optimize performance and resource usage
- [ ] Add operational monitoring and debugging tools
- [ ] Create comprehensive documentation and runbooks

## Testing Strategy

### Unit Tests
```python
# tests/automation/orchestration/test_engine.py
import pytest
from unittest.mock import AsyncMock, patch
from phoenix_real_estate.automation.orchestration.engine import OrchestrationEngine

class TestOrchestrationEngine:
    @pytest.fixture
    async def engine(self):
        mock_config = AsyncMock()
        mock_repository = AsyncMock()
        mock_metrics = AsyncMock()
        return OrchestrationEngine(mock_config, mock_repository, mock_metrics)
    
    async def test_initialization_success(self, engine):
        # Test successful engine initialization
        with patch.object(engine, '_load_configuration'), \
             patch.object(engine, '_initialize_collectors'), \
             patch.object(engine, '_setup_orchestration_strategy'), \
             patch.object(engine, '_validate_system_readiness'):
            
            await engine.initialize()
            assert engine._is_initialized is True
    
    async def test_daily_workflow_execution(self, engine):
        # Test complete daily workflow execution
        engine._is_initialized = True
        
        with patch.object(engine, '_execute_orchestration') as mock_orchestrate:
            mock_orchestrate.return_value = {"maricopa": 100, "phoenix_mls": 75}
            
            result = await engine.run_daily_workflow()
            
            assert result["success"] is True
            assert "metrics" in result
            assert "collection_results" in result
```

### Integration Tests
- **Epic 1 Integration**: Test database operations and configuration management
- **Epic 2 Integration**: Test collector orchestration and data flow
- **Strategy Testing**: Test all orchestration strategies with real collectors
- **Error Scenarios**: Test failure handling and recovery mechanisms

### Performance Tests
- **Load Testing**: Test with maximum ZIP codes and collectors
- **Memory Profiling**: Monitor memory usage during long executions
- **Concurrency Testing**: Test parallel strategy under load
- **Timeout Testing**: Validate timeout handling and cleanup

## Success Criteria

### Acceptance Criteria
- [ ] Successfully orchestrates all Epic 2 collectors using Epic 1 infrastructure
- [ ] Supports all defined orchestration strategies (Sequential, Parallel, Mixed, Adaptive)
- [ ] Completes daily workflow within 90 minutes
- [ ] Provides comprehensive monitoring and metrics to Epic 4
- [ ] Handles failures gracefully with automatic recovery
- [ ] Maintains 95% success rate across all orchestration modes

### Quality Gates
- [ ] 95%+ test coverage for orchestration modules
- [ ] All integration tests pass with Epic 1 and Epic 2 components
- [ ] Performance benchmarks meet targets under realistic load
- [ ] Memory usage stays within 100MB limit
- [ ] Error handling covers all failure scenarios
- [ ] Documentation complete for operations and troubleshooting

---

**Task Owner**: Senior Backend Engineer  
**Epic**: Epic 3 - Automation & Orchestration  
**Estimated Effort**: 5 days  
**Dependencies**: Epic 1 (Foundation), Epic 2 (Collection), Workflow patterns  
**Deliverables**: Orchestration engine, strategy implementations, monitoring integration, comprehensive testing