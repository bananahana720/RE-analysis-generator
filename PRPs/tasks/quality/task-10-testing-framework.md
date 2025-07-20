# Task 10: Testing Framework

## Overview
Implement a comprehensive testing framework that provides complete test coverage across all Phoenix Real Estate system components, integrating with Epic 1's logging and monitoring infrastructure.

## Integration Requirements

### Epic 1 Foundation Testing
```python
# Test foundation components
from phoenix_real_estate.foundation.database.repositories import PropertyRepository
from phoenix_real_estate.foundation.config.base import ConfigProvider
from phoenix_real_estate.foundation.logging import get_logger
from phoenix_real_estate.foundation.monitoring import MetricsCollector

class TestFoundationIntegration:
    """Integration tests for foundation layer"""
    
    async def test_database_repository_integration(self):
        config = ConfigProvider.get_test_instance()
        repo = PropertyRepository(DatabaseClient(config))
        
        # Test repository operations
        property_data = create_test_property()
        property_id = await repo.create(property_data)
        assert property_id is not None
        
        retrieved = await repo.get_by_id(property_id)
        assert retrieved.property_id == property_id
```

### Epic 2 Collection Testing
```python
# Test data collection components
from phoenix_real_estate.data_collection.collectors.maricopa import MaricopaCollector
from phoenix_real_estate.data_collection.pipeline.data_pipeline import DataPipeline

class TestCollectionIntegration:
    """Integration tests for data collection layer"""
    
    async def test_collection_pipeline_end_to_end(self):
        config = ConfigProvider.get_test_instance()
        pipeline = DataPipeline(config, get_logger("test"))
        
        # Test with mock data
        test_data = create_mock_property_data()
        result = await pipeline.process(test_data)
        
        assert result.success
        assert result.processed_count > 0
        assert result.error_count == 0
```

### Epic 3 Automation Testing
```python
# Test automation components
from phoenix_real_estate.automation.orchestration import OrchestrationEngine
from phoenix_real_estate.automation.workflows import DailyCollectionWorkflow

class TestAutomationIntegration:
    """Integration tests for automation layer"""
    
    async def test_workflow_orchestration(self):
        config = ConfigProvider.get_test_instance()
        engine = OrchestrationEngine(config)
        
        workflow = DailyCollectionWorkflow(config)
        result = await engine.execute(workflow)
        
        assert result.status == WorkflowStatus.COMPLETED
        assert result.quality_score > 0.9
```

## Testing Architecture

### Test Framework Structure
```
phoenix_real_estate/
├── tests/
│   ├── unit/                   # Unit tests for individual modules
│   │   ├── foundation/         # Epic 1 unit tests
│   │   ├── collection/         # Epic 2 unit tests
│   │   ├── automation/         # Epic 3 unit tests
│   │   └── quality/            # Epic 4 unit tests
│   ├── integration/            # Cross-component tests
│   │   ├── epic_integration/   # Cross-epic integration tests
│   │   ├── database/           # Database integration tests
│   │   └── external_apis/      # External API integration tests
│   ├── e2e/                   # End-to-end tests
│   │   ├── workflows/          # Complete workflow tests
│   │   └── scenarios/          # Business scenario tests
│   ├── performance/           # Performance and load tests
│   └── security/              # Security and vulnerability tests
```

### Test Configuration Management
```python
from phoenix_real_estate.foundation.config.base import ConfigProvider
from phoenix_real_estate.foundation.config.environment import Environment

class TestConfigProvider:
    """Test-specific configuration management"""
    
    @classmethod
    def get_test_config(cls, test_type: str = 'unit'):
        """Get configuration for different test types"""
        config_map = {
            'unit': cls._get_unit_test_config(),
            'integration': cls._get_integration_test_config(),
            'e2e': cls._get_e2e_test_config(),
            'performance': cls._get_performance_test_config()
        }
        return config_map.get(test_type, cls._get_unit_test_config())
    
    @staticmethod
    def _get_unit_test_config():
        return {
            'database': {
                'provider': 'memory',  # In-memory database for unit tests
                'connection_string': 'memory://test'
            },
            'logging': {
                'level': 'DEBUG',
                'output': 'memory'
            },
            'external_apis': {
                'mock': True,  # Mock external API calls
                'rate_limit': False
            }
        }
```

## Test Categories

### 1. Unit Tests (95% Coverage Target)
```python
import pytest
from unittest.mock import Mock, patch
from phoenix_real_estate.foundation.database.repositories import PropertyRepository

class TestPropertyRepository:
    """Unit tests for PropertyRepository"""
    
    @pytest.fixture
    def mock_db_client(self):
        return Mock()
    
    @pytest.fixture
    def repository(self, mock_db_client):
        return PropertyRepository(mock_db_client)
    
    async def test_create_property_success(self, repository, mock_db_client):
        # Arrange
        property_data = create_test_property()
        mock_db_client.create.return_value = "test_id"
        
        # Act
        result = await repository.create(property_data)
        
        # Assert
        assert result == "test_id"
        mock_db_client.create.assert_called_once_with(property_data)
    
    async def test_create_property_validation_error(self, repository):
        # Test validation error handling
        invalid_data = {}
        
        with pytest.raises(ValidationError):
            await repository.create(invalid_data)
```

### 2. Integration Tests
```python
class TestCrossEpicIntegration:
    """Tests integration between different epics"""
    
    async def test_complete_data_flow(self):
        """Test data flow from collection to storage"""
        # Epic 1: Setup foundation
        config = TestConfigProvider.get_test_config('integration')
        db_client = DatabaseClient(config)
        repo = PropertyRepository(db_client)
        logger = get_logger("integration_test")
        
        # Epic 2: Setup data collection
        collector = MaricopaCollector(config, logger)
        processor = LLMProcessor(config, logger)
        
        # Epic 3: Setup workflow
        workflow = DailyCollectionWorkflow(collector, processor, repo)
        engine = OrchestrationEngine(config, logger)
        
        # Execute complete flow
        result = await engine.execute(workflow)
        
        # Validate results
        assert result.success
        assert result.properties_collected > 0
        assert result.properties_stored > 0
        
        # Verify data in repository
        stored_properties = await repo.get_recent(limit=10)
        assert len(stored_properties) > 0
```

### 3. End-to-End Tests
```python
class TestE2EWorkflows:
    """End-to-end workflow tests"""
    
    @pytest.mark.e2e
    async def test_daily_collection_workflow(self):
        """Test complete daily collection workflow"""
        # Setup test environment
        config = TestConfigProvider.get_test_config('e2e')
        
        # Start with clean database
        await self._cleanup_test_data()
        
        # Execute daily workflow
        workflow_result = await self._run_daily_workflow(config)
        
        # Validate workflow completion
        assert workflow_result.status == 'completed'
        assert workflow_result.errors == []
        
        # Validate data quality
        quality_metrics = await self._check_data_quality()
        assert quality_metrics.completeness > 0.9
        assert quality_metrics.accuracy > 0.9
        
        # Validate monitoring metrics
        metrics = await self._get_workflow_metrics()
        assert metrics.success_rate > 0.95
```

### 4. Performance Tests
```python
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor

class TestPerformance:
    """Performance and load tests"""
    
    @pytest.mark.performance
    async def test_repository_performance(self):
        """Test repository performance under load"""
        config = TestConfigProvider.get_test_config('performance')
        repo = PropertyRepository(DatabaseClient(config))
        
        # Create test data
        test_properties = [create_test_property() for _ in range(1000)]
        
        # Measure bulk insert performance
        start_time = time.time()
        tasks = [repo.create(prop) for prop in test_properties]
        results = await asyncio.gather(*tasks)
        end_time = time.time()
        
        # Validate performance
        total_time = end_time - start_time
        throughput = len(results) / total_time
        
        assert throughput > 100  # At least 100 inserts per second
        assert all(result is not None for result in results)
    
    @pytest.mark.performance
    async def test_collection_pipeline_throughput(self):
        """Test data collection pipeline throughput"""
        config = TestConfigProvider.get_test_config('performance')
        pipeline = DataPipeline(config, get_logger("perf_test"))
        
        # Generate test data
        test_data = [create_mock_api_response() for _ in range(500)]
        
        # Measure processing throughput
        start_time = time.time()
        results = []
        
        for data_batch in batch(test_data, 50):
            batch_result = await pipeline.process_batch(data_batch)
            results.append(batch_result)
        
        end_time = time.time()
        
        # Validate performance metrics
        total_processed = sum(r.processed_count for r in results)
        processing_time = end_time - start_time
        throughput = total_processed / processing_time
        
        assert throughput > 50  # At least 50 properties per second
```

### 5. Security Tests
```python
class TestSecurity:
    """Security and vulnerability tests"""
    
    @pytest.mark.security
    async def test_configuration_security(self):
        """Test configuration doesn't expose sensitive data"""
        config = ConfigProvider.get_instance()
        
        # Check for exposed secrets
        config_dict = config.to_dict()
        sensitive_keys = ['password', 'secret', 'key', 'token']
        
        for key, value in config_dict.items():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                assert value is None or value.startswith('***')
    
    @pytest.mark.security
    async def test_data_sanitization(self):
        """Test proper data sanitization"""
        processor = LLMProcessor(TestConfigProvider.get_test_config())
        
        # Test with potentially malicious input
        malicious_data = {
            'address': '<script>alert("xss")</script>123 Main St',
            'description': 'DROP TABLE properties; --'
        }
        
        result = await processor.process(malicious_data)
        
        # Ensure data is sanitized
        assert '<script>' not in result.address
        assert 'DROP TABLE' not in result.description
```

## Test Utilities and Fixtures

### Test Data Factory
```python
from dataclasses import dataclass
from datetime import datetime
import random

class TestDataFactory:
    """Factory for creating test data"""
    
    @staticmethod
    def create_test_property():
        return Property(
            property_id=f"test_{random.randint(1000, 9999)}",
            address=Address(
                street=f"{random.randint(100, 9999)} Test St",
                city="Phoenix",
                state="AZ",
                zip_code="85001"
            ),
            features=PropertyFeatures(
                bedrooms=random.randint(1, 5),
                bathrooms=random.randint(1, 3),
                square_feet=random.randint(800, 3000),
                lot_size=random.randint(5000, 10000)
            ),
            listing_details={
                'price': random.randint(200000, 800000),
                'listing_date': datetime.now().isoformat()
            },
            last_updated=datetime.now()
        )
    
    @staticmethod
    def create_mock_api_response():
        return {
            'id': f"api_{random.randint(1000, 9999)}",
            'address': f"{random.randint(100, 9999)} API St, Phoenix, AZ 85001",
            'price': random.randint(200000, 800000),
            'beds': random.randint(1, 5),
            'baths': random.randint(1, 3),
            'sqft': random.randint(800, 3000)
        }
```

### Test Monitoring Integration
```python
from phoenix_real_estate.foundation.monitoring import MetricsCollector

class TestMetricsCollector:
    """Collect metrics during testing"""
    
    def __init__(self):
        self.metrics = MetricsCollector()
        self.test_metrics = {}
    
    async def record_test_execution(self, test_name: str, duration: float, result: str):
        """Record test execution metrics"""
        await self.metrics.increment('test_executions_total', {
            'test_name': test_name,
            'result': result
        })
        
        await self.metrics.histogram('test_duration_seconds', duration, {
            'test_name': test_name
        })
    
    async def get_test_coverage_metrics(self):
        """Get test coverage metrics"""
        return {
            'unit_test_coverage': await self._get_unit_coverage(),
            'integration_test_coverage': await self._get_integration_coverage(),
            'e2e_test_coverage': await self._get_e2e_coverage()
        }
```

## CI/CD Integration

### GitHub Actions Test Workflow
```yaml
name: Quality Assurance Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.12]
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Setup Python
      uses: actions/setup-python@v3
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        pip install uv
        uv sync --dev
    
    - name: Run unit tests
      run: |
        uv run pytest tests/unit/ --cov=phoenix_real_estate --cov-report=xml
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3

  integration-tests:
    runs-on: ubuntu-latest
    needs: unit-tests
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Setup test environment
      run: |
        docker-compose -f docker-compose.test.yml up -d
    
    - name: Run integration tests
      run: |
        uv run pytest tests/integration/ --maxfail=5
    
    - name: Cleanup test environment
      run: |
        docker-compose -f docker-compose.test.yml down

  e2e-tests:
    runs-on: ubuntu-latest
    needs: integration-tests
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Run E2E tests
      run: |
        uv run pytest tests/e2e/ --maxfail=1
```

## Quality Gates

### Test Coverage Requirements
```python
class TestCoverageValidator:
    """Validate test coverage requirements"""
    
    COVERAGE_THRESHOLDS = {
        'overall': 95,
        'foundation': 98,
        'collection': 95,
        'automation': 92,
        'quality': 98
    }
    
    async def validate_coverage(self, coverage_report):
        """Validate coverage meets requirements"""
        issues = []
        
        for component, threshold in self.COVERAGE_THRESHOLDS.items():
            actual_coverage = coverage_report.get(component, 0)
            if actual_coverage < threshold:
                issues.append(f"{component} coverage {actual_coverage}% < {threshold}%")
        
        return len(issues) == 0, issues
```

## Success Criteria
- Unit test coverage ≥95% across all modules
- Integration tests cover all epic interactions
- E2E tests validate complete workflows
- Performance tests ensure <5% overhead
- Security tests validate all compliance requirements
- All tests run in <10 minutes total
- Test failure rate <1%

## Deliverables
1. Complete test suite with 95%+ coverage
2. CI/CD integration with automated testing
3. Performance benchmarking framework
4. Security testing automation
5. Test metrics and reporting dashboard
6. Documentation for test maintenance and extension

## Resource Requirements
- GitHub Actions: 500 minutes/month for testing
- Test database: Separate MongoDB instance
- Test data: Synthetic data generation
- Performance monitoring: Lightweight metrics collection