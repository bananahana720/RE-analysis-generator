"""
Production scenario tests for Phoenix Real Estate configuration management.

Tests focus on:
- High-load concurrent access patterns
- Secret rotation without restart
- Configuration reload under load
- Memory usage under sustained access
- Error recovery in production environment
- Production-specific validations
- Performance benchmarks
"""

import concurrent.futures
import gc
import os
import time
import threading
from pathlib import Path
import tempfile

import pytest

from phoenix_real_estate.foundation.config import (
    get_config,
    reset_config_cache,
    Environment,
    EnvironmentFactory,
    ConfigurationError,
    get_secret_manager,
    get_secret,
    SecretManager,
)


@pytest.mark.production
class TestHighLoadConfigurationAccess:
    """Test configuration system under high load conditions."""

    def test_concurrent_read_access_50_threads(self):
        """Test 50+ concurrent threads accessing configuration."""
        reset_config_cache()
        results = []
        errors = []
        start_time = time.time()

        def access_config(thread_id: int):
            try:
                config = get_config()
                # Simulate reading multiple config values
                for _ in range(20):
                    _ = config.environment
                    _ = config.debug
                    _ = config.testing
                    _ = getattr(config, "mongodb_uri", "")
                    _ = getattr(config, "api_key", "")
                results.append((thread_id, time.time() - start_time))
            except Exception as e:
                errors.append((thread_id, str(e)))

        # Run 50 concurrent threads
        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(access_config, i) for i in range(50)]
            concurrent.futures.wait(futures)

        # All threads should succeed
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 50, f"Expected 50 results, got {len(results)}"

        # Performance check: all threads should complete within 1 second
        max_time = max(r[1] for r in results)
        assert max_time < 1.0, f"Concurrent access took too long: {max_time}s"

    def test_high_volume_reads_1000_sequential(self):
        """Test 1000+ sequential configuration reads."""
        reset_config_cache()
        start_time = time.time()

        # Perform 1000 reads
        for i in range(1000):
            config = get_config()
            # Access various properties
            _ = config.environment
            _ = getattr(config, "mongodb_uri", "")
            _ = getattr(config, "database_name", "")

        elapsed = time.time() - start_time

        # Should complete 1000 reads in under 1 second
        assert elapsed < 1.0, f"1000 reads took {elapsed}s"

        # Average read time should be < 1ms
        avg_read_time = elapsed / 1000
        assert avg_read_time < 0.001, f"Average read time {avg_read_time}s exceeds 1ms"

    def test_mixed_read_write_load(self):
        """Test mixed configuration read/write operations under load."""
        reset_config_cache()
        read_count = 0
        write_count = 0
        errors = []

        def reader_thread(thread_id: int):
            nonlocal read_count
            try:
                for _ in range(100):
                    config = get_config()
                    _ = config.environment
                    read_count += 1
            except Exception as e:
                errors.append(("reader", thread_id, str(e)))

        def writer_thread(thread_id: int):
            nonlocal write_count
            try:
                for _ in range(10):
                    reset_config_cache()
                    write_count += 1
                    time.sleep(0.001)  # Small delay to increase contention
            except Exception as e:
                errors.append(("writer", thread_id, str(e)))

        # Run mixed workload
        with concurrent.futures.ThreadPoolExecutor(max_workers=30) as executor:
            # 25 reader threads, 5 writer threads
            futures = []
            for i in range(25):
                futures.append(executor.submit(reader_thread, i))
            for i in range(5):
                futures.append(executor.submit(writer_thread, i))
            concurrent.futures.wait(futures)

        # No errors should occur
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert read_count == 2500  # 25 threads * 100 reads
        assert write_count == 50  # 5 threads * 10 writes


@pytest.mark.production
class TestSecretRotation:
    """Test secret rotation scenarios without application restart."""

    def test_secret_rotation_without_restart(self):
        """Test rotating secrets without restarting the application."""
        # Initial secret setup
        os.environ["SECRET_API_KEY"] = "initial_key_123"
        get_secret_manager()

        # Verify initial secret
        assert get_secret("SECRET_API_KEY") == "initial_key_123"

        # Simulate secret rotation
        os.environ["SECRET_API_KEY"] = "rotated_key_456"

        # Secret should be immediately available
        assert get_secret("SECRET_API_KEY") == "rotated_key_456"

        # Clean up
        del os.environ["SECRET_API_KEY"]

    def test_concurrent_secret_rotation(self):
        """Test secret rotation during concurrent access."""
        os.environ["SECRET_ROTATION_TEST"] = "version_1"
        results = []
        rotation_complete = threading.Event()

        def reader_thread(thread_id: int):
            values_seen = set()
            for _ in range(100):
                value = get_secret("SECRET_ROTATION_TEST")
                if value:
                    values_seen.add(value)
                time.sleep(0.001)
            results.append((thread_id, values_seen))

        def rotator_thread():
            time.sleep(0.05)  # Let readers start
            # Rotate secret
            os.environ["SECRET_ROTATION_TEST"] = "version_2"
            time.sleep(0.05)
            # Rotate again
            os.environ["SECRET_ROTATION_TEST"] = "version_3"
            rotation_complete.set()

        # Run concurrent access during rotation
        with concurrent.futures.ThreadPoolExecutor(max_workers=11) as executor:
            # 10 reader threads
            reader_futures = [executor.submit(reader_thread, i) for i in range(10)]
            # 1 rotator thread
            rotator_future = executor.submit(rotator_thread)

            concurrent.futures.wait(reader_futures + [rotator_future])

        # Verify all threads completed successfully
        assert len(results) == 10

        # Each thread should have seen at least one version
        for thread_id, values in results:
            assert len(values) >= 1, f"Thread {thread_id} saw no values"
            # Should only see valid versions
            assert values.issubset({"version_1", "version_2", "version_3"})

        # Clean up
        del os.environ["SECRET_ROTATION_TEST"]

    def test_encrypted_secret_rotation(self):
        """Test rotation of encrypted secrets."""
        secret_manager = SecretManager(secret_key="test_key_123")

        # Store initial encrypted secret
        secret_manager.store_secret("ENCRYPTED_SECRET", "initial_value", encrypt=True)
        assert secret_manager.get_secret("ENCRYPTED_SECRET") == "initial_value"

        # Rotate to new encrypted value
        secret_manager.store_secret("ENCRYPTED_SECRET", "rotated_value", encrypt=True)
        assert secret_manager.get_secret("ENCRYPTED_SECRET") == "rotated_value"

        # Verify encryption actually happened
        stored_value = secret_manager._secrets["ENCRYPTED_SECRET"]
        assert stored_value.startswith("enc:")
        assert "rotated_value" not in stored_value  # Should be encrypted


@pytest.mark.production
class TestConfigurationReloadUnderLoad:
    """Test configuration reloading while under load."""

    def test_config_reload_during_access(self):
        """Test configuration reload while being accessed."""
        reset_config_cache()
        access_count = 0
        reload_count = 0
        errors = []

        def access_thread(thread_id: int):
            nonlocal access_count
            try:
                for _ in range(100):
                    config = get_config()
                    # Verify config is valid
                    assert config.environment in Environment
                    access_count += 1
                    time.sleep(0.001)
            except Exception as e:
                errors.append(("access", thread_id, str(e)))

        def reload_thread():
            nonlocal reload_count
            try:
                for _ in range(20):
                    reset_config_cache()
                    reload_count += 1
                    time.sleep(0.025)
            except Exception as e:
                errors.append(("reload", 0, str(e)))

        # Run concurrent access and reload
        with concurrent.futures.ThreadPoolExecutor(max_workers=11) as executor:
            futures = []
            # 10 access threads
            for i in range(10):
                futures.append(executor.submit(access_thread, i))
            # 1 reload thread
            futures.append(executor.submit(reload_thread))
            concurrent.futures.wait(futures)

        # Verify no errors
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert access_count == 1000  # 10 threads * 100 accesses
        assert reload_count == 20

    def test_environment_switch_under_load(self):
        """Test switching environments while under load."""
        reset_config_cache()
        results = []
        errors = []

        # Start with development
        os.environ["ENVIRONMENT"] = "development"

        def reader_thread(thread_id: int):
            environments_seen = set()
            try:
                for _ in range(50):
                    config = get_config()
                    environments_seen.add(config.environment)
                    time.sleep(0.002)
                results.append((thread_id, environments_seen))
            except Exception as e:
                errors.append((thread_id, str(e)))

        def switcher_thread():
            time.sleep(0.025)
            os.environ["ENVIRONMENT"] = "production"
            reset_config_cache()
            time.sleep(0.025)
            os.environ["ENVIRONMENT"] = "development"
            reset_config_cache()

        # Run test
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
            futures = []
            for i in range(5):
                futures.append(executor.submit(reader_thread, i))
            futures.append(executor.submit(switcher_thread))
            concurrent.futures.wait(futures)

        # Verify no errors
        assert len(errors) == 0, f"Errors occurred: {errors}"

        # Some threads should have seen environment changes
        all_environments = set()
        for _, envs in results:
            all_environments.update(envs)

        # Should have seen at least development (might miss production due to timing)
        assert Environment.DEVELOPMENT in all_environments


@pytest.mark.production
class TestMemoryUsage:
    """Test memory usage under sustained access patterns."""

    def test_memory_usage_sustained_access(self):
        """Test memory usage doesn't grow unbounded under sustained access."""
        reset_config_cache()

        # Force garbage collection and get baseline
        gc.collect()
        gc.collect()
        gc.collect()

        # Get baseline memory (simplified - in production use tracemalloc)
        initial_objects = len(gc.get_objects())

        # Sustained access pattern
        for i in range(10000):
            config = get_config()
            _ = config.environment
            _ = getattr(config, "mongodb_uri", "")

            # Periodically reset cache to simulate normal operation
            if i % 1000 == 0:
                reset_config_cache()

        # Force garbage collection
        gc.collect()
        gc.collect()
        gc.collect()

        # Check object count hasn't grown significantly
        final_objects = len(gc.get_objects())
        object_growth = final_objects - initial_objects

        # Allow for some growth but should be bounded
        assert object_growth < 1000, f"Too many objects created: {object_growth}"

    def test_secret_manager_memory_usage(self):
        """Test secret manager doesn't leak memory."""
        # Get baseline
        gc.collect()
        initial_objects = len(gc.get_objects())

        # Repeatedly access and store secrets
        secret_manager = get_secret_manager()
        for i in range(1000):
            # Store temporary secrets
            secret_manager.store_secret(f"TEMP_SECRET_{i}", f"value_{i}")

            # Access secrets
            for j in range(10):
                _ = secret_manager.get_secret(f"TEMP_SECRET_{j % (i + 1)}")

            # Clear old secrets periodically
            if i % 100 == 0:
                secret_manager._secrets.clear()

        # Clean up
        secret_manager._secrets.clear()
        gc.collect()

        # Check memory usage
        final_objects = len(gc.get_objects())
        object_growth = final_objects - initial_objects

        assert object_growth < 500, f"Secret manager leaked objects: {object_growth}"


@pytest.mark.production
class TestErrorRecovery:
    """Test error recovery in production scenarios."""

    def test_recovery_from_invalid_config(self):
        """Test recovery when configuration becomes invalid."""
        reset_config_cache()

        # Set invalid environment
        original_env = os.environ.get("ENVIRONMENT")
        os.environ["ENVIRONMENT"] = "invalid_env"

        # Should raise error
        with pytest.raises(Exception):  # InvalidEnvironmentError
            get_config()

        # Fix environment
        os.environ["ENVIRONMENT"] = "production"
        reset_config_cache()

        # Should recover
        config = get_config()
        assert config.environment == Environment.PRODUCTION

        # Restore
        if original_env:
            os.environ["ENVIRONMENT"] = original_env
        else:
            del os.environ["ENVIRONMENT"]

    def test_concurrent_error_recovery(self):
        """Test error recovery during concurrent access."""
        reset_config_cache()
        successes = 0
        failures = 0
        recovered = 0

        def worker_thread(thread_id: int):
            nonlocal successes, failures, recovered

            for i in range(50):
                try:
                    # Randomly inject errors
                    if i == 25 and thread_id % 2 == 0:
                        # Temporarily break config
                        os.environ["ENVIRONMENT"] = "broken"
                        reset_config_cache()

                    config = get_config()
                    assert config is not None
                    successes += 1

                except Exception:
                    failures += 1
                    # Try to recover
                    try:
                        os.environ["ENVIRONMENT"] = "development"
                        reset_config_cache()
                        config = get_config()
                        recovered += 1
                    except:
                        pass

        # Run concurrent workers
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(worker_thread, i) for i in range(10)]
            concurrent.futures.wait(futures)

        # Should have some successes and recoveries
        assert successes > 0
        assert recovered > 0 or failures == 0  # Either recovered or no failures

    def test_secret_validation_error_recovery(self):
        """Test recovery from secret validation errors."""
        secret_manager = get_secret_manager()

        # Test recovery from missing required secrets
        try:
            secret_manager.validate_secrets(["SECRET_REQUIRED_KEY"])
            assert False, "Should have raised validation error"
        except Exception as e:
            assert "Missing" in str(e)

        # Add the required secret
        os.environ["SECRET_REQUIRED_KEY"] = "now_present"

        # Should now pass validation
        secret_manager.validate_secrets(["SECRET_REQUIRED_KEY"])

        # Clean up
        del os.environ["SECRET_REQUIRED_KEY"]


@pytest.mark.production
class TestProductionValidation:
    """Test production-specific validation requirements."""

    def test_production_required_fields(self):
        """Test that production configuration enforces required fields."""
        reset_config_cache()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create minimal production env file
            env_file = Path(tmpdir) / ".env.production"
            env_file.write_text("ENVIRONMENT=production\n")

            # Production should require certain fields
            factory = EnvironmentFactory(root_dir=Path(tmpdir))

            # Set required fields
            os.environ["MONGODB_URI"] = "mongodb://prod-server:27017"
            os.environ["DATABASE_NAME"] = "phoenix_prod"

            config = factory.create_production_config()
            assert config.environment == Environment.PRODUCTION
            assert config.debug is False
            assert config.testing is False

    def test_production_security_validation(self):
        """Test production-specific security validations."""
        # Production should not accept weak API keys
        os.environ["API_KEY"] = "weak"  # Too short

        factory = EnvironmentFactory()
        with pytest.raises(ConfigurationError) as exc_info:
            factory.create_production_config()

        assert "API_KEY must be at least 6 characters" in str(exc_info.value)

        # Clean up
        del os.environ["API_KEY"]

    def test_production_performance_requirements(self):
        """Test production configuration meets performance requirements."""
        reset_config_cache()

        # Time configuration load
        start = time.time()
        config = get_config()
        load_time = time.time() - start

        # Should load in under 100ms
        assert load_time < 0.1, f"Config load took {load_time}s"

        # Time validation
        validator_start = time.time()
        factory = EnvironmentFactory()
        try:
            factory._validate_config(config)
        except:
            pass  # We're testing performance, not correctness
        validation_time = time.time() - validator_start

        # Validation should be under 50ms
        assert validation_time < 0.05, f"Validation took {validation_time}s"


@pytest.mark.production
class TestPerformanceBenchmarks:
    """Performance benchmarks for production use."""

    def test_config_load_time_benchmark(self):
        """Benchmark configuration load time."""
        reset_config_cache()

        # Warm up
        for _ in range(10):
            reset_config_cache()
            get_config()

        # Benchmark
        times = []
        for _ in range(100):
            reset_config_cache()
            start = time.time()
            get_config()
            elapsed = time.time() - start
            times.append(elapsed)

        # Calculate statistics
        avg_time = sum(times) / len(times)
        max_time = max(times)
        min_time = min(times)

        # Performance requirements
        assert avg_time < 0.01, f"Average load time {avg_time}s exceeds 10ms"
        assert max_time < 0.1, f"Max load time {max_time}s exceeds 100ms"
        assert min_time < 0.005, f"Min load time {min_time}s exceeds 5ms"

    def test_secret_access_benchmark(self):
        """Benchmark secret access performance."""
        # Setup secrets
        for i in range(100):
            os.environ[f"SECRET_BENCH_{i}"] = f"value_{i}"

        secret_manager = get_secret_manager()

        # Benchmark secret access
        start = time.time()
        for _ in range(1000):
            for i in range(10):
                _ = secret_manager.get_secret(f"SECRET_BENCH_{i}")
        elapsed = time.time() - start

        # 10,000 secret accesses
        avg_access_time = elapsed / 10000

        # Should be very fast (< 0.1ms per access)
        assert avg_access_time < 0.0001, f"Secret access too slow: {avg_access_time}s"

        # Cleanup
        for i in range(100):
            del os.environ[f"SECRET_BENCH_{i}"]

    def test_concurrent_performance_benchmark(self):
        """Benchmark performance under concurrent load."""
        reset_config_cache()

        total_operations = 0
        start_time = time.time()

        def worker(thread_id: int) -> int:
            operations = 0
            thread_start = time.time()

            while time.time() - thread_start < 1.0:  # Run for 1 second
                config = get_config()
                _ = config.environment
                _ = get_secret(f"SECRET_KEY_{thread_id % 10}", "default")
                operations += 1

            return operations

        # Run concurrent benchmark
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(worker, i) for i in range(20)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        total_operations = sum(results)
        elapsed = time.time() - start_time

        # Calculate throughput
        ops_per_second = total_operations / elapsed

        # Should handle at least 10,000 ops/second with 20 threads
        assert ops_per_second > 10000, f"Throughput too low: {ops_per_second} ops/s"


# Fixture to clean up environment after tests
@pytest.fixture(autouse=True)
def cleanup_environment():
    """Clean up environment variables after each test."""
    # Store original environment
    original_env = dict(os.environ)

    yield

    # Restore environment
    # Remove any added keys
    for key in list(os.environ.keys()):
        if key not in original_env:
            del os.environ[key]

    # Restore original values
    for key, value in original_env.items():
        os.environ[key] = value

    # Reset config cache
    reset_config_cache()
