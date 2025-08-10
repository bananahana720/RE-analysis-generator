# Detailed Project File Index

## Root Directory

### README.md
Comprehensive project documentation serving as the main entry point for the Phoenix Real Estate Data Collection System. Contains quick start instructions, GitHub Actions setup guide, production operation procedures, architecture overview, and troubleshooting information. Includes essential commands, environment setup procedures, and complete workflow configuration details. Critical for understanding project scope, current operational status (98% complete), and budget compliance ($25/month constraint).

### pyproject.toml  
Python project configuration file defining build system, dependencies, and development tools. Specifies Python 3.13+ requirement and includes production dependencies (MongoDB, aiohttp, beautifulsoup4, pydantic, etc.) and development dependencies (pytest, ruff, pyright, etc.). Contains pytest configuration with test paths, asyncio mode, and custom markers for production and benchmark tests. Essential for dependency management and development environment setup.

### uv.lock
UV package manager lock file ensuring reproducible dependency installations across environments. Contains exact version pins for all direct and transitive dependencies. Critical for maintaining consistent development and production environments.

### Makefile
Build automation file providing convenient commands for development workflow. Includes targets for code quality (ruff, pyright), testing (pytest), development installation, and environment setup. Provides both Windows and Unix-compatible commands for cross-platform development.

### pyrightconfig.json
Type checking configuration for Pyright/Pylance. Configures strict type checking rules, Python version targets, and type checking behavior. Essential for maintaining type safety across the codebase.

### CODEOWNERS
GitHub repository code ownership configuration defining review requirements and ownership assignments for different parts of the codebase. Ensures proper code review processes and maintains code quality standards.

### start_mongodb.bat
Windows batch script for starting MongoDB service locally. Provides convenient local development database startup for Windows environments.

### .env.sample
Environment variables template file showing required configuration values including API keys (Maricopa, WebShare, CAPTCHA), database connections, and service endpoints. Critical reference for proper environment setup.

## Source Code (/src/phoenix_real_estate/)

### Core Package Structure

#### __init__.py
Main package initialization file exposing core components (ConfigProvider, PropertyRepository, get_logger) for convenient importing. Defines package version and provides clean API surface for external usage.

#### models/property.py
Pydantic data models defining the property data structure used throughout the system. Includes comprehensive property schema with address information, pricing history, features, and listing details. Provides data validation, serialization, and type safety for property records.

### Foundation Infrastructure (/foundation/)

The foundation layer implements core infrastructure components following clean architecture principles.

#### interfaces.py
Core interface definitions and abstract base classes that define contracts for repository patterns, configuration providers, and logging systems. Ensures consistent implementation across different concrete implementations.

#### Configuration Management (/config/)

**base.py**: Base configuration classes implementing hierarchical configuration loading from environment variables, YAML files, and defaults. Provides type-safe configuration access with validation and fallback mechanisms.

**provider.py**: Configuration provider implementation using the singleton pattern to ensure consistent configuration access across the application. Handles environment-specific configuration loading and provides caching for performance.

**secrets.py**: Secure secrets management system for handling API keys, database credentials, and other sensitive configuration. Implements encryption at rest and secure retrieval patterns with audit logging.

**environment.py**: Environment-specific configuration handling supporting development, testing, and production environments. Provides environment detection and appropriate configuration loading.

#### Database Layer (/database/)

**connection.py**: Database connection management implementing connection pooling, retry logic, and health checking. Supports both local MongoDB and MongoDB Atlas with SSL/TLS configuration.

**repositories.py**: Repository pattern implementation providing data access abstraction. Includes PropertyRepository with methods for CRUD operations, search functionality, and data aggregation. Implements async patterns for performance.

**repositories_backup.py**: Backup repository implementations used for testing and fallback scenarios. Maintains identical interfaces while providing alternative implementations.

**schema.py**: Database schema definitions and migration utilities. Defines MongoDB collections structure, indexes, and validation rules. Includes schema versioning for migrations.

**mock.py**: Mock database implementation for testing purposes. Provides in-memory data storage with identical interface to production database for unit and integration testing.

#### Logging System (/logging/)

**logger.py**: Main logger implementation providing structured logging with JSON output, context management, and performance tracking. Integrates with monitoring systems and provides correlation IDs for request tracing.

**factory.py**: Logger factory implementing the factory pattern for creating appropriately configured loggers for different components. Handles logger hierarchy and configuration inheritance.

**handlers.py**: Custom log handlers for different output destinations including file rotation, console output, and external log aggregation systems. Includes error handling and fallback mechanisms.

**formatters.py**: Log message formatters providing consistent output formatting across different handlers. Supports JSON formatting for structured logging and human-readable formats for development.

#### Monitoring System (/monitoring/)

**config.py**: Monitoring system configuration including metrics collection intervals, alert thresholds, and export destinations. Supports Prometheus metrics format and custom monitoring backends.

**metrics.py**: Metrics collection implementation providing business and technical metrics. Includes counters, gauges, histograms, and custom metric types for comprehensive system observability.

**exporters.py**: Metrics export functionality for sending metrics to external systems like Prometheus, Grafana, and custom dashboards. Handles batching, retry logic, and error handling.

**cost_tracking.py**: Budget and cost tracking implementation monitoring API usage, resource consumption, and operational costs. Provides alerts when approaching budget limits and cost optimization recommendations.

#### Utilities (/utils/)

**helpers.py**: General utility functions used across the application including date/time utilities, string manipulation, data transformation, and common algorithms. Provides reusable functionality to avoid code duplication.

**exceptions.py**: Custom exception hierarchy defining application-specific exceptions with proper error codes, messages, and context information. Enables consistent error handling and troubleshooting.

**validators.py**: Data validation utilities providing validation functions for different data types, business rules, and external API responses. Includes validation decorators and error reporting.

### Data Collection System (/collectors/)

The collectors implement the data collection engine (Epic 2) with support for multiple data sources.

#### Base Collection Framework (/base/)

**collector.py**: Abstract base collector class defining the interface and common functionality for all data collectors. Implements rate limiting, error handling, retry logic, and metrics collection patterns.

**adapter.py**: Data adapter pattern implementations for transforming external API responses into internal data models. Provides format conversion, field mapping, and data normalization.

**rate_limiter.py**: Rate limiting implementation using token bucket and sliding window algorithms. Prevents API rate limit violations and ensures compliant data collection behavior.

**validators.py**: Data validation specific to collection operations including response validation, data quality checks, and business rule enforcement for collected data.

#### Maricopa County Collector (/maricopa/)

**collector.py**: Main Maricopa County API collector implementing official property records collection from mcassessor.maricopa.gov. Handles authentication, pagination, error recovery, and data transformation. Includes comprehensive error handling and retry logic for robust data collection.

#### Phoenix MLS Scraper (/phoenix_mls/)

**scraper.py**: Main Phoenix MLS scraper implementation using Playwright for browser automation. Handles JavaScript-heavy website navigation, form submission, and data extraction. Includes session management and state preservation.

**parser.py**: HTML parsing utilities for extracting property data from MLS web pages. Uses BeautifulSoup and custom parsing logic to handle dynamic content and various page layouts.

**captcha_handler.py**: CAPTCHA solving integration using 2captcha.com service. Handles CAPTCHA detection, solving requests, and response integration into the scraping workflow.

**anti_detection.py**: Anti-detection mechanisms including user agent rotation, request timing randomization, and browser fingerprint management. Ensures ethical scraping while avoiding detection.

**error_detection.py**: Error detection and classification system for identifying different types of errors during scraping operations. Includes automated error recovery and escalation procedures.

**proxy_manager.py**: Proxy rotation system using WebShare proxy service. Handles proxy health checking, rotation policies, and fallback mechanisms for reliable web scraping.

**metrics_integration.py**: Metrics collection specific to MLS scraping operations including success rates, response times, and error categorization for monitoring and optimization.

#### Data Processing Pipeline (/processing/)

**service.py**: Main data processing service orchestrating the entire processing pipeline from raw data ingestion to cleaned property records. Coordinates between different processing stages.

**pipeline.py**: Data processing pipeline implementation with configurable stages, error handling, and data quality validation. Supports parallel processing and scalable data throughput.

**extractor.py**: Data extraction utilities for parsing and extracting structured data from various sources including HTML, JSON, and API responses. Handles data normalization and validation.

**validator.py**: Processing validation logic ensuring data quality and business rule compliance throughout the processing pipeline. Includes data completeness and accuracy checks.

**monitoring.py**: Processing pipeline monitoring providing metrics, alerts, and performance tracking for data processing operations. Integrates with overall system monitoring.

**performance.py**: Performance optimization utilities including caching strategies, batch processing, and resource management for efficient data processing at scale.

**error_handling.py**: Comprehensive error handling for processing operations including error classification, recovery strategies, and escalation procedures.

**cache.py**: Caching mechanisms for processed data including in-memory caching, persistent caching, and cache invalidation strategies for optimal performance.

**llm_client.py**: LLM integration client for processing property descriptions and extracting structured data using local Ollama LLM. Handles prompt engineering, response parsing, and error handling.

### Services Layer (/services/)

#### email_service.py
Email notification service for system alerts, data collection summaries, and operational notifications. Supports multiple email backends and template-based messaging.

### API Layer (/api/)

#### health.py
Health check endpoints providing system status information including database connectivity, external service availability, and overall system health metrics.

#### health_fixes.sed
Stream editor script for fixing health endpoint configurations and responses. Used for automated maintenance and configuration updates.

### Orchestration Layer (/orchestration/)

#### processing_integrator.py
Integration orchestration service coordinating between data collection, processing, and storage operations. Manages workflow dependencies and ensures data consistency.

## Configuration System (/config/)

The configuration system provides hierarchical configuration management supporting multiple environments and deployment scenarios.

### Environment Configuration

**base.yaml**: Base configuration providing default values and common settings used across all environments. Includes database connection defaults, logging levels, and service endpoints.

**environments/**: Environment-specific configuration overrides:
- **environment-config.yaml**: Template for environment configuration
- **development.yaml**: Development environment settings with debugging enabled
- **testing.yaml**: Test environment configuration with mock services
- **production.yaml**: Production configuration with security hardening

### Service Configuration

**services/**: Service-specific configuration files:
- **base-services.yaml**: Common service configurations
- **production-phoenix-mls.yaml**: Production Phoenix MLS scraper settings
- **llm-production.yaml**: LLM service production configuration
- **proxies.yaml**: Proxy service configuration and rotation policies

### Deployment Configuration  

**deployment/**: Deployment-specific configurations:
- **production-deployment.yaml**: Production deployment settings
- **deploy-staging.yaml**: Staging deployment configuration
- **deploy-production.yaml**: Production deployment pipeline configuration

### Web Scraping Configuration

**selectors/phoenix_mls.yaml**: CSS selectors and XPath expressions for Phoenix MLS web scraping. Maintained separately for easy updates when website structure changes.

### Configuration Templates

**templates/**: Configuration template files:
- **production-secrets.yaml.template**: Template for production secrets configuration
- **proxies.yaml.example**: Example proxy configuration showing required settings

### Monitoring and Alerting Configuration

**monitoring/**: Comprehensive monitoring system configuration:
- **prometheus.yml**: Prometheus monitoring configuration with scraping targets
- **alertmanager.yml**: AlertManager configuration for notification routing
- **grafana-datasources.yml**: Grafana data source configurations
- **grafana-dashboards.yml**: Dashboard provisioning configuration
- **alerts.yml**: Alert rule definitions for system monitoring
- **docker-compose.yml**: Monitoring stack deployment configuration

### Dashboard Definitions

**monitoring/dashboards/**: Pre-configured monitoring dashboards:
- **executive-dashboard.json**: High-level business metrics dashboard
- **operational-dashboard.json**: Operational metrics and system health
- **performance-dashboard.json**: Performance monitoring and optimization
- **business-intelligence-dashboard.json**: Business intelligence and analytics

## Testing Infrastructure (/tests/)

Comprehensive testing suite implementing test-driven development practices with multiple testing levels.

### Foundation Layer Tests

**foundation/**: Core infrastructure testing:
- **test_utils.py**: Utility function testing with edge cases and error conditions
- **test_exceptions.py**: Exception hierarchy testing ensuring proper error handling
- **test_logging.py**: Logging system testing including structured logging and performance

**foundation/config/**: Configuration system testing:
- **test_secrets.py**: Secrets management testing including encryption and secure access
- **test_base.py**: Base configuration testing with environment variable handling
- **test_environment.py**: Environment-specific configuration testing
- **test_benchmarks.py**: Configuration performance benchmarking
- **PRODUCTION_TEST_SUMMARY.md**: Documentation of production testing scenarios

**foundation/database/**: Database layer testing:
- **test_schema.py**: Database schema validation and migration testing
- **test_repositories.py**: Repository pattern testing with async operations
- **test_connection.py**: Database connection testing including connection pooling

**foundation/monitoring/**: Monitoring system testing:
- **test_metrics.py**: Metrics collection and export testing
- **test_exporters.py**: Metrics exporter testing with external systems
- **test_integration.py**: Monitoring integration testing

### Data Collection Tests

**collectors/**: Comprehensive collector testing:
- **test_integration_validation.py**: Cross-collector integration testing
- **test_performance_validation.py**: Performance benchmarking and optimization testing

**collectors/base/**: Base collector framework testing:
- **test_rate_limiter.py**: Rate limiting algorithm testing with various scenarios
- **test_validators.py**: Data validation testing with edge cases

**collectors/maricopa/**: Maricopa County collector testing:
- **test_collector.py**: Main collector functionality testing
- **test_integration.py**: Integration testing with live API (when available)

**collectors/phoenix_mls/**: Phoenix MLS scraper testing:
- **test_scraper.py**: Core scraping functionality testing
- **test_parser.py**: HTML parsing testing with various page layouts
- **test_captcha_handler.py**: CAPTCHA solving integration testing
- **test_anti_detection.py**: Anti-detection mechanism testing
- **test_proxy_manager.py**: Proxy rotation and health testing
- **test_session_management.py**: Session persistence and recovery testing

**collectors/processing/**: Data processing testing:
- **test_llm_service.py**: LLM integration testing
- **test_pipeline.py**: Processing pipeline testing with various data scenarios
- **test_extractor.py**: Data extraction testing
- **test_performance_benchmarks.py**: Processing performance benchmarking

### Integration Tests

**integration/**: Cross-component integration testing:
- **test_database_integration.py**: Database integration testing across components
- **test_logging_integration.py**: Logging integration testing
- **test_phoenix_mls_performance.py**: Phoenix MLS performance integration testing

### End-to-End Tests

**e2e/**: Complete workflow testing:
- **test_simple_e2e.py**: Basic end-to-end workflow testing
- **test_processing_pipeline_e2e.py**: Complete processing pipeline testing
- **test_infrastructure_e2e.py**: Infrastructure integration testing
- **E2E_TEST_REPORT.md**: Comprehensive E2E testing documentation

### Test Fixtures and Data

**fixtures/maricopa/**: Mock data for Maricopa County API testing:
- **search_response.json**: Mock search API responses
- **parcel_details.json**: Mock parcel detail responses
- **property_info.json**: Mock property information
- **error_responses.json**: Mock error scenarios for testing

## GitHub Actions Workflows (/.github/workflows/)

Production-ready CI/CD pipeline with comprehensive automation.

### Core Production Workflows

**ci-cd.yml**: Main continuous integration and deployment pipeline including code quality checks, testing, security scanning, and deployment orchestration. Runs on every push and pull request.

**data-collection.yml**: Daily automated data collection workflow running at 3 AM Phoenix time. Orchestrates Maricopa County and Phoenix MLS data collection with error handling and notifications.

**security.yml**: Security scanning and compliance workflow including dependency vulnerability scanning, code security analysis, and compliance validation. Runs daily and on security-related changes.

**deployment.yml**: Production deployment management workflow handling deployment orchestration, environment promotion, and rollback capabilities.

**monitoring.yml**: System monitoring and alerting workflow providing budget tracking, performance monitoring, and health checks. Includes automated issue creation for anomalies.

### Data Collection Workflows

**data-collection-maricopa.yml**: Specialized Maricopa County data collection workflow with API-specific error handling and retry logic.

**data-collection-phoenix-mls.yml**: Phoenix MLS data collection workflow with browser automation, proxy management, and CAPTCHA handling.

**data-processing-llm.yml**: LLM data processing workflow using Ollama for local property data processing and enhancement.

**data-validation.yml**: Data quality validation workflow ensuring collected data meets quality standards and business rules.

### Development and Testing Workflows

**test-workflows.yml**: Workflow testing and validation ensuring all GitHub Actions workflows are syntactically correct and functional.

**validate-secrets.yml**: Secrets validation workflow ensuring all required secrets are properly configured without exposing values.

### Utility and Maintenance Workflows

**maintenance.yml**: System maintenance workflow handling log rotation, cache cleanup, and system optimization tasks.

**proxy-update.yml**: Automated proxy configuration updates ensuring proxy services remain functional.

**setup-ollama.yml**: Ollama LLM service setup and configuration workflow for automated environment preparation.

## Scripts and Utilities (/scripts/)

Comprehensive collection of utilities supporting development, testing, deployment, and maintenance operations.

### Setup and Environment Scripts

**setup/**: Environment setup automation:
- **setup_development_environment.py**: Complete development environment setup including dependencies, services, and configuration
- **setup_ollama.py**: Ollama LLM service installation and configuration
- **setup_mongodb_atlas.py**: MongoDB Atlas configuration with security settings
- **setup_secrets.py**: Secure secrets configuration with validation
- **configure_services.py**: Service configuration automation

### Testing Utilities

**testing/**: Comprehensive testing utilities:
- **workflow_test_runner.py**: GitHub Actions workflow testing and validation
- **test_maricopa_api.py**: Maricopa County API testing with live endpoints
- **test_phoenix_mls_with_services.py**: Phoenix MLS testing with full service stack
- **verify_e2e_setup.py**: End-to-end setup verification
- **mock_services.py**: Mock service implementations for testing
- **api_integration_diagnostic.py**: API integration diagnostics and troubleshooting

**testing/production/**: Production testing utilities:
- **validate_environment.py**: Production environment validation
- **performance_monitor.py**: Production performance monitoring
- **smoke_tests.py**: Production smoke testing

### Validation Scripts

**validation/**: System validation utilities:
- **validate_structure.py**: Project structure validation ensuring architectural compliance
- **validate_configuration.py**: Configuration validation across environments
- **validate_system.py**: Complete system validation
- **workflow_validator.py**: GitHub Actions workflow validation
- **validate_mongodb_atlas.py**: MongoDB Atlas connectivity and configuration validation

### Deployment Scripts

**deploy/**: Production deployment utilities:
- **setup_production_environment.py**: Production environment setup and configuration
- **setup_monitoring.py**: Monitoring system deployment
- **deploy_llm_service.py**: LLM service deployment automation
- **validate_monitoring_system.py**: Monitoring system validation
- **health_check.py**: Production health checking
- **rollback.py**: Deployment rollback procedures

### Database Management

**database/**: Database management utilities:
- **migrate.py**: Database migration utilities with versioning support
- **backup.py**: Database backup and restoration utilities
- **validate_schema.py**: Database schema validation

## Documentation (/docs/)

Comprehensive documentation covering all aspects of the system from high-level architecture to implementation details.

### Architecture and Design

**design/architecture.md**: System architecture overview describing the clean architecture implementation, component relationships, and design principles.

**architecture/**: Detailed architecture documentation:
- **hot-reload-design.md**: Hot reload system design for development efficiency
- **hot-reload-api-spec.md**: API specifications for hot reload functionality
- **hot-reload-implementation-roadmap.md**: Implementation roadmap and milestones

### API Documentation

**api/**: API documentation and references:
- **README.md**: API documentation overview and navigation
- **phoenix-mls-scraper-api.md**: Phoenix MLS scraper API documentation
- **phoenix-mls-quick-reference.md**: Quick reference guide for MLS operations

### Technical Implementation Guides

**secrets-management.md**: Comprehensive secrets management guide including encryption, storage, and access patterns.

**logging.md**: Logging system documentation including structured logging, performance considerations, and troubleshooting.

**monitoring.md**: Monitoring system documentation covering metrics collection, alerting, and dashboard configuration.

**production-setup.md**: Production environment setup guide including security hardening and performance optimization.

**production-deployment-guide.md**: Complete production deployment guide with step-by-step procedures.

### Project Management Documentation

**project-management/**: Project management and planning documentation:
- **CLAUDE.md**: AI assistant development guide for AI-powered development workflows
- **epics/**: Epic-level documentation for major system components
- **tasks/**: Task-specific implementation documentation
- **architecture/adrs/**: Architecture Decision Records documenting key design decisions

### Research and Analysis

**research/**: Research findings and analysis:
- **research-plan.md**: Original research plan and methodology
- **final-analysis.md**: Comprehensive analysis of findings
- **MC-Assessor-API-Documentation.md**: Detailed Maricopa County API analysis
- **findings/**: Individual research findings and discoveries

### Reports and Status

**summaries/**: Implementation summaries and status reports:
- **quality_report.md**: Code quality assessment and recommendations
- **PRODUCTION_READINESS_REPORT.md**: Production readiness assessment
- **MONITORING_IMPLEMENTATION.md**: Monitoring system implementation summary

**project-reports/**: Detailed project reports:
- **EXECUTIVE_SUMMARY.md**: High-level project summary for stakeholders
- **testing/**: Test execution reports and metrics
- **production/**: Production deployment and readiness reports
- **validation/**: System validation and compliance reports

## Examples and Tools

### Examples (/examples/)
- **error_detection_demo.py**: Demonstration of error detection mechanisms
- **maricopa_adapter_demo.py**: Example usage of Maricopa County API adapter
- **phoenix_mls_session_demo.py**: Phoenix MLS session management examples
- **monitoring_demo.py**: Monitoring system usage examples

### Development Tools (/tools/)
- **cleanup_logs.py**: Log cleanup and maintenance utility
- **validation/run_benchmarks.py**: Performance benchmarking tools
- **validation/validate_environment.py**: Environment validation utilities

## Data and Configuration Management

### Backup and Migration

**backups/**: Configuration backups with timestamps:
- **migration_20250721_204757/**: Configuration migration backup
- **migration_20250721_204742/**: Additional migration backup

### Runtime Data

**data/validation/**: Validation data and results storage
**monitoring/**: Monitoring configuration and data
**docker/**: Docker-related configuration files
**security-reports/generated/**: Generated security scan reports

This comprehensive project structure implements a production-ready real estate data collection system with clean architecture principles, comprehensive testing, automated CI/CD, and operational monitoring. The system is designed to operate within strict budget constraints while maintaining high reliability and data quality standards.