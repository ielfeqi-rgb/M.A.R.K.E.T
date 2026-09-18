#!/usr/bin/env bash
# ==============================================================================
# 🚢 M.A.R.K.E.T AI - VPS & Production Automated Deployment Script
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=================================================================="
echo "🚢 [M.A.R.K.E.T AI] Automated Production Deployer"
echo "=================================================================="

# Check if running as root
if [ "$EUID" -ne 0 ]; then
  echo "⚠️ Note: For systemd or firewall installation, root/sudo permissions may be required."
fi

# 1. Check Docker vs Systemd
if command -v docker &> /dev/null && command -v docker-compose &> /dev/null; then
    echo "🐳 Docker & Docker-Compose detected."
    read -p "Do you want to deploy via Docker Compose? (y/n) [default: y]: " USE_DOCKER
    USE_DOCKER=${USE_DOCKER:-y}
    if [[ "$USE_DOCKER" =~ ^[Yy]$ ]]; then
        echo "🚀 Building and starting containers in background..."
        if [ ! -f ".env" ]; then
            cp .env.example .env
            echo "💡 Generated .env from .env.example. Update keys before live traffic."
        fi
        docker-compose down || true
        docker-compose build --pull
        docker-compose up -d
        echo "✅ Deployment successful via Docker!"
        echo "📊 Core Backend:     http://localhost:8000"
        echo "💬 WhatsApp Gateway: http://localhost:2785"
        exit 0
    fi
fi

# 2. Native Systemd Deployment
echo "⚙️ Setting up Native Systemd Service deployment..."

TARGET_DIR="/var/www/market-ai"
if [ "$SCRIPT_DIR" != "$TARGET_DIR" ]; then
    echo "📁 Syncing files to $TARGET_DIR..."
    mkdir -p "$TARGET_DIR"
    rsync -av --exclude 'venv' --exclude '__pycache__' --exclude '.git' "$SCRIPT_DIR/" "$TARGET_DIR/"
    cd "$TARGET_DIR"
fi

if [ ! -f ".env" ]; then
    cp .env.example .env
fi

if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q

if [ -f "market-ai.service" ]; then
    echo "🔧 Installing systemd service..."
    cp market-ai.service /etc/systemd/system/market-ai.service
    systemctl daemon-reload
    systemctl enable market-ai
    systemctl restart market-ai
    echo "✅ Systemd service 'market-ai' is active and running!"
    systemctl status market-ai --no-pager
fi

echo "=================================================================="
echo "🎉 [M.A.R.K.E.T AI] Deployment Complete!"
echo "=================================================================="
