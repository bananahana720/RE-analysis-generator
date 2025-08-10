# Task 9: Docker Deployment

## Overview

### Objective
Create comprehensive Docker containerization strategy for the Phoenix Real Estate Data Collection System that packages Epic 1's foundation infrastructure, Epic 2's data collection engine, and Epic 3's automation orchestration into deployable, secure, and efficient containers for multiple environments.

### Epic Integration
**Packages Epic 1**: Includes foundation infrastructure, configuration management, and database connectivity
**Containerizes Epic 2**: Packages all data collectors, processing pipelines, and monitoring systems
**Deploys Epic 3**: Provides runtime environment for orchestration engine and automation workflows
**Enables Epic 4**: Creates consistent deployment target for quality assurance and analytics

### Dependencies
- Epic 1: Complete foundation infrastructure with configuration patterns
- Epic 2: All data collection components and dependencies
- Epic 3: Orchestration engine and workflow automation
- GitHub Actions integration for automated builds and deployment

## Technical Architecture

### Multi-Stage Docker Build Strategy

#### Base Foundation Stage
```dockerfile
# docker/Dockerfile
FROM python:3.12.4-slim as foundation-base

# Build metadata
ARG BUILD_DATE
ARG VCS_REF
ARG PYTHON_VERSION=3.12.4

LABEL org.opencontainers.image.created=$BUILD_DATE \
      org.opencontainers.image.source="https://github.com/user/phoenix-real-estate" \
      org.opencontainers.image.version="epic-3" \
      org.opencontainers.image.revision=$VCS_REF \
      org.opencontainers.image.title="Phoenix Real Estate Data Collector" \
      org.opencontainers.image.description="Automated real estate data collection system" \
      org.opencontainers.image.vendor="Personal Project" \
      org.opencontainers.image.python.version=$PYTHON_VERSION

# Security: Create non-root user for Epic 1 foundation security patterns
RUN groupadd --gid 1000 phoenix && \
    useradd --uid 1000 --gid phoenix --shell /bin/bash --create-home phoenix

# System dependencies for Epic 1 & 2 components
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
        ca-certificates \
        git \
        build-essential \
        libssl-dev \
        libffi-dev \
        && \
    rm -rf /var/lib/apt/lists/* && \
    apt-get clean

# Install UV package manager for Epic 1's pyproject.toml patterns
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.cargo/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy project configuration (Epic 1 patterns)
COPY pyproject.toml uv.lock ./
COPY README.md ./

# Install system-level dependencies
RUN uv sync --frozen --no-dev

# Foundation stage complete - Epic 1 infrastructure ready
```

#### Development Dependencies Stage  
```dockerfile
FROM foundation-base as development

# Install development dependencies for Epic 1, 2, 3 development
RUN uv sync --frozen

# Copy development configuration
COPY config/development/ config/development/
COPY scripts/ scripts/
COPY tests/ tests/

# Set development environment
ENV DEPLOYMENT_ENVIRONMENT=development
ENV LOG_LEVEL=DEBUG
ENV PYTHONPATH=/app/src

USER phoenix

# Development container ready for Epic 1-3 development
```

#### Production Dependencies Stage
```dockerfile
FROM foundation-base as production-base

# Install only production dependencies
RUN uv sync --frozen --no-dev

# Epic 1, 2, 3 source code
COPY src/ src/

# Production configuration templates
COPY config/production/ config/production/

# Epic 3 automation scripts
COPY scripts/production/ scripts/

# Set production environment defaults
ENV DEPLOYMENT_ENVIRONMENT=production
ENV LOG_LEVEL=INFO
ENV PYTHONPATH=/app/src
ENV PROMETHEUS_MULTIPROC_DIR=/tmp/prometheus
ENV ORCHESTRATION_MODE=sequential

# Create necessary directories with proper permissions
RUN mkdir -p /app/logs /app/reports /app/data /tmp/prometheus && \
    chown -R phoenix:phoenix /app /tmp/prometheus

USER phoenix

# Production base ready for Epic 1-3 execution
```

#### Application Runtime Stage
```dockerfile
FROM production-base as application

# Health check using Epic 1's monitoring patterns
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -m phoenix_real_estate.foundation.monitoring.health_check || exit 1

# Epic 3 orchestration entrypoint
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Expose monitoring port (if needed)
EXPOSE 8080

# Use Epic 1's configuration-aware entrypoint
ENTRYPOINT ["/entrypoint.sh"]

# Default to Epic 3 daily collection workflow
CMD ["python", "-m", "phoenix_real_estate.automation.workflows.daily_collection"]
```

#### Testing Stage
```dockerfile
FROM development as testing

# Copy all test files and configurations
COPY tests/ tests/
COPY .pytest.ini pytest.ini

# Run Epic 1, 2, 3 test suites
RUN uv run pytest tests/foundation/ -v --cov=phoenix_real_estate.foundation && \
    uv run pytest tests/collectors/ -v --cov=phoenix_real_estate.collectors && \
    uv run pytest tests/automation/ -v --cov=phoenix_real_estate.automation

# Type checking for all epics
RUN uv run pyright src/

# Code quality checks
RUN uv run ruff check src/ && \
    uv run ruff format --check src/

# Security scanning
RUN uv run bandit -r src/ && \
    uv run safety check

# Testing stage validates Epic 1-3 integration
```

### Container Entrypoint Script
```bash
#!/bin/bash
# docker/entrypoint.sh
"""
Docker container entrypoint integrating Epic 1, 2, 3 components.
"""

set -euo pipefail

# Epic 1 foundation logging
exec > >(tee -a /app/logs/container.log)
exec 2>&1

echo "Phoenix Real Estate Container Starting..."
echo "Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "Environment: ${DEPLOYMENT_ENVIRONMENT:-unknown}"
echo "Python Version: $(python --version)"
echo "Working Directory: $(pwd)"

# Function to log with timestamps (Epic 1 logging patterns)
log() {
    echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] $1"
}

# Function to check Epic 1 database connectivity
check_database() {
    log "Checking Epic 1 database connectivity..."
    
    if ! python -m phoenix_real_estate.foundation.database.health_check; then
        log "ERROR: Database connectivity check failed"
        exit 1
    fi
    
    log "Database connectivity verified"
}

# Function to validate Epic 2 collector configuration
validate_collectors() {
    log "Validating Epic 2 collector configuration..."
    
    if ! python -m phoenix_real_estate.collectors.validation.config_check; then
        log "ERROR: Collector configuration validation failed"
        exit 1
    fi
    
    log "Collector configuration validated"
}

# Function to initialize Epic 3 orchestration
initialize_orchestration() {
    log "Initializing Epic 3 orchestration engine..."
    
    if ! python -m phoenix_real_estate.automation.orchestration.health_check; then
        log "ERROR: Orchestration engine initialization failed"
        exit 1
    fi
    
    log "Orchestration engine initialized"
}

# Function to setup monitoring (Epic 1 & 3 integration)
setup_monitoring() {
    log "Setting up monitoring and metrics collection..."
    
    # Create prometheus metrics directory
    mkdir -p ${PROMETHEUS_MULTIPROC_DIR:-/tmp/prometheus}
    
    # Initialize Epic 1 metrics collector
    python -m phoenix_real_estate.foundation.monitoring.setup
    
    log "Monitoring setup completed"
}

# Function to validate environment configuration (Epic 1 patterns)
validate_environment() {
    log "Validating environment configuration..."
    
    # Check required Epic 1 environment variables
    required_vars=(
        "MONGODB_CONNECTION_STRING"
        "TARGET_ZIP_CODES"
        "DEPLOYMENT_ENVIRONMENT"
    )
    
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            log "ERROR: Required environment variable $var is not set"
            exit 1
        fi
    done
    
    # Validate Epic 2 collector configuration
    if [[ -z "${MARICOPA_API_KEY:-}" ]]; then
        log "WARNING: MARICOPA_API_KEY not set, Maricopa collector will be disabled"
    fi
    
    if [[ -z "${WEBSHARE_USERNAME:-}" ]] || [[ -z "${WEBSHARE_PASSWORD:-}" ]]; then
        log "WARNING: Webshare credentials not set, Phoenix MLS collector will be disabled"
    fi
    
    log "Environment configuration validated"
}

# Function to run pre-execution health checks
health_check() {
    log "Running comprehensive health checks..."
    
    # Epic 1 foundation health
    check_database
    
    # Epic 2 collector health  
    validate_collectors
    
    # Epic 3 orchestration health
    initialize_orchestration
    
    log "All health checks passed"
}

# Function to handle graceful shutdown
cleanup() {
    log "Received shutdown signal, performing cleanup..."
    
    # Stop any running Epic 3 workflows
    if [[ -n "${WORKFLOW_PID:-}" ]]; then
        log "Stopping workflow process: $WORKFLOW_PID"
        kill -TERM "$WORKFLOW_PID" 2>/dev/null || true
        wait "$WORKFLOW_PID" 2>/dev/null || true
    fi
    
    # Epic 1 database cleanup
    python -m phoenix_real_estate.foundation.database.cleanup 2>/dev/null || true
    
    log "Cleanup completed"
    exit 0
}

# Set up signal handlers for graceful shutdown
trap cleanup SIGTERM SIGINT

# Main execution flow
main() {
    log "Starting Phoenix Real Estate Data Collection System"
    
    # Validate environment using Epic 1 patterns
    validate_environment
    
    # Setup monitoring (Epic 1 & 3 integration)
    setup_monitoring
    
    # Run health checks (Epic 1, 2, 3 integration)
    health_check
    
    log "Container initialization completed successfully"
    log "Starting application: $*"
    
    # Execute the provided command with Epic 1-3 integration
    if [[ $# -eq 0 ]]; then
        # Default to Epic 3 daily collection
        log "No command provided, starting default Epic 3 daily collection workflow"
        python -m phoenix_real_estate.automation.workflows.daily_collection &
        WORKFLOW_PID=$!
    else
        # Execute provided command
        log "Executing command: $*"
        exec "$@" &
        WORKFLOW_PID=$!
    fi
    
    # Wait for process to complete
    wait "$WORKFLOW_PID"
    exit_code=$?
    
    log "Application completed with exit code: $exit_code"
    exit $exit_code
}

# Run main function
main "$@"
```

### Environment-Specific Configurations

#### Development Docker Compose
```yaml
# docker/docker-compose.development.yml
version: '3.8'

services:
  phoenix-dev:
    build:
      context: ..
      dockerfile: docker/Dockerfile
      target: development
      args:
        BUILD_DATE: ${BUILD_DATE:-$(date -u +"%Y-%m-%dT%H:%M:%SZ")}
        VCS_REF: ${VCS_REF:-$(git rev-parse HEAD)}
    
    container_name: phoenix-real-estate-dev
    
    environment:
      # Epic 1 Foundation Configuration
      DEPLOYMENT_ENVIRONMENT: development
      LOG_LEVEL: DEBUG
      MONGODB_CONNECTION_STRING: ${MONGODB_CONNECTION_STRING}
      
      # Epic 2 Collection Configuration
      MARICOPA_API_KEY: ${MARICOPA_API_KEY}
      WEBSHARE_USERNAME: ${WEBSHARE_USERNAME}
      WEBSHARE_PASSWORD: ${WEBSHARE_PASSWORD}
      TARGET_ZIP_CODES: "85031,85032,85033"
      
      # Epic 3 Automation Configuration
      ORCHESTRATION_MODE: sequential
      COLLECTION_TIMEOUT_MINUTES: 30
      MAX_CONCURRENT_COLLECTORS: 1
    
    volumes:
      # Development source code mounting
      - ../src:/app/src:ro
      - ../tests:/app/tests:ro
      - ../config:/app/config:ro
      
      # Development artifacts
      - dev-logs:/app/logs
      - dev-reports:/app/reports
      - dev-data:/app/data
    
    ports:
      - "8080:8080"  # Monitoring port
    
    networks:
      - phoenix-network
    
    restart: unless-stopped
    
    healthcheck:
      test: ["CMD", "python", "-m", "phoenix_real_estate.foundation.monitoring.health_check"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s

volumes:
  dev-logs:
  dev-reports:
  dev-data:

networks:
  phoenix-network:
    driver: bridge
```

#### Production Docker Compose
```yaml
# docker/docker-compose.production.yml
version: '3.8'

services:
  phoenix-collector:
    build:
      context: ..
      dockerfile: docker/Dockerfile
      target: application
      args:
        BUILD_DATE: ${BUILD_DATE:-$(date -u +"%Y-%m-%dT%H:%M:%SZ")}
        VCS_REF: ${VCS_REF:-$(git rev-parse HEAD)}
    
    container_name: phoenix-real-estate-prod
    
    environment:
      # Epic 1 Foundation Configuration
      DEPLOYMENT_ENVIRONMENT: production
      LOG_LEVEL: INFO
      MONGODB_CONNECTION_STRING: ${MONGODB_CONNECTION_STRING}
      
      # Epic 2 Collection Configuration  
      MARICOPA_API_KEY: ${MARICOPA_API_KEY}
      WEBSHARE_USERNAME: ${WEBSHARE_USERNAME}
      WEBSHARE_PASSWORD: ${WEBSHARE_PASSWORD}
      TARGET_ZIP_CODES: ${TARGET_ZIP_CODES}
      
      # Epic 3 Automation Configuration
      ORCHESTRATION_MODE: ${ORCHESTRATION_MODE:-sequential}
      COLLECTION_TIMEOUT_MINUTES: 90
      MAX_CONCURRENT_COLLECTORS: 2
      WORKFLOW_TIMEOUT_MINUTES: 120
    
    volumes:
      # Production data persistence
      - prod-logs:/app/logs
      - prod-reports:/app/reports
      - prod-data:/app/data
      
      # Read-only production configuration
      - ../config/production:/app/config/production:ro
    
    # Resource limits for production
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 1G
        reservations:
          cpus: '0.5'  
          memory: 512M
    
    # Security settings
    read_only: true
    tmpfs:
      - /tmp
      - /var/tmp
    
    # No privileged access
    user: "1000:1000"
    
    networks:
      - phoenix-network
    
    restart: unless-stopped
    
    # Production health monitoring
    healthcheck:
      test: ["CMD", "python", "-m", "phoenix_real_estate.foundation.monitoring.health_check"]
      interval: 60s
      timeout: 30s
      retries: 5
      start_period: 120s
    
    # Logging configuration
    logging:
      driver: "json-file"
      options:
        max-size: "100m"
        max-file: "3"

  # Monitoring service (optional)
  phoenix-monitor:
    build:
      context: ..
      dockerfile: docker/Dockerfile.monitoring
      target: monitoring
    
    container_name: phoenix-monitoring
    
    environment:
      MONITORING_TARGET: phoenix-collector
      
    volumes:
      - prod-logs:/monitoring/logs:ro
      - prod-reports:/monitoring/reports:ro
    
    ports:
      - "9090:9090"  # Prometheus
      - "3000:3000"  # Grafana
    
    depends_on:
      - phoenix-collector
    
    networks:
      - phoenix-network
    
    restart: unless-stopped

volumes:
  prod-logs:
    driver: local
  prod-reports:
    driver: local  
  prod-data:
    driver: local

networks:
  phoenix-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
```

### GitHub Actions Integration

#### Container Build Workflow
```yaml
# .github/workflows/docker-build.yml (extends task-07-github-actions-workflow.yml)
name: Docker Build and Test

on:
  push:
    branches: [main, develop]
    paths:
      - 'src/**'
      - 'docker/**'
      - 'pyproject.toml'
      - 'uv.lock'
  pull_request:
    branches: [main]
    paths:
      - 'src/**'
      - 'docker/**'
      - 'pyproject.toml'
      - 'uv.lock'

env:
  REGISTRY: docker.io
  IMAGE_NAME: phoenix-real-estate

jobs:
  build-test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        target: [development, production-base, application, testing]
    
    steps:
      - name: Checkout Repository
        uses: actions/checkout@v4
        
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
        
      - name: Login to Container Registry
        if: github.event_name != 'pull_request'
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ secrets.DOCKER_USERNAME }}
          password: ${{ secrets.DOCKER_PASSWORD }}
          
      - name: Extract Metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=ref,event=branch,suffix=-${{ matrix.target }}
            type=ref,event=pr,suffix=-${{ matrix.target }}
            type=sha,prefix={{branch}}-${{ matrix.target }}-
            
      - name: Build Docker Image
        uses: docker/build-push-action@v5
        with:
          context: .
          file: ./docker/Dockerfile
          target: ${{ matrix.target }}
          push: ${{ github.event_name != 'pull_request' }}
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha,scope=${{ matrix.target }}
          cache-to: type=gha,mode=max,scope=${{ matrix.target }}
          build-args: |
            BUILD_DATE=${{ fromJSON(steps.meta.outputs.json).labels['org.opencontainers.image.created'] }}
            VCS_REF=${{ fromJSON(steps.meta.outputs.json).labels['org.opencontainers.image.revision'] }}
            
      - name: Run Container Security Scan
        if: matrix.target == 'application'
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: ${{ steps.meta.outputs.tags }}
          format: 'sarif'
          output: 'trivy-results.sarif'
          
      - name: Upload Security Scan Results
        if: matrix.target == 'application'
        uses: github/codeql-action/upload-sarif@v2
        with:
          sarif_file: 'trivy-results.sarif'

  integration-test:
    needs: build-test
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout Repository
        uses: actions/checkout@v4
        
      - name: Test Epic 1-2-3 Integration
        run: |
          # Pull the built testing image
          docker pull ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }}-testing
          
          # Run integration tests in container
          docker run --rm \
            -e MONGODB_CONNECTION_STRING="${{ secrets.MONGODB_CONNECTION_STRING_TEST }}" \
            -e MARICOPA_API_KEY="${{ secrets.MARICOPA_API_KEY_TEST }}" \
            -e TARGET_ZIP_CODES="85031" \
            ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }}-testing \
            python -m pytest tests/integration/ -v
            
      - name: Test Production Container Health
        run: |
          # Pull the application image
          docker pull ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }}-application
          
          # Start container with health check
          docker run -d --name test-container \
            -e MONGODB_CONNECTION_STRING="${{ secrets.MONGODB_CONNECTION_STRING_TEST }}" \
            -e TARGET_ZIP_CODES="85031" \
            -e ORCHESTRATION_MODE="sequential" \
            ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }}-application
          
          # Wait for health check to pass
          timeout 120 bash -c 'until docker inspect --format="{{.State.Health.Status}}" test-container | grep -q "healthy"; do sleep 5; done'
          
          # Check container logs
          docker logs test-container
          
          # Cleanup
          docker stop test-container
          docker rm test-container
```

### Container Configuration Management

#### Epic 1 Configuration Integration
```python
# src/phoenix_real_estate/automation/deployment/docker_config.py
"""
Docker deployment configuration using Epic 1's configuration patterns.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional

from phoenix_real_estate.foundation.config.base import ConfigProvider
from phoenix_real_estate.foundation.config.environment import Environment
from phoenix_real_estate.foundation.logging.factory import get_logger

class DockerConfigManager:
    """Docker deployment configuration management using Epic 1 patterns."""
    
    def __init__(self, environment: Environment) -> None:
        self.environment = environment
        self.logger = get_logger(f"docker.config.{environment.value}")
        self.config: Optional[ConfigProvider] = None
        
    def load_configuration(self) -> ConfigProvider:
        """Load configuration for Docker deployment environment."""
        try:
            self.logger.info(
                "Loading Docker deployment configuration",
                extra={"environment": self.environment.value}
            )
            
            # Load base configuration using Epic 1 patterns
            config_data = self._load_base_configuration()
            
            # Add Docker-specific configuration
            config_data.update(self._load_docker_configuration())
            
            # Add environment-specific overrides
            config_data.update(self._load_environment_overrides())
            
            # Validate configuration
            self._validate_docker_configuration(config_data)
            
            self.config = ConfigProvider(config_data)
            
            self.logger.info(
                "Docker configuration loaded successfully",
                extra={
                    "environment": self.environment.value,
                    "config_keys": len(config_data)
                }
            )
            
            return self.config
            
        except Exception as e:
            self.logger.error(
                "Failed to load Docker configuration",
                extra={
                    "environment": self.environment.value,
                    "error": str(e)
                }
            )
            raise
    
    def _load_base_configuration(self) -> Dict[str, Any]:
        """Load base configuration common to all environments."""
        return {
            # Epic 1 Foundation Configuration
            "DEPLOYMENT_ENVIRONMENT": self.environment.value,
            "LOG_LEVEL": os.getenv("LOG_LEVEL", self._get_default_log_level()),
            "PYTHONPATH": "/app/src",
            
            # Epic 1 Database Configuration
            "MONGODB_CONNECTION_STRING": os.getenv("MONGODB_CONNECTION_STRING"),
            "DATABASE_TIMEOUT_SECONDS": int(os.getenv("DATABASE_TIMEOUT_SECONDS", "30")),
            
            # Epic 2 Collection Configuration
            "TARGET_ZIP_CODES": os.getenv("TARGET_ZIP_CODES"),
            "MARICOPA_API_KEY": os.getenv("MARICOPA_API_KEY"),
            "WEBSHARE_USERNAME": os.getenv("WEBSHARE_USERNAME"),
            "WEBSHARE_PASSWORD": os.getenv("WEBSHARE_PASSWORD"),
            
            # Epic 3 Automation Configuration
            "ORCHESTRATION_MODE": os.getenv("ORCHESTRATION_MODE", "sequential"),
            "COLLECTION_TIMEOUT_MINUTES": int(os.getenv("COLLECTION_TIMEOUT_MINUTES", "90")),
            "MAX_CONCURRENT_COLLECTORS": int(os.getenv("MAX_CONCURRENT_COLLECTORS", "2")),
            "WORKFLOW_TIMEOUT_MINUTES": int(os.getenv("WORKFLOW_TIMEOUT_MINUTES", "120")),
            
            # Docker-specific configuration
            "CONTAINER_NAME": os.getenv("HOSTNAME", "phoenix-real-estate"),
            "CONTAINER_START_TIME": os.getenv("CONTAINER_START_TIME"),
            "PROMETHEUS_MULTIPROC_DIR": os.getenv("PROMETHEUS_MULTIPROC_DIR", "/tmp/prometheus")
        }
    
    def _load_docker_configuration(self) -> Dict[str, Any]:
        """Load Docker-specific configuration."""
        return {
            # Container runtime configuration
            "CONTAINER_MEMORY_LIMIT": os.getenv("CONTAINER_MEMORY_LIMIT", "1G"),
            "CONTAINER_CPU_LIMIT": os.getenv("CONTAINER_CPU_LIMIT", "1.0"),
            
            # Health check configuration
            "HEALTH_CHECK_INTERVAL": int(os.getenv("HEALTH_CHECK_INTERVAL", "60")),
            "HEALTH_CHECK_TIMEOUT": int(os.getenv("HEALTH_CHECK_TIMEOUT", "30")),
            "HEALTH_CHECK_RETRIES": int(os.getenv("HEALTH_CHECK_RETRIES", "5")),
            
            # Logging configuration
            "LOG_FILE_PATH": "/app/logs/application.log",
            "LOG_MAX_SIZE": os.getenv("LOG_MAX_SIZE", "100MB"),
            "LOG_MAX_FILES": int(os.getenv("LOG_MAX_FILES", "3")),
            
            # Monitoring configuration
            "METRICS_ENABLED": os.getenv("METRICS_ENABLED", "true").lower() == "true",
            "METRICS_PORT": int(os.getenv("METRICS_PORT", "8080")),
            
            # Security configuration
            "RUN_AS_USER": "phoenix",
            "RUN_AS_GROUP": "phoenix",
            "READ_ONLY_ROOT": True
        }
    
    def _load_environment_overrides(self) -> Dict[str, Any]:
        """Load environment-specific configuration overrides."""
        overrides = {}
        
        if self.environment == Environment.DEVELOPMENT:
            overrides.update({
                "LOG_LEVEL": "DEBUG",
                "COLLECTION_TIMEOUT_MINUTES": 30,
                "MAX_CONCURRENT_COLLECTORS": 1,
                "HEALTH_CHECK_INTERVAL": 30,
                "METRICS_ENABLED": True
            })
        elif self.environment == Environment.PRODUCTION:
            overrides.update({
                "LOG_LEVEL": "INFO",
                "COLLECTION_TIMEOUT_MINUTES": 90,
                "MAX_CONCURRENT_COLLECTORS": 2,
                "HEALTH_CHECK_INTERVAL": 60,
                "METRICS_ENABLED": True
            })
        elif self.environment == Environment.TESTING:
            overrides.update({
                "LOG_LEVEL": "WARNING",
                "COLLECTION_TIMEOUT_MINUTES": 15,
                "MAX_CONCURRENT_COLLECTORS": 1,
                "HEALTH_CHECK_INTERVAL": 15,
                "METRICS_ENABLED": False
            })
        
        return overrides
    
    def _get_default_log_level(self) -> str:
        """Get default log level for environment."""
        if self.environment == Environment.DEVELOPMENT:
            return "DEBUG"
        elif self.environment == Environment.PRODUCTION:
            return "INFO"
        else:
            return "WARNING"
    
    def _validate_docker_configuration(self, config_data: Dict[str, Any]) -> None:
        """Validate Docker deployment configuration."""
        required_keys = [
            "MONGODB_CONNECTION_STRING",
            "TARGET_ZIP_CODES",
            "DEPLOYMENT_ENVIRONMENT"
        ]
        
        missing_keys = [
            key for key in required_keys 
            if not config_data.get(key)
        ]
        
        if missing_keys:
            raise ValueError(f"Missing required configuration: {missing_keys}")
        
        # Validate Epic 2 collector configuration
        if not config_data.get("MARICOPA_API_KEY"):
            self.logger.warning("MARICOPA_API_KEY not configured, Maricopa collector will be disabled")
        
        if not config_data.get("WEBSHARE_USERNAME") or not config_data.get("WEBSHARE_PASSWORD"):
            self.logger.warning("Webshare credentials not configured, Phoenix MLS collector will be disabled")
        
        # Validate resource limits
        timeout_minutes = config_data.get("COLLECTION_TIMEOUT_MINUTES", 0)
        if timeout_minutes < 15 or timeout_minutes > 180:
            raise ValueError(f"Invalid collection timeout: {timeout_minutes} minutes")
        
        max_collectors = config_data.get("MAX_CONCURRENT_COLLECTORS", 0)
        if max_collectors < 1 or max_collectors > 10:
            raise ValueError(f"Invalid max concurrent collectors: {max_collectors}")
```

### Production Deployment Strategy

#### Health Check Implementation
```python
# src/phoenix_real_estate/foundation/monitoring/health_check.py
"""
Container health check implementation using Epic 1 monitoring patterns.
"""

import asyncio
import sys
from datetime import datetime
from typing import Dict, Any, List

from phoenix_real_estate.foundation.config.base import ConfigProvider
from phoenix_real_estate.foundation.database.connection import DatabaseClient
from phoenix_real_estate.foundation.logging.factory import get_logger

class ContainerHealthCheck:
    """Container health check using Epic 1 foundation patterns."""
    
    def __init__(self) -> None:
        self.logger = get_logger("foundation.monitoring.health_check")
        self.config: Optional[ConfigProvider] = None
        self.db_client: Optional[DatabaseClient] = None
        
    async def run_health_check(self) -> bool:
        """Run comprehensive health check for container."""
        try:
            self.logger.info("Starting container health check")
            
            # Load configuration
            await self._load_configuration()
            
            # Run individual health checks
            health_results = await self._run_health_checks()
            
            # Evaluate overall health
            overall_health = self._evaluate_health(health_results)
            
            self.logger.info(
                "Health check completed",
                extra={
                    "overall_health": overall_health,
                    "individual_results": health_results
                }
            )
            
            return overall_health
            
        except Exception as e:
            self.logger.error(
                "Health check failed with exception",
                extra={"error": str(e)}
            )
            return False
    
    async def _load_configuration(self) -> None:
        """Load configuration for health check."""
        from phoenix_real_estate.automation.deployment.docker_config import DockerConfigManager
        from phoenix_real_estate.foundation.config.environment import Environment
        
        env_str = os.getenv("DEPLOYMENT_ENVIRONMENT", "production")
        environment = Environment(env_str)
        
        config_manager = DockerConfigManager(environment)
        self.config = config_manager.load_configuration()
        
        self.db_client = DatabaseClient(self.config)
    
    async def _run_health_checks(self) -> Dict[str, Dict[str, Any]]:
        """Run individual health checks."""
        health_checks = [
            ("database", self._check_database_health),
            ("configuration", self._check_configuration_health),
            ("filesystem", self._check_filesystem_health),
            ("memory", self._check_memory_health),
            ("epic2_collectors", self._check_collectors_health),
            ("epic3_orchestration", self._check_orchestration_health)
        ]
        
        results = {}
        
        for check_name, check_function in health_checks:
            try:
                result = await check_function()
                results[check_name] = {
                    "status": "healthy" if result else "unhealthy",
                    "checked_at": datetime.utcnow().isoformat(),
                    "details": getattr(result, "details", {}) if hasattr(result, "details") else {}
                }
            except Exception as e:
                results[check_name] = {
                    "status": "error",
                    "checked_at": datetime.utcnow().isoformat(),
                    "error": str(e)
                }
        
        return results
    
    async def _check_database_health(self) -> bool:
        """Check Epic 1 database connectivity."""
        try:
            # Test database connection
            await self.db_client.ping()
            return True
        except Exception as e:
            self.logger.warning(
                "Database health check failed",
                extra={"error": str(e)}
            )
            return False
    
    async def _check_configuration_health(self) -> bool:
        """Check configuration completeness."""
        try:
            required_configs = [
                "MONGODB_CONNECTION_STRING",
                "TARGET_ZIP_CODES",
                "DEPLOYMENT_ENVIRONMENT"
            ]
            
            for config_key in required_configs:
                value = self.config.get_required(config_key)
                if not value:
                    return False
            
            return True
        except Exception:
            return False
    
    async def _check_filesystem_health(self) -> bool:
        """Check filesystem accessibility."""
        try:
            import os
            import tempfile
            
            # Check required directories
            required_dirs = ["/app/logs", "/app/reports", "/app/data"]
            
            for directory in required_dirs:
                if not os.path.exists(directory):
                    os.makedirs(directory, exist_ok=True)
                
                # Test write access
                test_file = os.path.join(directory, ".health_check")
                with open(test_file, "w") as f:
                    f.write("health_check")
                os.remove(test_file)
            
            return True
        except Exception as e:
            self.logger.warning(
                "Filesystem health check failed",
                extra={"error": str(e)}
            )
            return False
    
    async def _check_memory_health(self) -> bool:
        """Check memory usage."""
        try:
            import psutil
            
            memory = psutil.virtual_memory()
            memory_usage_percent = memory.percent
            
            # Consider healthy if memory usage < 90%
            return memory_usage_percent < 90
        except Exception:
            # If we can't check memory, assume healthy
            return True
    
    async def _check_collectors_health(self) -> bool:
        """Check Epic 2 collectors availability."""
        try:
            from phoenix_real_estate.collectors.factory import CollectorFactory, DataSourceType
            
            # Test collector creation
            available_collectors = 0
            
            for source_type in [DataSourceType.MARICOPA_API, DataSourceType.PHOENIX_MLS]:
                try:
                    await CollectorFactory.create_collector(
                        source_type, self.config, None  # No repository needed for health check
                    )
                    available_collectors += 1
                except Exception:
                    # Collector not available, but continue checking others
                    continue
            
            # At least one collector should be available
            return available_collectors > 0
        except Exception:
            return False
    
    async def _check_orchestration_health(self) -> bool:
        """Check Epic 3 orchestration readiness."""
        try:
            from phoenix_real_estate.automation.orchestration.engine import OrchestrationEngine
            from phoenix_real_estate.foundation.monitoring.metrics import MetricsCollector
            from phoenix_real_estate.foundation.database.repositories import PropertyRepository
            
            # Create minimal orchestration engine for health check
            metrics = MetricsCollector(self.config, "health_check")
            repository = PropertyRepository(self.db_client)
            engine = OrchestrationEngine(self.config, repository, metrics)
            
            # Test initialization (but don't fully initialize)
            engine._load_configuration()
            
            return True
        except Exception:
            return False
    
    def _evaluate_health(self, health_results: Dict[str, Dict[str, Any]]) -> bool:
        """Evaluate overall health based on individual check results."""
        critical_checks = ["database", "configuration", "filesystem"]
        important_checks = ["epic2_collectors", "epic3_orchestration"]
        
        # All critical checks must pass
        for check in critical_checks:
            if health_results.get(check, {}).get("status") != "healthy":
                self.logger.error(
                    "Critical health check failed",
                    extra={"check": check, "result": health_results.get(check)}
                )
                return False
        
        # At least 50% of important checks must pass
        important_passed = sum(
            1 for check in important_checks
            if health_results.get(check, {}).get("status") == "healthy"
        )
        
        if important_passed < len(important_checks) * 0.5:
            self.logger.warning(
                "Too many important health checks failed",
                extra={"passed": important_passed, "total": len(important_checks)}
            )
            return False
        
        return True

async def main():
    """Main entry point for container health check."""
    health_check = ContainerHealthCheck()
    is_healthy = await health_check.run_health_check()
    
    if is_healthy:
        print("✅ Container health check passed")
        sys.exit(0)
    else:
        print("❌ Container health check failed")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
```

## Implementation Plan

### Phase 1: Core Containerization (Days 1-2)
- [ ] Create multi-stage Dockerfile with Epic 1-3 integration
- [ ] Implement container entrypoint with comprehensive health checks
- [ ] Add Docker Compose configurations for development and production
- [ ] Integrate with Epic 1's configuration management patterns

### Phase 2: GitHub Actions Integration (Days 2-3)
- [ ] Extend GitHub Actions workflows for container builds
- [ ] Add automated container testing and security scanning
- [ ] Implement container registry integration and management
- [ ] Add deployment automation for different environments

### Phase 3: Production Hardening (Days 3-4)
- [ ] Implement comprehensive health monitoring and checks
- [ ] Add security hardening and resource optimization
- [ ] Create operational monitoring and logging integration
- [ ] Add disaster recovery and backup strategies

### Phase 4: Documentation and Validation (Days 4-5)
- [ ] Create comprehensive deployment documentation
- [ ] Add operational runbooks and troubleshooting guides
- [ ] Validate Epic 4 integration requirements
- [ ] Perform end-to-end testing and optimization

## Testing Strategy

### Container Testing
```python
# tests/automation/deployment/test_docker.py
import pytest
import docker
from unittest.mock import patch

class TestDockerDeployment:
    @pytest.fixture
    def docker_client(self):
        return docker.from_env()
    
    def test_container_build(self, docker_client):
        """Test Docker image builds successfully."""
        image, build_logs = docker_client.images.build(
            path=".",
            dockerfile="docker/Dockerfile",
            target="application",
            tag="phoenix-test:latest"
        )
        
        assert image is not None
        assert "phoenix-test:latest" in image.tags
    
    def test_container_health_check(self, docker_client):
        """Test container health check functionality."""
        container = docker_client.containers.run(
            "phoenix-test:latest",
            environment={
                "MONGODB_CONNECTION_STRING": "mongodb://test",
                "TARGET_ZIP_CODES": "85031",
                "DEPLOYMENT_ENVIRONMENT": "testing"
            },
            detach=True,
            remove=True
        )
        
        # Wait for health check
        import time
        time.sleep(30)
        
        container.reload()
        assert container.attrs["State"]["Health"]["Status"] == "healthy"
        
        container.stop()
```

### Integration Testing
- **Epic 1-3 Integration**: Test complete system in containerized environment
- **Environment Testing**: Validate all environment configurations
- **Security Testing**: Container vulnerability scanning and hardening validation
- **Performance Testing**: Resource usage and optimization validation

## Success Criteria

### Acceptance Criteria
- [ ] Multi-stage Docker builds successfully package Epic 1-3 components
- [ ] Containers run securely with non-root user and minimal privileges
- [ ] Health checks validate Epic 1 database, Epic 2 collectors, and Epic 3 orchestration
- [ ] GitHub Actions automatically builds, tests, and deploys containers
- [ ] Production deployment completes within resource constraints
- [ ] Comprehensive monitoring and logging integration works
- [ ] Documentation provides complete operational guidance

### Quality Gates
- [ ] Container security scan shows no high/critical vulnerabilities
- [ ] Container startup time < 30 seconds in production
- [ ] Memory usage stays within 1GB limit during operation
- [ ] All Epic 1-3 integration tests pass in containerized environment
- [ ] Health checks achieve 99%+ reliability
- [ ] Deployment automation handles all failure scenarios gracefully

---

**Task Owner**: DevOps Engineer  
**Epic**: Epic 3 - Automation & Orchestration  
**Estimated Effort**: 5 days  
**Dependencies**: Epic 1 (Foundation), Epic 2 (Collection), Epic 3 (Orchestration), GitHub Actions  
**Deliverables**: Multi-stage Dockerfiles, container orchestration, deployment automation, security hardening, operational documentation