# ADR-003: GitHub Actions vs Cloud Providers for Orchestration

## Status
**ACCEPTED** - Implemented in Epic 3 Automation & Orchestration

## Context
The Phoenix Real Estate Data Collection System requires automated daily orchestration to coordinate Epic 2's data collection across multiple sources. The system must:

- Execute daily collection workflows automatically
- Orchestrate Epic 2 collectors (Maricopa API, PhoenixMLS scraper)
- Coordinate with Epic 1's database and configuration systems
- Operate within strict budget constraints ($1-25/month total)
- Support containerized deployment with Docker
- Provide monitoring and alerting for workflow execution
- Handle error recovery and partial failure scenarios

Three primary orchestration platforms were considered:

### Option 1: Cloud Provider Managed Services
**AWS**: Lambda + EventBridge + ECS
- Event-driven execution with Lambda functions
- Container orchestration with ECS Fargate
- Managed scheduling with EventBridge

**Cost Analysis**:
- Lambda: $0.20 per 1M requests + compute time
- ECS Fargate: $0.04/vCPU-hour + $0.004/GB-hour
- EventBridge: $1.00 per million events
- **Monthly estimate: $15-40/month** (60%-160% of total budget)

**Google Cloud**: Cloud Functions + Cloud Scheduler + Cloud Run
- Similar pricing structure to AWS
- **Monthly estimate: $12-35/month** (48%-140% of total budget)

### Option 2: Self-Hosted Solutions
**Kubernetes + CronJobs**: Local or VPS deployment
- Full control over execution environment
- VPS costs: $5-20/month for suitable instance
- Additional complexity for management

**Docker + Cron**: Simple VPS or local deployment
- Minimal resource requirements
- VPS costs: $3-10/month
- Manual infrastructure management

### Option 3: GitHub Actions
**Execution Environment**: GitHub-hosted runners
- 2000 minutes/month free tier
- Built-in Docker support
- Native CI/CD integration with repository

**Cost Analysis**:
- Free tier: 2000 minutes/month
- Daily workflow: ~8 minutes execution time
- Monthly usage: 8 × 30 = 240 minutes (12% of free tier)
- **Total cost: $0/month**

## Decision
**We will implement GitHub Actions** as the primary orchestration platform.

### Architecture Decision
```
GitHub Actions Workflow → Docker Container → Epic 3 Orchestration Engine → Epic 2 Collectors → Epic 1 Database
```

### Key Implementation Components
```yaml
# .github/workflows/daily-collection.yml
name: Daily Real Estate Data Collection

on:
  schedule:
    - cron: '0 10 * * *'  # 3 AM Phoenix Time (10 AM UTC)
  workflow_dispatch:

jobs:
  collect-data:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run Data Collection
        run: |
          docker build -t phoenix-real-estate .
          docker run --env-file .env phoenix-real-estate
```

## Consequences

### Positive Consequences
1. **Budget Compliance**: $0/month cost preserves entire budget for other needs
2. **Native Integration**: Seamless CI/CD with code repository
3. **Docker Support**: Built-in containerization capabilities
4. **Monitoring**: Native workflow monitoring and logging
5. **Reliability**: GitHub's infrastructure reliability (99.9% uptime)
6. **Simplicity**: No additional infrastructure to manage
7. **Security**: Built-in secrets management for Epic 1 configuration

### Negative Consequences
1. **Resource Limits**: 6GB RAM, 14GB SSD per runner
2. **Execution Time**: 6-hour maximum workflow duration
3. **Concurrency**: Limited concurrent workflows
4. **Vendor Lock-in**: Dependent on GitHub's platform
5. **Network Limitations**: Potential IP blocking from heavy usage

### Impact on System Architecture

#### Epic 1 Foundation Integration
- GitHub Secrets store Epic 1's configuration variables
- Workflow environment injects configuration into containers
- GitHub Actions logs integrate with Epic 1's logging framework

#### Epic 2 Collection Coordination
- Orchestrates Maricopa API and PhoenixMLS collectors sequentially
- Manages rate limiting across collectors
- Handles individual collector failures gracefully

#### Epic 3 Orchestration Implementation
```python
class GitHubActionsOrchestrator:
    def __init__(self, config: ConfigProvider):
        self.config = config
        self.logger = get_logger("github.orchestrator")
    
    async def run_daily_collection(self):
        """Orchestrate daily collection within GitHub Actions environment"""
        # Use Epic 1 configuration
        zip_codes = self.config.get_required("TARGET_ZIP_CODES").split(",")
        
        # Coordinate Epic 2 collectors
        for collector_type in [DataSourceType.MARICOPA_API, DataSourceType.PHOENIX_MLS]:
            collector = await CollectorFactory.create_collector(
                collector_type, self.config, self.repository
            )
            await self._execute_collection(collector, zip_codes)
```

#### Epic 4 Quality Integration
- GitHub Actions provides execution metrics and logs
- Workflow status monitoring for quality assurance
- Artifact storage for execution reports and data quality metrics

### Performance Characteristics
- **Execution Time**: 8-15 minutes for daily collection (well under 6-hour limit)
- **Resource Usage**: ~2GB RAM, 4GB storage (within runner limits)
- **Throughput**: 200-500 properties/day (meets requirements)
- **Reliability**: 99.9% execution success rate based on GitHub SLA

### Alternative Comparison

#### Why Not AWS/GCP?
- **Cost**: Would consume 48%-160% of total budget
- **Complexity**: Additional infrastructure management overhead
- **Over-engineering**: GitHub Actions meets all requirements at $0 cost

#### Why Not Self-Hosted?
- **Cost**: VPS costs would consume 12%-80% of budget
- **Maintenance**: Additional operational overhead
- **Reliability**: Lower uptime guarantees than GitHub
- **Security**: Additional security management required

## Risk Mitigation

### GitHub Actions Quota Risk
- **Current Usage**: 240 minutes/month (12% of free tier)
- **Monitoring**: Track monthly usage with alerts at 75% and 90%
- **Optimization**: Streamline workflows to minimize execution time
- **Fallback**: Local execution capability for emergency scenarios

### Vendor Lock-in Risk
- **Mitigation**: Docker containers are portable across platforms
- **Fallback**: Epic 3 orchestration engine can run in any Docker environment
- **Testing**: Regular validation of local execution capability
- **Documentation**: Clear migration procedures to alternative platforms

### Network Limitations Risk
- **Proxy Integration**: Epic 2's proxy management for PhoenixMLS
- **Rate Limiting**: Conservative request patterns to avoid IP blocking
- **Monitoring**: Track request success rates and IP reputation
- **Fallback**: Alternative collection strategies if IP blocked

### Resource Constraints Risk
- **Memory Management**: Efficient processing with <2GB RAM usage
- **Storage Optimization**: Clean up temporary files during execution
- **Time Management**: Parallel processing where safe to reduce execution time
- **Monitoring**: Track resource usage trends

## Implementation Guidelines

### Workflow Design Principles
1. **Fail Fast**: Early validation of configuration and dependencies
2. **Graceful Degradation**: Continue with available collectors if one fails
3. **Comprehensive Logging**: Detailed execution logs for debugging
4. **Security**: Never log sensitive configuration values
5. **Monitoring**: Report execution metrics to Epic 4 quality systems

### Configuration Management
- GitHub Secrets for sensitive Epic 1 configuration
- Environment variable injection for non-sensitive settings
- Docker environment for consistent runtime configuration
- Validation of all required configuration before execution

### Error Handling Strategy
```python
async def execute_collection_workflow():
    try:
        # Initialize Epic 1 components
        config = await initialize_configuration()
        repository = await initialize_repository(config)
        
        # Execute Epic 2 collection
        results = await orchestrate_collectors(config, repository)
        
        # Generate Epic 3 reports
        await generate_daily_report(results)
        
    except Exception as e:
        logger.error(f"Workflow failed: {e}")
        await send_failure_notification(e)
        raise
```

### Quality and Monitoring
- Workflow execution metrics tracked in GitHub Actions
- Daily success/failure notifications
- Performance metrics collection
- Integration with Epic 4 quality monitoring

## Validation Criteria
- [ ] Daily workflow executes successfully within 15 minutes
- [ ] Resource usage stays under 2GB RAM and 4GB storage
- [ ] Monthly GitHub Actions usage under 500 minutes (25% of free tier)
- [ ] Epic 1 configuration successfully injected via GitHub Secrets
- [ ] Epic 2 collectors successfully orchestrated in workflow
- [ ] Workflow failures trigger appropriate notifications
- [ ] Execution logs provide sufficient debugging information
- [ ] Docker containers build and execute successfully in Actions environment

## Security Considerations
- GitHub Secrets encrypted storage for Epic 1 configuration
- No sensitive data in workflow logs or artifacts
- Minimal Docker image attack surface
- Regular security scanning of dependencies
- Principle of least privilege for GitHub Actions permissions

## Future Scalability
- **Parallel Workflows**: Multiple ZIP code regions in parallel
- **Advanced Scheduling**: Multiple collection times per day
- **Self-Hosted Runners**: If resource requirements exceed hosted runners
- **Hybrid Approach**: Critical workflows on GitHub, supplementary on self-hosted

## Monitoring and Alerting
```yaml
# GitHub Actions monitoring integration
on:
  workflow_run:
    workflows: ["Daily Real Estate Data Collection"]
    types:
      - completed

jobs:
  notify-status:
    if: ${{ github.event.workflow_run.conclusion == 'failure' }}
    runs-on: ubuntu-latest
    steps:
      - name: Send Failure Notification
        run: echo "Workflow failed - investigate immediately"
```

## References
- Epic 3: Automation & Orchestration workflow specification
- GitHub Actions documentation and pricing
- Phoenix Real Estate budget constraints
- Epic 1: Configuration management integration
- Epic 2: Data collection orchestration requirements

---
**Author**: Integration Architect  
**Date**: 2025-01-20  
**Review**: Architecture Review Board, DevOps Team  
**Next Review**: After 30 days of production workflow execution