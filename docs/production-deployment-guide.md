# Phoenix MLS Scraper - Production Deployment Guide

## Table of Contents
1. [System Overview](#system-overview)
2. [Prerequisites](#prerequisites)
3. [Infrastructure Setup](#infrastructure-setup)
4. [Environment Configuration](#environment-configuration)
5. [Application Deployment](#application-deployment)
6. [Database Setup](#database-setup)
7. [Monitoring & Observability](#monitoring--observability)
8. [Security Hardening](#security-hardening)
9. [Performance Optimization](#performance-optimization)
10. [Backup & Disaster Recovery](#backup--disaster-recovery)
11. [Troubleshooting Guide](#troubleshooting-guide)
12. [Maintenance Procedures](#maintenance-procedures)

## System Overview

The Phoenix MLS Scraper is a production-grade data collection system designed to aggregate real estate data from multiple sources including Maricopa County API, Phoenix MLS, and Particle Space. The system features:

- **Async Python Architecture**: Built with asyncio for high-performance data collection
- **MongoDB Atlas**: Cloud database with optimized connection pooling
- **Comprehensive Monitoring**: Prometheus metrics with structured logging
- **Resilient Design**: Retry logic, circuit breakers, and graceful degradation
- **Security First**: Environment-based configuration with secrets management

### Architecture Components

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Data Sources   │ ── │ Phoenix Scraper  │ ── │  MongoDB Atlas  │
│                 │    │                  │    │                 │
│ • Maricopa API  │    │ • Rate Limiting  │    │ • Connection    │
│ • Phoenix MLS   │    │ • Proxy Manager  │    │   Pooling       │
│ • Particle Space│    │ • Error Handling │    │ • Index Mgmt    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                │
                    ┌──────────────────┐
                    │   Monitoring     │
                    │                  │
                    │ • Prometheus     │
                    │ • Structured     │
                    │   Logging        │
                    │ • Health Checks  │
                    └──────────────────┘
```

## Prerequisites

### System Requirements

- **Operating System**: Ubuntu 20.04+ LTS or CentOS 8+ (recommended)
- **Python**: 3.13+ (required for compatibility)
- **Memory**: 2GB RAM minimum, 4GB recommended
- **Storage**: 20GB minimum, SSD recommended
- **Network**: Stable internet connection with HTTPS access

### Required Software

```bash
# System packages
sudo apt update && sudo apt install -y \
    python3.13 \
    python3.13-pip \
    python3.13-venv \
    python3.13-dev \
    build-essential \
    curl \
    wget \
    git \
    supervisor \
    nginx \
    ufw \
    htop \
    unzip

# Install uv package manager
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.cargo/env
```

### Cloud Services

1. **MongoDB Atlas** (free tier compatible)
   - M0 Sandbox cluster (512MB storage, 100 connections)
   - Network access configured for deployment IP
   - Database user with read/write permissions

2. **Proxy Services** (optional but recommended)
   - WebShare or similar residential proxy provider
   - Configure in `config/proxies.yaml`

## Infrastructure Setup

### 1. Server Provisioning

**AWS EC2 Instance (Recommended)**
```bash
# t3.small or larger recommended
# Ubuntu 20.04 LTS AMI
# Security group: SSH (22), HTTP (80), HTTPS (443), Custom (8000)
```

**DigitalOcean Droplet**
```bash
# $12/month droplet (2GB RAM, 1 vCPU)
# Ubuntu 20.04 LTS
# Add SSH keys during creation
```

### 2. Initial Server Setup

```bash
# Connect to server
ssh -i your-key.pem ubuntu@your-server-ip

# Update system
sudo apt update && sudo apt upgrade -y

# Create application user
sudo adduser phoenix --disabled-password --gecos ""
sudo usermod -aG sudo phoenix

# Switch to application user
sudo su - phoenix

# Create application directories
mkdir -p ~/phoenix-scraper/{logs,config,data,backups}
cd ~/phoenix-scraper
```

### 3. Firewall Configuration

```bash
# Enable UFW firewall
sudo ufw --force enable

# Allow essential ports
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw allow 8000/tcp # Application (if needed)

# Verify firewall status
sudo ufw status verbose
```

### 4. System Optimization

```bash
# Increase file descriptor limits
echo "phoenix soft nofile 65536" | sudo tee -a /etc/security/limits.conf
echo "phoenix hard nofile 65536" | sudo tee -a /etc/security/limits.conf

# Configure swap (if needed)
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# Optimize kernel parameters
echo "net.core.rmem_max = 268435456" | sudo tee -a /etc/sysctl.conf
echo "net.core.wmem_max = 268435456" | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

## Environment Configuration

### 1. Clone Repository

```bash
cd ~/phoenix-scraper
git clone https://github.com/your-org/phoenix-real-estate.git .

# Verify structure
ls -la
# Should show: src/, config/, tests/, pyproject.toml, etc.
```

### 2. Python Environment Setup

```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc

# Create virtual environment and install dependencies
uv venv --python 3.13
source .venv/bin/activate
uv pip install -e .

# Verify installation
python --version  # Should show Python 3.13.x
uv pip list       # Should show all dependencies
```

### 3. Environment Files

Create production environment files:

```bash
# Create base environment file
cat > .env << 'EOF'
# Environment
ENVIRONMENT=production

# Application
DEBUG=false
LOG_LEVEL=INFO

# Database will be set in production-specific file
EOF

# Create production environment file
cat > .env.production << 'EOF'
# Production MongoDB Atlas Configuration
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/
DATABASE_NAME=phoenix_real_estate

# API Keys (set actual values)
PARTICLE_SPACE_API_KEY=your_particle_space_api_key_here
WEBSHARE_PROXY_USERNAME=your_proxy_username_here
WEBSHARE_PROXY_PASSWORD=your_proxy_password_here

# Application Configuration
PORT=8000
WORKERS=2

# Security
SESSION_SECRET=your_32_character_session_secret_here
ENCRYPT_LOGS=true

# Performance
MAX_POOL_SIZE=10
MIN_POOL_SIZE=2
CONNECTION_TIMEOUT_MS=5000
RATE_LIMIT_REQUESTS_PER_HOUR=100

# Proxy Configuration
PROXY_ENABLED=true
PROXY_PROVIDER=webshare
PROXY_ROTATION_ENABLED=true

# Monitoring
METRICS_ENABLED=true
PROMETHEUS_PORT=9090
EOF

# Secure environment files
chmod 600 .env*
```

### 4. Configuration Files

```bash
# Copy production configuration
cp config/production.yaml config/production.local.yaml

# Copy and configure proxy settings
cp config/proxies.yaml config/proxies.local.yaml

# Edit configurations as needed
nano config/production.local.yaml
nano config/proxies.local.yaml
```

### 5. Secrets Management Template

Create secrets configuration:

```bash
cat > config/secrets.yaml << 'EOF'
# Production secrets configuration
# This file should be encrypted or managed by external secrets manager

mongodb:
  uri: "mongodb+srv://username:password@cluster.mongodb.net/"
  database: "phoenix_real_estate"

apis:
  particle_space:
    key: "your_particle_space_api_key"
    
proxies:
  webshare:
    username: "your_proxy_username"
    password: "your_proxy_password"
    
security:
  session_secret: "your_32_character_session_secret"
  encryption_key: "your_32_character_encryption_key"
EOF

chmod 600 config/secrets.yaml
```

## Application Deployment

### 1. Application Installation

```bash
# Install application in production mode
cd ~/phoenix-scraper
source .venv/bin/activate

# Install with production dependencies
uv pip install -e .

# Run configuration validation
python -m phoenix_real_estate.foundation.config.environment validate

# Run database connection test
python -c "
import asyncio
from phoenix_real_estate.foundation.database.connection import get_database_connection
from phoenix_real_estate.foundation.config.environment import get_config

async def test():
    config = get_config()
    conn = await get_database_connection(config.mongodb_uri, config.database_name)
    health = await conn.health_check()
    print('Database health:', health['connected'])

asyncio.run(test())
"
```

### 2. Systemd Service Configuration

Create systemd service file:

```bash
sudo tee /etc/systemd/system/phoenix-scraper.service << 'EOF'
[Unit]
Description=Phoenix Real Estate Scraper
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=phoenix
Group=phoenix
WorkingDirectory=/home/phoenix/phoenix-scraper
Environment=PATH=/home/phoenix/phoenix-scraper/.venv/bin
Environment=ENVIRONMENT=production
ExecStart=/home/phoenix/phoenix-scraper/.venv/bin/python -m phoenix_real_estate.orchestration.scheduler
ExecReload=/bin/kill -HUP $MAINPID
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Security settings
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/home/phoenix/phoenix-scraper/logs /home/phoenix/phoenix-scraper/data
PrivateTmp=true
ProtectKernelTunables=true
ProtectControlGroups=true
RestrictRealtime=true

# Resource limits
LimitNOFILE=65536
MemoryMax=1G
CPUQuota=80%

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable phoenix-scraper.service
sudo systemctl start phoenix-scraper.service

# Check service status
sudo systemctl status phoenix-scraper.service
```

### 3. Log Rotation Configuration

```bash
# Configure log rotation
sudo tee /etc/logrotate.d/phoenix-scraper << 'EOF'
/home/phoenix/phoenix-scraper/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0644 phoenix phoenix
    postrotate
        /bin/systemctl reload phoenix-scraper.service > /dev/null 2>&1 || true
    endscript
}
EOF

# Test log rotation
sudo logrotate -d /etc/logrotate.d/phoenix-scraper
```

## Database Setup

### 1. MongoDB Atlas Configuration

**Atlas Setup Steps:**

1. **Create Account**: Sign up at [MongoDB Atlas](https://www.mongodb.com/atlas)

2. **Create Cluster**:
   ```
   - Choose M0 Sandbox (Free)
   - Select closest region
   - Name: phoenix-real-estate-prod
   ```

3. **Network Access**:
   ```
   - Add IP address of production server
   - Or use 0.0.0.0/0 for development (not recommended for production)
   ```

4. **Database User**:
   ```
   - Username: phoenix_app
   - Password: Generate strong password
   - Roles: readWrite@phoenix_real_estate
   ```

5. **Connection String**:
   ```
   mongodb+srv://phoenix_app:PASSWORD@phoenix-real-estate-prod.mongodb.net/phoenix_real_estate
   ```

### 2. Database Initialization

```bash
# Run database setup script
cd ~/phoenix-scraper
source .venv/bin/activate

# Initialize database with indexes
python -c "
import asyncio
from phoenix_real_estate.foundation.database.connection import get_database_connection
from phoenix_real_estate.foundation.config.environment import get_config

async def setup():
    config = get_config()
    conn = await get_database_connection(config.mongodb_uri, config.database_name)
    print('Database initialized successfully')

asyncio.run(setup())
"

# Verify database structure
python scripts/validate_structure.py --environment production
```

### 3. Database Monitoring Setup

Create database monitoring script:

```bash
cat > ~/phoenix-scraper/scripts/db_health_check.py << 'EOF'
#!/usr/bin/env python3
"""Database health check script for monitoring."""

import asyncio
import json
import sys
from datetime import datetime
from phoenix_real_estate.foundation.database.connection import get_database_connection
from phoenix_real_estate.foundation.config.environment import get_config

async def main():
    try:
        config = get_config()
        conn = await get_database_connection(config.mongodb_uri, config.database_name)
        
        health = await conn.health_check()
        health['timestamp'] = datetime.utcnow().isoformat()
        
        print(json.dumps(health, indent=2))
        
        if not health['connected']:
            sys.exit(1)
            
    except Exception as e:
        print(json.dumps({
            'connected': False,
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }))
        sys.exit(1)

if __name__ == '__main__':
    asyncio.run(main())
EOF

chmod +x ~/phoenix-scraper/scripts/db_health_check.py
```

## Monitoring & Observability

### 1. Prometheus Metrics Setup

```bash
# Install Prometheus
cd /tmp
wget https://github.com/prometheus/prometheus/releases/download/v2.45.0/prometheus-2.45.0.linux-amd64.tar.gz
tar xzf prometheus-2.45.0.linux-amd64.tar.gz
sudo mv prometheus-2.45.0.linux-amd64/prometheus /usr/local/bin/
sudo mv prometheus-2.45.0.linux-amd64/promtool /usr/local/bin/

# Create Prometheus user and directories
sudo useradd --no-create-home --shell /bin/false prometheus
sudo mkdir /etc/prometheus /var/lib/prometheus
sudo chown prometheus:prometheus /etc/prometheus /var/lib/prometheus

# Create Prometheus configuration
sudo tee /etc/prometheus/prometheus.yml << 'EOF'
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "phoenix_scraper.rules"

scrape_configs:
  - job_name: 'phoenix-scraper'
    static_configs:
      - targets: ['localhost:9090']
    scrape_interval: 10s
    metrics_path: '/metrics'

  - job_name: 'node-exporter'
    static_configs:
      - targets: ['localhost:9100']

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - localhost:9093
EOF

# Create alerting rules
sudo tee /etc/prometheus/phoenix_scraper.rules << 'EOF'
groups:
  - name: phoenix_scraper
    rules:
      - alert: ScraperDown
        expr: up{job="phoenix-scraper"} == 0
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Phoenix Scraper is down"
          
      - alert: HighErrorRate
        expr: rate(scraper_errors_total[5m]) > 0.1
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "High error rate in Phoenix Scraper"
          
      - alert: DatabaseConnectionLost
        expr: database_connections_active == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Database connection lost"

      - alert: MemoryUsageHigh
        expr: system_memory_usage_percent > 90
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High memory usage"
EOF

sudo chown -R prometheus:prometheus /etc/prometheus

# Create Prometheus systemd service
sudo tee /etc/systemd/system/prometheus.service << 'EOF'
[Unit]
Description=Prometheus
Wants=network-online.target
After=network-online.target

[Service]
User=prometheus
Group=prometheus
Type=simple
ExecStart=/usr/local/bin/prometheus \
  --config.file /etc/prometheus/prometheus.yml \
  --storage.tsdb.path /var/lib/prometheus/ \
  --web.console.templates=/etc/prometheus/consoles \
  --web.console.libraries=/etc/prometheus/console_libraries \
  --web.listen-address=0.0.0.0:9090 \
  --web.enable-lifecycle

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable prometheus
sudo systemctl start prometheus
```

### 2. Node Exporter Setup

```bash
# Install Node Exporter
cd /tmp
wget https://github.com/prometheus/node_exporter/releases/download/v1.6.0/node_exporter-1.6.0.linux-amd64.tar.gz
tar xzf node_exporter-1.6.0.linux-amd64.tar.gz
sudo mv node_exporter-1.6.0.linux-amd64/node_exporter /usr/local/bin/

# Create node_exporter user
sudo useradd --no-create-home --shell /bin/false node_exporter

# Create systemd service
sudo tee /etc/systemd/system/node_exporter.service << 'EOF'
[Unit]
Description=Node Exporter
Wants=network-online.target
After=network-online.target

[Service]
User=node_exporter
Group=node_exporter
Type=simple
ExecStart=/usr/local/bin/node_exporter

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable node_exporter
sudo systemctl start node_exporter
```

### 3. Application Metrics Endpoint

Add metrics endpoint to your application:

```bash
# Create metrics server script
cat > ~/phoenix-scraper/scripts/metrics_server.py << 'EOF'
#!/usr/bin/env python3
"""Standalone metrics server for Prometheus."""

import asyncio
from aiohttp import web, web_runner
from phoenix_real_estate.foundation.monitoring.metrics import get_metrics_collector
from phoenix_real_estate.foundation.config.environment import get_config

async def metrics_handler(request):
    """Handle metrics endpoint."""
    config = get_config()
    collector = get_metrics_collector()
    metrics_data = collector.get_metrics()
    
    return web.Response(
        text=metrics_data.decode('utf-8'),
        content_type='text/plain; version=0.0.4'
    )

async def health_handler(request):
    """Handle health check endpoint."""
    return web.json_response({'status': 'healthy'})

async def create_app():
    """Create metrics web application."""
    app = web.Application()
    app.router.add_get('/metrics', metrics_handler)
    app.router.add_get('/health', health_handler)
    return app

async def main():
    app = await create_app()
    runner = web_runner.AppRunner(app)
    await runner.setup()
    
    site = web.TCPSite(runner, '0.0.0.0', 9090)
    await site.start()
    
    print("Metrics server started on http://0.0.0.0:9090")
    print("Metrics: http://0.0.0.0:9090/metrics")
    print("Health: http://0.0.0.0:9090/health")
    
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        pass
    finally:
        await runner.cleanup()

if __name__ == '__main__':
    asyncio.run(main())
EOF

chmod +x ~/phoenix-scraper/scripts/metrics_server.py
```

### 4. Structured Logging Configuration

```bash
# Create logging configuration
cat > ~/phoenix-scraper/config/logging.yaml << 'EOF'
version: 1
disable_existing_loggers: false

formatters:
  json:
    class: phoenix_real_estate.foundation.logging.formatters.JSONFormatter
    format: "%(asctime)s %(name)s %(levelname)s %(message)s"
  
  standard:
    class: logging.Formatter
    format: "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

handlers:
  console:
    class: logging.StreamHandler
    level: INFO
    formatter: standard
    stream: ext://sys.stdout

  file:
    class: logging.handlers.RotatingFileHandler
    level: INFO
    formatter: json
    filename: /home/phoenix/phoenix-scraper/logs/application.log
    maxBytes: 52428800  # 50MB
    backupCount: 10

  error_file:
    class: logging.handlers.RotatingFileHandler
    level: ERROR
    formatter: json
    filename: /home/phoenix/phoenix-scraper/logs/errors.log
    maxBytes: 52428800  # 50MB
    backupCount: 5

loggers:
  phoenix_real_estate:
    level: INFO
    handlers: [console, file, error_file]
    propagate: false

root:
  level: WARNING
  handlers: [console, file]
EOF
```

## Security Hardening

### 1. System Security

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install security updates automatically
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades

# Configure SSH security
sudo nano /etc/ssh/sshd_config
# Add/modify these settings:
# PermitRootLogin no
# PasswordAuthentication no
# PubkeyAuthentication yes
# Port 2222  # Change from default 22

sudo systemctl restart ssh
```

### 2. Application Security

```bash
# Set proper file permissions
chmod 700 ~/phoenix-scraper
chmod 600 ~/phoenix-scraper/.env*
chmod 600 ~/phoenix-scraper/config/secrets.yaml
chmod -R 755 ~/phoenix-scraper/src
chmod -R 755 ~/phoenix-scraper/scripts
chmod +x ~/phoenix-scraper/scripts/*.py

# Create security audit script
cat > ~/phoenix-scraper/scripts/security_audit.py << 'EOF'
#!/usr/bin/env python3
"""Security audit script for Phoenix Scraper."""

import os
import stat
import subprocess
from pathlib import Path

def check_file_permissions():
    """Check file permissions for sensitive files."""
    sensitive_files = [
        '.env',
        '.env.production',
        'config/secrets.yaml',
    ]
    
    base_path = Path.home() / 'phoenix-scraper'
    
    for file_path in sensitive_files:
        full_path = base_path / file_path
        if full_path.exists():
            file_stat = full_path.stat()
            perms = stat.filemode(file_stat.st_mode)
            print(f"{file_path}: {perms}")
            
            # Check if file is readable by others
            if file_stat.st_mode & 0o077:
                print(f"WARNING: {file_path} is readable by others!")

def check_environment_variables():
    """Check for exposed environment variables."""
    sensitive_vars = [
        'MONGODB_URI',
        'API_KEY',
        'SESSION_SECRET',
        'PROXY_PASSWORD'
    ]
    
    for var in sensitive_vars:
        if var in os.environ:
            value = os.environ[var]
            if len(value) > 10:
                masked = value[:4] + '*' * (len(value) - 8) + value[-4:]
            else:
                masked = '*' * len(value)
            print(f"{var}: {masked}")

if __name__ == '__main__':
    print("=== Security Audit ===")
    print("\nFile Permissions:")
    check_file_permissions()
    
    print("\nEnvironment Variables:")
    check_environment_variables()
EOF

chmod +x ~/phoenix-scraper/scripts/security_audit.py
```

### 3. Secrets Management

```bash
# Install and configure secrets management
pip install cryptography

# Create secrets encryption script
cat > ~/phoenix-scraper/scripts/encrypt_secrets.py << 'EOF'
#!/usr/bin/env python3
"""Encrypt sensitive configuration files."""

import os
import base64
from cryptography.fernet import Fernet
from pathlib import Path

def generate_key():
    """Generate encryption key."""
    return Fernet.generate_key()

def encrypt_file(file_path, key):
    """Encrypt a file."""
    fernet = Fernet(key)
    
    with open(file_path, 'rb') as file:
        file_data = file.read()
    
    encrypted_data = fernet.encrypt(file_data)
    
    with open(f"{file_path}.encrypted", 'wb') as file:
        file.write(encrypted_data)
    
    print(f"Encrypted: {file_path}")

def decrypt_file(encrypted_file_path, key):
    """Decrypt a file."""
    fernet = Fernet(key)
    
    with open(encrypted_file_path, 'rb') as file:
        encrypted_data = file.read()
    
    decrypted_data = fernet.decrypt(encrypted_data)
    
    original_path = encrypted_file_path.replace('.encrypted', '')
    with open(original_path, 'wb') as file:
        file.write(decrypted_data)
    
    print(f"Decrypted: {original_path}")

if __name__ == '__main__':
    # Example usage
    print("Secrets encryption utility")
    print("Run with appropriate arguments")
EOF

chmod +x ~/phoenix-scraper/scripts/encrypt_secrets.py
```

## Performance Optimization

### 1. System Performance

```bash
# Optimize system settings for the application
sudo tee -a /etc/sysctl.conf << 'EOF'

# Phoenix Scraper optimizations
# Network optimizations
net.ipv4.tcp_keepalive_time = 120
net.ipv4.tcp_keepalive_intvl = 30
net.ipv4.tcp_keepalive_probes = 3

# File system optimizations
vm.dirty_ratio = 10
vm.dirty_background_ratio = 5

# Connection limits
net.core.somaxconn = 65535
net.ipv4.tcp_max_syn_backlog = 65535
EOF

sudo sysctl -p
```

### 2. Application Performance

```bash
# Create performance monitoring script
cat > ~/phoenix-scraper/scripts/performance_monitor.py << 'EOF'
#!/usr/bin/env python3
"""Performance monitoring script."""

import time
import psutil
import asyncio
import json
from datetime import datetime

def get_system_metrics():
    """Get current system metrics."""
    return {
        'timestamp': datetime.utcnow().isoformat(),
        'cpu_percent': psutil.cpu_percent(interval=1),
        'memory': {
            'percent': psutil.virtual_memory().percent,
            'used_mb': psutil.virtual_memory().used / 1024 / 1024,
            'available_mb': psutil.virtual_memory().available / 1024 / 1024
        },
        'disk': {
            'percent': psutil.disk_usage('/').percent,
            'used_gb': psutil.disk_usage('/').used / 1024 / 1024 / 1024,
            'free_gb': psutil.disk_usage('/').free / 1024 / 1024 / 1024
        },
        'network': {
            'bytes_sent': psutil.net_io_counters().bytes_sent,
            'bytes_recv': psutil.net_io_counters().bytes_recv
        }
    }

async def monitor_performance():
    """Monitor performance continuously."""
    while True:
        metrics = get_system_metrics()
        
        # Log to file
        with open('/home/phoenix/phoenix-scraper/logs/performance.log', 'a') as f:
            f.write(json.dumps(metrics) + '\n')
        
        # Alert on high resource usage
        if metrics['cpu_percent'] > 90:
            print(f"HIGH CPU: {metrics['cpu_percent']:.1f}%")
        
        if metrics['memory']['percent'] > 90:
            print(f"HIGH MEMORY: {metrics['memory']['percent']:.1f}%")
        
        await asyncio.sleep(60)  # Monitor every minute

if __name__ == '__main__':
    print("Starting performance monitoring...")
    asyncio.run(monitor_performance())
EOF

chmod +x ~/phoenix-scraper/scripts/performance_monitor.py
```

### 3. Database Optimization

```bash
# Create database optimization script
cat > ~/phoenix-scraper/scripts/optimize_database.py << 'EOF'
#!/usr/bin/env python3
"""Database optimization utilities."""

import asyncio
import json
from datetime import datetime, timedelta
from phoenix_real_estate.foundation.database.connection import get_database_connection
from phoenix_real_estate.foundation.config.environment import get_config

async def analyze_query_performance():
    """Analyze database query performance."""
    config = get_config()
    conn = await get_database_connection(config.mongodb_uri, config.database_name)
    
    async with conn.get_database() as db:
        # Get slow query log
        try:
            profiler_status = await db.command("profile", -1)
            print("Database profiler status:")
            print(json.dumps(profiler_status, indent=2, default=str))
        except Exception as e:
            print(f"Could not get profiler status: {e}")
        
        # Get database stats
        stats = await db.command("dbStats")
        print("\nDatabase statistics:")
        print(json.dumps(stats, indent=2, default=str))
        
        # Get collection stats for main collections
        for collection_name in ['properties', 'daily_reports']:
            try:
                coll_stats = await db.command("collStats", collection_name)
                print(f"\nCollection '{collection_name}' statistics:")
                print(f"Documents: {coll_stats.get('count', 0)}")
                print(f"Size: {coll_stats.get('size', 0) / 1024 / 1024:.2f} MB")
                print(f"Storage Size: {coll_stats.get('storageSize', 0) / 1024 / 1024:.2f} MB")
                print(f"Indexes: {coll_stats.get('nindexes', 0)}")
            except Exception as e:
                print(f"Could not get stats for {collection_name}: {e}")

async def cleanup_old_data():
    """Clean up old data to optimize storage."""
    config = get_config()
    conn = await get_database_connection(config.mongodb_uri, config.database_name)
    
    cutoff_date = datetime.utcnow() - timedelta(days=90)
    
    async with conn.get_database() as db:
        # Remove old daily reports (keep last 90 days)
        result = await db.daily_reports.delete_many({
            "date": {"$lt": cutoff_date}
        })
        print(f"Deleted {result.deleted_count} old daily reports")
        
        # Update inactive properties (mark as inactive if not updated in 30 days)
        inactive_cutoff = datetime.utcnow() - timedelta(days=30)
        result = await db.properties.update_many(
            {
                "last_updated": {"$lt": inactive_cutoff},
                "is_active": True
            },
            {"$set": {"is_active": False}}
        )
        print(f"Marked {result.modified_count} properties as inactive")

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'analyze':
        asyncio.run(analyze_query_performance())
    elif len(sys.argv) > 1 and sys.argv[1] == 'cleanup':
        asyncio.run(cleanup_old_data())
    else:
        print("Usage: python optimize_database.py [analyze|cleanup]")
EOF

chmod +x ~/phoenix-scraper/scripts/optimize_database.py
```

## Backup & Disaster Recovery

### 1. Database Backup Strategy

```bash
# Create backup script
cat > ~/phoenix-scraper/scripts/backup_database.py << 'EOF'
#!/usr/bin/env python3
"""Database backup script using mongodump."""

import os
import subprocess
import gzip
import shutil
from datetime import datetime
from pathlib import Path
from phoenix_real_estate.foundation.config.environment import get_config

def create_backup():
    """Create database backup using mongodump."""
    config = get_config()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_dir = Path.home() / 'phoenix-scraper' / 'backups'
    backup_path = backup_dir / f'mongodb_backup_{timestamp}'
    
    # Create backup directory
    backup_path.mkdir(parents=True, exist_ok=True)
    
    # Extract connection details
    import re
    uri_parts = re.match(r'mongodb\+srv://([^:]+):([^@]+)@([^/]+)/(.+)', config.mongodb_uri)
    if not uri_parts:
        print("Error: Could not parse MongoDB URI")
        return False
    
    username, password, host, database = uri_parts.groups()
    
    try:
        # Run mongodump
        cmd = [
            'mongodump',
            '--uri', config.mongodb_uri,
            '--out', str(backup_path),
            '--gzip'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
        
        if result.returncode == 0:
            print(f"Backup created successfully: {backup_path}")
            
            # Create compressed archive
            archive_path = f"{backup_path}.tar.gz"
            shutil.make_archive(str(backup_path), 'gztar', str(backup_path))
            shutil.rmtree(backup_path)  # Remove uncompressed backup
            
            print(f"Compressed backup: {archive_path}")
            
            # Clean up old backups (keep last 7 days)
            cleanup_old_backups(backup_dir, days=7)
            
            return True
        else:
            print(f"Backup failed: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("Backup timed out after 1 hour")
        return False
    except Exception as e:
        print(f"Backup error: {e}")
        return False

def cleanup_old_backups(backup_dir, days=7):
    """Clean up backups older than specified days."""
    cutoff_time = datetime.now().timestamp() - (days * 24 * 3600)
    
    for backup_file in backup_dir.glob('mongodb_backup_*.tar.gz'):
        if backup_file.stat().st_mtime < cutoff_time:
            backup_file.unlink()
            print(f"Deleted old backup: {backup_file}")

def restore_backup(backup_file):
    """Restore from backup file."""
    config = get_config()
    
    # Extract backup
    temp_dir = Path('/tmp') / 'mongodb_restore'
    temp_dir.mkdir(exist_ok=True)
    
    try:
        shutil.unpack_archive(backup_file, temp_dir)
        
        # Find the backup directory
        backup_dirs = list(temp_dir.glob('mongodb_backup_*'))
        if not backup_dirs:
            print("Error: No backup directory found in archive")
            return False
        
        backup_path = backup_dirs[0]
        
        # Run mongorestore
        cmd = [
            'mongorestore',
            '--uri', config.mongodb_uri,
            '--gzip',
            '--drop',  # Drop collections before restoring
            str(backup_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
        
        if result.returncode == 0:
            print("Restore completed successfully")
            return True
        else:
            print(f"Restore failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"Restore error: {e}")
        return False
    finally:
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'restore':
        if len(sys.argv) < 3:
            print("Usage: python backup_database.py restore <backup_file>")
        else:
            restore_backup(sys.argv[2])
    else:
        create_backup()
EOF

chmod +x ~/phoenix-scraper/scripts/backup_database.py
```

### 2. Automated Backup Setup

```bash
# Install MongoDB tools
wget https://fastdl.mongodb.org/tools/db/mongodb-database-tools-ubuntu2004-x86_64-100.7.3.tgz
tar -zxvf mongodb-database-tools-*.tgz
sudo mv mongodb-database-tools-*/bin/* /usr/local/bin/
rm -rf mongodb-database-tools-*

# Create backup cron job
(crontab -l 2>/dev/null; echo "0 2 * * * /home/phoenix/phoenix-scraper/.venv/bin/python /home/phoenix/phoenix-scraper/scripts/backup_database.py") | crontab -

# Verify cron job
crontab -l
```

### 3. Disaster Recovery Plan

```bash
# Create disaster recovery documentation
cat > ~/phoenix-scraper/DISASTER_RECOVERY.md << 'EOF'
# Disaster Recovery Plan

## Recovery Time Objectives (RTO)
- **Critical**: 4 hours
- **Important**: 24 hours
- **Normal**: 72 hours

## Recovery Point Objectives (RPO)
- **Database**: 24 hours (daily backups)
- **Configuration**: Immediate (version controlled)
- **Logs**: 24 hours (rotated daily)

## Recovery Procedures

### 1. Complete System Failure
1. Provision new server with same specifications
2. Follow deployment guide sections 1-4
3. Restore database from latest backup
4. Restore configuration files from version control
5. Start services and verify functionality

### 2. Database Corruption
1. Stop application services
2. Identify latest clean backup
3. Restore database using backup script
4. Verify data integrity
5. Restart services

### 3. Application Failure
1. Check service status: `systemctl status phoenix-scraper`
2. Review logs: `journalctl -u phoenix-scraper -f`
3. Restart service: `systemctl restart phoenix-scraper`
4. If persistent, rollback to last known good version

### 4. Configuration Corruption
1. Stop services
2. Restore configuration from version control
3. Validate configuration: `python -m phoenix_real_estate.foundation.config.environment validate`
4. Restart services

## Emergency Contacts
- DevOps Team: ops@company.com
- Database Admin: dba@company.com
- Application Team: dev@company.com

## Recovery Testing
- Monthly: Test database restore procedure
- Quarterly: Full disaster recovery simulation
- Annually: Complete infrastructure rebuild test
EOF
```

## Troubleshooting Guide

### 1. Common Issues and Solutions

#### Application Won't Start

**Problem**: Service fails to start
```bash
# Check service status
sudo systemctl status phoenix-scraper.service

# Check logs
sudo journalctl -u phoenix-scraper -f --lines=50

# Common fixes:
# 1. Configuration error
python -m phoenix_real_estate.foundation.config.environment validate

# 2. Database connection issue
~/phoenix-scraper/scripts/db_health_check.py

# 3. Permission issue
sudo chown -R phoenix:phoenix /home/phoenix/phoenix-scraper
chmod 600 /home/phoenix/phoenix-scraper/.env*
```

#### High Memory Usage

**Problem**: Application consuming too much memory
```bash
# Check memory usage
top -p $(pgrep -f phoenix-scraper)

# Check for memory leaks
~/phoenix-scraper/scripts/performance_monitor.py

# Solutions:
# 1. Restart service to clear memory
sudo systemctl restart phoenix-scraper

# 2. Reduce batch size in configuration
nano ~/phoenix-scraper/config/production.local.yaml
# Set: processing.batch_size: 5

# 3. Enable memory limits in systemd
sudo nano /etc/systemd/system/phoenix-scraper.service
# Add: MemoryMax=512M
```

#### Database Connection Failures

**Problem**: Cannot connect to MongoDB Atlas
```bash
# Test connection
~/phoenix-scraper/scripts/db_health_check.py

# Check network connectivity
ping cluster.mongodb.net
telnet cluster.mongodb.net 27017

# Common fixes:
# 1. IP whitelist issue (Atlas)
# 2. Wrong credentials in .env.production
# 3. Network firewall blocking connection
```

#### Scraping Blocked

**Problem**: Getting blocked by target websites
```bash
# Check proxy status
tail -f ~/phoenix-scraper/logs/application.log | grep proxy

# Solutions:
# 1. Enable proxy rotation
nano ~/phoenix-scraper/config/proxies.local.yaml
# Set: rotation_enabled: true

# 2. Increase delays between requests
nano ~/phoenix-scraper/config/production.local.yaml
# Set: collection.min_request_delay: 5.0

# 3. Update user agents and headers
```

### 2. Performance Issues

#### Slow Database Queries

```bash
# Analyze query performance
~/phoenix-scraper/scripts/optimize_database.py analyze

# Enable MongoDB profiling (if using dedicated cluster)
# This requires elevated permissions not available in Atlas free tier
```

#### High CPU Usage

```bash
# Check CPU usage by component
htop
ps aux | grep python

# Reduce processing load
nano ~/phoenix-scraper/config/production.local.yaml
# Reduce: processing.max_processing_workers: 1
```

### 3. Monitoring and Alerts

#### Setup Health Check Endpoint

```bash
# Create health check script
cat > ~/phoenix-scraper/scripts/health_check.py << 'EOF'
#!/usr/bin/env python3
"""Comprehensive health check script."""

import asyncio
import json
import sys
import time
from datetime import datetime
from phoenix_real_estate.foundation.database.connection import get_database_connection
from phoenix_real_estate.foundation.config.environment import get_config

async def check_health():
    """Perform comprehensive health check."""
    health_status = {
        'timestamp': datetime.utcnow().isoformat(),
        'status': 'healthy',
        'checks': {}
    }
    
    try:
        # Configuration check
        config = get_config()
        health_status['checks']['configuration'] = {
            'status': 'healthy',
            'environment': config.environment.value
        }
        
        # Database check
        start_time = time.time()
        conn = await get_database_connection(config.mongodb_uri, config.database_name)
        db_health = await conn.health_check()
        
        health_status['checks']['database'] = {
            'status': 'healthy' if db_health['connected'] else 'unhealthy',
            'ping_time_ms': db_health.get('ping_time_ms'),
            'connection_time_ms': round((time.time() - start_time) * 1000, 2)
        }
        
        if not db_health['connected']:
            health_status['status'] = 'unhealthy'
            
        # Memory check
        import psutil
        memory = psutil.virtual_memory()
        health_status['checks']['memory'] = {
            'status': 'healthy' if memory.percent < 90 else 'warning',
            'usage_percent': memory.percent,
            'available_mb': round(memory.available / 1024 / 1024, 1)
        }
        
        # Disk check
        disk = psutil.disk_usage('/')
        health_status['checks']['disk'] = {
            'status': 'healthy' if disk.percent < 90 else 'warning',
            'usage_percent': disk.percent,
            'free_gb': round(disk.free / 1024 / 1024 / 1024, 1)
        }
        
    except Exception as e:
        health_status['status'] = 'unhealthy'
        health_status['error'] = str(e)
    
    return health_status

async def main():
    health = await check_health()
    print(json.dumps(health, indent=2))
    
    # Exit with error code if unhealthy
    if health['status'] != 'healthy':
        sys.exit(1)

if __name__ == '__main__':
    asyncio.run(main())
EOF

chmod +x ~/phoenix-scraper/scripts/health_check.py
```

#### Setup External Monitoring

```bash
# Create monitoring configuration for external services
cat > ~/phoenix-scraper/config/monitoring.yaml << 'EOF'
# External monitoring configuration

# Health check endpoints
health_checks:
  - name: "Application Health"
    url: "http://localhost:9090/health"
    interval: 60
    timeout: 10
    
  - name: "Database Health"
    command: "/home/phoenix/phoenix-scraper/scripts/db_health_check.py"
    interval: 300
    timeout: 30

# Alert thresholds
alerts:
  memory_usage_percent: 85
  disk_usage_percent: 90
  cpu_usage_percent: 80
  error_rate_per_hour: 10
  response_time_ms: 5000

# Notification settings
notifications:
  email:
    smtp_server: "smtp.gmail.com"
    smtp_port: 587
    username: "alerts@company.com"
    # Password should be in secrets.yaml
    
  slack:
    webhook_url: "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK"
EOF
```

## Maintenance Procedures

### 1. Regular Maintenance Tasks

#### Daily Tasks (Automated)

```bash
# Create daily maintenance script
cat > ~/phoenix-scraper/scripts/daily_maintenance.py << 'EOF'
#!/usr/bin/env python3
"""Daily maintenance tasks."""

import asyncio
import logging
from datetime import datetime, timedelta
from phoenix_real_estate.foundation.database.connection import get_database_connection
from phoenix_real_estate.foundation.config.environment import get_config

async def daily_maintenance():
    """Run daily maintenance tasks."""
    print(f"Starting daily maintenance at {datetime.now()}")
    
    config = get_config()
    conn = await get_database_connection(config.mongodb_uri, config.database_name)
    
    async with conn.get_database() as db:
        # 1. Clean up old temporary data
        cutoff_date = datetime.utcnow() - timedelta(days=7)
        
        # Remove old error logs from database (if stored there)
        result = await db.error_logs.delete_many({
            "timestamp": {"$lt": cutoff_date}
        })
        print(f"Cleaned up {result.deleted_count} old error logs")
        
        # 2. Update collection statistics
        for collection_name in ['properties', 'daily_reports']:
            stats = await db.command("collStats", collection_name)
            print(f"{collection_name}: {stats['count']} documents, "
                  f"{stats['size'] / 1024 / 1024:.1f}MB")
        
        # 3. Check for stale data
        stale_cutoff = datetime.utcnow() - timedelta(days=30)
        stale_count = await db.properties.count_documents({
            "last_updated": {"$lt": stale_cutoff},
            "is_active": True
        })
        print(f"Found {stale_count} stale properties")
    
    print("Daily maintenance completed")

if __name__ == '__main__':
    asyncio.run(daily_maintenance())
EOF

chmod +x ~/phoenix-scraper/scripts/daily_maintenance.py

# Add to cron
(crontab -l 2>/dev/null; echo "0 1 * * * /home/phoenix/phoenix-scraper/.venv/bin/python /home/phoenix/phoenix-scraper/scripts/daily_maintenance.py >> /home/phoenix/phoenix-scraper/logs/maintenance.log 2>&1") | crontab -
```

#### Weekly Tasks

```bash
# Create weekly maintenance script
cat > ~/phoenix-scraper/scripts/weekly_maintenance.py << 'EOF'
#!/usr/bin/env python3
"""Weekly maintenance tasks."""

import asyncio
import subprocess
from datetime import datetime

async def weekly_maintenance():
    """Run weekly maintenance tasks."""
    print(f"Starting weekly maintenance at {datetime.now()}")
    
    # 1. System updates
    print("Checking for system updates...")
    try:
        subprocess.run(["sudo", "apt", "update"], check=True, capture_output=True)
        result = subprocess.run(["apt", "list", "--upgradable"], 
                              capture_output=True, text=True)
        if "upgradable" in result.stdout:
            print("System updates available - manual review required")
        else:
            print("System is up to date")
    except subprocess.CalledProcessError as e:
        print(f"Update check failed: {e}")
    
    # 2. Log rotation and cleanup
    print("Cleaning up old log files...")
    try:
        subprocess.run(["sudo", "logrotate", "-f", "/etc/logrotate.d/phoenix-scraper"], 
                      check=True)
        print("Log rotation completed")
    except subprocess.CalledProcessError as e:
        print(f"Log rotation failed: {e}")
    
    # 3. Performance analysis
    print("Analyzing performance metrics...")
    # Run performance analysis script
    subprocess.run(["/home/phoenix/phoenix-scraper/scripts/optimize_database.py", "analyze"])
    
    # 4. Security audit
    print("Running security audit...")
    subprocess.run(["/home/phoenix/phoenix-scraper/scripts/security_audit.py"])
    
    print("Weekly maintenance completed")

if __name__ == '__main__':
    asyncio.run(weekly_maintenance())
EOF

chmod +x ~/phoenix-scraper/scripts/weekly_maintenance.py

# Add to cron (Sunday at 2 AM)
(crontab -l 2>/dev/null; echo "0 2 * * 0 /home/phoenix/phoenix-scraper/.venv/bin/python /home/phoenix/phoenix-scraper/scripts/weekly_maintenance.py >> /home/phoenix/phoenix-scraper/logs/maintenance.log 2>&1") | crontab -
```

### 2. Application Updates

#### Update Procedure

```bash
# Create update script
cat > ~/phoenix-scraper/scripts/update_application.sh << 'EOF'
#!/bin/bash
"""Application update script."""

set -e  # Exit on error

echo "=== Phoenix Scraper Update Procedure ==="
echo "Starting update at $(date)"

# 1. Create backup
echo "Creating backup..."
/home/phoenix/phoenix-scraper/scripts/backup_database.py

# 2. Stop services
echo "Stopping services..."
sudo systemctl stop phoenix-scraper.service

# 3. Backup current application
echo "Backing up current application..."
tar -czf "/home/phoenix/phoenix-scraper-backup-$(date +%Y%m%d_%H%M%S).tar.gz" \
    -C /home/phoenix phoenix-scraper --exclude=phoenix-scraper/.venv

# 4. Pull updates
echo "Pulling updates from repository..."
cd /home/phoenix/phoenix-scraper
git fetch origin
git checkout main
git pull origin main

# 5. Update dependencies
echo "Updating dependencies..."
source .venv/bin/activate
uv pip install -e .

# 6. Run tests
echo "Running tests..."
python -m pytest tests/ -v --tb=short

# 7. Validate configuration
echo "Validating configuration..."
python -m phoenix_real_estate.foundation.config.environment validate

# 8. Start services
echo "Starting services..."
sudo systemctl start phoenix-scraper.service

# 9. Verify deployment
echo "Verifying deployment..."
sleep 10
sudo systemctl status phoenix-scraper.service

# 10. Run health check
echo "Running health check..."
/home/phoenix/phoenix-scraper/scripts/health_check.py

echo "Update completed successfully at $(date)"
EOF

chmod +x ~/phoenix-scraper/scripts/update_application.sh
```

### 3. Monitoring Dashboard

```bash
# Create simple monitoring dashboard
cat > ~/phoenix-scraper/scripts/monitoring_dashboard.py << 'EOF'
#!/usr/bin/env python3
"""Simple monitoring dashboard."""

import asyncio
import json
import time
from datetime import datetime
import subprocess

class MonitoringDashboard:
    """Simple text-based monitoring dashboard."""
    
    def __init__(self):
        self.start_time = time.time()
        
    async def get_system_status(self):
        """Get current system status."""
        try:
            # Service status
            result = subprocess.run(
                ['systemctl', 'is-active', 'phoenix-scraper.service'],
                capture_output=True, text=True
            )
            service_status = result.stdout.strip()
            
            # Health check
            try:
                health_result = subprocess.run(
                    ['/home/phoenix/phoenix-scraper/scripts/health_check.py'],
                    capture_output=True, text=True, timeout=30
                )
                health_data = json.loads(health_result.stdout)
                health_status = health_data['status']
            except:
                health_status = 'unknown'
            
            # System metrics
            import psutil
            
            return {
                'timestamp': datetime.now().isoformat(),
                'uptime': time.time() - self.start_time,
                'service_status': service_status,
                'health_status': health_status,
                'cpu_percent': psutil.cpu_percent(),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_percent': psutil.disk_usage('/').percent,
                'network_connections': len(psutil.net_connections()),
            }
        except Exception as e:
            return {'error': str(e)}
    
    def format_status(self, status):
        """Format status for display."""
        if 'error' in status:
            return f"ERROR: {status['error']}"
        
        uptime_hours = status['uptime'] / 3600
        
        return f"""
╔═══════════════════════════════════════════════════════════╗
║                 Phoenix Scraper Status                     ║
╠═══════════════════════════════════════════════════════════╣
║ Timestamp: {status['timestamp']:<40} ║
║ Uptime: {uptime_hours:>8.1f} hours                        ║
║                                                           ║
║ Service Status: {status['service_status']:<20}            ║
║ Health Status:  {status['health_status']:<20}             ║
║                                                           ║
║ CPU Usage:    {status['cpu_percent']:>6.1f}%              ║
║ Memory Usage: {status['memory_percent']:>6.1f}%           ║
║ Disk Usage:   {status['disk_percent']:>6.1f}%             ║
║                                                           ║
║ Network Connections: {status['network_connections']:>6d}  ║
╚═══════════════════════════════════════════════════════════╝
"""

    async def run_dashboard(self, refresh_interval=30):
        """Run the monitoring dashboard."""
        print("Phoenix Scraper Monitoring Dashboard")
        print("Press Ctrl+C to exit")
        print("=" * 60)
        
        try:
            while True:
                # Clear screen (works on most terminals)
                print("\033[2J\033[H")
                
                status = await self.get_system_status()
                print(self.format_status(status))
                
                print(f"Refreshing in {refresh_interval} seconds... (Ctrl+C to exit)")
                await asyncio.sleep(refresh_interval)
                
        except KeyboardInterrupt:
            print("\nDashboard stopped.")

if __name__ == '__main__':
    dashboard = MonitoringDashboard()
    asyncio.run(dashboard.run_dashboard())
EOF

chmod +x ~/phoenix-scraper/scripts/monitoring_dashboard.py
```

## Final Deployment Checklist

### Pre-Deployment Checklist

- [ ] Server provisioned and configured
- [ ] Firewall configured and tested
- [ ] SSL certificates installed (if using HTTPS)
- [ ] MongoDB Atlas cluster created and configured
- [ ] Environment variables configured in `.env.production`
- [ ] Secrets properly secured and encrypted
- [ ] Application dependencies installed
- [ ] Database connection tested
- [ ] Configuration validation passed
- [ ] All services configured in systemd
- [ ] Log rotation configured
- [ ] Monitoring and alerting configured
- [ ] Backup procedures tested
- [ ] Performance optimization applied

### Post-Deployment Checklist

- [ ] Application service started successfully
- [ ] Health checks passing
- [ ] Database connectivity confirmed
- [ ] Metrics collection working
- [ ] Log files being generated
- [ ] Backup schedule working
- [ ] All monitoring alerts configured
- [ ] Performance within expected parameters
- [ ] Security audit completed
- [ ] Documentation updated
- [ ] Team notified of deployment completion

## Support and Maintenance

### Emergency Procedures

**Critical Issues (Production Down)**
1. Check service status: `sudo systemctl status phoenix-scraper`
2. Review recent logs: `sudo journalctl -u phoenix-scraper --since "10 minutes ago"`
3. Try service restart: `sudo systemctl restart phoenix-scraper`
4. If restart fails, check configuration: `python -m phoenix_real_estate.foundation.config.environment validate`
5. Check database connectivity: `~/phoenix-scraper/scripts/db_health_check.py`
6. If database issues, check MongoDB Atlas dashboard
7. Contact support team with logs and error messages

**Performance Issues**
1. Run performance monitor: `~/phoenix-scraper/scripts/performance_monitor.py`
2. Check system resources: `htop` and `df -h`
3. Review application logs for errors
4. Consider restarting services if memory/CPU usage high
5. Analyze database performance: `~/phoenix-scraper/scripts/optimize_database.py analyze`

### Maintenance Windows

**Recommended Schedule:**
- **Daily**: Automated backup and log rotation (2:00 AM)
- **Weekly**: Performance analysis and security audit (Sunday 2:00 AM)
- **Monthly**: Application updates and dependency updates (First Sunday 3:00 AM)
- **Quarterly**: Full disaster recovery test and configuration review

### Contact Information

For technical support and maintenance:
- **Application Team**: dev@yourcompany.com
- **DevOps Team**: ops@yourcompany.com  
- **Database Team**: dba@yourcompany.com
- **Emergency Escalation**: +1-555-PHOENIX

---

**Document Version**: 1.0  
**Last Updated**: 2025-01-21  
**Next Review**: 2025-04-21