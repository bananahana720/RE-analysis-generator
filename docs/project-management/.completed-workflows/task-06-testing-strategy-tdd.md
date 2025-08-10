# Task 06: LLM Data Processing - Test-Driven Development Strategy

## TDD Philosophy: Tests Drive LLM Integration

### Core TDD Principles for AI/LLM Systems
1. **Deterministic Testing First**: Test predictable components before LLM integration
2. **Mock-Driven Development**: Use mock LLM responses to define expected behavior
3. **Accuracy as Code**: Define extraction accuracy requirements through tests
4. **Fallback by Design**: Error paths tested before happy paths
5. **Performance from Start**: Speed requirements drive implementation

### The LLM TDD Cycle
```
     ┌─────────────┐
     │   1. RED    │ Write test with mock LLM response
     │   (Fail)    │ defining expected extraction
     └──────┬──────┘
            │
     ┌──────▼──────┐
     │  2. GREEN   │ Implement extraction logic
     │   (Pass)    │ to handle mock response
     └──────┬──────┘
            │
     ┌──────▼──────┐
     │ 3. REFACTOR │ Optimize prompts and parsing
     │  (Clean)    │ while maintaining accuracy
     └──────┬──────┘
            │
     ┌──────▼──────┐
     │ 4. VALIDATE │ Test with real Ollama
     │   (Real)    │ verify accuracy metrics
     └──────┬──────┘
            │
            └────────────┐
                        │
                 (Repeat for next feature)
```

## TDD Workflow for LLM Processing

### Starting with Ollama Client: Connection Management

#### Step 1: Write the First Failing Test (RED)
```python
# tests/processors/llm/test_ollama_client.py

import pytest
from phoenix_real_estate.processors.llm.ollama_client import OllamaClient

class TestOllamaClient:
    """Test-driven development of Ollama integration."""
    
    def test_ollama_client_exists(self):
        """First test: OllamaClient class should exist."""
        # This will fail - OllamaClient doesn't exist yet
        client = OllamaClient()
        assert client is not None
```

Run test: `uv run pytest tests/processors/llm/test_ollama_client.py::TestOllamaClient::test_ollama_client_exists -v`

**Expected Result**: ImportError - OllamaClient doesn't exist

#### Step 2: Make it Pass with Minimal Code (GREEN)
```python
# src/phoenix_real_estate/processors/llm/ollama_client.py

class OllamaClient:
    """Minimal implementation to make test pass."""
    pass
```

#### Step 3: Test Health Check Requirements
```python
async def test_ollama_health_check_when_running(self):
    """Ollama client should verify Ollama is running."""
    client = OllamaClient(base_url="http://localhost:11434")
    
    # This drives the health check API
    is_healthy = await client.health_check()
    assert isinstance(is_healthy, bool)

async def test_ollama_health_check_when_not_running(self):
    """Should handle Ollama not running gracefully."""
    client = OllamaClient(base_url="http://localhost:99999")
    
    is_healthy = await client.health_check()
    assert is_healthy is False
```

#### Step 4: Test Model Availability
```python
async def test_check_model_availability(self):
    """Should verify required models are available."""
    client = OllamaClient()
    
    # This will fail - method doesn't exist
    available = await client.is_model_available("llama3.2")
    assert isinstance(available, bool)

async def test_list_available_models(self):
    """Should list all available models for selection."""
    client = OllamaClient()
    
    models = await client.list_models()
    assert isinstance(models, list)
    # When Ollama running, should have at least one model
    if await client.health_check():
        assert len(models) > 0
```

### Testing LLM Response Processing

#### Pattern 1: Mock-First Development
```python
class TestLLMResponseParsing:
    """Define expected LLM behavior through mocks."""
    
    @pytest.fixture
    def mock_property_extraction_response(self):
        """Mock Ollama response for property data extraction."""
        return {
            "response": """{
                "address": "123 Main St, Phoenix, AZ 85001",
                "price": 450000,
                "bedrooms": 3,
                "bathrooms": 2.5,
                "square_feet": 1850,
                "lot_size": 6500,
                "year_built": 2015,
                "property_type": "Single Family",
                "listing_status": "Active",
                "mls_number": "MLS123456",
                "extraction_confidence": 0.95
            }""",
            "model": "llama3.2",
            "done": True,
            "total_duration": 1523000000,  # 1.523 seconds
            "prompt_eval_duration": 234000000,
            "eval_duration": 1289000000
        }
    
    async def test_parse_property_extraction(self, mock_property_extraction_response):
        """Test parsing of LLM property extraction response."""
        parser = LLMResponseParser()
        
        # Parse the mock response
        result = parser.parse_property_extraction(mock_property_extraction_response)
        
        # Verify all fields extracted correctly
        assert result.address == "123 Main St, Phoenix, AZ 85001"
        assert result.price == 450000
        assert result.bedrooms == 3
        assert result.bathrooms == 2.5
        assert result.square_feet == 1850
        assert result.lot_size == 6500
        assert result.year_built == 2015
        assert result.property_type == "Single Family"
        assert result.listing_status == "Active"
        assert result.mls_number == "MLS123456"
        assert result.confidence >= 0.9  # High confidence requirement
        
        # Performance requirements
        assert result.processing_time < 2.0  # Under 2 seconds
```

#### Pattern 2: Prompt Engineering Through Tests
```python
class TestPromptGeneration:
    """Test-driven prompt engineering."""
    
    def test_property_extraction_prompt_structure(self):
        """Define the structure of property extraction prompts."""
        generator = PromptGenerator()
        
        html_content = "<div>Sample property listing HTML</div>"
        prompt = generator.create_property_extraction_prompt(html_content)
        
        # Prompt should have clear instructions
        assert "Extract the following property information" in prompt
        assert "Return as valid JSON" in prompt
        assert "Required fields:" in prompt
        
        # Should specify all required fields
        required_fields = [
            "address", "price", "bedrooms", "bathrooms",
            "square_feet", "lot_size", "year_built",
            "property_type", "listing_status", "mls_number"
        ]
        for field in required_fields:
            assert field in prompt
        
        # Should include confidence scoring
        assert "extraction_confidence" in prompt
        assert "0.0 to 1.0" in prompt
    
    def test_prompt_includes_examples(self):
        """Prompts should include few-shot examples."""
        generator = PromptGenerator()
        
        prompt = generator.create_property_extraction_prompt("<html>...</html>")
        
        # Should have at least one example
        assert "Example:" in prompt or "For example:" in prompt
        assert '"address": "' in prompt  # Example JSON structure
```

#### Pattern 3: Accuracy Testing with Fixtures
```python
class TestExtractionAccuracy:
    """Test extraction accuracy against known data."""
    
    @pytest.fixture
    def property_test_cases(self):
        """Real property listings with verified data."""
        return [
            {
                "html": """<div class="property-details">
                    <h1>123 Main St, Phoenix, AZ 85001</h1>
                    <span class="price">$450,000</span>
                    <div class="specs">
                        <span>3 beds</span> | <span>2.5 baths</span> |
                        <span>1,850 sqft</span>
                    </div>
                    <div class="lot">Lot: 6,500 sqft</div>
                    <div class="year">Built in 2015</div>
                </div>""",
                "expected": {
                    "address": "123 Main St, Phoenix, AZ 85001",
                    "price": 450000,
                    "bedrooms": 3,
                    "bathrooms": 2.5,
                    "square_feet": 1850,
                    "lot_size": 6500,
                    "year_built": 2015
                }
            },
            # Add more test cases for different formats
        ]
    
    async def test_extraction_accuracy_target(self, property_test_cases):
        """Test that extraction meets 90% accuracy target."""
        extractor = PropertyExtractor(ollama_client=MockOllamaClient())
        
        correct_extractions = 0
        total_fields = 0
        
        for test_case in property_test_cases:
            result = await extractor.extract(test_case["html"])
            expected = test_case["expected"]
            
            # Check each field
            for field, expected_value in expected.items():
                total_fields += 1
                if getattr(result, field) == expected_value:
                    correct_extractions += 1
        
        accuracy = correct_extractions / total_fields
        assert accuracy >= 0.9, f"Accuracy {accuracy:.2%} below 90% target"
```

### Testing Fallback Mechanisms

#### Test-Driven Fallback Implementation
```python
class TestFallbackMechanisms:
    """Drive fallback behavior through tests."""
    
    async def test_llm_timeout_triggers_fallback(self):
        """When LLM times out, should use regex fallback."""
        # Configure mock to simulate timeout
        mock_ollama = Mock()
        mock_ollama.generate.side_effect = asyncio.TimeoutError()
        
        extractor = PropertyExtractor(
            ollama_client=mock_ollama,
            timeout=2.0
        )
        
        html = '<span class="price">$450,000</span>'
        result = await extractor.extract(html)
        
        # Should still extract price via fallback
        assert result.price == 450000
        assert result.extraction_method == "regex_fallback"
        assert result.confidence < 0.8  # Lower confidence for fallback
    
    async def test_llm_parse_error_triggers_fallback(self):
        """When LLM returns invalid JSON, use fallback."""
        mock_ollama = Mock()
        mock_ollama.generate.return_value = {
            "response": "This is not valid JSON",
            "done": True
        }
        
        extractor = PropertyExtractor(ollama_client=mock_ollama)
        
        html = '''
            <h1>123 Main St</h1>
            <div class="price">$450,000</div>
            <span>3 beds | 2 baths</span>
        '''
        
        result = await extractor.extract(html)
        
        # Fallback should extract what it can
        assert result.address == "123 Main St"
        assert result.price == 450000
        assert result.bedrooms == 3
        assert result.bathrooms == 2
        assert result.extraction_method == "regex_fallback"
    
    async def test_fallback_success_rate(self):
        """Fallback should achieve >70% success rate."""
        fallback = RegexFallbackExtractor()
        
        test_cases = load_test_cases("fallback_test_cases.json")
        successful_extractions = 0
        
        for test_case in test_cases:
            result = fallback.extract(test_case["html"])
            
            # Count as success if critical fields extracted
            critical_fields = ["address", "price", "bedrooms"]
            if all(getattr(result, field) is not None for field in critical_fields):
                successful_extractions += 1
        
        success_rate = successful_extractions / len(test_cases)
        assert success_rate >= 0.7, f"Fallback success rate {success_rate:.2%} below 70% target"
```

### Testing Performance Requirements

#### Performance Testing Patterns
```python
class TestPerformanceRequirements:
    """Ensure processing meets speed requirements."""
    
    @pytest.mark.performance
    async def test_single_property_processing_time(self):
        """Single property must process in <2 seconds."""
        extractor = PropertyExtractor()
        
        html = load_fixture("sample_property.html")
        
        start_time = time.time()
        result = await extractor.extract(html)
        processing_time = time.time() - start_time
        
        assert processing_time < 2.0, f"Processing took {processing_time:.2f}s (max 2s)"
        assert result is not None
    
    @pytest.mark.performance
    async def test_batch_processing_efficiency(self):
        """Test batch processing meets performance targets."""
        processor = BatchProcessor()
        
        # Load 100 property HTMLs
        properties = [load_fixture(f"property_{i}.html") for i in range(100)]
        
        start_time = time.time()
        results = await processor.process_batch(properties, max_concurrent=5)
        total_time = time.time() - start_time
        
        # Should process 100 properties in reasonable time
        avg_time = total_time / len(properties)
        assert avg_time < 2.0, f"Average {avg_time:.2f}s per property"
        
        # With concurrency, total should be much less than serial
        assert total_time < len(properties) * 0.5  # 50% of serial time
    
    async def test_memory_usage_under_load(self):
        """Memory usage should stay reasonable under load."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        processor = BatchProcessor()
        
        # Process large batch
        for i in range(10):
            batch = [load_fixture("large_property.html") for _ in range(50)]
            await processor.process_batch(batch)
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Should not leak memory excessively
        assert memory_increase < 500, f"Memory increased by {memory_increase}MB"
```

### Test Infrastructure

#### Mock Ollama Responses
```python
# tests/processors/llm/fixtures/mock_responses.py

class MockOllamaResponses:
    """Predefined Ollama responses for testing."""
    
    SUCCESSFUL_EXTRACTION = {
        "response": json.dumps({
            "address": "123 Test St, Phoenix, AZ 85001",
            "price": 450000,
            "bedrooms": 3,
            "bathrooms": 2,
            "square_feet": 1800,
            "lot_size": 6000,
            "year_built": 2020,
            "property_type": "Single Family",
            "listing_status": "Active",
            "mls_number": "TEST123",
            "extraction_confidence": 0.95
        }),
        "done": True,
        "total_duration": 1500000000
    }
    
    PARTIAL_EXTRACTION = {
        "response": json.dumps({
            "address": "456 Incomplete Ave",
            "price": 500000,
            "bedrooms": None,  # Missing data
            "extraction_confidence": 0.6
        }),
        "done": True,
        "total_duration": 1200000000
    }
    
    MALFORMED_RESPONSE = {
        "response": "This is not JSON {invalid: json}",
        "done": True,
        "total_duration": 800000000
    }
    
    TIMEOUT_RESPONSE = None  # Simulates timeout

class MockOllamaClient:
    """Mock Ollama client for deterministic testing."""
    
    def __init__(self, response_type="success"):
        self.response_type = response_type
        self.call_count = 0
    
    async def generate(self, model, prompt):
        self.call_count += 1
        
        if self.response_type == "timeout":
            await asyncio.sleep(3)  # Simulate timeout
            raise asyncio.TimeoutError()
        
        responses = {
            "success": MockOllamaResponses.SUCCESSFUL_EXTRACTION,
            "partial": MockOllamaResponses.PARTIAL_EXTRACTION,
            "malformed": MockOllamaResponses.MALFORMED_RESPONSE,
        }
        
        return responses.get(self.response_type, MockOllamaResponses.SUCCESSFUL_EXTRACTION)
```

#### Test Fixtures for Various HTML Formats
```python
# tests/processors/llm/fixtures/html_fixtures.py

class HTMLFixtures:
    """Various HTML formats found in real estate sites."""
    
    STANDARD_MLS_FORMAT = """
    <div class="listing-detail-page">
        <div class="property-header">
            <h1 class="address">123 Main Street, Phoenix, AZ 85001</h1>
            <div class="price-container">
                <span class="currency">$</span>
                <span class="price">450,000</span>
            </div>
        </div>
        <div class="property-features">
            <div class="feature-group">
                <span class="beds">3</span> Bedrooms
                <span class="baths">2.5</span> Bathrooms
                <span class="sqft">1,850</span> Sq Ft
            </div>
            <div class="lot-info">
                Lot Size: <span class="lot-size">6,500</span> Sq Ft
            </div>
            <div class="year-info">
                Year Built: <span class="year">2015</span>
            </div>
        </div>
    </div>
    """
    
    TABLE_FORMAT = """
    <table class="property-details">
        <tr><td>Address:</td><td>456 Elm St, Phoenix, AZ 85033</td></tr>
        <tr><td>Price:</td><td>$325,000</td></tr>
        <tr><td>Beds/Baths:</td><td>4 / 3</td></tr>
        <tr><td>Square Feet:</td><td>2,100</td></tr>
        <tr><td>Lot Size:</td><td>0.25 acres</td></tr>
        <tr><td>Built:</td><td>2018</td></tr>
    </table>
    """
    
    MINIMAL_FORMAT = """
    <div>
        123 Simple St $400K 3BR/2BA 1,500sqft
    </div>
    """
    
    COMPLEX_FORMAT_WITH_NOISE = """
    <div class="page-wrapper">
        <!-- Advertisement -->
        <div class="ad">Buy now! Special offer!</div>
        
        <article class="listing">
            <header>
                <h2>Beautiful Home at 789 Complex Rd, Phoenix, AZ 85035</h2>
                <div class="pricing">
                    <span class="original-price">$550,000</span>
                    <span class="sale-price">$525,000</span>
                    <span class="price-drop">$25,000 Price Drop!</span>
                </div>
            </header>
            
            <section class="details">
                <p>This stunning 4 bedroom, 3.5 bathroom home offers 2,450 square feet 
                of living space on a spacious 8,000 square foot lot.</p>
                <p>Built in 2019, this modern home features...</p>
            </section>
            
            <!-- More ads and noise -->
            <div class="related-listings">See similar homes...</div>
        </article>
    </div>
    """
```

#### Performance Benchmarks
```python
# tests/processors/llm/benchmarks/performance_benchmarks.py

class PerformanceBenchmarks:
    """Performance benchmarks for LLM processing."""
    
    TIMING_REQUIREMENTS = {
        "ollama_health_check": 0.1,  # 100ms
        "model_check": 0.2,  # 200ms
        "single_extraction": 2.0,  # 2 seconds
        "batch_extraction_per_item": 1.5,  # 1.5s average with concurrency
        "fallback_extraction": 0.5,  # 500ms for regex fallback
    }
    
    ACCURACY_REQUIREMENTS = {
        "llm_extraction": 0.9,  # 90% accuracy
        "fallback_extraction": 0.7,  # 70% accuracy
        "critical_fields": 0.95,  # 95% for address and price
    }
    
    RESOURCE_LIMITS = {
        "memory_per_extraction_mb": 50,
        "max_concurrent_extractions": 5,
        "max_retry_attempts": 3,
    }

@pytest.fixture
def performance_monitor():
    """Monitor performance during tests."""
    class PerformanceMonitor:
        def __init__(self):
            self.start_time = None
            self.measurements = []
        
        def start(self):
            self.start_time = time.time()
        
        def record(self, operation):
            duration = time.time() - self.start_time
            self.measurements.append((operation, duration))
            return duration
        
        def assert_within_limit(self, operation, limit):
            duration = self.record(operation)
            assert duration < limit, f"{operation} took {duration:.2f}s (limit: {limit}s)"
    
    return PerformanceMonitor()
```

#### Error Scenario Simulations
```python
# tests/processors/llm/scenarios/error_scenarios.py

class ErrorScenarios:
    """Simulate various error conditions."""
    
    @staticmethod
    async def simulate_ollama_not_running():
        """Simulate Ollama service not running."""
        return ConnectionError("Cannot connect to Ollama at localhost:11434")
    
    @staticmethod
    async def simulate_model_not_available():
        """Simulate requested model not downloaded."""
        return {
            "error": "model 'llama3.2' not found, try pulling it first"
        }
    
    @staticmethod
    async def simulate_ollama_overloaded():
        """Simulate Ollama being overloaded."""
        await asyncio.sleep(5)  # Simulate slow response
        return {
            "error": "server is busy, please try again later"
        }
    
    @staticmethod
    async def simulate_corrupt_response():
        """Simulate corrupted/incomplete response."""
        return {
            "response": '{"address": "123 Main St", "price": 45',  # Truncated JSON
            "done": False,
            "error": "connection lost"
        }

class TestErrorHandling:
    """Test error handling using scenarios."""
    
    async def test_handle_ollama_not_running(self):
        """Should gracefully handle Ollama not running."""
        client = OllamaClient()
        client._make_request = ErrorScenarios.simulate_ollama_not_running
        
        extractor = PropertyExtractor(ollama_client=client)
        result = await extractor.extract("<html>...</html>")
        
        # Should fall back to regex
        assert result.extraction_method == "regex_fallback"
        assert result.errors == ["Ollama service not available"]
    
    async def test_handle_model_not_available(self):
        """Should handle missing model gracefully."""
        client = OllamaClient()
        
        with patch.object(client, 'generate') as mock_generate:
            mock_generate.side_effect = Exception("model 'llama3.2' not found")
            
            extractor = PropertyExtractor(ollama_client=client)
            result = await extractor.extract("<html>...</html>")
            
            assert result.extraction_method == "regex_fallback"
            assert "model" in result.errors[0].lower()
```

### Test Execution Strategy

#### Local Ollama Setup for CI/CD
```yaml
# .github/workflows/llm-tests.yml
name: LLM Processing Tests

on:
  pull_request:
    paths:
      - 'src/phoenix_real_estate/processors/**'
      - 'tests/processors/**'

jobs:
  test-with-ollama:
    runs-on: ubuntu-latest
    
    services:
      ollama:
        image: ollama/ollama:latest
        ports:
          - 11434:11434
        options: --health-cmd "curl -f http://localhost:11434/api/tags || exit 1"
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.13'
      
      - name: Install dependencies
        run: |
          pip install uv
          uv sync
      
      - name: Pull Ollama model
        run: |
          curl -X POST http://localhost:11434/api/pull \
            -d '{"name": "llama3.2", "stream": false}'
      
      - name: Run unit tests with mocks
        run: |
          uv run pytest tests/processors/llm/unit/ -v \
            --mock-ollama
      
      - name: Run integration tests with real Ollama
        run: |
          uv run pytest tests/processors/llm/integration/ -v \
            --real-ollama
      
      - name: Run performance tests
        run: |
          uv run pytest tests/processors/llm/performance/ -v \
            --benchmark-only
      
      - name: Generate accuracy report
        run: |
          uv run python scripts/test_accuracy.py \
            --test-data tests/fixtures/accuracy_test_set.json \
            --output accuracy_report.json
      
      - name: Check accuracy thresholds
        run: |
          python -c "
          import json
          with open('accuracy_report.json') as f:
              report = json.load(f)
          assert report['overall_accuracy'] >= 0.9
          assert report['fallback_success_rate'] >= 0.7
          "
```

#### Mock vs Real LLM Testing Strategy
```python
# tests/conftest.py

def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--mock-ollama",
        action="store_true",
        help="Use mock Ollama client for faster tests"
    )
    parser.addoption(
        "--real-ollama",
        action="store_true",
        help="Use real Ollama for integration tests"
    )

@pytest.fixture
def ollama_client(request):
    """Provide appropriate Ollama client based on test mode."""
    if request.config.getoption("--mock-ollama"):
        return MockOllamaClient()
    elif request.config.getoption("--real-ollama"):
        client = OllamaClient()
        # Skip if Ollama not running
        if not asyncio.run(client.health_check()):
            pytest.skip("Ollama not running")
        return client
    else:
        # Default to mock for unit tests
        return MockOllamaClient()

# Usage in tests:
async def test_extraction(ollama_client):
    """Test works with both mock and real Ollama."""
    extractor = PropertyExtractor(ollama_client=ollama_client)
    result = await extractor.extract(sample_html)
    assert result.address is not None
```

#### Continuous Accuracy Monitoring
```python
# scripts/monitor_accuracy.py
"""Monitor extraction accuracy over time."""

import json
from datetime import datetime
from pathlib import Path

class AccuracyMonitor:
    """Track extraction accuracy metrics."""
    
    def __init__(self, history_file="accuracy_history.json"):
        self.history_file = Path(history_file)
        self.history = self.load_history()
    
    def load_history(self):
        """Load historical accuracy data."""
        if self.history_file.exists():
            with open(self.history_file) as f:
                return json.load(f)
        return []
    
    def record_test_run(self, results):
        """Record results from a test run."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "overall_accuracy": results["overall_accuracy"],
            "field_accuracy": results["field_accuracy"],
            "fallback_rate": results["fallback_rate"],
            "performance_metrics": results["performance_metrics"],
            "model_version": results.get("model_version", "unknown"),
        }
        
        self.history.append(entry)
        self.save_history()
        
        # Check for regression
        if len(self.history) > 1:
            previous = self.history[-2]["overall_accuracy"]
            current = entry["overall_accuracy"]
            
            if current < previous - 0.05:  # 5% regression threshold
                self.alert_regression(previous, current)
    
    def alert_regression(self, previous, current):
        """Alert on accuracy regression."""
        print(f"⚠️  ACCURACY REGRESSION DETECTED!")
        print(f"Previous: {previous:.2%}")
        print(f"Current: {current:.2%}")
        print(f"Drop: {previous - current:.2%}")
    
    def generate_report(self):
        """Generate accuracy trend report."""
        if len(self.history) < 2:
            return "Insufficient data for trends"
        
        recent = self.history[-10:]  # Last 10 runs
        
        report = {
            "trend": self.calculate_trend(recent),
            "average_accuracy": sum(r["overall_accuracy"] for r in recent) / len(recent),
            "best_run": max(recent, key=lambda r: r["overall_accuracy"]),
            "worst_run": min(recent, key=lambda r: r["overall_accuracy"]),
            "stability": self.calculate_stability(recent),
        }
        
        return report
```

#### Performance Regression Detection
```python
# tests/processors/llm/test_performance_regression.py

class TestPerformanceRegression:
    """Detect performance regressions."""
    
    @pytest.fixture
    def performance_baseline(self):
        """Load performance baseline metrics."""
        with open("tests/baselines/llm_performance.json") as f:
            return json.load(f)
    
    @pytest.mark.performance
    async def test_extraction_speed_regression(self, performance_baseline):
        """Ensure extraction speed doesn't regress."""
        extractor = PropertyExtractor()
        
        # Run multiple extractions
        timings = []
        for _ in range(10):
            html = load_random_fixture()
            start = time.time()
            await extractor.extract(html)
            timings.append(time.time() - start)
        
        avg_time = sum(timings) / len(timings)
        baseline = performance_baseline["avg_extraction_time"]
        
        # Allow 10% variance
        assert avg_time <= baseline * 1.1, \
            f"Performance regression: {avg_time:.2f}s vs baseline {baseline:.2f}s"
    
    @pytest.mark.performance  
    async def test_memory_usage_regression(self, performance_baseline):
        """Ensure memory usage doesn't increase."""
        import tracemalloc
        
        tracemalloc.start()
        
        extractor = PropertyExtractor()
        
        # Process batch
        for _ in range(50):
            await extractor.extract(load_random_fixture())
        
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        peak_mb = peak / 1024 / 1024
        baseline_mb = performance_baseline["peak_memory_mb"]
        
        # Allow 20% increase
        assert peak_mb <= baseline_mb * 1.2, \
            f"Memory regression: {peak_mb:.1f}MB vs baseline {baseline_mb:.1f}MB"
```

### TDD Integration Patterns

#### Test-First Prompt Engineering
```python
class TestPromptDevelopment:
    """Develop prompts through testing."""
    
    def test_prompt_evolution(self):
        """Track prompt improvements through tests."""
        
        # Version 1: Basic prompt (fails accuracy test)
        prompt_v1 = "Extract property data from HTML"
        accuracy_v1 = self.measure_accuracy(prompt_v1)
        assert accuracy_v1 < 0.9  # Probably fails
        
        # Version 2: Add structure (improves accuracy)
        prompt_v2 = """
        Extract property data from HTML.
        Return as JSON with fields: address, price, bedrooms...
        """
        accuracy_v2 = self.measure_accuracy(prompt_v2)
        assert accuracy_v2 > accuracy_v1  # Better
        
        # Version 3: Add examples (meets target)
        prompt_v3 = """
        Extract property data from HTML.
        
        Example input: <div class="price">$450,000</div>
        Example output: {"price": 450000}
        
        Return as JSON with fields: address, price, bedrooms...
        """
        accuracy_v3 = self.measure_accuracy(prompt_v3)
        assert accuracy_v3 >= 0.9  # Meets target!
    
    def measure_accuracy(self, prompt):
        """Measure prompt accuracy on test set."""
        # Implementation details...
        pass
```

#### Incremental Capability Building
```python
class TestCapabilityProgression:
    """Build capabilities incrementally."""
    
    # Step 1: Basic extraction
    async def test_extract_simple_price(self):
        """Start with simplest case."""
        extractor = PropertyExtractor()
        result = await extractor.extract('<div class="price">$450,000</div>')
        assert result.price == 450000
    
    # Step 2: Handle variations
    async def test_extract_price_variations(self):
        """Add handling for price variations."""
        test_cases = [
            ("$450,000", 450000),
            ("$450K", 450000),
            ("450000", 450000),
            ("$1.2M", 1200000),
        ]
        
        extractor = PropertyExtractor()
        for html_price, expected in test_cases:
            html = f'<div class="price">{html_price}</div>'
            result = await extractor.extract(html)
            assert result.price == expected
    
    # Step 3: Handle missing data
    async def test_handle_missing_price(self):
        """Gracefully handle missing prices."""
        extractor = PropertyExtractor()
        result = await extractor.extract('<div>No price info</div>')
        assert result.price is None
        assert result.confidence < 1.0
```

### Summary: TDD for LLM Systems

#### Key Principles
1. **Mock First**: Define behavior with mocks before implementing
2. **Accuracy as Tests**: Encode accuracy requirements in test assertions
3. **Performance from Start**: Test speed requirements from day one
4. **Fallback by Design**: Test error paths before happy paths
5. **Incremental Complexity**: Build from simple to complex cases

#### Benefits for LLM Processing
- **Predictable Behavior**: Despite LLM non-determinism
- **Performance Guarantees**: Speed requirements enforced
- **Accuracy Tracking**: Regression detection built-in
- **Cost Control**: Zero external API costs verified
- **Robust Fallbacks**: Error handling thoroughly tested

#### Getting Started
1. Write test for Ollama connection
2. Implement minimal connection code
3. Write test for basic extraction
4. Implement with mock response
5. Add accuracy requirements
6. Implement real extraction
7. Add performance tests
8. Optimize until passing
9. Add fallback tests
10. Implement fallback logic

The goal is not just working LLM integration, but a robust, fast, and accurate system that handles all edge cases gracefully.