#!/bin/bash
# Production Setup Script for Phoenix Real Estate LLM Processing

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT="/opt/phoenix-real-estate"
SERVICE_USER="phoenix"
PYTHON_VERSION="3.13"

echo -e "${GREEN}Phoenix Real Estate LLM Processing - Production Setup${NC}"
echo "=================================================="

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}This script must be run as root${NC}" 
   exit 1
fi

# Function to check command existence
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to create user if not exists
create_user() {
    if ! id "$1" &>/dev/null; then
        echo -e "${YELLOW}Creating user $1...${NC}"
        useradd -r -s /bin/false -m -d "/home/$1" "$1"
    fi
}

# Step 1: Install system dependencies
echo -e "\n${GREEN}Step 1: Installing system dependencies...${NC}"
apt-get update
apt-get install -y \
    python${PYTHON_VERSION} \
    python${PYTHON_VERSION}-venv \
    python${PYTHON_VERSION}-dev \
    build-essential \
    git \
    curl \
    wget \
    postgresql-client \
    redis-tools \
    htop \
    iotop \
    jq

# Step 2: Install uv if not present
if ! command_exists uv; then
    echo -e "\n${GREEN}Step 2: Installing uv...${NC}"
    curl -LsSf https://astral.sh/uv/install.sh | sh
    source $HOME/.cargo/env
else
    echo -e "\n${GREEN}Step 2: uv already installed${NC}"
fi

# Step 3: Create service users
echo -e "\n${GREEN}Step 3: Creating service users...${NC}"
create_user "$SERVICE_USER"
create_user "ollama"

# Step 4: Create directory structure
echo -e "\n${GREEN}Step 4: Creating directory structure...${NC}"
mkdir -p "$PROJECT_ROOT"
mkdir -p /var/log/phoenix_real_estate
mkdir -p /var/lib/phoenix_real_estate
mkdir -p /etc/phoenix_real_estate
mkdir -p /tmp/phoenix_llm
mkdir -p /var/lib/ollama/models

# Set ownership
chown -R "$SERVICE_USER:$SERVICE_USER" "$PROJECT_ROOT"
chown -R "$SERVICE_USER:$SERVICE_USER" /var/log/phoenix_real_estate
chown -R "$SERVICE_USER:$SERVICE_USER" /var/lib/phoenix_real_estate
chown -R "$SERVICE_USER:$SERVICE_USER" /etc/phoenix_real_estate
chown -R "$SERVICE_USER:$SERVICE_USER" /tmp/phoenix_llm
chown -R ollama:ollama /var/lib/ollama

# Step 5: Clone or update repository
echo -e "\n${GREEN}Step 5: Setting up project repository...${NC}"
if [ -d "$PROJECT_ROOT/.git" ]; then
    echo "Repository exists, pulling latest changes..."
    cd "$PROJECT_ROOT"
    sudo -u "$SERVICE_USER" git pull
else
    echo "Cloning repository..."
    sudo -u "$SERVICE_USER" git clone https://github.com/phoenix-real-estate/collector.git "$PROJECT_ROOT"
    cd "$PROJECT_ROOT"
fi

# Step 6: Setup Python environment
echo -e "\n${GREEN}Step 6: Setting up Python environment...${NC}"
cd "$PROJECT_ROOT"
sudo -u "$SERVICE_USER" uv venv
sudo -u "$SERVICE_USER" uv sync --all-extras

# Step 7: Install Ollama
if ! command_exists ollama; then
    echo -e "\n${GREEN}Step 7: Installing Ollama...${NC}"
    curl -fsSL https://ollama.ai/install.sh | sh
else
    echo -e "\n${GREEN}Step 7: Ollama already installed${NC}"
fi

# Step 8: Setup configuration
echo -e "\n${GREEN}Step 8: Setting up configuration...${NC}"
if [ ! -f "/etc/phoenix_real_estate/.env.production" ]; then
    cp "$PROJECT_ROOT/.env.production.template" "/etc/phoenix_real_estate/.env.production"
    echo -e "${YELLOW}Please edit /etc/phoenix_real_estate/.env.production with your API keys${NC}"
fi

# Step 9: Install systemd services
echo -e "\n${GREEN}Step 9: Installing systemd services...${NC}"
cp "$PROJECT_ROOT/scripts/deploy/systemd/ollama.service" /etc/systemd/system/
cp "$PROJECT_ROOT/scripts/deploy/systemd/phoenix-llm-processor.service" /etc/systemd/system/

# Update service file with correct paths
sed -i "s|/opt/phoenix-real-estate|$PROJECT_ROOT|g" /etc/systemd/system/phoenix-llm-processor.service

systemctl daemon-reload

# Step 10: Setup Ollama
echo -e "\n${GREEN}Step 10: Setting up Ollama service...${NC}"
systemctl enable ollama.service
systemctl start ollama.service

# Wait for Ollama to start
sleep 5

# Pull the required model
echo "Pulling llama3.2:latest model (this may take a while)..."
ollama pull llama3.2:latest

# Step 11: Setup log rotation
echo -e "\n${GREEN}Step 11: Setting up log rotation...${NC}"
cat > /etc/logrotate.d/phoenix-real-estate << EOF
/var/log/phoenix_real_estate/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    create 0640 $SERVICE_USER $SERVICE_USER
    sharedscripts
    postrotate
        systemctl reload phoenix-llm-processor >/dev/null 2>&1 || true
    endscript
}
EOF

# Step 12: Setup firewall rules (if ufw is installed)
if command_exists ufw; then
    echo -e "\n${GREEN}Step 12: Setting up firewall rules...${NC}"
    ufw allow 8080/tcp comment "Phoenix LLM Service"
    ufw allow 9090/tcp comment "Prometheus metrics"
fi

# Step 13: Create helper scripts
echo -e "\n${GREEN}Step 13: Creating helper scripts...${NC}"

# Status check script
cat > /usr/local/bin/phoenix-status << 'EOF'
#!/bin/bash
echo "Phoenix Real Estate LLM Service Status"
echo "====================================="
echo
echo "Services:"
systemctl status ollama --no-pager | head -n 5
echo
systemctl status phoenix-llm-processor --no-pager | head -n 5
echo
echo "Health Check:"
curl -s http://localhost:8080/health/llm | jq .
echo
echo "Recent Logs:"
journalctl -u phoenix-llm-processor -n 10 --no-pager
EOF

chmod +x /usr/local/bin/phoenix-status

# Restart script
cat > /usr/local/bin/phoenix-restart << 'EOF'
#!/bin/bash
echo "Restarting Phoenix services..."
systemctl restart ollama
sleep 5
systemctl restart phoenix-llm-processor
sleep 3
phoenix-status
EOF

chmod +x /usr/local/bin/phoenix-restart

# Final message
echo -e "\n${GREEN}Setup completed!${NC}"
echo -e "\n${YELLOW}Next steps:${NC}"
echo "1. Edit /etc/phoenix_real_estate/.env.production with your API keys"
echo "2. Start the service: systemctl start phoenix-llm-processor"
echo "3. Enable auto-start: systemctl enable phoenix-llm-processor"
echo "4. Check status: phoenix-status"
echo "5. View logs: journalctl -u phoenix-llm-processor -f"
echo
echo -e "${GREEN}Useful commands:${NC}"
echo "  phoenix-status    - Check service status"
echo "  phoenix-restart   - Restart all services"
echo "  systemctl status phoenix-llm-processor"
echo "  journalctl -u phoenix-llm-processor -f"