# Task 05: Phoenix MLS Scraper - Implementation Tasks

## Task Breakdown & Assignments

### Day 1: Foundation & Infrastructure

#### TASK-05-001: Project Structure Setup
**Assignee**: Backend Developer  
**Duration**: 1 hour  
**Priority**: P0 - Blocker  
**Dependencies**: None

```bash
# Commands to execute
mkdir -p src/phoenix_real_estate/collectors/phoenix_mls
mkdir -p tests/collectors/phoenix_mls
mkdir -p tests/integration/phoenix_mls

# Create module files
touch src/phoenix_real_estate/collectors/phoenix_mls/{__init__.py,proxy_manager.py,anti_detection.py,scraper.py,collector.py,adapter.py}

# Update pyproject.toml dependencies
# playwright = "^1.41.0"
# beautifulsoup4 = "^4.12.3"
# aiohttp = "^3.9.0"

uv sync --extra dev
playwright install chromium
```

**Acceptance Criteria**:
- [ ] All directories created
- [ ] Dependencies installed successfully
- [ ] Playwright browser downloaded
- [ ] Import tests pass

---

#### TASK-05-002: Proxy Manager Implementation
**Assignee**: Backend Developer  
**Duration**: 3 hours  
**Priority**: P0 - Critical Path  
**Dependencies**: TASK-05-001

**Implementation Checklist**:
```python
# src/phoenix_real_estate/collectors/phoenix_mls/proxy_manager.py

class ProxyStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded" 
    FAILED = "failed"
    TESTING = "testing"

@dataclass
class ProxyInfo:
    host: str
    port: int
    username: str
    password: str
    status: ProxyStatus = ProxyStatus.TESTING
    # ... health metrics

class ProxyManager:
    def __init__(self, config: ConfigProvider):
        # Initialize with Epic 1 config
        # Load Webshare.io credentials
        # Setup proxy pool
    
    async def get_proxy(self) -> str:
        # Intelligent proxy selection
        # Health-based routing
        # Automatic failover
    
    async def report_result(self, proxy_url: str, success: bool):
        # Update proxy health
        # Track success rates
        # Trigger recovery if needed
```

**Test Requirements**:
- [ ] Unit tests for proxy rotation
- [ ] Health monitoring tests
- [ ] Recovery mechanism tests
- [ ] Integration with ConfigProvider

---

#### TASK-05-003: Anti-Detection System
**Assignee**: Backend Developer  
**Duration**: 3 hours  
**Priority**: P0 - Critical Path  
**Dependencies**: TASK-05-001

**Implementation Components**:

1. **Browser Fingerprinting**:
   - User agent rotation (5+ agents)
   - Viewport randomization (5+ sizes)
   - Timezone randomization
   - WebGL/Canvas spoofing

2. **Human Behavior Simulation**:
   ```python
   async def human_like_delay(min_s=1.0, max_s=3.0):
       delay = random.uniform(min_s, max_s)
       await asyncio.sleep(delay)
   
   async def human_like_mouse_movement(page, element):
       # Bezier curve movements
       # Random acceleration/deceleration
       # Occasional overshoots
   
   async def human_like_typing(page, element, text):
       # Variable typing speed
       # Occasional typos/corrections
       # Natural pauses
   ```

3. **Stealth Configuration**:
   - Remove automation indicators
   - Mock browser APIs
   - Disable headless detection

**Test Coverage**:
- [ ] Fingerprint randomization
- [ ] Timing pattern tests
- [ ] Behavior simulation
- [ ] Detection resistance

---

### Day 2: Core Implementation

#### TASK-05-004: Web Scraper Engine
**Assignee**: Backend Developer  
**Duration**: 4 hours  
**Priority**: P0 - Critical Path  
**Dependencies**: TASK-05-002, TASK-05-003

**Core Methods**:

```python
class PhoenixMLSScraper:
    def __init__(self, config: ConfigProvider):
        self.proxy_manager = ProxyManager(config)
        self.anti_detection = AntiDetectionManager()
        
    async def __aenter__(self):
        # Setup browser with proxy
        # Apply anti-detection
        
    async def search_zipcode(self, zipcode: str, max_pages: int = 5):
        # Navigate to search
        # Handle pagination
        # Extract listings
        # Manage session
        
    async def get_property_details(self, property_url: str):
        # Load detail page
        # Extract full data
        # Handle dynamic content
```

**Integration Requirements**:
- [ ] Proxy integration for all requests
- [ ] Anti-detection on every page
- [ ] Epic 1 retry utilities
- [ ] Structured logging

---

#### TASK-05-005: Data Extraction & Parsing
**Assignee**: Backend Developer  
**Duration**: 3 hours  
**Priority**: P1 - High  
**Dependencies**: TASK-05-004

**Parser Implementation**:

```python
def _parse_listing_element(self, listing_element) -> Dict[str, Any]:
    """Extract property data from listing HTML."""
    return {
        "source": "phoenix_mls",
        "scraped_at": datetime.utcnow().isoformat(),
        "address": self._extract_address(listing_element),
        "price": self._extract_price(listing_element),
        "features": self._extract_features(listing_element),
        "raw_html": str(listing_element),  # For LLM
        "structured_data": {...}
    }

def _extract_structured_details(self, soup: BeautifulSoup) -> Dict:
    """Extract detailed property information."""
    # Flexible selector patterns
    # Multiple extraction attempts
    # Fallback strategies
```

**Data Quality Requirements**:
- [ ] Address extraction accuracy >95%
- [ ] Price parsing reliability >98%
- [ ] Feature extraction completeness
- [ ] Raw HTML preservation

---

#### TASK-05-006: Error Handling Framework
**Assignee**: Backend Developer  
**Duration**: 2 hours  
**Priority**: P1 - High  
**Dependencies**: TASK-05-004

**Error Handling Matrix**:

```python
ERROR_STRATEGIES = {
    NetworkError: {
        "strategy": "exponential_backoff",
        "max_retries": 3,
        "base_delay": 2.0
    },
    ParsingError: {
        "strategy": "store_raw_fallback", 
        "max_retries": 1,
        "flag_for_llm": True
    },
    RateLimitError: {
        "strategy": "proxy_switch_delay",
        "max_retries": 5,
        "delay_multiplier": 2.0
    },
    BrowserCrashError: {
        "strategy": "restart_from_checkpoint",
        "max_retries": 2,
        "checkpoint_interval": 10
    }
}
```

**Recovery Mechanisms**:
- [ ] Automatic retry with backoff
- [ ] Proxy rotation on rate limits
- [ ] Browser restart capability
- [ ] Checkpoint/resume support

---

### Day 3: Integration & Testing

#### TASK-05-007: PhoenixMLS Collector Integration
**Assignee**: Backend Developer  
**Duration**: 3 hours  
**Priority**: P0 - Integration Critical  
**Dependencies**: TASK-05-005, TASK-05-006

**Collector Implementation**:

```python
class PhoenixMLSCollector(DataCollector):
    """Phoenix MLS data collector with Epic 1 integration."""
    
    def __init__(self, config: ConfigProvider, 
                 repository: PropertyRepository,
                 logger_name: str):
        super().__init__(config, repository, logger_name)
        self.scraper = PhoenixMLSScraper(config)
        self.adapter = PhoenixMLSAdapter(validator, logger_name)
        
    async def collect_zipcode(self, zipcode: str) -> List[Dict]:
        """Collect properties for zipcode."""
        async with self.scraper as scraper:
            return await scraper.search_zipcode(zipcode)
            
    async def adapt_property(self, raw_data: Dict) -> Property:
        """Convert to Epic 1 schema."""
        return await self.adapter.adapt_property(raw_data)
```

**Integration Points**:
- [ ] Epic 1 ConfigProvider usage
- [ ] PropertyRepository integration
- [ ] Structured logging throughout
- [ ] Exception hierarchy compliance

---

#### TASK-05-008: Comprehensive Test Suite
**Assignee**: Backend Developer + QA Engineer  
**Duration**: 3 hours  
**Priority**: P1 - Quality Gate  
**Dependencies**: TASK-05-007

**Test Implementation Plan**:

1. **Unit Tests** (tests/collectors/phoenix_mls/):
   ```python
   test_proxy_manager.py     # 20+ tests
   test_anti_detection.py    # 15+ tests
   test_scraper.py          # 25+ tests
   test_adapter.py          # 10+ tests
   ```

2. **Integration Tests** (tests/integration/phoenix_mls/):
   ```python
   test_end_to_end.py       # Full workflow
   test_error_recovery.py   # Failure scenarios
   test_performance.py      # Load testing
   ```

3. **Fixtures & Mocks**:
   - Mock Playwright pages
   - Sample HTML responses
   - Proxy response simulations
   - Error scenario generators

**Coverage Requirements**:
- [ ] Unit test coverage ≥90%
- [ ] Integration coverage ≥80%
- [ ] Performance benchmarks met
- [ ] Security tests passing

---

#### TASK-05-009: Documentation Package
**Assignee**: Backend Developer  
**Duration**: 2 hours  
**Priority**: P2 - Important  
**Dependencies**: TASK-05-008

**Documentation Deliverables**:

1. **docs/collectors/phoenix_mls_architecture.md**
   - System design overview
   - Component interactions
   - Data flow diagrams
   - Security considerations

2. **docs/collectors/phoenix_mls_configuration.md**
   - Environment variables
   - Proxy setup guide
   - Performance tuning
   - Troubleshooting

3. **docs/collectors/phoenix_mls_api.md**
   - Collector interface
   - Data schemas
   - Error codes
   - Usage examples

**Quality Standards**:
- [ ] Code examples tested
- [ ] Diagrams included
- [ ] Troubleshooting complete
- [ ] API fully documented

---

### Day 4: Validation & Launch

#### TASK-05-010: Security Audit
**Assignee**: Security Engineer / Backend Developer  
**Duration**: 2 hours  
**Priority**: P0 - Gate  
**Dependencies**: TASK-05-008

**Security Checklist**:
- [ ] Credential encryption verified
- [ ] Proxy auth security confirmed
- [ ] No sensitive data in logs
- [ ] Input validation complete
- [ ] Rate limiting compliant
- [ ] Legal compliance verified

**Deliverables**:
- Security audit report
- Vulnerability assessment
- Compliance certification
- Remediation if needed

---

#### TASK-05-011: Production Configuration
**Assignee**: DevOps / Backend Developer  
**Duration**: 2 hours  
**Priority**: P0 - Launch Blocker  
**Dependencies**: TASK-05-010

**Production Setup**:

1. **Environment Configuration**:
   ```yaml
   PHOENIX_MLS_BASE_URL: "https://phoenixmlssearch.com"
   PHOENIX_MLS_MAX_RETRIES: 3
   PHOENIX_MLS_TIMEOUT: 30000
   WEBSHARE_USERNAME: <encrypted>
   WEBSHARE_PASSWORD: <encrypted>
   PROXY_HEALTH_CHECK_INTERVAL: 300
   ```

2. **Resource Limits**:
   - Browser memory: 512MB max
   - Concurrent pages: 3 max
   - Request rate: 10/minute
   - Proxy pool: 5-10 active

3. **Monitoring Setup**:
   - Prometheus metrics
   - Grafana dashboards
   - Alert thresholds
   - Log aggregation

**Validation**:
- [ ] Config encrypted properly
- [ ] Resource limits tested
- [ ] Monitoring active
- [ ] Alerts configured

---

#### TASK-05-012: Launch & 24h Monitoring
**Assignee**: Team Lead + Backend Developer  
**Duration**: 2 hours + 24h monitoring  
**Priority**: P0 - Launch  
**Dependencies**: TASK-05-011

**Launch Protocol**:

1. **Deployment Steps**:
   ```bash
   # Deploy to production
   ./deploy.sh production phoenix-mls-scraper
   
   # Run smoke tests
   pytest tests/smoke/test_phoenix_mls_live.py
   
   # Verify integrations
   python -m phoenix_real_estate.verify_integrations
   ```

2. **Monitoring Metrics** (First 24h):
   - Success rate: Target ≥95%
   - Response time: Target <2s
   - Proxy health: ≥80% healthy
   - Error rate: Target <5%
   - Data quality: ≥98% valid

3. **Incident Response**:
   - On-call engineer assigned
   - Escalation path defined
   - Rollback plan ready
   - Communication channels open

**Success Criteria**:
- [ ] All smoke tests pass
- [ ] Metrics within targets
- [ ] No blocking incidents
- [ ] Data flow validated

---

## Task Dependencies Graph

```
Day 1:
TASK-05-001 (Setup) 
    ├→ TASK-05-002 (Proxy Manager)
    └→ TASK-05-003 (Anti-Detection)

Day 2:
TASK-05-002 + TASK-05-003
    └→ TASK-05-004 (Scraper Engine)
         ├→ TASK-05-005 (Data Extraction)
         └→ TASK-05-006 (Error Handling)

Day 3:
TASK-05-005 + TASK-05-006
    └→ TASK-05-007 (Collector Integration)
         ├→ TASK-05-008 (Test Suite)
         └→ TASK-05-009 (Documentation)

Day 4:
TASK-05-008
    └→ TASK-05-010 (Security Audit)
         └→ TASK-05-011 (Production Config)
              └→ TASK-05-012 (Launch)
```

## Resource Allocation

| Developer | Day 1 | Day 2 | Day 3 | Day 4 |
|-----------|-------|-------|-------|-------|
| Backend Dev | 001,002,003 | 004,005,006 | 007,008,009 | 010,011,012 |
| QA Engineer | - | - | 008 | 010,012 |
| Security Eng | - | - | - | 010 |
| DevOps | - | - | - | 011,012 |
| Team Lead | Planning | Review | Review | 012 |

## Risk Mitigation by Task

| Task | Risk | Mitigation | Contingency |
|------|------|------------|-------------|
| 002 | Proxy failure | Health monitoring | Backup providers |
| 003 | Detection | Advanced techniques | Method updates |
| 004 | Site changes | Flexible parsing | LLM fallback |
| 006 | Cascading errors | Circuit breakers | Manual intervention |
| 008 | Low coverage | TDD approach | Extended timeline |
| 010 | Security issues | Early audit | Immediate fixes |
| 012 | Launch failure | Staged rollout | Quick rollback |