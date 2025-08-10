# Production Deployment Guide - Phoenix Real Estate Collector

## Overview

This guide provides comprehensive instructions for deploying the Phoenix Real Estate data collection system to production using GitHub Actions, with integrated LLM processing via Ollama.

## Pre-Deployment Checklist

### System Requirements Validation
- [ ] MongoDB Atlas connection configured (10 connection limit)
- [ ] GitHub repository with Actions enabled
- [ ] Docker Hub account for container registry
- [ ] All API keys obtained (Maricopa, WebShare, 2captcha)
- [ ] Target ZIP codes defined (85031, 85033, 85035)
- [ ] Budget verified ($25/month maximum)

### Code Readiness
- [ ] All tests passing (90%+ coverage)
- [ ] No security vulnerabilities (Bandit/Safety clean)
- [ ] Task 6 LLM processing integrated and tested
- [ ] Performance benchmarks met
- [ ] Documentation complete

## Step 1: GitHub Secrets Configuration

### Required Secrets Setup

Navigate to Settings → Secrets and variables → Actions:

```bash
# Foundation Secrets (Epic 1)
MONGODB_CONNECTION_STRING    # mongodb+srv://user:pass@cluster.mongodb.net/phoenix_real_estate
LOG_LEVEL                    # INFO (or DEBUG for troubleshooting)

# Collection Secrets (Epic 2)
MARICOPA_API_KEY            # From mcassessor.maricopa.gov
WEBSHARE_USERNAME           # WebShare proxy username
WEBSHARE_PASSWORD           # WebShare proxy password
CAPTCHA_API_KEY            # 2captcha API key

# Automation Secrets (Epic 3)
TARGET_ZIP_CODES           # 85031,85033,85035
ORCHESTRATION_MODE         # sequential (or parallel)
DEPLOYMENT_ENVIRONMENT     # production

# Container Registry
DOCKER_USERNAME            # Docker Hub username
DOCKER_PASSWORD            # Docker Hub password

# LLM Configuration (Task 6)
OLLAMA_HOST               # http://localhost:11434
OLLAMA_MODEL              # llama3.2:latest
PROCESSING_BATCH_SIZE     # 10
PROCESSING_TIMEOUT        # 30
```

### Verification Script

```bash
# scripts/verify_secrets.py
import os
import sys

REQUIRED_SECRETS = [
    "MONGODB_CONNECTION_STRING",
    "MARICOPA_API_KEY",
    "WEBSHARE_USERNAME",
    "WEBSHARE_PASSWORD",
    "TARGET_ZIP_CODES",
    "DOCKER_USERNAME",
    "DOCKER_PASSWORD"
]

missing = [s for s in REQUIRED_SECRETS if not os.getenv(s)]
if missing:
    print(f"❌ Missing secrets: {', '.join(missing)}")
    sys.exit(1)
else:
    print("✅ All required secrets configured")
```

## Step 2: Workflow Deployment

### 1. Deploy Daily Collection Workflow

```bash
# Create workflow file
mkdir -p .github/workflows
```

Create `.github/workflows/daily-collection.yml`:

```yaml
name: Daily Real Estate Data Collection

on:
  schedule:
    # 3 AM Phoenix time (10 AM UTC during standard time, 9 AM during DST)
    - cron: '0 10 * * *'
  workflow_dispatch:
    inputs:
      debug_mode:
        description: 'Enable debug logging'
        required: false
        default: 'false'
        type: boolean
      zip_codes:
        description: 'Override ZIP codes (comma-separated)'
        required: false
        type: string

env:
  PYTHON_VERSION: '3.13.4'
  UV_VERSION: '0.4.10'
  OLLAMA_VERSION: 'latest'

jobs:
  collect-data:
    runs-on: ubuntu-latest
    timeout-minutes: 90
    
    steps:
      - name: Checkout Repository
        uses: actions/checkout@v4
        
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          
      - name: Install UV Package Manager
        run: |
          curl -LsSf https://astral.sh/uv/install.sh | sh
          echo "$HOME/.cargo/bin" >> $GITHUB_PATH
          
      - name: Cache Dependencies
        uses: actions/cache@v4
        with:
          path: |
            ~/.cache/uv
            ~/.cache/pip
          key: ${{ runner.os }}-uv-${{ hashFiles('**/pyproject.toml', '**/uv.lock') }}
          restore-keys: |
            ${{ runner.os }}-uv-
            
      - name: Install Dependencies
        run: uv sync --dev
        
      - name: Setup Ollama for LLM Processing
        run: |
          # Install Ollama
          curl -fsSL https://ollama.ai/install.sh | sh
          
          # Start service
          OLLAMA_MAX_LOADED_MODELS=1 OLLAMA_NUM_PARALLEL=2 ollama serve &
          
          # Wait for service
          timeout 60 bash -c 'until curl -s http://localhost:11434/api/version; do sleep 2; done'
          
          # Pull model
          ollama pull llama3.2:latest
          
      - name: Configure Environment
        env:
          MONGODB_CONNECTION_STRING: ${{ secrets.MONGODB_CONNECTION_STRING }}
          MARICOPA_API_KEY: ${{ secrets.MARICOPA_API_KEY }}
          WEBSHARE_USERNAME: ${{ secrets.WEBSHARE_USERNAME }}
          WEBSHARE_PASSWORD: ${{ secrets.WEBSHARE_PASSWORD }}
          TARGET_ZIP_CODES: ${{ inputs.zip_codes || secrets.TARGET_ZIP_CODES }}
          LOG_LEVEL: ${{ inputs.debug_mode == 'true' && 'DEBUG' || secrets.LOG_LEVEL }}
        run: |
          uv run python scripts/setup_github_environment.py
          
      - name: Run Daily Collection
        id: collection
        run: |
          uv run python -m phoenix_real_estate.automation.workflows.daily_collection
        timeout-minutes: 75
        
      - name: Generate Collection Report
        if: always()
        run: |
          uv run python -m phoenix_real_estate.automation.reporting.daily_summary
          
      - name: Upload Artifacts
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: collection-${{ github.run_number }}
          path: |
            reports/daily-*.json
            logs/collection-*.log
          retention-days: 30
          
      - name: Create Issue on Failure
        if: failure()
        uses: actions/github-script@v7
        with:
          script: |
            const title = `Daily Collection Failed - ${new Date().toDateString()}`;
            const body = `
            ## Collection Failure Report
            
            **Run ID**: ${{ github.run_id }}
            **Run Number**: ${{ github.run_number }}
            **Timestamp**: ${new Date().toISOString()}
            
            ### Error Summary
            Check the [workflow run](${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}) for details.
            
            ### Next Steps
            1. Review workflow logs
            2. Check service health (MongoDB, Ollama)
            3. Verify API keys are valid
            4. Run manual collection if needed
            `;
            
            await github.rest.issues.create({
              owner: context.repo.owner,
              repo: context.repo.repo,
              title: title,
              body: body,
              labels: ['bug', 'automation', 'high-priority']
            });
```

### 2. Deploy Build and Test Workflow

Create `.github/workflows/build-test.yml`:

```yaml
name: Build and Test

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.13.4'
          
      - name: Install UV
        run: |
          curl -LsSf https://astral.sh/uv/install.sh | sh
          echo "$HOME/.cargo/bin" >> $GITHUB_PATH
          
      - name: Install Dependencies
        run: uv sync --dev
        
      - name: Run Tests
        run: |
          uv run pytest tests/ -v --cov=phoenix_real_estate --cov-report=xml
          
      - name: Type Check
        run: uv run pyright src/
        
      - name: Lint Check
        run: |
          uv run ruff check src/
          uv run ruff format --check src/
          
      - name: Security Scan
        run: |
          uv run bandit -r src/
          uv run safety check
```

### 3. Deploy Container Build Workflow

Create `.github/workflows/container-build.yml`:

```yaml
name: Container Build and Push

on:
  push:
    branches: [main]
    tags: ['v*']

env:
  REGISTRY: docker.io
  IMAGE_NAME: ${{ secrets.DOCKER_USERNAME }}/phoenix-real-estate

jobs:
  build:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout
        uses: actions/checkout@v4
        
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
        
      - name: Login to Docker Hub
        uses: docker/login-action@v3
        with:
          username: ${{ secrets.DOCKER_USERNAME }}
          password: ${{ secrets.DOCKER_PASSWORD }}
          
      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.IMAGE_NAME }}
          tags: |
            type=ref,event=branch
            type=ref,event=tag
            type=sha
            
      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          file: ./docker/Dockerfile
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

## Step 3: Initial Deployment

### 1. Prepare Repository

```bash
# Ensure all files are committed
git add .
git commit -m "feat: Add GitHub Actions workflows for production deployment

- Daily collection workflow with LLM processing
- Build and test automation
- Container deployment pipeline
- Comprehensive error handling"

# Create production branch
git checkout -b production
git push -u origin production
```

### 2. Enable Workflows

1. Go to Actions tab in GitHub
2. Click "I understand my workflows, go ahead and enable them"
3. Verify all workflows appear in the left sidebar

### 3. Test Manual Execution

```bash
# Trigger manual workflow run
gh workflow run "Daily Real Estate Data Collection" \
  --ref production \
  -f debug_mode=true \
  -f zip_codes="85031"
```

### 4. Monitor First Run

```bash
# Watch workflow execution
gh run watch

# View logs
gh run view --log

# Check for issues
gh issue list --label automation
```

## Step 4: Production Configuration

### 1. Set Up Monitoring

Create `.github/workflows/monitoring.yml`:

```yaml
name: Workflow Health Monitor

on:
  schedule:
    - cron: '0 */6 * * *'  # Every 6 hours
    
jobs:
  check-health:
    runs-on: ubuntu-latest
    
    steps:
      - name: Check Recent Workflow Runs
        uses: actions/github-script@v7
        with:
          script: |
            const runs = await github.rest.actions.listWorkflowRuns({
              owner: context.repo.owner,
              repo: context.repo.repo,
              workflow_id: 'daily-collection.yml',
              per_page: 5
            });
            
            const failures = runs.data.workflow_runs.filter(r => 
              r.conclusion === 'failure'
            );
            
            if (failures.length >= 3) {
              // Create alert issue
              await github.rest.issues.create({
                owner: context.repo.owner,
                repo: context.repo.repo,
                title: '🚨 Multiple Workflow Failures Detected',
                body: `${failures.length} failures in recent runs`,
                labels: ['critical', 'automation']
              });
            }
```

### 2. Configure Alerts

```yaml
# .github/CODEOWNERS
# Workflow files
.github/workflows/ @devops-team @project-lead

# Critical components
src/phoenix_real_estate/automation/ @backend-team
src/phoenix_real_estate/collectors/ @data-team
```

### 3. Set Up Environments

1. Go to Settings → Environments
2. Create "production" environment
3. Add protection rules:
   - Required reviewers: 1
   - Restrict to main branch
   - Add secrets specific to production

## Step 5: Operational Procedures

### Daily Operations

#### Morning Checks (9 AM Phoenix Time)
1. Verify overnight collection completed
2. Check GitHub Actions summary
3. Review any failure notifications
4. Validate data in MongoDB

#### Weekly Tasks
1. Review workflow execution metrics
2. Check GitHub Actions minute usage
3. Update dependencies if needed
4. Run security scans

### Incident Response

#### Collection Failure
```bash
# 1. Check failure reason
gh run view <run-id> --log | grep ERROR

# 2. Verify services
curl http://localhost:11434/api/version  # Ollama
mongosh $MONGODB_CONNECTION_STRING --eval "db.adminCommand('ping')"

# 3. Run manual collection
gh workflow run "Daily Real Estate Data Collection" \
  --ref production \
  -f debug_mode=true

# 4. Monitor execution
gh run watch
```

#### LLM Processing Issues
```bash
# 1. Check Ollama status
ollama list
ollama ps

# 2. Restart service
pkill ollama
OLLAMA_MAX_LOADED_MODELS=1 ollama serve &

# 3. Test model
echo "test" | ollama run llama3.2:latest "Extract: 3 bed"

# 4. Re-run failed properties
uv run python scripts/reprocess_failed.py --date today
```

### Maintenance Windows

#### Monthly Tasks
1. **Dependency Updates**
   ```bash
   uv lock --upgrade
   uv sync
   uv run pytest tests/
   ```

2. **Performance Review**
   ```bash
   # Generate monthly report
   uv run python scripts/monthly_performance_report.py
   ```

3. **Cost Analysis**
   - GitHub Actions usage
   - MongoDB storage
   - API call volumes

## Step 6: Scaling Considerations

### Horizontal Scaling
```yaml
# For multiple ZIP code groups
strategy:
  matrix:
    zip_group: 
      - "85031,85033"
      - "85035,85037"
```

### Performance Optimization
1. **Caching Strategy**
   - Model caching between runs
   - Dependency caching
   - Processed data caching

2. **Batch Size Tuning**
   ```bash
   # Adjust based on performance
   PROCESSING_BATCH_SIZE=20  # Increase if stable
   ```

## Troubleshooting

### Common Issues

#### 1. GitHub Actions Timeout
- **Symptom**: Workflow cancelled after 90 minutes
- **Solution**: 
  - Reduce batch sizes
  - Split ZIP codes across multiple jobs
  - Optimize LLM processing

#### 2. MongoDB Connection Limit
- **Symptom**: "Too many connections" error
- **Solution**:
  - Ensure proper connection pooling
  - Close connections in finally blocks
  - Monitor active connections

#### 3. Ollama Model Loading
- **Symptom**: "Model not found" errors
- **Solution**:
  - Verify model is pulled
  - Check disk space
  - Use model caching

### Debug Commands

```bash
# Enable verbose logging
export LOG_LEVEL=DEBUG
export OLLAMA_DEBUG=1

# Test individual components
uv run python -m phoenix_real_estate.foundation.config.test
uv run python -m phoenix_real_estate.collectors.test_connection
uv run python -m phoenix_real_estate.orchestration.test_llm

# Check resource usage
free -h
df -h
ps aux | grep ollama
```

## Security Best Practices

### Secret Rotation
1. Schedule quarterly secret rotation
2. Update one secret at a time
3. Test after each update
4. Document rotation dates

### Access Control
1. Limit workflow modification to senior developers
2. Review PR changes to workflows
3. Enable branch protection for workflow files
4. Audit secret access logs

### Monitoring
1. Track failed authentication attempts
2. Monitor unusual data access patterns
3. Alert on configuration changes
4. Review workflow modification history

## Success Metrics

### KPIs to Track
1. **Collection Success Rate**: Target >95%
2. **LLM Processing Accuracy**: Target >90%
3. **Workflow Execution Time**: Target <75 minutes
4. **GitHub Actions Usage**: Target <600 minutes/month
5. **Cost per Property**: Target <$0.001

### Reporting Dashboard

```python
# scripts/generate_dashboard.py
import json
from datetime import datetime, timedelta

def generate_dashboard():
    """Generate operational dashboard."""
    
    metrics = {
        "period": "last_7_days",
        "collection": {
            "total_runs": 7,
            "successful": 6,
            "failed": 1,
            "success_rate": 0.857
        },
        "properties": {
            "collected": 2145,
            "processed": 2089,
            "failed_processing": 56
        },
        "performance": {
            "avg_runtime_minutes": 68.3,
            "avg_properties_per_minute": 31.4
        },
        "costs": {
            "github_actions_minutes": 478,
            "estimated_monthly": 2052
        }
    }
    
    print(json.dumps(metrics, indent=2))
```

## Continuous Improvement

### Weekly Review Checklist
- [ ] Review failure patterns
- [ ] Identify optimization opportunities
- [ ] Update documentation
- [ ] Plan next improvements

### Monthly Planning
- [ ] Analyze trend data
- [ ] Review budget usage
- [ ] Plan feature additions
- [ ] Schedule maintenance

### Quarterly Assessment
- [ ] Full system audit
- [ ] Performance benchmarking
- [ ] Security review
- [ ] Architecture evaluation

## Support and Escalation

### Level 1: Automated Recovery
- Automatic retries
- Circuit breakers
- Fallback mechanisms

### Level 2: Operations Team
- Manual intervention
- Service restarts
- Configuration updates

### Level 3: Development Team
- Code fixes
- Architecture changes
- Feature additions

### Emergency Contacts
- On-call rotation schedule
- Escalation procedures
- Communication channels

---

This production deployment guide ensures reliable, scalable operation of the Phoenix Real Estate collection system within budget constraints while maintaining high data quality through integrated LLM processing.