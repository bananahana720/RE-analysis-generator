# Project File Index

## Root Directory
- **README.md** - Main project documentation and quick start guide
- **pyproject.toml** - Python project configuration and dependencies
- **uv.lock** - UV package manager lock file
- **Makefile** - Build automation and development commands
- **pyrightconfig.json** - TypeScript/Python type checking configuration
- **CODEOWNERS** - Repository code ownership assignments
- **start_mongodb.bat** - Windows batch script to start MongoDB service
- **.env.sample** - Environment variables template
- **nul** - Temporary system file

## Source Code (/src/phoenix_real_estate/)

### Core Package
- **__init__.py** - Main package initialization and exports
- **models/** - Data models and schemas
  - **__init__.py** - Models package initialization
  - **property.py** - Property data model definition

### Foundation Infrastructure (/foundation/)
- **__init__.py** - Foundation package initialization
- **interfaces.py** - Core interface definitions
- **config/** - Configuration management system
  - **__init__.py** - Config package initialization
  - **base.py** - Base configuration classes
  - **provider.py** - Configuration provider implementation
  - **secrets.py** - Secrets management system
  - **environment.py** - Environment-specific configurations
- **database/** - Database abstraction layer
  - **__init__.py** - Database package initialization
  - **connection.py** - Database connection management
  - **repositories.py** - Repository pattern implementation
  - **repositories_backup.py** - Backup repository implementations
  - **schema.py** - Database schema definitions
  - **mock.py** - Mock database for testing
- **logging/** - Structured logging system
  - **__init__.py** - Logging package initialization
  - **logger.py** - Main logger implementation
  - **factory.py** - Logger factory pattern
  - **handlers.py** - Custom log handlers
  - **formatters.py** - Log message formatters
- **monitoring/** - System monitoring and metrics
  - **__init__.py** - Monitoring package initialization
  - **config.py** - Monitoring configuration
  - **metrics.py** - Metrics collection
  - **exporters.py** - Metrics export functionality
  - **cost_tracking.py** - Budget and cost tracking
- **utils/** - Common utilities
  - **__init__.py** - Utils package initialization
  - **helpers.py** - General helper functions
  - **exceptions.py** - Custom exception hierarchy
  - **validators.py** - Data validation utilities

### Data Collectors (/collectors/)
- **__init__.py** - Collectors package initialization
- **base/** - Base collector classes
  - **__init__.py** - Base package initialization
  - **collector.py** - Abstract base collector
  - **adapter.py** - Data adapter patterns
  - **rate_limiter.py** - Rate limiting implementation
  - **validators.py** - Data validation for collectors
- **maricopa/** - Maricopa County API collector
  - **__init__.py** - Maricopa package initialization
  - **collector.py** - Main Maricopa API collector
- **phoenix_mls/** - Phoenix MLS scraping system
  - **__init__.py** - Phoenix MLS package initialization
  - **scraper.py** - Main MLS scraper implementation
  - **parser.py** - HTML parsing utilities
  - **captcha_handler.py** - CAPTCHA solving integration
  - **anti_detection.py** - Anti-detection mechanisms
  - **error_detection.py** - Error detection and handling
  - **proxy_manager.py** - Proxy rotation system
  - **metrics_integration.py** - Metrics collection for scraping
- **processing/** - Data processing pipeline
  - **__init__.py** - Processing package initialization
  - **service.py** - Main processing service
  - **pipeline.py** - Data processing pipeline
  - **extractor.py** - Data extraction utilities
  - **validator.py** - Processing validation
  - **monitoring.py** - Processing monitoring
  - **performance.py** - Performance optimization
  - **error_handling.py** - Error handling for processing
  - **cache.py** - Caching mechanisms
  - **llm_client.py** - LLM integration client

### Services (/services/)
- **__init__.py** - Services package initialization
- **email_service.py** - Email notification service

### API Layer (/api/)
- **__init__.py** - API package initialization
- **health.py** - Health check endpoints
- **health_fixes.sed** - Health endpoint fixes script

### Orchestration (/orchestration/)
- **__init__.py** - Orchestration package initialization
- **processing_integrator.py** - Integration orchestration

## Configuration (/config/)

### Environment Configuration
- **base.yaml** - Base configuration settings
- **environments/** - Environment-specific configs
  - **environment-config.yaml** - Environment configuration template
  - **development.yaml** - Development environment settings
  - **testing.yaml** - Test environment settings
  - **production.yaml** - Production environment settings

### Service Configuration
- **services/** - Service-specific configurations
  - **base-services.yaml** - Base service configurations
  - **production-phoenix-mls.yaml** - Production Phoenix MLS settings
  - **llm-production.yaml** - LLM service production config
  - **proxies.yaml** - Proxy service configuration
- **deployment/** - Deployment configurations
  - **production-deployment.yaml** - Production deployment config
  - **deploy-staging.yaml** - Staging deployment config
  - **deploy-production.yaml** - Production deployment config
- **selectors/** - Web scraping selectors
  - **phoenix_mls.yaml** - Phoenix MLS CSS selectors
- **templates/** - Configuration templates
  - **production-secrets.yaml.template** - Production secrets template
  - **proxies.yaml.example** - Proxy configuration example

### Monitoring Configuration
- **monitoring/** - Monitoring and alerting configs
  - **alerts.yml** - Basic alert definitions
  - **alerts_generated.yml** - Generated alert rules
  - **alertmanager.yml** - AlertManager configuration
  - **alertmanager-fixed.yml** - Fixed AlertManager config
  - **docker-compose.yml** - Monitoring stack Docker compose
  - **production-docker-compose.yml** - Production monitoring stack
  - **optimized-docker-compose.yml** - Optimized monitoring config
  - **baseline-configuration.yml** - Baseline monitoring config
  - **production-alerts.yml** - Production alert rules
  - **grafana-datasources.yml** - Grafana data source config
  - **grafana-dashboards.yml** - Grafana dashboard config
  - **grafana_dashboard.json** - Main Grafana dashboard
  - **llm_dashboard.json** - LLM-specific dashboard
  - **logrotate.conf** - Log rotation configuration
  - **prometheus.yml** - Prometheus configuration
  - **phoenix_alerts.yml** - Phoenix-specific alerts
  - **validation-report.json** - Monitoring validation report
  - **dashboards/** - Dashboard definitions
    - **executive-dashboard.json** - Executive summary dashboard
    - **operational-dashboard.json** - Operations dashboard
    - **performance-dashboard.json** - Performance metrics dashboard
    - **business-intelligence-dashboard.json** - BI dashboard
- **prometheus/** - Prometheus-specific configs
  - **prometheus.yml** - Main Prometheus configuration
  - **alerts/** - Prometheus alert rules
    - **llm_processing_alerts.yml** - LLM processing alerts
- **grafana/** - Grafana-specific configs
  - **dashboards/** - Grafana dashboard definitions
    - **llm_processing_dashboard.json** - LLM processing dashboard

## Tests (/tests/)

### Core Test Structure
- **conftest.py** - Pytest configuration and fixtures
- **__init__.py** - Tests package initialization

### Foundation Tests
- **foundation/** - Foundation layer tests
  - **__init__.py** - Foundation tests initialization
  - **test_utils.py** - Utility function tests
  - **test_exceptions.py** - Exception handling tests
  - **test_logging.py** - Logging system tests
  - **config/** - Configuration tests
    - **__init__.py** - Config tests initialization
    - **test_secrets.py** - Secrets management tests
    - **test_base.py** - Base configuration tests
    - **test_base_enhanced.py** - Enhanced configuration tests
    - **test_enhanced_validation.py** - Enhanced validation tests
    - **test_environment.py** - Environment configuration tests
    - **test_benchmarks.py** - Configuration benchmark tests
    - **test_performance.py** - Configuration performance tests
    - **test_production_scenarios.py** - Production scenario tests
    - **test_task04_phase3_configuration.py** - Phase 3 config tests
    - **test_task04_phase3_environment_setup.py** - Environment setup tests
    - **test_thread_safe_rotation.py** - Thread safety tests
    - **PRODUCTION_TEST_SUMMARY.md** - Production test summary
    - **BENCHMARKS_README.md** - Benchmark documentation
    - **benchmarks.py** - Benchmark test implementations
  - **database/** - Database tests
    - **__init__.py** - Database tests initialization
    - **test_schema.py** - Database schema tests
    - **test_repositories.py** - Repository pattern tests
    - **test_connection.py** - Database connection tests
  - **monitoring/** - Monitoring tests
    - **__init__.py** - Monitoring tests initialization
    - **test_integration.py** - Monitoring integration tests
    - **test_exporters.py** - Metrics exporter tests
    - **test_metrics.py** - Metrics collection tests

### Collector Tests
- **collectors/** - Data collector tests
  - **__init__.py** - Collectors tests initialization
  - **test_integration_validation.py** - Integration validation tests
  - **test_maricopa_integration.py** - Maricopa integration tests
  - **test_performance_validation.py** - Performance validation tests
  - **base/** - Base collector tests
    - **__init__.py** - Base tests initialization
    - **test_rate_limiter.py** - Rate limiting tests
    - **test_validators.py** - Validation logic tests
  - **maricopa/** - Maricopa collector tests
    - **__init__.py** - Maricopa tests initialization
    - **test_collector.py** - Main collector tests
    - **test_integration.py** - Maricopa integration tests
  - **phoenix_mls/** - Phoenix MLS tests
    - **__init__.py** - Phoenix MLS tests initialization
    - **test_address_normalization.py** - Address normalization tests
    - **test_proxy_manager.py** - Proxy management tests
    - **test_proxy_manager_edge_cases.py** - Proxy edge case tests
    - **test_tdd_runner.py** - TDD test runner
    - **test_anti_detection.py** - Anti-detection tests
    - **test_error_detection.py** - Error detection tests
    - **test_session_management.py** - Session management tests
    - **test_scraper.py** - Main scraper tests
    - **test_captcha_handler.py** - CAPTCHA handling tests
    - **test_parser.py** - HTML parser tests
    - **conftest.py** - Phoenix MLS test configuration
  - **processing/** - Processing pipeline tests
    - **test_llm_service.py** - LLM service tests
    - **test_service_unit.py** - Service unit tests
    - **test_ollama_setup.py** - Ollama setup tests
    - **test_extractor.py** - Data extraction tests
    - **test_resource_monitor.py** - Resource monitoring tests
    - **test_pipeline_integration.py** - Pipeline integration tests
    - **test_processing_validator.py** - Processing validation tests
    - **test_ollama_integration.py** - Ollama integration tests
    - **test_error_handling_simple_integration.py** - Error handling tests
    - **test_pipeline.py** - Pipeline tests
    - **test_ollama_client.py** - Ollama client tests
    - **test_llm_service_comprehensive.py** - Comprehensive LLM tests
    - **test_performance_benchmarks.py** - Performance benchmark tests
    - **test_integration_performance.py** - Integration performance tests
    - **test_imports.py** - Import validation tests
    - **test_error_handling.py** - Error handling tests

### Integration Tests
- **integration/** - Cross-component integration tests
  - **__init__.py** - Integration tests initialization
  - **test_database_integration.py** - Database integration tests
  - **test_database_connection.py** - Database connection integration
  - **test_captcha_integration.py** - CAPTCHA integration tests
  - **test_logging_integration.py** - Logging integration tests
  - **test_phoenix_mls_performance.py** - Phoenix MLS performance tests
  - **test_processing_integrator.py** - Processing integrator tests
  - **config/** - Configuration integration tests
    - **__init__.py** - Config integration tests initialization
    - **INTEGRATION_TEST_SUMMARY.md** - Integration test summary
    - **test_task04_phase3_integration.py** - Phase 3 integration tests
    - **test_config_integration.py** - Configuration integration tests
    - **test_system_integration.py** - System integration tests

### End-to-End Tests
- **e2e/** - End-to-end tests
  - **__init__.py** - E2E tests initialization
  - **pytest.ini** - E2E pytest configuration
  - **E2E_TEST_REPORT.md** - E2E test report
  - **E2E_TESTING_GUIDE.md** - E2E testing guide
  - **test_simple_e2e.py** - Simple E2E tests
  - **conftest.py** - E2E test configuration
  - **test_processing_pipeline_e2e.py** - Processing pipeline E2E tests
  - **test_infrastructure_e2e.py** - Infrastructure E2E tests
  - **fixtures/** - E2E test fixtures
    - **__init__.py** - Fixtures initialization
    - **property_samples.py** - Property test data samples

### Test Fixtures and Data
- **fixtures/** - Test data fixtures
  - **maricopa/** - Maricopa test data
    - **search_response.json** - Mock search responses
    - **parcel_details.json** - Mock parcel data
    - **valuations.json** - Mock valuation data
    - **error_responses.json** - Mock error responses
    - **residential_details.json** - Mock residential data
    - **property_info.json** - Mock property information
    - **README.md** - Test fixtures documentation

### Workflow Tests
- **test_workflow_coordinator.py** - Workflow coordination tests
- **test_secrets_validator.py** - Secrets validation tests
- **test_workflow_validator.py** - Workflow validation tests
- **test_workflow_runner.py** - Workflow runner tests
- **test_secrets_setup.py** - Secrets setup tests
- **test_mock_services.py** - Mock services tests

## GitHub Actions Workflows (/.github/workflows/)

### Core Workflows
- **ci-cd.yml** - Continuous integration and deployment
- **data-collection.yml** - Main data collection workflow
- **security.yml** - Security scanning and compliance
- **deployment.yml** - Production deployment management
- **monitoring.yml** - System monitoring and alerting
- **maintenance.yml** - System maintenance tasks

### Data Collection Workflows
- **data-collection-maricopa.yml** - Maricopa County data collection
- **data-collection-phoenix-mls.yml** - Phoenix MLS data collection
- **data-collection-orchestrator.yml** - Collection orchestration
- **data-processing-llm.yml** - LLM data processing
- **data-validation.yml** - Data quality validation

### Test and Development Workflows
- **test-workflows.yml** - Workflow testing
- **test-dispatch.yml** - Manual workflow dispatch testing
- **workflow-test-minimal.yml** - Minimal workflow testing
- **data-collection-test.yml** - Data collection testing
- **data-collection-production.yml** - Production data collection
- **validate-secrets.yml** - Secrets validation workflow
- **test-secrets-access.yml** - Secrets access testing

### Utility Workflows
- **proxy-update.yml** - Proxy configuration updates
- **setup-ollama.yml** - Ollama service setup

### Legacy and Debug Workflows
- **data-collection-simple.yml** - Simplified data collection
- **data-collection-debug-simple.yml** - Debug data collection
- **data-collection-test-complexity.yml** - Complex test scenarios
- **data-collection-backup.yml** - Backup data collection
- **data-collection-debug.yml** - Debug workflows
- **data-collection-no-env.yml** - No environment data collection
- **data-collection-minimal.yml** - Minimal data collection

## Scripts (/scripts/)

### Setup Scripts
- **setup/** - Environment setup utilities
  - **setup_development_environment.py** - Development environment setup
  - **setup_ollama.py** - Ollama service setup
  - **setup_mongodb_atlas.py** - MongoDB Atlas configuration
  - **setup_database.py** - Database initialization
  - **setup_secrets.py** - Secrets configuration
  - **setup_dev.py** - Development setup
  - **configure_services.py** - Service configuration
  - **auto_configure_services.py** - Automated service setup
  - **check_setup_status.py** - Setup status validation
  - **update_env_safely.py** - Safe environment updates
  - **start_mongodb_service.bat** - MongoDB service start script

### Testing Scripts
- **testing/** - Testing utilities
  - **WEBSHARE_API_GUIDE.md** - WebShare API documentation
  - **discover_phoenix_mls_selectors.py** - Selector discovery
  - **test_phoenix_mls_selectors.py** - Selector testing
  - **workflow_test_runner.py** - Workflow test execution
  - **test_webshare_proxy.py** - Proxy testing
  - **test_data_collection.py** - Data collection testing
  - **quick_e2e_check.py** - Quick E2E validation
  - **test_property_extractor.py** - Property extraction testing
  - **mock_services.py** - Mock service implementations
  - **test_maricopa_api.py** - Maricopa API testing
  - **test_webshare_fix.py** - WebShare fixes testing
  - **test_services_simple.py** - Simple service testing
  - **demo_performance_optimizations.py** - Performance demo
  - **test_webshare_final.py** - Final WebShare testing
  - **run_e2e_tests.py** - E2E test runner
  - **test_mongodb_connection.py** - MongoDB connection testing
  - **test_db_connection.py** - Database connection testing
  - **test_workflow_chain.py** - Workflow chain testing
  - **verify_e2e_setup.py** - E2E setup verification
  - **test_maricopa_summary.py** - Maricopa testing summary
  - **test_phoenix_mls_with_services.py** - Phoenix MLS service testing
  - **test_performance_optimizations.py** - Performance testing
  - **test_maricopa_collector.py** - Maricopa collector testing
  - **run_llm_e2e_tests.py** - LLM E2E test runner
  - **test_llm_processing.py** - LLM processing tests
  - **simple_llm_test.py** - Simple LLM testing
  - **simple_mongodb_test.py** - Simple MongoDB testing
  - **simple_performance_test.py** - Simple performance testing
  - **simple_error_test.py** - Simple error testing
  - **test_llm_import_fixes.py** - LLM import fixes testing
  - **api_integration_diagnostic.py** - API integration diagnostics
  - **api_credential_setup.py** - API credential setup
  - **test_maricopa_ci.py** - Maricopa CI testing
  - **production/** - Production testing
    - **validate_environment.py** - Environment validation
    - **performance_monitor.py** - Performance monitoring
    - **smoke_tests.py** - Production smoke tests
    - **production_test.py** - Production testing
    - **prod_test.py** - Production test suite
  - **validation/** - Validation utilities
    - **test_microservice_workflows.py** - Microservice workflow testing
    - **validate_data_quality_backup.py** - Data quality backup validation
    - **validate_data_quality.py** - Data quality validation
    - **send_notification.py** - Notification testing

### Validation Scripts
- **validation/** - System validation utilities
  - **validate_structure.py** - Project structure validation
  - **validate_configuration.py** - Configuration validation
  - **validate_system.py** - System validation
  - **validate_secrets.py** - Secrets validation
  - **validate_mongodb_atlas.py** - MongoDB Atlas validation
  - **validate_phoenix_mls_performance.py** - Phoenix MLS performance validation
  - **validate_enhanced.py** - Enhanced validation suite
  - **workflow_validator.py** - Workflow validation

### Deployment Scripts
- **deploy/** - Deployment utilities
  - **setup_production_environment.py** - Production environment setup
  - **deploy_llm_service.py** - LLM service deployment
  - **start_processors.py** - Processing service startup
  - **start_collectors.py** - Collector service startup
  - **validate_component.py** - Component validation
  - **start_orchestration.py** - Orchestration startup
  - **validate_pipeline.py** - Pipeline validation
  - **rollback.py** - Deployment rollback
  - **health_check.py** - Health check utilities
  - **performance_baseline.py** - Performance baseline
  - **send_collection_email.py** - Collection email notifications
  - **validate_email_service.py** - Email service validation
  - **test_production_workflow.py** - Production workflow testing
  - **monitoring_dashboard.py** - Monitoring dashboard setup
  - **batch_optimizer.py** - Batch processing optimization
  - **quality_monitor.py** - Quality monitoring
  - **cost_optimizer.py** - Cost optimization
  - **setup_monitoring.py** - Monitoring setup
  - **deploy_production_monitoring.py** - Production monitoring deployment
  - **start_monitoring.bat** - Windows monitoring startup
  - **setup_monitoring_dashboards.py** - Dashboard setup
  - **validate_monitoring_system.py** - Monitoring system validation
  - **infrastructure_optimizer.py** - Infrastructure optimization
  - **systemd/** - Linux systemd service files
    - **phoenix-llm-processor.service** - LLM processor service
    - **ollama.service** - Ollama service definition
    - **phoenix-real-estate.service** - Main service definition
  - **setup_production.sh** - Production setup script
  - **logs/** - Deployment logs
    - **development.log** - Development deployment logs

### Database Scripts
- **database/** - Database management utilities
  - **README.md** - Database scripts documentation
  - **validate_schema.py** - Schema validation
  - **migrate.py** - Database migration utilities
  - **backup.py** - Database backup utilities

### Utility Scripts
- **utilities/** - General utilities
  - **launch_llm_processing.py** - LLM processing launcher
  - **migrate_maricopa_client.py** - Maricopa client migration
  - **check_llm_status.py** - LLM service status check

### Example Scripts
- **examples/** - Example implementations
  - **test_epic_integration.py** - Epic integration examples

## Documentation (/docs/)

### Project Overview
- **project-overview/** - High-level project documentation
  - **CONTRIBUTING.md** - Contribution guidelines

### Architecture Documentation
- **design/** - Design documentation
  - **architecture.md** - System architecture overview
- **architecture/** - Detailed architecture docs
  - **hot-reload-design.md** - Hot reload system design
  - **hot-reload-api-spec.md** - Hot reload API specification
  - **hot-reload-implementation-roadmap.md** - Implementation roadmap
  - **hot-reload-usage-examples.md** - Usage examples

### API Documentation
- **api/** - API documentation
  - **README.md** - API documentation overview
  - **phoenix-mls-scraper-api.md** - Phoenix MLS scraper API
  - **phoenix-mls-quick-reference.md** - Quick reference guide

### Technical Documentation
- **secrets-management.md** - Secrets management guide
- **logging.md** - Logging system documentation
- **logging-implementation-summary.md** - Logging implementation summary
- **rate-limiting-strategies.md** - Rate limiting documentation
- **phoenix-mls-selector-update-guide.md** - Selector update guide
- **production-setup.md** - Production setup guide
- **phoenix_mls_session_management.md** - Session management guide
- **phoenix-mls-performance-validation.md** - Performance validation
- **monitoring.md** - Monitoring system documentation
- **captcha-handling.md** - CAPTCHA handling guide
- **collectors/maricopa-api-collector.md** - Maricopa collector documentation
- **mongodb-local-setup.md** - Local MongoDB setup
- **mongodb-atlas-setup.md** - MongoDB Atlas setup
- **github-push-checklist.md** - GitHub push checklist
- **SETUP_SERVICES_GUIDE.md** - Services setup guide
- **FINAL_ACTION_PLAN.md** - Final action plan
- **MARICOPA_API_ANALYSIS_REPORT.md** - Maricopa API analysis
- **configuration.md** - Configuration documentation
- **production-deployment-guide.md** - Production deployment guide

### Project Management
- **project-management/** - Project management documentation
  - **CLAUDE.md** - AI assistant development guide
  - **epics/** - Epic-level documentation
    - **epic-01-foundation-infrastructure.md** - Foundation epic
    - **epic-03-automation-orchestration.md** - Automation epic
    - **epic-04-quality-assurance.md** - Quality assurance epic
  - **tasks/** - Task-specific documentation
    - **foundation/** - Foundation tasks
      - **task-02-database-schema.md** - Database schema task
      - **task-04-maricopa-api-client-architecture.md** - Maricopa architecture
      - **task-04-phase3-summary.md** - Phase 3 summary
      - **task-04-phase-4-validation-report.md** - Phase 4 validation
    - **data-collection/** - Data collection tasks
      - **task-04-maricopa-api-client.md** - Maricopa API client
      - **task-05-phoenix-mls-scraper.md** - Phoenix MLS scraper
    - **automation/** - Automation tasks
      - **task-07-github-actions-workflow.md** - GitHub Actions workflow
      - **task-08-orchestration-engine.md** - Orchestration engine
      - **task-09-docker-deployment.md** - Docker deployment
    - **quality/** - Quality tasks
      - **task-10-testing-framework.md** - Testing framework
      - **task-11-monitoring-observability.md** - Monitoring and observability
      - **task-12-compliance-validation.md** - Compliance validation
  - **architecture/** - Architecture documentation
    - **epic-integration-architecture.md** - Integration architecture
    - **system-validation.md** - System validation
    - **adrs/** - Architecture Decision Records
      - **adr-001-repository-pattern-vs-direct-database-access.md** - Repository pattern ADR
      - **adr-003-github-actions-vs-cloud-providers-orchestration.md** - Orchestration ADR
      - **adr-005-error-handling-exception-strategy.md** - Error handling ADR
    - **interfaces/** - Interface definitions
      - **epic-1-foundation-interfaces.py** - Foundation interfaces
      - **epic-2-collection-interfaces.py** - Collection interfaces
      - **epic-3-automation-interfaces.py** - Automation interfaces

### Reports and Summaries
- **summaries/** - Implementation summaries
  - **quality_report.md** - Quality assessment report
  - **VALIDATION_FIXES_REQUIRED.md** - Required validation fixes
  - **VALIDATION_REPORT.md** - Validation report
  - **TASK_04_IMPLEMENTATION_SUMMARY.md** - Task 4 implementation summary
  - **MONITORING_IMPLEMENTATION.md** - Monitoring implementation summary
  - **PRODUCTION_READINESS_REPORT.md** - Production readiness report
  - **SETUP_STATUS_REPORT.md** - Setup status report
  - **REAL_WORLD_TEST_REPORT.md** - Real-world testing report
  - **TROUBLESHOOTING_FIXES.md** - Troubleshooting fixes
  - **LLM_REAL_ESTATE_PROCESSING_RESEARCH.md** - LLM processing research
  - **PHOENIX_REAL_ESTATE_DEEP_ANALYSIS_FINDINGS.md** - Deep analysis findings
  - **system-workflow-overview.md** - System workflow overview
- **project-reports/** - Detailed project reports
  - **README.md** - Project reports overview
  - **EXECUTIVE_SUMMARY.md** - Executive summary report
  - **ROOT_CLEANUP_SUMMARY.md** - Root cleanup summary
  - **maricopa_api_test_report.json** - Maricopa API test results
  - **maricopa_api_analysis_summary.md** - Maricopa API analysis
  - **production/** - Production reports
    - **MONGODB_ATLAS_SETUP_SUMMARY.md** - MongoDB Atlas setup
    - **MONGODB_QUICK_START.md** - MongoDB quick start
    - **PRODUCTION_READINESS_REPORT.md** - Production readiness
    - **TASK_04_IMPLEMENTATION_SUMMARY.md** - Task 4 implementation
  - **validation/** - Validation reports
    - **ENVIRONMENT_VALIDATION_REPORT.md** - Environment validation
    - **VALIDATION_REPORT.md** - System validation
    - **STRUCTURE_CLEANUP_SUMMARY.md** - Structure cleanup
    - **SERVICE_STATUS_REPORT.md** - Service status
  - **testing/** - Test reports
    - **E2E_INTEGRATION_TEST_REPORT.md** - E2E integration tests
    - **E2E_TEST_REPORT.md** - E2E test report
    - **FINAL_E2E_TEST_REPORT.md** - Final E2E test report
    - **maricopa_api_test_report.json** - Maricopa API test data
    - **mutation_test_results.json** - Mutation testing results
  - **setup/** - Setup reports
    - **setup_status_20250723_172628.json** - Setup status snapshot
  - **fixes/** - Fix reports
    - **FINAL_BUGFIX_REPORT.md** - Final bugfix report

### Research Documentation
- **research/** - Research and analysis
  - **research-plan.md** - Research plan
  - **refined-research-plan.md** - Refined research plan
  - **final-analysis.md** - Final research analysis
  - **augmented-final-analysis.md** - Augmented analysis
  - **key_considerations.md** - Key considerations
  - **MC-Assessor-API-Documentation.md** - Maricopa County API documentation
  - **findings/** - Research findings
    - **ra-1-findings.md** through **ra-6-findings.md** - Research findings
    - **refined-ra-1-findings.md** through **refined-ra-4-findings.md** - Refined findings

### Troubleshooting
- **troubleshooting/** - Troubleshooting guides
  - **COMPREHENSIVE_WORKFLOW_FIXES_DOCUMENTATION.md** - Workflow fixes documentation

### Operations Documentation
- **operations/** - Operations documentation
  - **COMPREHENSIVE_OPERATIONAL_GUIDE.md** - Comprehensive operations guide
  - **MONITORING_ALERTING_IMPLEMENTATION.md** - Monitoring and alerting implementation

## Examples (/examples/)
- **error_detection_demo.py** - Error detection demonstration
- **maricopa_adapter_demo.py** - Maricopa adapter usage example
- **phoenix_mls_session_demo.py** - Phoenix MLS session demonstration
- **monitoring_demo.py** - Monitoring system demonstration

## Tools (/tools/)
- **README.md** - Tools documentation
- **cleanup_logs.py** - Log cleanup utility
- **validation/** - Validation tools
  - **run_benchmarks.py** - Benchmark runner
  - **validate_environment.py** - Environment validation

## Data and Backup Files
- **backups/** - Configuration backups
  - **migration_20250721_204757/base.yaml** - Migration backup 1
  - **migration_20250721_204742/base.yaml** - Migration backup 2
- **data/** - Data storage
  - **validation/** - Validation data files
- **monitoring/** - Monitoring data and configs
- **docker/** - Docker-related files
- **security-reports/** - Security scan reports
  - **generated/** - Generated security reports