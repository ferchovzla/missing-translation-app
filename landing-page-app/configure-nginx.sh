#!/bin/bash

# 🔵 Nginx Configuration Script for TransQA
DOMAIN=${1:-"transqa.local"}
PROJECT_DIR="/opt/transqa"

if [[ $EUID -ne 0 ]]; then
   echo "❌ This script must be run as root"
   exit 1
fi

echo "🔵 Configuring Nginx for TransQA"
echo "📍 Domain: $DOMAIN"

# Create Nginx configuration
cat > /etc/nginx/sites-available/transqa << EOF
# TransQA Landing Page Configuration
upstream transqa_backend {
    server 127.0.0.1:8000;
    keepalive 32;
}

upstream languagetool_backend {
    server 127.0.0.1:8081;
    keepalive 8;
}

# Rate limiting
limit_req_zone \$binary_remote_addr zone=api:10m rate=10r/s;
limit_req_zone \$binary_remote_addr zone=static:10m rate=50r/s;

server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    add_header Content-Security-Policy "default-src 'self' http: https: data: blob: 'unsafe-inline'" always;

    # Logging
    access_log /var/log/nginx/transqa_access.log;
    error_log /var/log/nginx/transqa_error.log warn;

    # Root and index
    root $PROJECT_DIR/landing-page-app;
    index index.html;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types
        text/plain
        text/css
        text/xml
        text/javascript
        application/json
        application/javascript
        application/xml+rss
        application/atom+xml
        image/svg+xml;

    # Static files with long caching
    location /static/ {
        alias $PROJECT_DIR/landing-page-app/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
        add_header Vary "Accept-Encoding";
        
        # Rate limiting for static files
        limit_req zone=static burst=100 nodelay;
        
        # Security for static files
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|webp|woff|woff2|ttf|eot)$ {
            add_header Cache-Control "public, max-age=31536000, immutable";
        }
    }

    # API endpoints with rate limiting
    location /api/ {
        limit_req zone=api burst=20 nodelay;
        
        proxy_pass http://transqa_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 300s;  # Análisis puede tomar tiempo
        
        # Buffer settings
        proxy_buffering on;
        proxy_buffer_size 128k;
        proxy_buffers 4 256k;
        proxy_busy_buffers_size 256k;
    }

    # Health check (no rate limiting)
    location /health {
        proxy_pass http://transqa_backend;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        access_log off;
    }

    # Documentation endpoints
    location ~ ^/(docs|redoc|openapi.json)$ {
        limit_req zone=api burst=50 nodelay;
        
        proxy_pass http://transqa_backend;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    # LanguageTool proxy (internal use)
    location /languagetool/ {
        internal;
        proxy_pass http://languagetool_backend/;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 60s;
    }

    # Main application
    location / {
        # Try static files first, then proxy to app
        try_files \$uri @transqa_app;
    }

    location @transqa_app {
        proxy_pass http://transqa_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Security: Block access to sensitive files
    location ~ /\. {
        deny all;
        access_log off;
        log_not_found off;
    }

    location ~* \.(env|log|conf)$ {
        deny all;
        access_log off;
        log_not_found off;
    }

    # Robots.txt
    location = /robots.txt {
        add_header Content-Type text/plain;
        return 200 "User-agent: *\nDisallow: /api/\nAllow: /\n";
    }
}

# Redirect www to non-www
server {
    listen 80;
    server_name www.$DOMAIN;
    return 301 http://$DOMAIN\$request_uri;
}
EOF

# Enable the site
ln -sf /etc/nginx/sites-available/transqa /etc/nginx/sites-enabled/

# Remove default site if exists
rm -f /etc/nginx/sites-enabled/default

# Test configuration
echo "🧪 Testing Nginx configuration..."
nginx -t

if [ $? -eq 0 ]; then
    echo "✅ Nginx configuration is valid"
    
    # Reload Nginx
    systemctl reload nginx
    systemctl status nginx --no-pager
    
    echo ""
    echo "🎉 Nginx configuration completed!"
    echo ""
    echo "📋 Next steps:"
    echo "1. Start TransQA services:"
    echo "   cd $PROJECT_DIR/landing-page-app"
    echo "   docker-compose -f docker-compose.prod.yml up -d"
    echo ""
    echo "2. Test the deployment:"
    echo "   curl -I http://$DOMAIN/health"
    echo ""
    echo "3. Setup SSL certificate:"
    echo "   sudo certbot --nginx -d $DOMAIN"
    echo ""
    echo "4. Monitor logs:"
    echo "   sudo tail -f /var/log/nginx/transqa_access.log"
    echo "   sudo docker-compose -f docker-compose.prod.yml logs -f"
    
else
    echo "❌ Nginx configuration has errors. Please check and fix them."
    exit 1
fi
