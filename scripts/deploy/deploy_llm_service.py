#!/usr/bin/env python3
"""
Deploy LLM Processing Service for Production

This script sets up the LLM processing service for production deployment,
including Ollama configuration, systemd service creation, and health checks.
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict

import yaml


class LLMServiceDeployer:
    """Handles deployment of the LLM processing service."""

    def __init__(self, config_path: str = "config/llm-production.yaml"):
        """Initialize deployer with configuration."""
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.service_name = "phoenix-llm-processor"
        self.ollama_service = "ollama"

    def _load_config(self) -> Dict:
        """Load production configuration."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")

        with open(self.config_path, "r") as f:
            return yaml.safe_load(f)

    def check_prerequisites(self) -> bool:
        """Check if all prerequisites are met."""
        print("Checking prerequisites...")

        # Check if running as root (for systemd operations)
        if os.geteuid() != 0:
            print("❌ This script must be run as root for systemd operations")
            return False

        # Check Python version
        if sys.version_info < (3, 13):
            print("❌ Python 3.13+ is required")
            return False

        # Check if Ollama is installed
        if not shutil.which("ollama"):
            print("❌ Ollama is not installed. Please install Ollama first.")
            print("   Visit: https://ollama.ai/download")
            return False

        # Check if MongoDB is running
        try:
            result = subprocess.run(
                ["systemctl", "is-active", "mongodb"], capture_output=True, text=True
            )
            if result.stdout.strip() != "active":
                print("❌ MongoDB is not running")
                return False
        except Exception:
            print("⚠️  Could not check MongoDB status")

        print("✅ All prerequisites met")
        return True

    def setup_ollama_service(self) -> bool:
        """Setup and configure Ollama service."""
        print("\nSetting up Ollama service...")

        # Check if Ollama service exists
        result = subprocess.run(
            ["systemctl", "list-unit-files", self.ollama_service + ".service"],
            capture_output=True,
            text=True,
        )

        if self.ollama_service not in result.stdout:
            print(f"Creating {self.ollama_service} systemd service...")

            service_content = """[Unit]
Description=Ollama Model Server
Documentation=https://ollama.ai
After=network-online.target

[Service]
Type=simple
User=ollama
Group=ollama
ExecStart=/usr/local/bin/ollama serve
Restart=always
RestartSec=3
Environment="OLLAMA_HOST=0.0.0.0:11434"
Environment="OLLAMA_MODELS=/var/lib/ollama/models"
Environment="OLLAMA_NUM_PARALLEL=2"
Environment="OLLAMA_MAX_LOADED_MODELS=1"

# Resource limits
LimitNOFILE=65536
LimitMEMLOCK=infinity

# Security
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/lib/ollama

[Install]
WantedBy=multi-user.target
"""

            # Create ollama user if not exists
            subprocess.run(
                ["useradd", "-r", "-s", "/bin/false", "-m", "-d", "/var/lib/ollama", "ollama"],
                capture_output=True,
            )

            # Write service file
            service_path = f"/etc/systemd/system/{self.ollama_service}.service"
            with open(service_path, "w") as f:
                f.write(service_content)

            # Create necessary directories
            subprocess.run(["mkdir", "-p", "/var/lib/ollama/models"], capture_output=True)
            subprocess.run(["chown", "-R", "ollama:ollama", "/var/lib/ollama"], capture_output=True)

            # Reload systemd
            subprocess.run(["systemctl", "daemon-reload"])

        # Enable and start Ollama service
        subprocess.run(["systemctl", "enable", self.ollama_service])
        subprocess.run(["systemctl", "start", self.ollama_service])

        # Wait for service to be ready
        print("Waiting for Ollama to start...")
        import time

        time.sleep(5)

        # Pull the required model
        model = self.config["ollama"]["model"]
        print(f"Pulling {model} model...")
        result = subprocess.run(["ollama", "pull", model], capture_output=True, text=True)

        if result.returncode != 0:
            print(f"❌ Failed to pull model: {result.stderr}")
            return False

        print("✅ Ollama service configured successfully")
        return True

    def create_app_directories(self) -> bool:
        """Create necessary application directories."""
        print("\nCreating application directories...")

        directories = [
            "/var/log/phoenix_real_estate",
            "/var/lib/phoenix_real_estate",
            "/etc/phoenix_real_estate",
            "/tmp/phoenix_llm",
        ]

        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)

        # Set permissions
        subprocess.run(["chown", "-R", "phoenix:phoenix", "/var/log/phoenix_real_estate"])
        subprocess.run(["chown", "-R", "phoenix:phoenix", "/var/lib/phoenix_real_estate"])
        subprocess.run(["chown", "-R", "phoenix:phoenix", "/tmp/phoenix_llm"])

        print("✅ Application directories created")
        return True

    def create_systemd_service(self) -> bool:
        """Create systemd service for LLM processor."""
        print(f"\nCreating {self.service_name} systemd service...")

        # Get the project root directory
        project_root = Path(__file__).parent.parent.parent.absolute()

        service_content = f"""[Unit]
Description=Phoenix Real Estate LLM Processing Service
Documentation=https://github.com/phoenix-real-estate/collector
After=network-online.target mongodb.service {self.ollama_service}.service
Wants=network-online.target
Requires=mongodb.service {self.ollama_service}.service

[Service]
Type=simple
User=phoenix
Group=phoenix
WorkingDirectory={project_root}

# Python virtual environment
Environment="PATH={project_root}/.venv/bin:/usr/local/bin:/usr/bin:/bin"
Environment="PYTHONPATH={project_root}/src"
Environment="PHOENIX_ENV=production"

# LLM specific environment
Environment="OLLAMA_HOST=http://localhost:11434"
Environment="LLM_MODEL=llama3.2:latest"
Environment="LLM_BATCH_SIZE=10"
Environment="LLM_MAX_WORKERS=2"

# Start command
ExecStart={project_root}/.venv/bin/python -m phoenix_real_estate.collectors.processing.service

# Restart configuration
Restart=always
RestartSec=5
StartLimitInterval=600
StartLimitBurst=5

# Resource limits
LimitNOFILE=65536
MemoryLimit=3G
CPUQuota=200%

# Timeouts
TimeoutStartSec=300
TimeoutStopSec=30

# Security
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/log/phoenix_real_estate /var/lib/phoenix_real_estate /tmp/phoenix_llm

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier={self.service_name}

[Install]
WantedBy=multi-user.target
"""

        # Write service file
        service_path = f"/etc/systemd/system/{self.service_name}.service"
        with open(service_path, "w") as f:
            f.write(service_content)

        # Reload systemd
        subprocess.run(["systemctl", "daemon-reload"])

        print(f"✅ {self.service_name} service created")
        return True

    def setup_monitoring(self) -> bool:
        """Setup monitoring and alerting."""
        print("\nSetting up monitoring...")

        # Create Prometheus scrape config
        prometheus_config = """
# Phoenix LLM Processor metrics
- job_name: 'phoenix_llm_processor'
  static_configs:
    - targets: ['localhost:9090']
  scrape_interval: 30s
  scrape_timeout: 10s
"""

        # Append to existing Prometheus config if exists
        prometheus_path = Path("/etc/prometheus/prometheus.yml")
        if prometheus_path.exists():
            with open(prometheus_path, "a") as f:
                f.write(prometheus_config)

            # Reload Prometheus
            subprocess.run(["systemctl", "reload", "prometheus"], capture_output=True)
            print("✅ Prometheus configuration updated")
        else:
            print("⚠️  Prometheus not found, skipping monitoring setup")

        return True

    def create_health_check_script(self) -> bool:
        """Create health check script."""
        print("\nCreating health check script...")

        script_content = '''#!/usr/bin/env python3
"""Health check script for LLM processing service."""

import sys
import requests
import psutil
from datetime import datetime

def check_ollama():
    """Check if Ollama is responsive."""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        return response.status_code == 200
    except:
        return False

def check_memory():
    """Check memory usage."""
    memory = psutil.virtual_memory()
    return memory.percent < 80

def check_disk():
    """Check disk usage."""
    disk = psutil.disk_usage('/')
    return disk.percent < 90

def check_service():
    """Check if LLM service endpoint is healthy."""
    try:
        response = requests.get("http://localhost:8080/health/llm", timeout=5)
        return response.status_code == 200
    except:
        return False

def main():
    """Run all health checks."""
    checks = {
        "Ollama": check_ollama(),
        "Memory": check_memory(),
        "Disk": check_disk(),
        "Service": check_service(),
    }
    
    all_healthy = all(checks.values())
    
    print(f"Health Check - {datetime.now().isoformat()}")
    for check, status in checks.items():
        status_icon = "✅" if status else "❌"
        print(f"{status_icon} {check}")
    
    sys.exit(0 if all_healthy else 1)

if __name__ == "__main__":
    main()
'''

        script_path = Path("/usr/local/bin/phoenix-llm-health-check")
        with open(script_path, "w") as f:
            f.write(script_content)

        # Make executable
        script_path.chmod(0o755)

        # Create systemd timer for periodic health checks
        timer_content = """[Unit]
Description=Phoenix LLM Health Check Timer
Requires=phoenix-llm-health-check.service

[Timer]
OnBootSec=5min
OnUnitActiveSec=5min
Unit=phoenix-llm-health-check.service

[Install]
WantedBy=timers.target
"""

        service_content = """[Unit]
Description=Phoenix LLM Health Check
After=phoenix-llm-processor.service

[Service]
Type=oneshot
ExecStart=/usr/local/bin/phoenix-llm-health-check
StandardOutput=journal
StandardError=journal
"""

        with open("/etc/systemd/system/phoenix-llm-health-check.timer", "w") as f:
            f.write(timer_content)

        with open("/etc/systemd/system/phoenix-llm-health-check.service", "w") as f:
            f.write(service_content)

        subprocess.run(["systemctl", "daemon-reload"])
        subprocess.run(["systemctl", "enable", "phoenix-llm-health-check.timer"])

        print("✅ Health check script created")
        return True

    def deploy(self, start_services: bool = True) -> bool:
        """Run full deployment."""
        print("Starting LLM Service Deployment...\n")

        # Check prerequisites
        if not self.check_prerequisites():
            return False

        # Create phoenix user if not exists
        subprocess.run(["useradd", "-r", "-s", "/bin/false", "-m", "phoenix"], capture_output=True)

        # Setup components
        steps = [
            ("Setting up Ollama", self.setup_ollama_service),
            ("Creating directories", self.create_app_directories),
            ("Creating systemd service", self.create_systemd_service),
            ("Setting up monitoring", self.setup_monitoring),
            ("Creating health checks", self.create_health_check_script),
        ]

        for step_name, step_func in steps:
            print(f"\n{step_name}...")
            if not step_func():
                print(f"❌ Failed at: {step_name}")
                return False

        if start_services:
            print("\nStarting services...")
            subprocess.run(["systemctl", "enable", self.service_name])
            subprocess.run(["systemctl", "start", self.service_name])
            subprocess.run(["systemctl", "start", "phoenix-llm-health-check.timer"])

            # Check service status
            import time

            time.sleep(3)
            result = subprocess.run(
                ["systemctl", "is-active", self.service_name], capture_output=True, text=True
            )

            if result.stdout.strip() == "active":
                print(f"✅ {self.service_name} is running")
            else:
                print(f"❌ {self.service_name} failed to start")
                subprocess.run(["journalctl", "-u", self.service_name, "-n", "50"])
                return False

        print("\n✅ LLM Service deployment completed successfully!")
        print("\nUseful commands:")
        print(f"  systemctl status {self.service_name}")
        print(f"  journalctl -u {self.service_name} -f")
        print("  /usr/local/bin/phoenix-llm-health-check")

        return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Deploy LLM Processing Service")
    parser.add_argument(
        "--config", default="config/llm-production.yaml", help="Path to configuration file"
    )
    parser.add_argument(
        "--no-start", action="store_true", help="Don't start services after deployment"
    )

    args = parser.parse_args()

    try:
        deployer = LLMServiceDeployer(args.config)
        success = deployer.deploy(start_services=not args.no_start)
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Deployment failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
