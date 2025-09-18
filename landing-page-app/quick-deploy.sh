#!/bin/bash

# 🚀 TransQA Quick Deployment Script
# Complete automated deployment for Ubuntu/Debian

set -e

DOMAIN=${1:-""}
WEBSERVER=${2:-"nginx"}
EMAIL=${3:-"admin@$DOMAIN"}
REPO_URL=${4:-"https://github.com/your-username/missing-translation-app.git"}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions for colored output
error() { echo -e "${RED}❌ $1${NC}"; }
success() { echo -e "${GREEN}✅ $1${NC}"; }
info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
warn() { echo -e "${YELLOW}⚠️  $1${NC}"; }

# Usage and validation
show_usage() {
    echo "🚀 TransQA Quick Deployment Script"
    echo ""
    echo "Usage: $0 <domain> [webserver] [email] [repo_url]"
    echo ""
    echo "Parameters:"
    echo "  domain     - Your domain (e.g., transqa.mysite.com) [REQUIRED]"
    echo "  webserver  - Web server: 'nginx' or 'apache' [default: nginx]"
    echo "  email      - Email for SSL certificate [default: admin@domain]"
    echo "  repo_url   - Git repository URL [default: GitHub repo]"
    echo ""
    echo "Examples:"
    echo "  $0 transqa.mysite.com"
    echo "  $0 transqa.mysite.com apache admin@mysite.com"
    echo "  $0 transqa.mysite.com nginx ssl@mysite.com https://github.com/myuser/transqa.git"
    echo ""
    echo "Prerequisites:"
    echo "  - Ubuntu 20.04+ or Debian 11+"
    echo "  - Root access (run with sudo)"
    echo "  - Domain pointing to this server"
    echo "  - Ports 80 and 443 open"
}

if [ -z "$DOMAIN" ]; then
    show_usage
    exit 1
fi

if [[ $EUID -ne 0 ]]; then
   error "This script must be run as root (use sudo)"
   exit 1
fi

# Validate domain format
if [[ ! "$DOMAIN" =~ ^[a-zA-Z0-9][a-zA-Z0-9-]*[a-zA-Z0-9]*\.[a-zA-Z]{2,}$ ]]; then
    error "Invalid domain format: $DOMAIN"
    info "Example: transqa.mysite.com"
    exit 1
fi

# Validate web server
if [[ "$WEBSERVER" != "nginx" && "$WEBSERVER" != "apache" ]]; then
    error "Unsupported web server: $WEBSERVER"
    info "Supported: nginx, apache"
    exit 1
fi

# Set default email if not provided
if [[ "$EMAIL" == "admin@$DOMAIN" && "$3" == "" ]]; then
    EMAIL="admin@$DOMAIN"
fi

# Display configuration
echo "🚀 TransQA Quick Deployment Starting..."
echo "=================================="
info "Domain: $DOMAIN"
info "Web Server: $WEBSERVER"
info "Email: $EMAIL"
info "Repository: $REPO_URL"
echo ""

# Confirmation prompt
read -p "Continue with deployment? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    warn "Deployment cancelled"
    exit 0
fi

# Start deployment
START_TIME=$(date +%s)

# Step 1: System preparation
echo ""
info "📦 Step 1/7: System preparation..."
apt update >/dev/null 2>&1
apt upgrade -y >/dev/null 2>&1
apt install -y curl wget git unzip htop ufw fail2ban >/dev/null 2>&1
success "System updated and dependencies installed"

# Step 2: Install Docker
echo ""
info "🐳 Step 2/7: Installing Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh >/dev/null 2>&1
    sh get-docker.sh >/dev/null 2>&1
    rm get-docker.sh
    success "Docker installed"
else
    success "Docker already installed"
fi

if ! command -v docker-compose &> /dev/null; then
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose >/dev/null 2>&1
    chmod +x /usr/local/bin/docker-compose
    success "Docker Compose installed"
else
    success "Docker Compose already installed"
fi

# Step 3: Clone project
echo ""
info "📂 Step 3/7: Cloning project..."
# Create service user
id -u transqa &>/dev/null || useradd -r -s /bin/false transqa

# Setup directories
mkdir -p /opt/transqa
mkdir -p /var/log/transqa
chown -R transqa:transqa /opt/transqa
chown -R transqa:transqa /var/log/transqa

# Clone or update project
if [ -d "/opt/transqa/.git" ]; then
    cd /opt/transqa
    git pull origin main >/dev/null 2>&1
    success "Project updated"
else
    git clone $REPO_URL /opt/transqa >/dev/null 2>&1
    success "Project cloned"
fi

cd /opt/transqa/landing-page-app
chmod +x *.sh
success "Project setup completed"

# Step 4: Install and configure web server
echo ""
info "🌐 Step 4/7: Installing $WEBSERVER..."
if [[ "$WEBSERVER" == "nginx" ]]; then
    if ! command -v nginx &> /dev/null; then
        apt install -y nginx >/dev/null 2>&1
        systemctl enable nginx >/dev/null 2>&1
        success "Nginx installed"
    else
        success "Nginx already installed"
    fi
elif [[ "$WEBSERVER" == "apache" ]]; then
    if ! command -v apache2 &> /dev/null; then
        apt install -y apache2 >/dev/null 2>&1
        a2enmod proxy proxy_http proxy_balancer lbmethod_byrequests >/dev/null 2>&1
        a2enmod rewrite ssl headers expires deflate >/dev/null 2>&1
        systemctl enable apache2 >/dev/null 2>&1
        success "Apache installed and modules enabled"
    else
        success "Apache already installed"
    fi
fi

# Step 5: Configure web server
echo ""
info "⚙️ Step 5/7: Configuring $WEBSERVER..."
if [[ "$WEBSERVER" == "nginx" ]]; then
    ./configure-nginx.sh $DOMAIN >/dev/null 2>&1
    success "Nginx configured for TransQA"
else
    ./configure-apache.sh $DOMAIN >/dev/null 2>&1
    success "Apache configured for TransQA"
fi

# Step 6: Configure firewall
echo ""
info "🛡️ Step 6/7: Configuring firewall..."
ufw --force enable >/dev/null 2>&1
ufw allow ssh >/dev/null 2>&1
ufw allow 80/tcp >/dev/null 2>&1
ufw allow 443/tcp >/dev/null 2>&1
success "Firewall configured"

# Step 7: Start services
echo ""
info "🐳 Step 7/7: Starting Docker services..."
docker-compose -f docker-compose.prod.yml up -d --build >/dev/null 2>&1
success "Docker services started"

# Wait for services to be ready
info "⏳ Waiting for services to be ready..."
for i in {1..30}; do
    if curl -s -f http://localhost:8000/health >/dev/null 2>&1; then
        success "TransQA API is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        warn "TransQA API is taking longer than expected to start"
    fi
    sleep 2
done

# Step 8: Install Certbot and setup SSL
echo ""
info "🔐 Setting up SSL certificate..."
apt install -y certbot >/dev/null 2>&1
if [[ "$WEBSERVER" == "nginx" ]]; then
    apt install -y python3-certbot-nginx >/dev/null 2>&1
elif [[ "$WEBSERVER" == "apache" ]]; then
    apt install -y python3-certbot-apache >/dev/null 2>&1
fi

# Check if domain resolves to this server
DOMAIN_IP=$(dig +short $DOMAIN 2>/dev/null)
SERVER_IP=$(curl -s https://ipv4.icanhazip.com/ 2>/dev/null)

if [[ -n "$DOMAIN_IP" && "$DOMAIN_IP" == "$SERVER_IP" ]]; then
    info "Domain resolution is correct, setting up SSL..."
    if [[ "$WEBSERVER" == "nginx" ]]; then
        certbot --nginx -d $DOMAIN --non-interactive --agree-tos --email $EMAIL --redirect >/dev/null 2>&1
    else
        certbot --apache -d $DOMAIN --non-interactive --agree-tos --email $EMAIL --redirect >/dev/null 2>&1
    fi
    
    if [ $? -eq 0 ]; then
        success "SSL certificate installed successfully"
        
        # Setup auto-renewal
        (crontab -l 2>/dev/null; echo "0 12 * * * /usr/bin/certbot renew --quiet") | crontab -
        success "Auto-renewal configured"
    else
        warn "SSL certificate installation failed, but HTTP is working"
        info "You can setup SSL later with: sudo ./setup-ssl.sh $DOMAIN $EMAIL $WEBSERVER"
    fi
else
    warn "Domain doesn't resolve to this server or DNS not ready"
    info "Please configure DNS A record for $DOMAIN to point to $SERVER_IP"
    info "Then run: sudo ./setup-ssl.sh $DOMAIN $EMAIL $WEBSERVER"
fi

# Calculate deployment time
END_TIME=$(date +%s)
DEPLOY_TIME=$((END_TIME - START_TIME))

# Final status check
echo ""
echo "🧪 Running final tests..."
TESTS_PASSED=0
TOTAL_TESTS=4

# Test 1: Health endpoint
if curl -s -f http://localhost:8000/health >/dev/null 2>&1; then
    success "✅ TransQA API health check"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    error "❌ TransQA API health check"
fi

# Test 2: LanguageTool
if curl -s -f http://localhost:8081/v2/languages >/dev/null 2>&1; then
    success "✅ LanguageTool service"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    error "❌ LanguageTool service"
fi

# Test 3: Web server
if curl -s -f http://$DOMAIN/health >/dev/null 2>&1; then
    success "✅ Web server proxy"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    error "❌ Web server proxy"
fi

# Test 4: SSL (if configured)
if curl -s -f https://$DOMAIN/health >/dev/null 2>&1; then
    success "✅ HTTPS access"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    warn "⚠️  HTTPS not available (check SSL setup)"
fi

# Final summary
echo ""
echo "🎉 =================================="
echo "    TransQA Deployment Complete!"
echo "===================================="
echo ""
success "Deployment completed in ${DEPLOY_TIME} seconds"
success "Tests passed: ${TESTS_PASSED}/${TOTAL_TESTS}"
echo ""
echo "🌐 Your TransQA site is now available at:"
if curl -s -f https://$DOMAIN/health >/dev/null 2>&1; then
    echo "   🔒 https://$DOMAIN (Secure)"
    echo "   🔒 https://$DOMAIN/docs (API Documentation)"
    echo "   🔒 https://$DOMAIN/redoc (API Reference)"
else
    echo "   🌐 http://$DOMAIN"
    echo "   🌐 http://$DOMAIN/docs (API Documentation)"
    echo "   🌐 http://$DOMAIN/redoc (API Reference)"
    warn "SSL is not configured. Run: sudo ./setup-ssl.sh $DOMAIN $EMAIL $WEBSERVER"
fi
echo ""
echo "📊 Monitoring and management:"
echo "   sudo bash /opt/transqa/landing-page-app/monitor-transqa.sh $DOMAIN status"
echo "   sudo bash /opt/transqa/landing-page-app/monitor-transqa.sh $DOMAIN logs"
echo "   sudo bash /opt/transqa/landing-page-app/monitor-transqa.sh $DOMAIN restart"
echo ""
echo "📂 Project location: /opt/transqa"
echo "📋 Full documentation: /opt/transqa/landing-page-app/DEPLOYMENT-GUIDE.md"
echo ""
if [ $TESTS_PASSED -lt $TOTAL_TESTS ]; then
    warn "Some tests failed. Check the logs and troubleshooting guide."
    echo "   View logs: sudo docker-compose -f /opt/transqa/landing-page-app/docker-compose.prod.yml logs"
else
    success "All systems operational! 🚀"
fi
echo ""
