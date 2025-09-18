#!/bin/bash

# 🚀 TransQA Simple Deployment - One-Click Deploy
# Usage: ./deploy-simple.sh [domain] [ssl-email]

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

echo "🚀 TransQA Simple Deployment"
echo "============================"
info "Domain: $DOMAIN"
info "SSL Email: $SSL_EMAIL"
info "Directory: $SCRIPT_DIR"
echo ""

cd "$SCRIPT_DIR"

# Check for Docker
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

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    info "Creating .env file from template..."
    cp env.example .env
    
    # Update domain in .env
    if [[ "$DOMAIN" != "localhost" ]]; then
        sed -i.bak "s/DOMAIN=localhost/DOMAIN=$DOMAIN/" .env
        rm -f .env.bak
    fi
    
    # Update SSL email if provided and not default
    if [[ "$SSL_EMAIL" != "admin@$DOMAIN" && "$2" != "" ]]; then
        echo "SSL_EMAIL=$SSL_EMAIL" >> .env
    fi
    
    success ".env file created"
else
    info ".env file already exists, skipping creation"
fi

# Stop any existing services
info "Stopping existing services..."
docker-compose -f docker-compose.unified.yml down --remove-orphans 2>/dev/null || true

# Build and start services
info "Building and starting services..."
docker-compose -f docker-compose.unified.yml up -d --build

# Wait for services
info "Waiting for services to be ready..."
sleep 10

# Health checks
success_count=0
total_checks=3

# Check TransQA API
if timeout 30 bash -c 'until curl -sf http://localhost:8000/health; do sleep 2; done' 2>/dev/null; then
    success "TransQA API is ready"
    ((success_count++))
else
    error "TransQA API failed to start"
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
echo "🎉 Deployment Summary"
echo "===================="
success "Services started: $success_count/$total_checks"

if [[ "$DOMAIN" == "localhost" ]]; then
    echo ""
    info "🌐 Your TransQA site is available at:"
    echo "   📍 http://localhost"
    echo "   📍 http://localhost/docs (API Documentation)"
    echo "   📍 http://localhost/redoc (API Reference)"
else
    echo ""
    info "🌐 Your TransQA site should be available at:"
    echo "   📍 http://$DOMAIN"
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
echo "   View logs:    docker-compose -f docker-compose.unified.yml logs -f"
echo "   Stop:         docker-compose -f docker-compose.unified.yml down"  
echo "   Restart:      docker-compose -f docker-compose.unified.yml restart"
echo "   Update:       docker-compose -f docker-compose.unified.yml up -d --build"

if [ $success_count -lt $total_checks ]; then
    echo ""
    warn "Some services may still be starting. Check logs if issues persist:"
    echo "   docker-compose -f docker-compose.unified.yml logs"
else
    echo ""
    success "🎊 All systems operational!"
fi

echo ""
