# Task 05: Phoenix MLS Web Scraper - Master Workflow

## Overview
This document provides the master workflow for implementing the Phoenix MLS web scraper with anti-detection capabilities, proxy management, and Epic 1 foundation integration.

**Task ID**: TASK-05  
**Epic**: Epic 2 - Data Collection Infrastructure  
**Priority**: High  
**Estimated Duration**: 3-4 days  
**Dependencies**: Epic 1 Foundation (Complete)

## Workflow Summary

### Phase Distribution
```
Day 1: Foundation & Infrastructure (30% - Proxy, Anti-Detection)
Day 2: Core Implementation (40% - Scraper, Parser)  
Day 3: Integration & Testing (20% - Collector, Tests)
Day 4: Validation & Launch (10% - Security, Deploy)
```

### Team Requirements
- **Primary**: 1 Senior Backend Developer (Python, Web Scraping)
- **Secondary**: 1 QA Engineer (Day 3-4)
- **Optional**: 1 Security Engineer (Day 4)

## Phase 1: Foundation & Infrastructure (Day 1)

### 1.1 Project Setup (1 hour)
**Owner**: Backend Developer  
**Type**: Sequential

```bash
# Create directory structure
mkdir -p src/phoenix_real_estate/collectors/phoenix_mls
mkdir -p tests/collectors/phoenix_mls
mkdir -p tests/integration/phoenix_mls

# Update dependencies
# Add to pyproject.toml:
# playwright = "^1.41.0"
# beautifulsoup4 = "^4.12.3"

# Install dependencies
uv sync --extra dev
playwright install chromium
```

**Deliverables**:
- [ ] Directory structure created
- [ ] Dependencies installed
- [ ] Module imports configured

### 1.2 Proxy Management System (3 hours)
**Owner**: Backend Developer  
**Type**: Critical Path

Key Components:
- `ProxyStatus` enum for health states
- `ProxyInfo` dataclass with metrics
- `ProxyManager` with rotation logic
- Health monitoring and recovery

**Critical Requirements**:
- Webshare.io integration via Epic 1 ConfigProvider
- Automatic failover for failed proxies
- Success rate tracking and optimization
- Comprehensive logging with Epic 1 logger

### 1.3 Anti-Detection Framework (3 hours)
**Owner**: Backend Developer  
**Type**: Critical Path

Key Components:
- Browser fingerprint randomization
- Human-like behavior simulation
- Request timing randomization
- Stealth browser configuration

**Critical Requirements**:
- User agent rotation pool
- Viewport size randomization
- Mouse movement simulation
- Typing pattern randomization

## Phase 2: Core Implementation (Day 2)

### 2.1 Web Scraper Engine (4 hours)
**Owner**: Backend Developer  
**Type**: Critical Path

Architecture:
```python
PhoenixMLSScraper
├── __init__ (browser setup)
├── search_zipcode (listing search)
├── get_property_details (detail pages)
└── _extract_property_listings (parsing)
```

**Integration Points**:
- Proxy Manager for all requests
- Anti-Detection for page setup
- Epic 1 retry utilities
- Structured error handling

### 2.2 Data Extraction Logic (3 hours)
**Owner**: Backend Developer  
**Type**: Parallel

Parser Implementation:
- BeautifulSoup4 for HTML parsing
- Flexible selector patterns
- Fallback extraction methods
- Raw HTML storage for LLM

**Data Schema**:
```json
{
  "source": "phoenix_mls",
  "scraped_at": "ISO-8601",
  "address": "string",
  "price": "string",
  "features": {},
  "raw_html": "string",
  "structured_data": {}
}
```

### 2.3 Error Handling & Recovery (2 hours)
**Owner**: Backend Developer  
**Type**: Sequential

Error Matrix:
| Error Type | Recovery Strategy | Max Retries |
|------------|------------------|-------------|
| Network | Exponential backoff | 3 |
| Parsing | Store raw, flag LLM | 1 |
| Rate Limit | Switch proxy, delay | 5 |
| Browser | Restart, checkpoint | 2 |

## Phase 3: Integration & Testing (Day 3)

### 3.1 PhoenixMLS Collector (3 hours)
**Owner**: Backend Developer  
**Type**: Critical Path

Implementation:
- Inherit from `DataCollector` base class
- Implement abstract methods
- Epic 1 foundation integration
- Adapter for schema conversion

### 3.2 Test Suite Development (3 hours)
**Owner**: Backend Developer / QA  
**Type**: Parallel

Test Coverage Targets:
- Unit Tests: 90% coverage
- Integration Tests: E2E scenarios
- Performance Tests: Load validation
- Security Tests: Credential safety

### 3.3 Documentation (2 hours)
**Owner**: Backend Developer  
**Type**: Parallel

Documentation Set:
- Technical architecture
- Configuration guide
- API reference
- Troubleshooting guide

## Phase 4: Validation & Launch (Day 4)

### 4.1 Security Validation (2 hours)
**Owner**: Security Engineer / Backend Developer  
**Type**: Gate

Checklist:
- [ ] Credential management audit
- [ ] Proxy authentication security
- [ ] Data privacy compliance
- [ ] Legal compliance verification

### 4.2 Production Readiness (2 hours)
**Owner**: DevOps / Backend Developer  
**Type**: Sequential

Requirements:
- Performance optimization
- Monitoring configuration
- Alert setup
- Runbook creation

### 4.3 Launch & Monitoring (2 hours)
**Owner**: Team Lead  
**Type**: Sequential

Launch Protocol:
1. Deploy to production
2. Run smoke tests
3. Monitor metrics (24h)
4. Validate data quality
5. Confirm integrations

## Risk Management

### Critical Risks
1. **Detection & Blocking** (High)
   - Mitigation: Advanced anti-detection, proxy rotation
   - Contingency: Alternative scraping methods

2. **Site Structure Changes** (Medium)
   - Mitigation: Flexible parsing, LLM fallback
   - Contingency: Manual selector updates

3. **Proxy Service Failure** (Low)
   - Mitigation: Health monitoring, multiple providers
   - Contingency: Direct connection mode

## Success Metrics

### Technical KPIs
- Test Coverage: ≥90%
- Success Rate: ≥95%
- Response Time: <2s avg
- Error Rate: <5%

### Business KPIs
- Data Accuracy: ≥98%
- Compliance: 100%
- Throughput: 1000+ properties/hour
- Cost: Within budget

## Integration Points

### Epic 1 Foundation
- ConfigProvider for settings
- PropertyRepository for storage
- Logger for monitoring
- Exception hierarchy

### Epic 3 Orchestration
```python
collector = PhoenixMLSCollector(config, repository, logger_name)
properties = await collector.collect_zipcode("85031")
```

### Epic 6 LLM Processing
```python
raw_data = {
    "raw_html": property["raw_html"],
    "source": "phoenix_mls"
}
# Send to LLM for extraction
```

## Workflow Management

### Daily Standups
- Day 1: Foundation progress, blockers
- Day 2: Core implementation status
- Day 3: Integration testing results
- Day 4: Launch readiness review

### Quality Gates
- [ ] Day 1: Proxy/Anti-detection working
- [ ] Day 2: Basic scraping functional
- [ ] Day 3: All tests passing
- [ ] Day 4: Production ready

### Escalation Path
1. Technical blockers → Senior Developer
2. Resource issues → Project Manager
3. Legal concerns → Compliance Team
4. Security issues → Security Team