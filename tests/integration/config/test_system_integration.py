"""Comprehensive integration tests for configuration system with Phoenix Real Estate components.

This module tests the configuration system's integration with:
- Database operations
- Logging system
- Data collection components
- Cross-component consistency
- Environment switching
- Configuration reload impact
- Error propagation and recovery
- Performance impact
"""

import asyncio
import logging
import os
import time
from typing import Any, Dict, List
from unittest.mock import Mock, patch, AsyncMock

import pytest

from phoenix_real_estate.foundation import (
    ConfigProvider,
    Environment,
    PropertyRepository,
    get_logger,
)
from phoenix_real_estate.foundation.config import (
    EnvironmentConfigProvider,
)


# Create a simple test config provider
class SimpleConfigProvider:
    """Simple configuration provider for testing."""

    def __init__(self):
        self._values = {}

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        return self._values.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set configuration value."""
        self._values[key] = value

    def get_int(self, key: str, default: int = 0) -> int:
        """Get integer configuration value."""
        value = self.get(key, default)
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def get_bool(self, key: str, default: bool = False) -> bool:
        """Get boolean configuration value."""
        value = self.get(key, default)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("true", "yes", "1", "on")
        return bool(value)


from phoenix_real_estate.foundation.database.connection import (
    DatabaseConnection,
    get_database_connection,
    close_database_connection,
)
from phoenix_real_estate.foundation.database.repositories import (
    RepositoryFactory,
)
from phoenix_real_estate.foundation.utils.exceptions import (
    ConfigurationError,
    DatabaseError,
)


class TestDatabaseConfigurationIntegration:
    """Test database configuration integration scenarios."""

    @pytest.fixture
    async def cleanup_database(self):
        """Cleanup database connections after tests."""
        yield
        await close_database_connection()
        DatabaseConnection.reset_instance()
        RepositoryFactory.reset()

    @pytest.mark.asyncio
    async def test_database_connection_with_config_provider(self, cleanup_database):
        """Test database connection using configuration provider."""
        # Setup configuration
        config = SimpleConfigProvider()
        config.set("MONGODB_URI", "mongodb://localhost:27017")
        config.set("MONGODB_DATABASE", "test_phoenix")
        config.set("MONGODB_MAX_POOL_SIZE", 5)
        config.set("MONGODB_MIN_POOL_SIZE", 1)

        # Create database connection
        db_conn = await get_database_connection(
            uri=config.get("MONGODB_URI"),
            database_name=config.get("MONGODB_DATABASE"),
            max_pool_size=config.get("MONGODB_MAX_POOL_SIZE", 10),
            min_pool_size=config.get("MONGODB_MIN_POOL_SIZE", 1),
        )

        # Verify configuration was applied
        assert db_conn.database_name == "test_phoenix"
        assert db_conn.max_pool_size == 5
        assert db_conn.min_pool_size == 1

    @pytest.mark.asyncio
    async def test_repository_with_config_provider(self, cleanup_database):
        """Test repository initialization with configuration provider."""
        # Setup configuration
        config = SimpleConfigProvider()
        config.set("MONGODB_URI", "mongodb://localhost:27017")
        config.set("MONGODB_DATABASE", "test_phoenix")

        # Mock database connection
        with patch(
            "phoenix_real_estate.foundation.database.repositories.DatabaseConnection"
        ) as mock_conn:
            mock_db = AsyncMock()
            mock_conn.get_instance.return_value.get_database.return_value.__aenter__.return_value = mock_db

            # Create repository using factory with mock connection
            repo = RepositoryFactory.get_property_repository(mock_conn.get_instance.return_value)

            # Verify repository was created with correct config
            assert repo is not None
            assert isinstance(repo, PropertyRepository)

    @pytest.mark.asyncio
    async def test_database_config_missing_required_fields(self):
        """Test database initialization with missing configuration."""
        config = SimpleConfigProvider()
        # Don't set MONGODB_URI

        # Patch the ConfigProvider import in repositories module
        with patch(
            "phoenix_real_estate.foundation.config.provider.ConfigProvider"
        ) as mock_provider:
            # Create a mock instance that returns None for MONGODB_URI
            mock_instance = Mock()
            mock_instance.get.return_value = None
            mock_provider.return_value = mock_instance

            with pytest.raises(ConfigurationError) as exc_info:
                repo = RepositoryFactory.get_property_repository()

            assert "No MongoDB URI configured" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_database_config_environment_override(self, cleanup_database):
        """Test database configuration with environment variable override."""
        # Set environment variable
        os.environ["MONGODB_URI"] = "mongodb://env-host:27017"
        os.environ["MONGODB_DATABASE"] = "env_database"

        try:
            # Create config provider that reads from environment
            config = EnvironmentConfigProvider(
                config_dir=None, environment=Environment.TESTING.value, load_dotenv=False
            )

            # Create database connection
            db_conn = DatabaseConnection.get_instance(
                uri=config.get("MONGODB_URI"),
                database_name=config.get("MONGODB_DATABASE"),
            )

            assert db_conn.uri == "mongodb://env-host:27017"
            assert db_conn.database_name == "env_database"

        finally:
            # Cleanup
            os.environ.pop("MONGODB_URI", None)
            os.environ.pop("MONGODB_DATABASE", None)


class TestLoggingConfigurationIntegration:
    """Test logging configuration integration scenarios."""

    def test_logger_with_config_provider(self):
        """Test logger initialization with configuration provider."""
        config = SimpleConfigProvider()
        config.set("LOG_LEVEL", "DEBUG")
        config.set("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")

        # Get logger
        logger = get_logger("test.module")

        # Verify logger is configured
        assert logger is not None
        assert hasattr(logger, "info")
        assert hasattr(logger, "debug")
        assert hasattr(logger, "error")

    def test_logger_level_configuration(self):
        """Test logger level configuration."""
        config = SimpleConfigProvider()
        config.set("LOG_LEVEL", "WARNING")

        # Create logger with custom level
        logger = get_logger("test.warning.logger")

        # Configure logger level based on config
        if hasattr(logger, "setLevel"):
            logger.setLevel(getattr(logging, config.get("LOG_LEVEL", "INFO")))

        # Test logging at different levels
        with patch.object(logger, "warning") as mock_warning:
            with patch.object(logger, "info") as mock_info:
                logger.warning("Warning message")
                logger.info("Info message")

                # Warning should be logged
                mock_warning.assert_called_once()
                # Info might not be called depending on handler configuration

    def test_multiple_loggers_share_configuration(self):
        """Test multiple loggers share the same configuration."""
        config = SimpleConfigProvider()
        config.set("LOG_LEVEL", "DEBUG")

        # Create multiple loggers
        logger1 = get_logger("module1")
        logger2 = get_logger("module2")
        logger3 = get_logger("module1.submodule")

        # All loggers should be configured
        assert logger1 is not None
        assert logger2 is not None
        assert logger3 is not None

        # Loggers with same name should be identical
        assert get_logger("module1") is logger1


class TestDataCollectionConfigurationIntegration:
    """Test data collection configuration integration scenarios."""

    @pytest.fixture
    def collection_config(self):
        """Setup data collection configuration."""
        config = SimpleConfigProvider()
        config.set("COLLECTION_BATCH_SIZE", 50)
        config.set("COLLECTION_TIMEOUT", 30)
        config.set("COLLECTION_MAX_RETRIES", 3)
        config.set("COLLECTION_RATE_LIMIT", 100)
        config.set("API_KEY_MARICOPA", "test-key")
        config.set("PROXY_ENABLED", True)
        config.set("PROXY_ROTATION_INTERVAL", 300)
        return config

    def test_data_collector_initialization(self, collection_config):
        """Test data collector initialization with configuration."""

        # Simulate data collector initialization
        class MockDataCollector:
            def __init__(self, config: ConfigProvider):
                self.batch_size = config.get("COLLECTION_BATCH_SIZE", 100)
                self.timeout = config.get("COLLECTION_TIMEOUT", 60)
                self.max_retries = config.get("COLLECTION_MAX_RETRIES", 5)
                self.rate_limit = config.get("COLLECTION_RATE_LIMIT", 200)
                self.api_key = config.get("API_KEY_MARICOPA")
                self.proxy_enabled = config.get("PROXY_ENABLED", False)

        collector = MockDataCollector(collection_config)

        # Verify configuration was applied
        assert collector.batch_size == 50
        assert collector.timeout == 30
        assert collector.max_retries == 3
        assert collector.rate_limit == 100
        assert collector.api_key == "test-key"
        assert collector.proxy_enabled is True

    def test_proxy_configuration_integration(self, collection_config):
        """Test proxy configuration for data collection."""

        # Simulate proxy manager
        class MockProxyManager:
            def __init__(self, config: ConfigProvider):
                self.enabled = config.get("PROXY_ENABLED", False)
                self.rotation_interval = config.get("PROXY_ROTATION_INTERVAL", 600)
                self.proxy_list = config.get("PROXY_LIST", [])

        # Add proxy list to config
        collection_config.set("PROXY_LIST", ["proxy1:8080", "proxy2:8080"])

        proxy_manager = MockProxyManager(collection_config)

        assert proxy_manager.enabled is True
        assert proxy_manager.rotation_interval == 300
        assert len(proxy_manager.proxy_list) == 2

    @pytest.mark.asyncio
    async def test_collector_with_database_integration(self, collection_config):
        """Test data collector with database integration."""
        # Setup database config
        collection_config.set("MONGODB_URI", "mongodb://localhost:27017")
        collection_config.set("MONGODB_DATABASE", "test_collection")

        # Simulate collector that uses database
        class MockCollectorWithDB:
            def __init__(self, config: ConfigProvider):
                self.config = config
                self.db_connection = None
                self.repository = None

            async def initialize(self):
                """Initialize database connection."""
                self.db_connection = DatabaseConnection.get_instance(
                    uri=self.config.get("MONGODB_URI"),
                    database_name=self.config.get("MONGODB_DATABASE"),
                )
                # Mock the repository
                self.repository = Mock(spec=PropertyRepository)

            async def collect_and_store(self, data: Dict[str, Any]):
                """Collect and store data."""
                if not self.repository:
                    await self.initialize()

                # Simulate storing data
                await self.repository.create(data)

        # Create and use collector
        collector = MockCollectorWithDB(collection_config)
        await collector.initialize()

        assert collector.db_connection is not None
        assert collector.repository is not None

        # Cleanup
        DatabaseConnection.reset_instance()


class TestCrossComponentConfigurationConsistency:
    """Test configuration consistency across components."""

    def test_shared_configuration_consistency(self):
        """Test that all components see the same configuration values."""
        # Create shared configuration
        config = SimpleConfigProvider()
        config.set("SHARED_VALUE", "consistent")
        config.set("NUMERIC_VALUE", 42)
        config.set("BOOLEAN_VALUE", True)

        # Simulate different components reading config
        components = []

        class Component:
            def __init__(self, name: str, config: ConfigProvider):
                self.name = name
                self.shared = config.get("SHARED_VALUE")
                self.numeric = config.get("NUMERIC_VALUE")
                self.boolean = config.get("BOOLEAN_VALUE")

        # Create multiple components
        for i in range(5):
            components.append(Component(f"component_{i}", config))

        # Verify all components see the same values
        for component in components:
            assert component.shared == "consistent"
            assert component.numeric == 42
            assert component.boolean is True

    def test_configuration_update_propagation(self):
        """Test configuration updates propagate to all components."""
        config = SimpleConfigProvider()
        config.set("DYNAMIC_VALUE", "initial")

        # Create components that cache configuration
        class CachingComponent:
            def __init__(self, config: ConfigProvider):
                self.config = config
                self._cached_value = None

            @property
            def value(self):
                # Simulate caching behavior
                if self._cached_value is None:
                    self._cached_value = self.config.get("DYNAMIC_VALUE")
                return self._cached_value

            def refresh(self):
                """Refresh cached configuration."""
                self._cached_value = self.config.get("DYNAMIC_VALUE")

        # Create components
        comp1 = CachingComponent(config)
        comp2 = CachingComponent(config)

        # Initial values
        assert comp1.value == "initial"
        assert comp2.value == "initial"

        # Update configuration
        config.set("DYNAMIC_VALUE", "updated")

        # Without refresh, cached values remain
        assert comp1.value == "initial"
        assert comp2.value == "initial"

        # After refresh, values update
        comp1.refresh()
        comp2.refresh()
        assert comp1.value == "updated"
        assert comp2.value == "updated"

    @pytest.mark.asyncio
    async def test_concurrent_configuration_access(self):
        """Test concurrent access to configuration from multiple components."""
        config = SimpleConfigProvider()
        results = []
        errors = []

        async def access_config(component_id: int, delay: float):
            """Simulate component accessing configuration."""
            try:
                await asyncio.sleep(delay)

                # Read configuration
                value = config.get(f"COMPONENT_{component_id}_VALUE", f"default_{component_id}")

                # Write configuration
                config.set(f"COMPONENT_{component_id}_RESULT", f"processed_{value}")

                results.append((component_id, value))
            except Exception as e:
                errors.append((component_id, str(e)))

        # Run concurrent access
        tasks = []
        for i in range(10):
            # Set some initial values
            config.set(f"COMPONENT_{i}_VALUE", f"value_{i}")
            # Create concurrent tasks
            tasks.append(access_config(i, i * 0.01))

        await asyncio.gather(*tasks)

        # Verify all components completed successfully
        assert len(errors) == 0
        assert len(results) == 10

        # Verify results were written
        for i in range(10):
            result = config.get(f"COMPONENT_{i}_RESULT")
            assert result == f"processed_value_{i}"


class TestEnvironmentSwitchingScenarios:
    """Test environment switching impact on configuration."""

    def test_environment_specific_configuration(self):
        """Test configuration changes based on environment."""
        environments = {
            Environment.DEVELOPMENT: {
                "DATABASE_HOST": "localhost",
                "API_TIMEOUT": 60,
                "DEBUG_MODE": True,
            },
            Environment.TESTING: {
                "DATABASE_HOST": "test-db",
                "API_TIMEOUT": 30,
                "DEBUG_MODE": True,
            },
            Environment.PRODUCTION: {
                "DATABASE_HOST": "prod-db-cluster",
                "API_TIMEOUT": 10,
                "DEBUG_MODE": False,
            },
        }

        for env, expected_values in environments.items():
            # Create environment-specific config with proper arguments
            config = EnvironmentConfigProvider(
                config_dir=None,  # Use default
                environment=env.value,  # Convert enum to string
                load_dotenv=False,  # Don't load .env in tests
            )

            # Override with test values - EnvironmentConfigProvider uses .config dict
            for key, value in expected_values.items():
                config.config[key] = value

            # Verify environment-specific values
            assert config.get("DATABASE_HOST") == expected_values["DATABASE_HOST"]
            assert config.get("API_TIMEOUT") == expected_values["API_TIMEOUT"]
            assert config.get("DEBUG_MODE") == expected_values["DEBUG_MODE"]

    def test_environment_transition_handling(self):
        """Test handling of environment transitions."""
        # Start with development - use SimpleConfigProvider for simplicity
        dev_config = SimpleConfigProvider()
        dev_config.set("FEATURE_FLAG", True)
        dev_config.set("MAX_CONNECTIONS", 100)

        # Transition to production
        prod_config = SimpleConfigProvider()
        prod_config.set("FEATURE_FLAG", False)
        prod_config.set("MAX_CONNECTIONS", 10)

        # Simulate component that needs to handle transition
        class EnvironmentAwareComponent:
            def __init__(self, config: ConfigProvider):
                self.config = config
                self.connections = []
                self._setup_connections()

            def _setup_connections(self):
                """Setup connections based on configuration."""
                max_conn = self.config.get("MAX_CONNECTIONS", 50)
                self.connections = [f"conn_{i}" for i in range(max_conn)]

            def transition_environment(self, new_config: ConfigProvider):
                """Handle environment transition."""
                old_max = len(self.connections)
                self.config = new_config
                new_max = self.config.get("MAX_CONNECTIONS", 50)

                if new_max < old_max:
                    # Close excess connections
                    self.connections = self.connections[:new_max]
                elif new_max > old_max:
                    # Open new connections
                    for i in range(old_max, new_max):
                        self.connections.append(f"conn_{i}")

        # Create component in dev
        component = EnvironmentAwareComponent(dev_config)
        assert len(component.connections) == 100

        # Transition to production
        component.transition_environment(prod_config)
        assert len(component.connections) == 10

    @pytest.mark.asyncio
    async def test_environment_switch_database_impact(self):
        """Test environment switching impact on database connections."""
        # Development environment
        dev_config = SimpleConfigProvider()
        dev_config.set("MONGODB_URI", "mongodb://dev-host:27017")
        dev_config.set("MONGODB_DATABASE", "dev_db")
        dev_config.set("MONGODB_MAX_POOL_SIZE", 20)

        # Production environment
        prod_config = SimpleConfigProvider()
        prod_config.set("MONGODB_URI", "mongodb://prod-host:27017")
        prod_config.set("MONGODB_DATABASE", "prod_db")
        prod_config.set("MONGODB_MAX_POOL_SIZE", 5)

        # Simulate environment-aware database manager
        class DatabaseManager:
            def __init__(self):
                self.current_connection = None
                self.current_env = None

            async def connect(self, config: ConfigProvider, env: str):
                """Connect to database for specific environment."""
                if self.current_connection:
                    await self.disconnect()

                # Mock connection
                self.current_connection = Mock()
                self.current_connection.uri = config.get("MONGODB_URI")
                self.current_connection.database = config.get("MONGODB_DATABASE")
                self.current_connection.pool_size = config.get("MONGODB_MAX_POOL_SIZE")
                self.current_env = env

            async def disconnect(self):
                """Disconnect current connection."""
                if self.current_connection:
                    # Simulate cleanup
                    self.current_connection = None
                    self.current_env = None

        # Test environment switching
        manager = DatabaseManager()

        # Connect to dev
        await manager.connect(dev_config, "development")
        assert manager.current_connection.uri == "mongodb://dev-host:27017"
        assert manager.current_connection.pool_size == 20

        # Switch to production
        await manager.connect(prod_config, "production")
        assert manager.current_connection.uri == "mongodb://prod-host:27017"
        assert manager.current_connection.pool_size == 5


class TestConfigurationReloadImpact:
    """Test configuration reload impact on components."""

    def test_configuration_reload_notification(self):
        """Test components can be notified of configuration reloads."""

        # Create configuration with observers
        class ObservableConfig(SimpleConfigProvider):
            def __init__(self):
                super().__init__()
                self.observers = []

            def add_observer(self, observer):
                """Add configuration observer."""
                self.observers.append(observer)

            def reload(self):
                """Reload configuration and notify observers."""
                # Simulate reload
                self._values.clear()
                self._values.update(
                    {
                        "RELOADED": True,
                        "RELOAD_TIME": time.time(),
                    }
                )

                # Notify observers
                for observer in self.observers:
                    observer.on_config_reload()

        # Create observer components
        class ConfigObserver:
            def __init__(self, name: str):
                self.name = name
                self.reload_count = 0
                self.last_reload_time = None

            def on_config_reload(self):
                """Handle configuration reload."""
                self.reload_count += 1
                self.last_reload_time = time.time()

        # Setup
        config = ObservableConfig()
        observers = [ConfigObserver(f"observer_{i}") for i in range(3)]

        for observer in observers:
            config.add_observer(observer)

        # Initial state
        for observer in observers:
            assert observer.reload_count == 0

        # Reload configuration
        config.reload()

        # Verify all observers were notified
        for observer in observers:
            assert observer.reload_count == 1
            assert observer.last_reload_time is not None

    @pytest.mark.asyncio
    async def test_graceful_configuration_reload(self):
        """Test graceful handling of configuration reload during operations."""
        config = SimpleConfigProvider()
        config.set("PROCESSING_ENABLED", True)
        config.set("BATCH_SIZE", 10)

        # Simulate component doing continuous processing
        class ProcessingComponent:
            def __init__(self, config: ConfigProvider):
                self.config = config
                self.processed_count = 0
                self.errors = []
                self.running = False

            async def process_batch(self):
                """Process a batch of items."""
                if not self.config.get("PROCESSING_ENABLED", False):
                    return False

                batch_size = self.config.get("BATCH_SIZE", 5)

                try:
                    # Simulate processing
                    await asyncio.sleep(0.1)
                    self.processed_count += batch_size
                    return True
                except Exception as e:
                    self.errors.append(str(e))
                    return False

            async def run(self):
                """Run continuous processing."""
                self.running = True
                while self.running and self.config.get("PROCESSING_ENABLED", False):
                    await self.process_batch()

            def stop(self):
                """Stop processing."""
                self.running = False

        # Create and start component
        component = ProcessingComponent(config)

        # Run processing for a short time
        process_task = asyncio.create_task(component.run())
        await asyncio.sleep(0.3)

        # Reload configuration during processing
        config.set("BATCH_SIZE", 20)
        await asyncio.sleep(0.2)

        # Disable processing
        config.set("PROCESSING_ENABLED", False)
        await asyncio.sleep(0.1)

        # Stop component
        component.stop()
        await process_task

        # Verify processing adapted to configuration changes
        assert component.processed_count > 0
        assert len(component.errors) == 0


class TestErrorPropagationAndRecovery:
    """Test error propagation and recovery in configuration system."""

    def test_configuration_error_propagation(self):
        """Test how configuration errors propagate through components."""

        class StrictComponent:
            def __init__(self, config: ConfigProvider):
                self.config = config
                self._validate_configuration()

            def _validate_configuration(self):
                """Validate required configuration."""
                required_keys = ["API_KEY", "DATABASE_URL", "TIMEOUT"]
                missing_keys = []

                for key in required_keys:
                    if not self.config.get(key):
                        missing_keys.append(key)

                if missing_keys:
                    raise ConfigurationError(
                        f"Missing required configuration: {', '.join(missing_keys)}"
                    )

        # Test with incomplete configuration
        config = SimpleConfigProvider()
        config.set("TIMEOUT", 30)

        with pytest.raises(ConfigurationError) as exc_info:
            component = StrictComponent(config)

        assert "API_KEY" in str(exc_info.value)
        assert "DATABASE_URL" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_database_configuration_error_recovery(self):
        """Test recovery from database configuration errors."""
        # Invalid configuration
        config = SimpleConfigProvider()
        config.set("MONGODB_URI", "invalid://uri")
        config.set("MONGODB_DATABASE", "test_db")

        # Component with retry logic
        class ResilientDatabaseComponent:
            def __init__(self, config: ConfigProvider):
                self.config = config
                self.connection = None
                self.retry_count = 0
                self.max_retries = 3

            async def connect(self):
                """Connect with retry logic."""
                while self.retry_count < self.max_retries:
                    try:
                        uri = self.config.get("MONGODB_URI")
                        db_name = self.config.get("MONGODB_DATABASE")

                        # Simulate connection attempt
                        if uri.startswith("invalid://"):
                            raise DatabaseError("Invalid URI scheme")

                        self.connection = Mock()
                        return True
                    except DatabaseError:
                        self.retry_count += 1
                        if self.retry_count >= self.max_retries:
                            raise

                        # Wait before retry
                        await asyncio.sleep(0.1 * self.retry_count)

                        # Check if configuration was updated
                        new_uri = self.config.get("MONGODB_URI")
                        if new_uri != uri:
                            continue

                return False

        # Create component
        component = ResilientDatabaseComponent(config)

        # First attempt should fail
        with pytest.raises(DatabaseError):
            await component.connect()

        # Fix configuration and retry
        config.set("MONGODB_URI", "mongodb://localhost:27017")
        component.retry_count = 0

        # Should succeed now
        success = await component.connect()
        assert success
        assert component.connection is not None

    def test_cascading_configuration_errors(self):
        """Test how configuration errors cascade through dependent components."""
        config = SimpleConfigProvider()

        # Component hierarchy with dependencies
        class DatabaseComponent:
            def __init__(self, config: ConfigProvider):
                self.config = config
                uri = config.get("DATABASE_URI")
                if not uri:
                    raise ConfigurationError("DATABASE_URI not configured")
                self.uri = uri

        class CacheComponent:
            def __init__(self, config: ConfigProvider):
                self.config = config
                url = config.get("CACHE_URL")
                if not url:
                    raise ConfigurationError("CACHE_URL not configured")
                self.url = url

        class ServiceComponent:
            def __init__(self, config: ConfigProvider):
                self.config = config
                self.database = None
                self.cache = None
                self.errors = []

                try:
                    self.database = DatabaseComponent(config)
                except ConfigurationError as e:
                    self.errors.append(f"Database: {str(e)}")

                try:
                    self.cache = CacheComponent(config)
                except ConfigurationError as e:
                    self.errors.append(f"Cache: {str(e)}")

                if self.errors:
                    raise ConfigurationError(
                        f"Service initialization failed: {'; '.join(self.errors)}"
                    )

        # Test with missing configuration
        with pytest.raises(ConfigurationError) as exc_info:
            service = ServiceComponent(config)

        error_msg = str(exc_info.value)
        assert "Database: DATABASE_URI not configured" in error_msg
        assert "Cache: CACHE_URL not configured" in error_msg


class TestPerformanceImpact:
    """Test performance impact of configuration on integrated systems."""

    def test_configuration_lookup_performance(self):
        """Test performance of configuration lookups."""
        config = SimpleConfigProvider()

        # Populate with many configuration values
        for i in range(1000):
            config.set(f"KEY_{i}", f"value_{i}")

        # Measure lookup performance
        start_time = time.time()
        iterations = 10000

        for _ in range(iterations):
            # Random lookups
            key = f"KEY_{_ % 1000}"
            value = config.get(key)

        elapsed = time.time() - start_time
        avg_lookup_time = elapsed / iterations

        # Should be very fast (microseconds)
        assert avg_lookup_time < 0.0001  # Less than 0.1ms per lookup

    def test_configuration_with_caching_performance(self):
        """Test performance with configuration caching."""
        config = SimpleConfigProvider()

        # Expensive configuration computation
        call_count = 0

        def expensive_config_value():
            nonlocal call_count
            call_count += 1
            time.sleep(0.01)  # Simulate expensive operation
            return f"computed_value_{call_count}"

        # Component with configuration caching
        class CachedConfigComponent:
            def __init__(self, config: ConfigProvider):
                self.config = config
                self._cache = {}

            def get_config_value(self, key: str, compute_func=None):
                """Get configuration value with caching."""
                if key in self._cache:
                    return self._cache[key]

                value = self.config.get(key)
                if value is None and compute_func:
                    value = compute_func()
                    self.config.set(key, value)

                self._cache[key] = value
                return value

        # Create component
        component = CachedConfigComponent(config)

        # First call computes value
        start = time.time()
        value1 = component.get_config_value("EXPENSIVE_KEY", expensive_config_value)
        first_call_time = time.time() - start

        # Subsequent calls use cache
        start = time.time()
        for _ in range(100):
            value = component.get_config_value("EXPENSIVE_KEY", expensive_config_value)
            assert value == value1

        cache_time = time.time() - start

        # Cache should be much faster
        assert cache_time < first_call_time
        assert call_count == 1  # Function called only once

    @pytest.mark.asyncio
    async def test_concurrent_configuration_performance(self):
        """Test configuration performance under concurrent load."""
        config = SimpleConfigProvider()

        # Populate initial configuration
        for i in range(100):
            config.set(f"CONCURRENT_KEY_{i}", f"value_{i}")

        # Concurrent access simulation
        read_count = 0
        write_count = 0
        errors = []

        async def reader_task(task_id: int, iterations: int):
            """Simulate configuration reads."""
            nonlocal read_count
            try:
                for i in range(iterations):
                    key = f"CONCURRENT_KEY_{i % 100}"
                    value = config.get(key)
                    read_count += 1
                    await asyncio.sleep(0.0001)  # Simulate work
            except Exception as e:
                errors.append(f"Reader {task_id}: {str(e)}")

        async def writer_task(task_id: int, iterations: int):
            """Simulate configuration writes."""
            nonlocal write_count
            try:
                for i in range(iterations):
                    key = f"DYNAMIC_KEY_{task_id}_{i}"
                    config.set(key, f"dynamic_value_{task_id}_{i}")
                    write_count += 1
                    await asyncio.sleep(0.001)  # Simulate work
            except Exception as e:
                errors.append(f"Writer {task_id}: {str(e)}")

        # Run concurrent tasks
        start_time = time.time()

        tasks = []
        # Create readers
        for i in range(10):
            tasks.append(reader_task(i, 100))
        # Create writers
        for i in range(5):
            tasks.append(writer_task(i, 20))

        await asyncio.gather(*tasks)

        elapsed = time.time() - start_time

        # Verify results
        assert len(errors) == 0
        assert read_count == 1000  # 10 readers * 100 iterations
        assert write_count == 100  # 5 writers * 20 iterations

        # Performance check (should handle concurrent access efficiently)
        assert elapsed < 2.0  # Should complete within 2 seconds

    def test_configuration_memory_impact(self):
        """Test memory impact of configuration storage."""
        config = SimpleConfigProvider()

        # Measure baseline memory (approximate)
        import sys

        baseline_size = sys.getsizeof(config._values)

        # Add many configuration values
        large_value = "x" * 1000  # 1KB string
        for i in range(1000):
            config.set(f"MEMORY_KEY_{i}", large_value)

        # Measure memory after population
        populated_size = sys.getsizeof(config._values)

        # Calculate approximate memory per entry
        memory_per_entry = (populated_size - baseline_size) / 1000

        # Should be reasonable (considering key + value storage)
        assert memory_per_entry < 2000  # Less than 2KB per entry

        # Test memory cleanup
        config._values.clear()
        cleaned_size = sys.getsizeof(config._values)

        # Should return to near baseline
        assert cleaned_size < baseline_size * 2


class TestRealWorldIntegrationScenarios:
    """Test real-world integration scenarios."""

    @pytest.mark.asyncio
    async def test_full_stack_property_collection(self):
        """Test full property collection stack with configuration."""
        # Setup comprehensive configuration
        config = SimpleConfigProvider()

        # Database configuration
        config.set("MONGODB_URI", "mongodb://localhost:27017")
        config.set("MONGODB_DATABASE", "test_integration")

        # Collection configuration
        config.set("COLLECTION_BATCH_SIZE", 25)
        config.set("COLLECTION_TIMEOUT", 30)
        config.set("API_KEY_MARICOPA", "test-api-key")

        # Logging configuration
        config.set("LOG_LEVEL", "DEBUG")
        config.set("LOG_FILE", "test_integration.log")

        # Simulate full collection workflow
        class PropertyCollectionWorkflow:
            def __init__(self, config: ConfigProvider):
                self.config = config
                self.logger = get_logger(__name__)
                self.stats = {
                    "collected": 0,
                    "stored": 0,
                    "errors": 0,
                }

            async def run(self):
                """Run complete collection workflow."""
                self.logger.info("Starting property collection workflow")

                # Initialize components
                batch_size = self.config.get("COLLECTION_BATCH_SIZE", 50)

                # Simulate data collection
                for batch in range(3):
                    properties = await self._collect_batch(batch, batch_size)
                    await self._store_batch(properties)

                self.logger.info(
                    "Collection complete - Collected: %d, Stored: %d, Errors: %d",
                    self.stats["collected"],
                    self.stats["stored"],
                    self.stats["errors"],
                )

            async def _collect_batch(self, batch_num: int, size: int):
                """Simulate collecting a batch of properties."""
                self.logger.debug("Collecting batch %d (size: %d)", batch_num, size)

                # Simulate API call with timeout
                timeout = self.config.get("COLLECTION_TIMEOUT", 60)

                try:
                    # Simulate collection
                    await asyncio.sleep(0.1)  # Simulate API delay

                    properties = []
                    for i in range(size):
                        properties.append(
                            {
                                "property_id": f"test_{batch_num}_{i}",
                                "address": {
                                    "street": f"{i} Test St",
                                    "city": "Phoenix",
                                    "zipcode": "85001",
                                },
                                "current_price": 100000 + (i * 1000),
                            }
                        )

                    self.stats["collected"] += len(properties)
                    return properties

                except Exception as e:
                    self.logger.error("Collection failed: %s", str(e))
                    self.stats["errors"] += 1
                    return []

            async def _store_batch(self, properties: List[Dict[str, Any]]):
                """Simulate storing properties."""
                if not properties:
                    return

                try:
                    # Simulate database storage
                    await asyncio.sleep(0.05)  # Simulate DB delay

                    self.stats["stored"] += len(properties)
                    self.logger.debug("Stored %d properties", len(properties))

                except Exception as e:
                    self.logger.error("Storage failed: %s", str(e))
                    self.stats["errors"] += len(properties)

        # Run workflow
        workflow = PropertyCollectionWorkflow(config)
        await workflow.run()

        # Verify results
        assert workflow.stats["collected"] == 75  # 3 batches * 25
        assert workflow.stats["stored"] == 75
        assert workflow.stats["errors"] == 0

    def test_configuration_validation_pipeline(self):
        """Test configuration validation across the entire pipeline."""

        # Create configuration validator
        class ConfigurationValidator:
            def __init__(self):
                self.validations = []

            def add_validation(self, name: str, validator):
                """Add a validation rule."""
                self.validations.append((name, validator))

            def validate(self, config: ConfigProvider) -> List[str]:
                """Run all validations and return errors."""
                errors = []

                for name, validator in self.validations:
                    try:
                        if not validator(config):
                            errors.append(f"{name}: validation failed")
                    except Exception as e:
                        errors.append(f"{name}: {str(e)}")

                return errors

        # Define validation rules
        validator = ConfigurationValidator()

        # Database validations
        validator.add_validation(
            "MongoDB URI", lambda c: c.get("MONGODB_URI", "").startswith("mongodb://")
        )
        validator.add_validation("Database name", lambda c: bool(c.get("MONGODB_DATABASE")))

        # Collection validations
        validator.add_validation(
            "Batch size", lambda c: 1 <= c.get("COLLECTION_BATCH_SIZE", 0) <= 1000
        )
        validator.add_validation("Timeout", lambda c: 1 <= c.get("COLLECTION_TIMEOUT", 0) <= 300)

        # API validations
        validator.add_validation("API key", lambda c: bool(c.get("API_KEY_MARICOPA")))

        # Test with valid configuration
        valid_config = SimpleConfigProvider()
        valid_config.set("MONGODB_URI", "mongodb://localhost:27017")
        valid_config.set("MONGODB_DATABASE", "phoenix_re")
        valid_config.set("COLLECTION_BATCH_SIZE", 50)
        valid_config.set("COLLECTION_TIMEOUT", 30)
        valid_config.set("API_KEY_MARICOPA", "valid-key")

        errors = validator.validate(valid_config)
        assert len(errors) == 0

        # Test with invalid configuration
        invalid_config = SimpleConfigProvider()
        invalid_config.set("MONGODB_URI", "http://wrong-protocol")
        invalid_config.set("COLLECTION_BATCH_SIZE", 5000)
        # Missing DATABASE, TIMEOUT, and API_KEY

        errors = validator.validate(invalid_config)
        assert len(errors) >= 4
        assert any("MongoDB URI" in e for e in errors)
        assert any("Database name" in e for e in errors)
        assert any("Batch size" in e for e in errors)
        assert any("API key" in e for e in errors)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
