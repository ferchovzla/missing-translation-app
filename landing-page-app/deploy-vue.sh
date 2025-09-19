#!/bin/bash

# 🚀 TransQA Vue.js Deployment Script
# Deploys the modern Vue.js + FastAPI stack

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Functions
error() { echo -e "${RED}❌ $1${NC}"; }
success() { echo -e "${GREEN}✅ $1${NC}"; }
info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
warn() { echo -e "${YELLOW}⚠️  $1${NC}"; }

DOMAIN=${1:-"localhost"}
SSL_EMAIL=${2:-"admin@$DOMAIN"}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🚀 TransQA Vue.js Deployment"
echo "============================"
info "Domain: $DOMAIN"
info "SSL Email: $SSL_EMAIL"
info "Directory: $SCRIPT_DIR"
echo ""

cd "$SCRIPT_DIR"

# Check for required tools
if ! command -v docker &> /dev/null; then
    error "Docker is required but not installed"
    info "Install Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    error "Docker Compose is required but not installed"
    info "Install Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi

if ! command -v node &> /dev/null; then
    warn "Node.js not found. Vue.js frontend will be built inside Docker."
    warn "For faster development, install Node.js 18+: https://nodejs.org/"
fi

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    info "Creating .env file from template..."
    cp env.example .env
    
    # Update domain in .env
    if [[ "$DOMAIN" != "localhost" ]]; then
        sed -i.bak "s/DOMAIN=localhost/DOMAIN=$DOMAIN/" .env
        rm -f .env.bak
    fi
    
    # Update SSL email if provided
    if [[ "$SSL_EMAIL" != "admin@$DOMAIN" && "$2" != "" ]]; then
        echo "SSL_EMAIL=$SSL_EMAIL" >> .env
    fi
    
    success ".env file created"
else
    info ".env file already exists"
fi

# Build Vue.js frontend locally if Node.js is available
if command -v node &> /dev/null && [ -d "vue-frontend" ]; then
    info "Building Vue.js frontend locally..."
    cd vue-frontend
    
    # Check if node_modules exists
    if [ ! -d "node_modules" ]; then
        info "Installing Node.js dependencies..."
        npm install
    fi
    
    info "Building Vue.js for production..."
    npm run build
    
    success "Vue.js frontend built successfully"
    cd ..
else
    info "Vue.js will be built inside Docker container"
fi

# Stop any existing services
info "Stopping existing services..."
docker-compose -f docker-compose.vue.yml down --remove-orphans 2>/dev/null || true

# Build and start services
info "Building and starting Vue.js + FastAPI stack..."
docker-compose -f docker-compose.vue.yml up -d --build

# Wait for services
info "Waiting for services to be ready..."
sleep 15

# Health checks
success_count=0
total_checks=3

# Check TransQA Vue API
if timeout 30 bash -c 'until curl -sf http://localhost:8000/health; do sleep 2; done' 2>/dev/null; then
    success "TransQA Vue.js App is ready"
    ((success_count++))
else
    error "TransQA Vue.js App failed to start"
fi

# Check LanguageTool
if timeout 60 bash -c 'until curl -sf http://localhost:8081/v2/languages; do sleep 5; done' 2>/dev/null; then
    success "LanguageTool is ready"
    ((success_count++))
else
    warn "LanguageTool is still starting (this is normal)"
fi

# Check Nginx
if timeout 30 bash -c 'until curl -sf http://localhost/health; do sleep 2; done' 2>/dev/null; then
    success "Nginx proxy is ready"
    ((success_count++))
else
    error "Nginx proxy failed to start"
fi

echo ""
echo "🎉 Vue.js Deployment Summary"
echo "============================"
success "Services started: $success_count/$total_checks"

if [[ "$DOMAIN" == "localhost" ]]; then
    echo ""
    info "🌐 Your Modern TransQA Vue.js App is available at:"
    echo "   📍 http://localhost (Vue.js SPA)"
    echo "   📍 http://localhost/docs (API Documentation)" 
    echo "   📍 http://localhost/redoc (API Reference)"
else
    echo ""
    info "🌐 Your TransQA Vue.js App should be available at:"
    echo "   📍 http://$DOMAIN (Vue.js SPA)"
    echo "   📍 http://$DOMAIN/docs (API Documentation)"
    echo "   📍 http://$DOMAIN/redoc (API Reference)"
    
    if [[ "$2" != "" ]]; then
        echo ""
        warn "🔒 To enable HTTPS with SSL certificate:"
        echo "   1. Make sure $DOMAIN points to this server"
        echo "   2. Run: ./setup-ssl.sh $DOMAIN $SSL_EMAIL"
    fi
fi

echo ""
info "📊 Management Commands:"
echo "   View logs:    docker-compose -f docker-compose.vue.yml logs -f"
echo "   Stop:         docker-compose -f docker-compose.vue.yml down"  
echo "   Restart:      docker-compose -f docker-compose.vue.yml restart"
echo "   Update:       docker-compose -f docker-compose.vue.yml up -d --build"

echo ""
info "🔧 Development Commands:"
echo "   Vue.js dev:   cd vue-frontend && npm run dev"
echo "   Vue.js build: cd vue-frontend && npm run build"
echo "   API only:     docker-compose -f docker-compose.vue.yml up -d transqa-vue languagetool"

if [ $success_count -lt $total_checks ]; then
    echo ""
    warn "Some services may still be starting. Check logs if issues persist:"
    echo "   docker-compose -f docker-compose.vue.yml logs"
else
    echo ""
    success "🎊 Modern Vue.js stack is operational!"
fi

echo ""

