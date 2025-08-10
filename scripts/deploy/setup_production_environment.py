#!/usr/bin/env python3
"""Production environment setup script.

This script configures the production environment for the Phoenix Real Estate system,
including database setup, email configuration, monitoring, and security settings.
"""

import os
import sys
import asyncio
import logging
from pathlib import Path
from typing import Dict
from datetime import datetime, UTC

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from phoenix_real_estate.foundation.config.base import EnvironmentConfigProvider
from phoenix_real_estate.foundation.database.connection import DatabaseConnection


def setup_logging() -> logging.Logger:
    """Set up logging for the setup script."""
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


def create_production_env_file(logger: logging.Logger) -> bool:
    """Create production environment file with sensible defaults."""
    logger.info("Creating production environment configuration...")

    env_file = Path(".env.production")
    if env_file.exists():
        logger.info("Production environment file already exists, skipping creation")
        return True

    # Production configuration template
    production_config = f"""# Phoenix Real Estate Production Environment
# Generated on {datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")}

# Environment
PHOENIX_ENV=production
TZ=America/Phoenix
LOG_LEVEL=INFO

# Database Configuration
MONGODB_URI=mongodb://localhost:27017
MONGODB_DATABASE=phoenix_real_estate
MONGODB_MAX_POOL_SIZE=10
MONGODB_MIN_POOL_SIZE=2

# Email Configuration (Enable for production)
EMAIL_ENABLED=true
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
SENDER_EMAIL=your_email@gmail.com
SENDER_NAME=Phoenix Real Estate Collector
RECIPIENT_EMAILS=your_email@gmail.com
EMAIL_RATE_LIMIT_PER_HOUR=100
EMAIL_TIMEOUT=30

# API Keys (Required - Replace with actual values)
MARICOPA_API_KEY=your_maricopa_api_key_here
WEBSHARE_API_KEY=your_webshare_api_key_here
CAPTCHA_API_KEY=your_2captcha_api_key_here

# Proxy Configuration
WEBSHARE_USERNAME=your_webshare_username
WEBSHARE_PASSWORD=your_webshare_password
PROXY_ROTATION_ENABLED=true
PROXY_HEALTH_CHECK_INTERVAL=300

# LLM Configuration
OLLAMA_BASE_URL=http://localhost:11434
LLM_MODEL=llama3.2:latest
LLM_TIMEOUT=30
LLM_MAX_RETRIES=3
LLM_BATCH_SIZE=10
LLM_MAX_WORKERS=2

# Processing Configuration
PROCESSING_BATCH_SIZE=10
PROCESSING_MAX_CONCURRENT=3
PROCESSING_QUEUE_SIZE=100
PROCESSING_RETRY_ATTEMPTS=3
PROCESSING_RETRY_DELAY=1.0

# Collection Configuration
COLLECTION_MAX_REQUESTS_PER_HOUR=100
COLLECTION_MIN_REQUEST_DELAY=3.6
COLLECTION_TARGET_ZIP_CODES=85031,85033,85035

# Performance Configuration
ENABLE_CACHING=true
CACHE_TTL_MINUTES=60
MAX_MEMORY_USAGE_MB=512
GARBAGE_COLLECTION_INTERVAL=100

# Security Configuration
SESSION_MAX_AGE_HOURS=12
ENCRYPT_SENSITIVE_LOGS=true
SANITIZE_RAW_DATA=true
RATE_LIMIT_REQUESTS_PER_MINUTE=60
RATE_LIMIT_REQUESTS_PER_HOUR=1000

# Monitoring Configuration
MONITORING_ENABLED=true
HEALTH_CHECK_INTERVAL=60
ALERT_ERROR_THRESHOLD=10
ALERT_EMAIL=alerts@yourdomain.com

# Logging Configuration
LOG_FORMAT=json
LOG_FILE=logs/phoenix_real_estate.log
LOG_MAX_SIZE_MB=100
LOG_BACKUP_COUNT=10
LOG_SLOW_REQUESTS=true
LOG_SLOW_THRESHOLD_MS=5000

# Error Handling Configuration
MAX_ERROR_RATE=0.05
ERROR_COOLDOWN_MINUTES=30
ALERT_CONSECUTIVE_FAILURES=3
DEAD_LETTER_QUEUE_ENABLED=true
DEAD_LETTER_QUEUE_SIZE=1000
"""

    try:
        with open(env_file, "w") as f:
            f.write(production_config)

        logger.info(f"Created production environment file: {env_file}")
        logger.warning("IMPORTANT: Update the API keys and email configuration in .env.production")
        return True

    except Exception as e:
        logger.error(f"Failed to create production environment file: {e}")
        return False


async def setup_production_database(logger: logging.Logger) -> bool:
    """Set up production database with proper indexes and configuration."""
    logger.info("Setting up production database...")

    try:
        # Use production environment
        os.environ["PHOENIX_ENV"] = "production"
        config_provider = EnvironmentConfigProvider()

        # Connect to production database
        db_connection = DatabaseConnection(config_provider)
        await db_connection.connect()

        logger.info("Successfully connected to production database")

        # Verify collections and indexes
        database = db_connection.database
        collections = await database.list_collection_names()
        logger.info(f"Database collections: {collections}")

        # Create collections if they don't exist
        required_collections = ["maricopa_properties", "phoenix_mls_properties", "processing_logs"]
        for collection_name in required_collections:
            if collection_name not in collections:
                await database.create_collection(collection_name)
                logger.info(f"Created collection: {collection_name}")

        # Set up indexes (they're created automatically in DatabaseConnection.connect())
        logger.info("Production database indexes are configured")

        await db_connection.close()
        logger.info("Production database setup completed successfully")
        return True

    except Exception as e:
        logger.error(f"Production database setup failed: {e}")
        return False


def validate_production_secrets(logger: logging.Logger) -> Dict[str, bool]:
    """Validate production secrets and configuration."""
    logger.info("Validating production secrets...")

    # Load production environment
    env_file = Path(".env.production")
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                if "=" in line and not line.strip().startswith("#"):
                    key, value = line.strip().split("=", 1)
                    os.environ[key] = value

    validation_results = {}

    # Required API keys
    api_keys = {
        "MARICOPA_API_KEY": "Maricopa County API",
        "WEBSHARE_API_KEY": "WebShare Proxy Service",
        "CAPTCHA_API_KEY": "2captcha Service",
    }

    for env_var, service_name in api_keys.items():
        value = os.environ.get(env_var, "")
        is_valid = value and not value.startswith("your_") and len(value) > 10
        validation_results[env_var] = is_valid

        if is_valid:
            logger.info(f"✓ {service_name} API key configured")
        else:
            logger.warning(f"✗ {service_name} API key missing or invalid")

    # Email configuration
    email_config = {
        "SMTP_HOST": "SMTP Host",
        "SMTP_USERNAME": "SMTP Username",
        "SMTP_PASSWORD": "SMTP Password",
        "SENDER_EMAIL": "Sender Email",
        "RECIPIENT_EMAILS": "Recipient Emails",
    }

    email_valid = True
    for env_var, config_name in email_config.items():
        value = os.environ.get(env_var, "")
        is_valid = value and not value.startswith("your_")
        validation_results[env_var] = is_valid

        if not is_valid:
            email_valid = False
            logger.warning(f"✗ {config_name} not configured")

    if email_valid:
        logger.info("✓ Email configuration appears valid")
    else:
        logger.warning("✗ Email configuration incomplete")

    validation_results["EMAIL_CONFIGURED"] = email_valid

    # Database configuration
    db_uri = os.environ.get("MONGODB_URI", "")
    db_valid = "mongodb://" in db_uri
    validation_results["MONGODB_URI"] = db_valid

    if db_valid:
        logger.info("✓ Database URI configured")
    else:
        logger.warning("✗ Database URI not configured")

    return validation_results


def create_production_systemd_service(logger: logging.Logger) -> bool:
    """Create systemd service file for production deployment."""
    logger.info("Creating systemd service configuration...")

    service_dir = Path("scripts/deploy/systemd")
    service_dir.mkdir(exist_ok=True)

    service_content = """[Unit]
Description=Phoenix Real Estate Data Collector
After=network.target mongod.service
Wants=mongod.service

[Service]
Type=simple
User=phoenix
Group=phoenix
WorkingDirectory=/opt/phoenix-real-estate
Environment=PHOENIX_ENV=production
EnvironmentFile=/opt/phoenix-real-estate/.env.production
ExecStart=/opt/phoenix-real-estate/.venv/bin/python -m phoenix_real_estate.orchestration.scheduler
ExecReload=/bin/kill -HUP $MAINPID
KillMode=mixed
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=phoenix-real-estate

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/phoenix-real-estate/logs /opt/phoenix-real-estate/data

# Resource limits
LimitNOFILE=65536
LimitNPROC=4096

[Install]
WantedBy=multi-user.target
"""

    service_file = service_dir / "phoenix-real-estate.service"
    try:
        with open(service_file, "w") as f:
            f.write(service_content)

        logger.info(f"Created systemd service file: {service_file}")
        logger.info(
            "To install: sudo cp scripts/deploy/systemd/phoenix-real-estate.service /etc/systemd/system/"
        )
        logger.info(
            "Then run: sudo systemctl daemon-reload && sudo systemctl enable phoenix-real-estate"
        )
        return True

    except Exception as e:
        logger.error(f"Failed to create systemd service file: {e}")
        return False


def create_production_docker_compose(logger: logging.Logger) -> bool:
    """Create Docker Compose configuration for production."""
    logger.info("Creating Docker Compose configuration...")

    docker_compose_content = """version: '3.8'

services:
  phoenix-real-estate:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: phoenix-real-estate
    restart: always
    environment:
      - PHOENIX_ENV=production
    env_file:
      - .env.production
    volumes:
      - ./logs:/app/logs
      - ./data:/app/data
      - ./config:/app/config
    depends_on:
      - mongodb
      - ollama
    networks:
      - phoenix-network
    healthcheck:
      test: ["CMD", "python", "-c", "import requests; requests.get('http://localhost:8080/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  mongodb:
    image: mongo:8.1.2
    container_name: phoenix-mongodb
    restart: always
    environment:
      MONGO_INITDB_ROOT_USERNAME: admin
      MONGO_INITDB_ROOT_PASSWORD: ${MONGODB_PASSWORD:-defaultpassword}
      MONGO_INITDB_DATABASE: phoenix_real_estate
    volumes:
      - mongodb_data:/data/db
      - mongodb_config:/data/configdb
    ports:
      - "27017:27017"
    networks:
      - phoenix-network
    healthcheck:
      test: echo 'db.runCommand("ping").ok' | mongosh localhost:27017/phoenix_real_estate --quiet
      interval: 30s
      timeout: 10s
      retries: 3

  ollama:
    image: ollama/ollama:latest
    container_name: phoenix-ollama
    restart: always
    volumes:
      - ollama_data:/root/.ollama
    ports:
      - "11434:11434"
    networks:
      - phoenix-network
    environment:
      - OLLAMA_KEEP_ALIVE=24h
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:11434/api/tags"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  mongodb_data:
    driver: local
  mongodb_config:
    driver: local
  ollama_data:
    driver: local

networks:
  phoenix-network:
    driver: bridge
"""

    try:
        with open("docker/docker-compose.production.yml", "w") as f:
            f.write(docker_compose_content)

        logger.info("Created Docker Compose configuration: docker/docker-compose.production.yml")
        logger.info("To start: docker-compose -f docker/docker-compose.production.yml up -d")
        return True

    except Exception as e:
        logger.error(f"Failed to create Docker Compose configuration: {e}")
        return False


def create_production_monitoring_config(logger: logging.Logger) -> bool:
    """Create monitoring and alerting configuration."""
    logger.info("Creating monitoring configuration...")

    monitoring_dir = Path("config/monitoring")
    monitoring_dir.mkdir(exist_ok=True)

    # Prometheus configuration
    prometheus_config = """global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "phoenix_alerts.yml"

scrape_configs:
  - job_name: 'phoenix-real-estate'
    static_configs:
      - targets: ['localhost:8080']
    metrics_path: '/metrics'
    scrape_interval: 30s

  - job_name: 'mongodb'
    static_configs:
      - targets: ['localhost:27017']
    scrape_interval: 30s

  - job_name: 'ollama'
    static_configs:
      - targets: ['localhost:11434']
    scrape_interval: 60s

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - localhost:9093
"""

    # Alerting rules
    alert_rules = """groups:
  - name: phoenix_real_estate_alerts
    rules:
      - alert: ServiceDown
        expr: up == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Service {{ $labels.job }} is down"
          description: "Service {{ $labels.job }} has been down for more than 1 minute"

      - alert: HighErrorRate
        expr: (rate(phoenix_errors_total[5m]) / rate(phoenix_requests_total[5m])) > 0.05
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value | humanizePercentage }} for the last 5 minutes"

      - alert: DatabaseConnectionFailed
        expr: phoenix_database_connection_errors_total > 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Database connection failures"
          description: "Database connection has failed {{ $value }} times"

      - alert: LLMProcessingStalled
        expr: phoenix_llm_processing_duration_seconds > 300
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "LLM processing taking too long"
          description: "LLM processing has been running for {{ $value }} seconds"
"""

    try:
        with open(monitoring_dir / "prometheus.yml", "w") as f:
            f.write(prometheus_config)

        with open(monitoring_dir / "phoenix_alerts.yml", "w") as f:
            f.write(alert_rules)

        logger.info(f"Created monitoring configuration in {monitoring_dir}")
        return True

    except Exception as e:
        logger.error(f"Failed to create monitoring configuration: {e}")
        return False


async def main():
    """Main setup function."""
    logger = setup_logging()

    logger.info("Phoenix Real Estate Production Environment Setup")
    logger.info("=" * 60)

    success_count = 0
    total_tasks = 0

    # Setup tasks
    tasks = [
        ("Create production environment file", lambda: create_production_env_file(logger)),
        ("Validate production secrets", lambda: bool(validate_production_secrets(logger))),
        (
            "Setup production database",
            lambda: asyncio.create_task(setup_production_database(logger)),
        ),
        ("Create systemd service", lambda: create_production_systemd_service(logger)),
        ("Create Docker Compose config", lambda: create_production_docker_compose(logger)),
        ("Create monitoring config", lambda: create_production_monitoring_config(logger)),
    ]

    for task_name, task_func in tasks:
        logger.info(f"\n🔧 {task_name}...")
        total_tasks += 1

        try:
            result = task_func()
            if asyncio.iscoroutine(result):
                result = await result

            if result:
                success_count += 1
                logger.info(f"✓ {task_name} completed successfully")
            else:
                logger.error(f"✗ {task_name} failed")

        except Exception as e:
            logger.error(f"✗ {task_name} failed with exception: {e}")

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info(f"Setup Summary: {success_count}/{total_tasks} tasks completed successfully")

    if success_count == total_tasks:
        logger.info("🎉 Production environment setup completed!")
        logger.info("\nNext steps:")
        logger.info("1. Update API keys and email configuration in .env.production")
        logger.info("2. Test email service: python scripts/deploy/validate_email_service.py --all")
        logger.info("3. Run end-to-end validation: python scripts/testing/verify_e2e_setup.py")
        logger.info("4. Start services and run production workflow")
        return 0
    else:
        logger.warning(f"⚠️ {total_tasks - success_count} setup tasks failed")
        logger.info("Please review the errors above and retry failed tasks")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
