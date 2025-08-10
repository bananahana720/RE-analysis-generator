# Task 05: Phoenix MLS Scraper - Test-Driven Development Strategy

## TDD Philosophy: Tests Drive Development

### Core TDD Principles
1. **Tests First, Always**: Never write production code without a failing test
2. **Red-Green-Refactor**: The fundamental TDD cycle
3. **Baby Steps**: Small increments, frequent commits
4. **Emergent Design**: Let tests guide architecture decisions
5. **100% Coverage by Design**: Not a goal, but a natural outcome

### The TDD Cycle
```
     ┌─────────────┐
     │   1. RED    │ Write a failing test
     │   (Fail)    │ that defines desired behavior
     └──────┬──────┘
            │
     ┌──────▼──────┐
     │  2. GREEN   │ Write minimal code to
     │   (Pass)    │ make the test pass
     └──────┬──────┘
            │
     ┌──────▼──────┐
     │ 3. REFACTOR │ Improve code structure
     │  (Clean)    │ while keeping tests green
     └──────┬──────┘
            │
            └────────────┐
                        │
                 (Repeat for next test)
```

## TDD Workflow for Phoenix MLS Scraper

### Starting a New Component: Proxy Manager Example

#### Step 1: Write the First Failing Test (RED)
```python
# tests/collectors/phoenix_mls/test_proxy_manager.py

import pytest
from phoenix_real_estate.collectors.phoenix_mls.proxy_manager import ProxyManager

class TestProxyManager:
    """Test-driven development of proxy management system."""
    
    def test_proxy_manager_exists(self):
        """First test: ProxyManager class should exist."""
        # This will fail - ProxyManager doesn't exist yet
        manager = ProxyManager()
        assert manager is not None
```

Run test: `uv run pytest tests/collectors/phoenix_mls/test_proxy_manager.py::TestProxyManager::test_proxy_manager_exists -v`

**Expected Result**: ImportError - ProxyManager doesn't exist

#### Step 2: Make it Pass with Minimal Code (GREEN)
```python
# src/phoenix_real_estate/collectors/phoenix_mls/proxy_manager.py

class ProxyManager:
    """Minimal implementation to make test pass."""
    pass
```

Run test again: Test passes! ✅

#### Step 3: Write Next Failing Test
```python
def test_proxy_manager_requires_config(self):
    """ProxyManager should require configuration."""
    # This test drives the API design
    with pytest.raises(TypeError):
        ProxyManager()  # Should fail without config
    
    # This should work
    config = Mock()
    manager = ProxyManager(config)
    assert manager.config is config
```

#### Step 4: Implement to Pass
```python
class ProxyManager:
    """Proxy manager with required configuration."""
    
    def __init__(self, config):
        self.config = config
```

#### Step 5: Continue Building Feature by Feature
```python
async def test_get_proxy_returns_formatted_url(self):
    """get_proxy should return a properly formatted proxy URL."""
    config = Mock()
    config.get_required.side_effect = lambda key: {
        "WEBSHARE_USERNAME": "testuser",
        "WEBSHARE_PASSWORD": "testpass",
    }.get(key)
    
    manager = ProxyManager(config)
    
    # This will fail - get_proxy doesn't exist
    proxy_url = await manager.get_proxy()
    
    # Define expected behavior through assertions
    assert proxy_url.startswith("http://")
    assert "testuser:testpass" in proxy_url
    assert "@" in proxy_url
    assert ":" in proxy_url.split("@")[1]  # Port number
```

### TDD Patterns and Best Practices

#### Pattern 1: Specification by Example
```python
class TestPropertyDataAdapter:
    """Using tests as executable specifications."""
    
    def test_adapt_phoenix_mls_listing_to_property(self):
        """Test defines the contract for data adaptation."""
        # Given: Raw Phoenix MLS data (specification by example)
        raw_data = {
            "listing_id": "MLS123456",
            "address": "123 Main St, Phoenix, AZ 85001",
            "list_price": "$450,000",
            "bedrooms": "3",
            "bathrooms": "2.5",
            "square_feet": "1,850",
            "lot_size": "6,500 sq ft",
            "year_built": "2015",
            "listing_date": "2024-01-15",
            "mls_status": "Active"
        }
        
        # When: Adapted to our schema
        adapter = PhoenixMLSAdapter()
        property_obj = adapter.adapt(raw_data)
        
        # Then: Verify the transformation (executable documentation)
        assert property_obj.property_id == "phoenix_mls_MLS123456"
        assert property_obj.address.street == "123 Main St"
        assert property_obj.address.city == "Phoenix"
        assert property_obj.address.state == "AZ"
        assert property_obj.address.zip_code == "85001"
        assert property_obj.prices[0].amount == 450000
        assert property_obj.prices[0].currency == "USD"
        assert property_obj.prices[0].price_type == "listing"
        assert property_obj.features.bedrooms == 3
        assert property_obj.features.bathrooms == 2.5
        assert property_obj.features.square_feet == 1850
        assert property_obj.features.lot_size_sqft == 6500
        assert property_obj.features.year_built == 2015
```

#### Pattern 2: Test-Driven Error Handling
```python
class TestErrorHandlingTDD:
    """Drive error handling implementation through tests."""
    
    async def test_proxy_failure_triggers_rotation(self):
        """Define how system should handle proxy failures."""
        # Start with the desired behavior
        manager = ProxyManager(mock_config)
        
        # Given: A proxy that will fail
        failing_proxy = await manager.get_proxy()
        
        # When: We report the failure
        await manager.report_failure(failing_proxy, "Connection timeout")
        
        # Then: Next proxy should be different (rotation)
        next_proxy = await manager.get_proxy()
        assert next_proxy != failing_proxy
        
        # And: Failed proxy should be marked unhealthy
        health = await manager.get_proxy_health(failing_proxy)
        assert health.status == "unhealthy"
        assert health.last_error == "Connection timeout"
    
    async def test_all_proxies_failed_triggers_recovery(self):
        """Define recovery behavior when all proxies fail."""
        manager = ProxyManager(mock_config)
        
        # Given: All proxies have failed
        all_proxies = await manager.get_all_proxies()
        for proxy in all_proxies:
            await manager.report_failure(proxy, "Failed")
        
        # When: We request a proxy
        # Then: Should trigger recovery process
        with pytest.raises(NoHealthyProxiesError) as exc_info:
            await manager.get_proxy()
        
        assert "Initiating proxy recovery" in str(exc_info.value)
        assert manager.recovery_in_progress
```

#### Pattern 3: Incremental Algorithm Development
```python
class TestAntiDetectionTDD:
    """Build anti-detection features incrementally."""
    
    def test_human_like_delay_basic(self):
        """Step 1: Basic delay implementation."""
        detector = AntiDetectionManager()
        
        start = time.time()
        detector.human_delay(1.0)  # 1 second delay
        duration = time.time() - start
        
        assert 0.9 <= duration <= 1.1  # Allow 10% variance
    
    def test_human_like_delay_with_randomization(self):
        """Step 2: Add randomization."""
        detector = AntiDetectionManager()
        
        delays = []
        for _ in range(10):
            start = time.time()
            detector.human_delay(1.0, variance=0.2)
            delays.append(time.time() - start)
        
        # Should have variety
        assert len(set(delays)) > 5
        # But within bounds
        assert all(0.8 <= d <= 1.2 for d in delays)
    
    def test_human_like_delay_with_distribution(self):
        """Step 3: Add realistic distribution."""
        detector = AntiDetectionManager()
        
        delays = []
        for _ in range(100):
            delay = detector.human_delay(1.0, distribution='normal')
            delays.append(delay)
        
        # Most delays should cluster around mean
        mean_delay = sum(delays) / len(delays)
        assert 0.95 <= mean_delay <= 1.05
        
        # But some outliers for realism
        assert any(d < 0.8 for d in delays)
        assert any(d > 1.2 for d in delays)
```

### Evolving Tests as Understanding Improves

#### Initial Test (Naive Understanding)
```python
def test_scrape_property_listing_v1(self):
    """Early test based on initial assumptions."""
    scraper = PhoenixMLSScraper()
    
    html = '<div class="price">$450,000</div>'
    result = scraper.extract_price(html)
    
    assert result == 450000
```

#### Evolved Test (After Discovering Edge Cases)
```python
def test_scrape_property_listing_v2(self):
    """Evolved test handling real-world complexity."""
    scraper = PhoenixMLSScraper()
    
    # Discovered: Prices can have various formats
    test_cases = [
        ('<div class="price">$450,000</div>', 450000),
        ('<div class="price">$1,250,000</div>', 1250000),
        ('<div class="price">Price: $450K</div>', 450000),
        ('<div class="price">$450,000 USD</div>', 450000),
        ('<div class="price">Contact for Price</div>', None),
        ('<div class="price">$0</div>', None),  # Likely error
    ]
    
    for html, expected in test_cases:
        result = scraper.extract_price(html)
        assert result == expected, f"Failed for: {html}"
```

#### Final Test (Production-Ready)
```python
def test_scrape_property_listing_v3(self):
    """Production test with full context and error handling."""
    scraper = PhoenixMLSScraper()
    
    # Real page structure discovered through exploration
    html = """
    <div class="listing-detail">
        <div class="price-wrapper">
            <span class="currency">$</span>
            <span class="price-major">450</span>
            <span class="price-minor">,000</span>
            <span class="price-frequency">/month</span>
        </div>
        <div class="original-price">Was: $475,000</div>
    </div>
    """
    
    result = scraper.extract_price_info(html)
    
    assert result.current_price == 450000
    assert result.original_price == 475000
    assert result.price_type == "monthly_rent"
    assert result.currency == "USD"
    assert result.extracted_at is not None
```

### TDD Anti-Patterns to Avoid

#### Anti-Pattern 1: Testing Implementation Details
```python
# ❌ BAD: Testing internal implementation
def test_proxy_manager_uses_round_robin():
    manager = ProxyManager()
    assert manager._strategy == "round_robin"  # Don't test privates!
    assert manager._current_index == 0  # Implementation detail!

# ✅ GOOD: Testing behavior
def test_proxy_manager_distributes_load():
    manager = ProxyManager()
    proxy_counts = defaultdict(int)
    
    for _ in range(100):
        proxy = manager.get_proxy()
        proxy_counts[proxy] += 1
    
    # All proxies should get roughly equal load
    counts = list(proxy_counts.values())
    assert max(counts) - min(counts) <= 10
```

#### Anti-Pattern 2: Writing Tests After Code
```python
# ❌ BAD: Retrofitting tests to existing code
def complex_business_logic(data):
    # 50 lines of tangled logic written without tests
    # ...
    return result

# Tests written after the fact tend to:
# - Test the implementation, not the requirements
# - Miss edge cases
# - Be hard to understand

# ✅ GOOD: Let tests drive the design
def test_business_rule_x():
    """When condition A and B, system should do X."""
    # Write this FIRST
    # Then implement the minimum to pass
```

#### Anti-Pattern 3: Large Test Steps
```python
# ❌ BAD: Trying to test everything at once
def test_entire_scraping_workflow():
    # 200 lines testing everything end-to-end
    # Hard to debug when it fails
    # Unclear what exactly is being tested

# ✅ GOOD: Small, focused tests
def test_proxy_format_validation():
    """Proxy URLs must follow http://user:pass@host:port format."""
    # 5-10 lines, tests ONE thing

def test_proxy_authentication():
    """Proxy auth headers should be properly encoded."""
    # Another 5-10 lines, tests ONE thing
```

### Test Quality Metrics and Mutation Testing

#### Code Coverage vs Test Quality
```python
# Install mutation testing tool
# pip install mutmut

# Run mutation testing
# mutmut run --paths-to-mutate=src/phoenix_real_estate/collectors/phoenix_mls/

# Example mutation test results:
"""
Mutation Testing Report
======================
Total mutations: 247
Killed: 235 (95.1%)  ✅ Good - tests caught the mutations
Survived: 12 (4.9%)  ❌ Bad - tests didn't catch these
Timeout: 0
Suspicious: 0

Survived mutations indicate missing test cases!
"""

# Investigate survived mutations
# mutmut show 14
```

#### Test Quality Metrics Dashboard
```python
# tests/quality/test_metrics.py

class TestQualityMetrics:
    """Monitor and enforce test quality standards."""
    
    def test_assertion_density(self):
        """Tests should have meaningful assertions."""
        test_files = glob.glob("tests/**/*test*.py", recursive=True)
        
        for test_file in test_files:
            with open(test_file) as f:
                content = f.read()
            
            test_count = content.count("def test_")
            assert_count = content.count("assert ")
            
            # At least 2 assertions per test average
            if test_count > 0:
                assert assert_count / test_count >= 2.0
    
    def test_test_naming_quality(self):
        """Test names should describe behavior, not implementation."""
        bad_patterns = [
            r"test_\w+_method",  # test_get_method
            r"test_\w+_function",  # test_parse_function  
            r"test_\w+_works",  # test_scraper_works
        ]
        
        test_files = glob.glob("tests/**/*test*.py", recursive=True)
        
        for test_file in test_files:
            with open(test_file) as f:
                content = f.read()
            
            for pattern in bad_patterns:
                matches = re.findall(pattern, content)
                assert not matches, f"Poor test names in {test_file}: {matches}"
```

### TDD Integration with CI/CD

#### Pre-commit Hook for TDD
```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: tdd-check
        name: TDD Compliance Check
        entry: python scripts/check_tdd_compliance.py
        language: python
        pass_filenames: false
```

```python
# scripts/check_tdd_compliance.py
"""Ensure TDD practices are followed."""

def check_tdd_compliance():
    """Verify tests exist for all production code."""
    
    # Find all production Python files
    prod_files = glob.glob("src/**/*.py", recursive=True)
    
    missing_tests = []
    for prod_file in prod_files:
        # Derive expected test file path
        test_file = prod_file.replace("src/", "tests/").replace(".py", "_test.py")
        
        if not os.path.exists(test_file):
            missing_tests.append(prod_file)
    
    if missing_tests:
        print("ERROR: Production code without tests:")
        for file in missing_tests:
            print(f"  - {file}")
        sys.exit(1)
    
    print("✅ All production code has corresponding tests")
```

#### TDD Workflow Integration
```yaml
# .github/workflows/tdd-workflow.yml
name: TDD Workflow

on:
  pull_request:
    types: [opened, synchronize]

jobs:
  tdd-compliance:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
        with:
          fetch-depth: 0
      
      - name: Check test-first compliance
        run: |
          # Get all commits in PR
          COMMITS=$(git rev-list origin/main..HEAD)
          
          for commit in $COMMITS; do
            echo "Checking commit: $commit"
            
            # Get changed files
            PROD_FILES=$(git diff-tree --no-commit-id --name-only -r $commit | grep "^src/")
            TEST_FILES=$(git diff-tree --no-commit-id --name-only -r $commit | grep "^tests/")
            
            # Verify tests were committed first or together
            if [ -n "$PROD_FILES" ] && [ -z "$TEST_FILES" ]; then
              echo "ERROR: Commit $commit adds production code without tests!"
              exit 1
            fi
          done
          
      - name: Run mutation testing
        run: |
          pip install mutmut
          mutmut run --CI --paths-to-mutate=src/
          
      - name: Check mutation score
        run: |
          SCORE=$(mutmut results | grep "Killed:" | grep -oE "[0-9]+\.[0-9]+")
          if (( $(echo "$SCORE < 90.0" | bc -l) )); then
            echo "ERROR: Mutation score $SCORE% is below 90% threshold"
            exit 1
          fi
```

### TDD Learning Resources

#### TDD Katas for Practice
```python
# exercises/tdd_kata_proxy_rotation.py
"""
TDD Kata: Implement a weighted proxy rotation system

Requirements (implement one at a time):
1. Return a proxy from a list
2. Track success/failure for each proxy  
3. Prefer proxies with higher success rates
4. Disable proxies below 50% success rate
5. Re-enable disabled proxies after cooldown period
6. Implement circuit breaker pattern

Remember: RED -> GREEN -> REFACTOR for each requirement!
"""

# Start with this failing test:
def test_get_proxy_from_list():
    rotation = WeightedProxyRotation(["proxy1", "proxy2", "proxy3"])
    proxy = rotation.get_next()
    assert proxy in ["proxy1", "proxy2", "proxy3"]
```

## Summary: TDD as a Development Philosophy

### The TDD Mindset
1. **Tests are not verification** - they are specification
2. **Tests drive design** - if it's hard to test, the design is wrong
3. **Tests document intent** - better than any comment
4. **Tests enable refactoring** - change with confidence
5. **Tests catch regressions** - before users do

### TDD Benefits for Phoenix MLS Scraper
- **Resilient to website changes**: Tests define expected behavior
- **Easy to maintain**: Clear specifications for each component
- **Confident deployments**: Comprehensive test suite
- **Living documentation**: Tests show how to use the code
- **Quality by design**: Bugs prevented, not fixed

### Getting Started with TDD
1. Pick the smallest possible feature
2. Write one failing test
3. Make it pass with minimal code
4. Refactor if needed
5. Commit
6. Repeat

Remember: The goal isn't to write tests. The goal is to write better code, and TDD is the tool that gets us there.