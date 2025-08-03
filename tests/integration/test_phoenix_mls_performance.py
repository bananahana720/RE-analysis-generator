"""Integration tests for Phoenix MLS scraper performance validation.

Tests the performance validator to ensure it correctly measures throughput,
success rates, and resource usage.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta, UTC

from scripts.validation.validate_phoenix_mls_performance import PerformanceValidator


class TestPerformanceValidator:
    """Test suite for performance validator."""

    @pytest.fixture
    def validator_config(self):
        """Standard configuration for testing."""
        return {
            "target_properties_per_hour": 1000,
            "test_duration_minutes": 5,
            "sample_interval_seconds": 10,
            "test_zipcodes": ["85001", "85003", "85004"],
        }

    @pytest.fixture
    def validator(self, validator_config):
        """Create validator instance."""
        return PerformanceValidator(validator_config)

    @pytest.fixture
    def mock_scraper(self):
        """Create mock Phoenix MLS scraper."""
        scraper = AsyncMock()

        # Mock rate limiter
        scraper.rate_limiter = Mock()
        scraper.rate_limiter.get_current_usage.return_value = {
            "is_rate_limited": False,
            "current_requests": 50,
            "effective_limit": 60,
        }

        # Mock statistics
        scraper.get_statistics.return_value = {
            "total_requests": 100,
            "successful_requests": 95,
            "failed_requests": 5,
            "success_rate": 95.0,
        }

        return scraper

    def test_initialization(self, validator, validator_config):
        """Test validator initialization."""
        assert validator.target_properties_per_hour == 1000
        assert validator.test_duration_minutes == 5
        assert validator.sample_interval_seconds == 10
        assert len(validator.test_zipcodes) == 3
        assert validator.metrics["total_properties_scraped"] == 0

    def test_update_throughput(self, validator):
        """Test throughput tracking."""
        # Update throughput
        validator._update_throughput(10)
        validator._update_throughput(15)

        # Check tracking
        current_minute = datetime.now().replace(second=0, microsecond=0)
        assert validator.properties_per_minute[current_minute] == 25

    def test_should_continue(self, validator):
        """Test continuation logic."""
        # Before start
        assert validator._should_continue() is True

        # Set start time
        validator.metrics["start_time"] = datetime.now(UTC)
        assert validator._should_continue() is True

        # Simulate elapsed time
        validator.metrics["start_time"] = datetime.now(UTC) - timedelta(minutes=10)
        validator.test_duration_minutes = 5
        assert validator._should_continue() is False

    def test_generate_recommendations(self, validator):
        """Test recommendation generation."""
        # Below target throughput
        recommendations = validator._generate_recommendations(actual_rate=500, success_rate=95)
        assert any("below target" in rec for rec in recommendations)

        # Low success rate
        recommendations = validator._generate_recommendations(actual_rate=1200, success_rate=80)
        assert any("Success rate" in rec for rec in recommendations)

        # Rate limiting occurred
        validator.metrics["rate_limited_events"] = 5
        recommendations = validator._generate_recommendations(actual_rate=1200, success_rate=98)
        assert any("Rate limiting" in rec for rec in recommendations)

        # High resource usage
        validator.metrics["cpu_usage_samples"] = [85, 90, 88, 92]
        validator.metrics["memory_usage_samples"] = [1500, 1600, 1550]
        recommendations = validator._generate_recommendations(actual_rate=1200, success_rate=98)
        assert any("CPU usage" in rec for rec in recommendations)
        assert any("memory usage" in rec for rec in recommendations)

    def test_generate_report(self, validator):
        """Test report generation."""
        # Set up metrics
        validator.metrics["start_time"] = datetime.now(UTC) - timedelta(hours=1)
        validator.metrics["end_time"] = datetime.now(UTC)
        validator.metrics["total_properties_scraped"] = 1100
        validator.metrics["total_properties_attempted"] = 1150
        validator.metrics["successful_requests"] = 1100
        validator.metrics["failed_requests"] = 50
        validator.metrics["throughput_samples"] = [1050, 1100, 1150]
        validator.metrics["response_times"] = [0.5, 0.6, 0.7, 0.8, 0.9]
        validator.metrics["cpu_usage_samples"] = [20, 25, 30]
        validator.metrics["memory_usage_samples"] = [200, 250, 300]

        # Generate report
        report = validator._generate_report()

        # Validate summary
        assert report["summary"]["test_passed"] is True
        assert report["summary"]["actual_properties_per_hour"] == 1100
        assert report["summary"]["success_rate"] > 95

        # Validate throughput metrics
        assert report["throughput"]["properties_per_hour"] == 1100
        assert report["throughput"]["properties_per_minute"] > 18

        # Validate performance metrics
        assert report["performance"]["avg_response_time_seconds"] == 0.7
        assert report["performance"]["avg_cpu_percent"] == 25
        assert report["performance"]["avg_memory_mb"] == 250

    @pytest.mark.asyncio
    async def test_scraping_task_success(self, validator, mock_scraper):
        """Test successful scraping task execution."""
        # Mock search results
        mock_scraper.search_properties_by_zipcode.return_value = [
            {"url": f"https://example.com/property/{i}"} for i in range(50)
        ]

        # Mock batch scraping
        mock_scraper.scrape_properties_batch.return_value = [
            {"url": f"https://example.com/property/{i}", "data": "test"} for i in range(20)
        ]

        # Run one iteration
        validator.running = True
        validator.test_duration_minutes = 0.1  # Very short for testing
        validator.metrics["start_time"] = datetime.now(UTC)

        # Create task and run briefly
        task = asyncio.create_task(validator._scraping_task(mock_scraper))
        await asyncio.sleep(0.1)
        validator.running = False

        try:
            await task
        except Exception:
            pass  # Task might be cancelled

        # Verify calls were made
        assert mock_scraper.search_properties_by_zipcode.called
        assert mock_scraper.scrape_properties_batch.called

    @pytest.mark.asyncio
    async def test_scraping_task_error_handling(self, validator, mock_scraper):
        """Test error handling in scraping task."""
        # Mock search to raise error
        mock_scraper.search_properties_by_zipcode.side_effect = Exception("Test error")

        # Run one iteration
        validator.running = True
        validator.test_duration_minutes = 0.1
        validator.metrics["start_time"] = datetime.now(UTC)

        # Create task and run briefly
        task = asyncio.create_task(validator._scraping_task(mock_scraper))
        await asyncio.sleep(0.1)
        validator.running = False

        try:
            await task
        except Exception:
            pass

        # Check error was recorded
        assert validator.metrics["failed_requests"] > 0
        assert "Exception" in validator.metrics["error_types"]

    @pytest.mark.asyncio
    async def test_monitoring_task(self, validator):
        """Test resource monitoring task."""
        # Mock process CPU and memory
        with patch.object(validator.process, "cpu_percent", return_value=25.5):
            with patch.object(validator.process, "memory_info") as mock_memory:
                mock_memory.return_value = MagicMock(rss=524288000)  # 500MB

                # Run monitoring briefly
                validator.running = True
                validator.sample_interval_seconds = 0.1

                task = asyncio.create_task(validator._monitoring_task())
                await asyncio.sleep(0.3)
                validator.running = False

                try:
                    await task
                except Exception:
                    pass

                # Check samples were collected
                assert len(validator.metrics["cpu_usage_samples"]) > 0
                assert len(validator.metrics["memory_usage_samples"]) > 0
                assert validator.metrics["cpu_usage_samples"][0] == 25.5
                assert validator.metrics["memory_usage_samples"][0] == 500.0

    @pytest.mark.asyncio
    async def test_throughput_monitor(self, validator):
        """Test throughput monitoring."""
        # Set up initial metrics
        validator.metrics["start_time"] = datetime.now(UTC) - timedelta(minutes=30)
        validator.metrics["total_properties_scraped"] = 500
        validator.running = True

        # Run monitor briefly
        task = asyncio.create_task(validator._throughput_monitor())
        await asyncio.sleep(0.1)
        validator.running = False

        try:
            await task
        except Exception:
            pass

        # Check throughput was calculated
        assert len(validator.metrics["throughput_samples"]) > 0
        assert validator.metrics["throughput_samples"][0] == 1000  # 500 in 0.5 hours

    def test_load_scraper_config(self, validator):
        """Test scraper configuration loading."""
        config = validator._load_scraper_config()

        assert config["base_url"] == "https://www.phoenixmlssearch.com"
        assert config["search_endpoint"] == "/search"
        assert config["rate_limit"]["requests_per_minute"] == 60
        assert config["rate_limit"]["safety_margin"] == 0.1

    @pytest.mark.asyncio
    async def test_rate_limit_detection(self, validator, mock_scraper):
        """Test rate limit detection and compliance tracking."""
        # Mock rate limiter to show rate limited state
        mock_scraper.rate_limiter.get_current_usage.return_value = {
            "is_rate_limited": True,
            "current_requests": 60,
            "effective_limit": 60,
        }

        # Mock successful search
        mock_scraper.search_properties_by_zipcode.return_value = [
            {"url": "https://example.com/property/1"}
        ]
        mock_scraper.scrape_properties_batch.return_value = []

        # Run one iteration
        validator.running = True
        validator.metrics["start_time"] = datetime.now(UTC)

        task = asyncio.create_task(validator._scraping_task(mock_scraper))
        await asyncio.sleep(0.1)
        validator.running = False

        try:
            await task
        except Exception:
            pass

        # Check rate limit was detected
        assert validator.metrics["rate_limited_events"] > 0
        assert validator.metrics["rate_limit_compliance"] is False

    def test_performance_target_evaluation(self, validator):
        """Test performance target evaluation logic."""
        # Test passing scenario
        validator.metrics["start_time"] = datetime.now(UTC) - timedelta(hours=1)
        validator.metrics["end_time"] = datetime.now(UTC)
        validator.metrics["total_properties_scraped"] = 1200

        report = validator._generate_report()
        assert report["summary"]["test_passed"] is True

        # Test failing scenario
        validator.metrics["total_properties_scraped"] = 800

        report = validator._generate_report()
        assert report["summary"]["test_passed"] is False


@pytest.mark.integration
class TestPerformanceValidatorIntegration:
    """Integration tests with real components."""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_short_validation_run(self):
        """Test a short validation run with mocked scraper."""
        config = {
            "target_properties_per_hour": 1000,
            "test_duration_minutes": 0.1,  # 6 seconds
            "sample_interval_seconds": 2,
            "test_zipcodes": ["85001"],
        }

        validator = PerformanceValidator(config)

        # Mock the scraper initialization
        with patch("scripts.validate_phoenix_mls_performance.PhoenixMLSScraper") as MockScraper:
            mock_instance = AsyncMock()
            MockScraper.return_value = mock_instance

            # Setup mock behaviors
            mock_instance.initialize_browser = AsyncMock()
            mock_instance.close_browser = AsyncMock()
            mock_instance.search_properties_by_zipcode.return_value = [
                {"url": f"https://example.com/{i}"} for i in range(10)
            ]
            mock_instance.scrape_properties_batch.return_value = [
                {"url": f"https://example.com/{i}", "price": "$500,000"} for i in range(5)
            ]
            mock_instance.rate_limiter = Mock()
            mock_instance.rate_limiter.get_current_usage.return_value = {"is_rate_limited": False}
            mock_instance.get_statistics.return_value = {"success_rate": 95.0}

            # Run validation
            report = await validator.run_validation()

            # Verify basic execution
            assert report is not None
            assert "summary" in report
            assert "throughput" in report
            assert "performance" in report
            assert mock_instance.initialize_browser.called
            assert mock_instance.close_browser.called
