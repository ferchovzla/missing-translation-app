#!/bin/bash

# 🚀 TransQA Production Deployment Script
# Supports Ubuntu/Debian with Apache or Nginx

set -e  # Exit on any error

DOMAIN=${1:-"transqa.local"}
WEBSERVER=${2:-"nginx"}  # nginx or apache
PROJECT_DIR="/opt/transqa"
SERVICE_USER="transqa"

echo "🚀 Starting TransQA Production Deployment"
echo "📍 Domain: $DOMAIN"
echo "🌐 Web Server: $WEBSERVER"
echo "📂 Install Directory: $PROJECT_DIR"

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo "❌ This script must be run as root (use sudo)"
   exit 1
fi

# Update system
echo "📦 Updating system packages..."
apt update && apt upgrade -y

# Install basic dependencies
echo "🔧 Installing basic dependencies..."
apt install -y curl wget git unzip htop ufw fail2ban

# Install Docker and Docker Compose
if ! command -v docker &> /dev/null; then
    echo "🐳 Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    usermod -aG docker $SERVICE_USER 2>/dev/null || true
fi

if ! command -v docker-compose &> /dev/null; then
    echo "🐙 Installing Docker Compose..."
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
fi

# Create service user
echo "👤 Creating service user..."
id -u $SERVICE_USER &>/dev/null || useradd -r -s /bin/false $SERVICE_USER

# Create project directory
echo "📂 Setting up project directory..."
mkdir -p $PROJECT_DIR
mkdir -p /var/log/transqa
chown -R $SERVICE_USER:$SERVICE_USER $PROJECT_DIR
chown -R $SERVICE_USER:$SERVICE_USER /var/log/transqa

# Install and configure web server
if [[ "$WEBSERVER" == "nginx" ]]; then
    echo "🔵 Installing and configuring Nginx..."
    apt install -y nginx
    systemctl enable nginx
elif [[ "$WEBSERVER" == "apache" ]]; then
    echo "🔴 Installing and configuring Apache..."
    apt install -y apache2
    a2enmod proxy proxy_http rewrite ssl headers
    systemctl enable apache2
else
    echo "❌ Unsupported web server: $WEBSERVER"
    exit 1
fi

# Install Certbot for SSL
echo "🔐 Installing Certbot for SSL..."
apt install -y certbot
if [[ "$WEBSERVER" == "nginx" ]]; then
    apt install -y python3-certbot-nginx
elif [[ "$WEBSERVER" == "apache" ]]; then
    apt install -y python3-certbot-apache
fi

# Configure firewall
echo "🛡️ Configuring firewall..."
ufw --force enable
ufw allow ssh
ufw allow 80/tcp
ufw allow 443/tcp

echo ""
echo "✅ Base system setup completed!"
echo ""
echo "📋 Next steps:"
echo "1. Clone your TransQA repository to $PROJECT_DIR"
echo "2. Run the appropriate configuration script:"
echo "   - For Nginx: sudo bash configure-nginx.sh $DOMAIN"
echo "   - For Apache: sudo bash configure-apache.sh $DOMAIN"
echo "3. Deploy with: cd $PROJECT_DIR/landing-page-app && docker-compose -f docker-compose.prod.yml up -d"
echo "4. Setup SSL: sudo certbot --${WEBSERVER} -d $DOMAIN"
echo ""
echo "🎉 Ready for deployment!"
