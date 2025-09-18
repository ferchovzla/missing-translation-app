#!/bin/bash

# 🔴 Apache Configuration Script for TransQA
DOMAIN=${1:-"transqa.local"}
PROJECT_DIR="/opt/transqa"

if [[ $EUID -ne 0 ]]; then
   echo "❌ This script must be run as root"
   exit 1
fi

echo "🔴 Configuring Apache for TransQA"
echo "📍 Domain: $DOMAIN"

# Enable required Apache modules
echo "🔧 Enabling Apache modules..."
a2enmod proxy proxy_http proxy_balancer lbmethod_byrequests
a2enmod rewrite ssl headers expires deflate
a2enmod security2 || echo "⚠️ mod_security2 not available, skipping..."

# Create Apache configuration
cat > /etc/apache2/sites-available/transqa.conf << 'EOF'
# TransQA Landing Page Configuration

# Define upstream backends
Define TRANSQA_BACKEND 127.0.0.1:8000
Define LANGUAGETOOL_BACKEND 127.0.0.1:8081
Define TRANSQA_DOMAIN DOMAIN_PLACEHOLDER
Define PROJECT_PATH PROJECT_PLACEHOLDER

# Proxy balancer for TransQA (allows for future scaling)
<Proxy balancer://transqa-cluster>
    BalancerMember http://${TRANSQA_BACKEND}
    ProxySet connectiontimeout=5
    ProxySet retry=300
</Proxy>

# Rate limiting (requires mod_security2 or mod_evasive)
<IfModule mod_security2.c>
    SecRuleEngine On
    SecRule REQUEST_URI "^/api/" \
        "id:1001,phase:1,pass,setvar:ip.api_requests=+1,expirevar:ip.api_requests=60"
    SecRule IP:api_requests "@gt 100" \
        "id:1002,phase:1,deny,status:429,msg:'API rate limit exceeded'"
</IfModule>

<VirtualHost *:80>
    ServerName ${TRANSQA_DOMAIN}
    ServerAlias www.${TRANSQA_DOMAIN}
    
    DocumentRoot ${PROJECT_PATH}/landing-page-app
    
    # Logging
    LogLevel warn
    ErrorLog ${APACHE_LOG_DIR}/transqa_error.log
    CustomLog ${APACHE_LOG_DIR}/transqa_access.log combined
    
    # Security headers
    Header always set X-Frame-Options "SAMEORIGIN"
    Header always set X-XSS-Protection "1; mode=block"
    Header always set X-Content-Type-Options "nosniff"
    Header always set Referrer-Policy "no-referrer-when-downgrade"
    Header always set Content-Security-Policy "default-src 'self' http: https: data: blob: 'unsafe-inline'"
    
    # Remove server signature
    ServerTokens Prod
    ServerSignature Off
    
    # Compression
    <IfModule mod_deflate.c>
        SetOutputFilter DEFLATE
        SetEnvIfNoCase Request_URI \
            \.(?:gif|jpe?g|png|ico)$ no-gzip dont-vary
        SetEnvIfNoCase Request_URI \
            \.(?:exe|t?gz|zip|bz2|sit|rar)$ no-gzip dont-vary
        
        DeflateCompressionLevel 6
        AddOutputFilterByType DEFLATE text/plain
        AddOutputFilterByType DEFLATE text/html
        AddOutputFilterByType DEFLATE text/xml
        AddOutputFilterByType DEFLATE text/css
        AddOutputFilterByType DEFLATE text/javascript
        AddOutputFilterByType DEFLATE application/xml
        AddOutputFilterByType DEFLATE application/xhtml+xml
        AddOutputFilterByType DEFLATE application/rss+xml
        AddOutputFilterByType DEFLATE application/javascript
        AddOutputFilterByType DEFLATE application/x-javascript
        AddOutputFilterByType DEFLATE application/json
    </IfModule>
    
    # Static files with caching
    <Directory "${PROJECT_PATH}/landing-page-app/static">
        # Enable following symlinks
        Options +FollowSymLinks
        
        # Disable directory browsing
        Options -Indexes
        
        # Allow .htaccess
        AllowOverride All
        
        # Access control
        Require all granted
        
        # Cache static assets for 1 year
        <IfModule mod_expires.c>
            ExpiresActive On
            ExpiresDefault "access plus 1 year"
            
            # Specific rules for different file types
            ExpiresByType text/css "access plus 1 year"
            ExpiresByType application/javascript "access plus 1 year"
            ExpiresByType application/x-javascript "access plus 1 year"
            ExpiresByType text/javascript "access plus 1 year"
            ExpiresByType image/png "access plus 1 year"
            ExpiresByType image/jpg "access plus 1 year"
            ExpiresByType image/jpeg "access plus 1 year"
            ExpiresByType image/gif "access plus 1 year"
            ExpiresByType image/ico "access plus 1 year"
            ExpiresByType image/icon "access plus 1 year"
            ExpiresByType text/ico "access plus 1 year"
            ExpiresByType image/svg+xml "access plus 1 year"
            ExpiresByType font/woff "access plus 1 year"
            ExpiresByType font/woff2 "access plus 1 year"
        </IfModule>
        
        # Cache control headers
        <IfModule mod_headers.c>
            Header set Cache-Control "public, max-age=31536000, immutable"
        </IfModule>
    </Directory>
    
    # API endpoints proxy
    ProxyPreserveHost On
    ProxyRequests Off
    
    # Health check endpoint (no caching)
    ProxyPass /health http://${TRANSQA_BACKEND}/health connectiontimeout=5 timeout=30
    ProxyPassReverse /health http://${TRANSQA_BACKEND}/health
    <Location "/health">
        # Disable caching for health checks
        Header set Cache-Control "no-cache, no-store, must-revalidate"
        Header set Pragma "no-cache"
        Header set Expires 0
    </Location>
    
    # API endpoints with timeout handling
    ProxyPass /api/ balancer://transqa-cluster/api/ connectiontimeout=10 timeout=300
    ProxyPassReverse /api/ balancer://transqa-cluster/api/
    <Location "/api/">
        # API specific headers
        Header set Cache-Control "no-cache, must-revalidate"
        
        # CORS headers if needed
        Header always set Access-Control-Allow-Origin "*"
        Header always set Access-Control-Allow-Methods "GET, POST, OPTIONS, PUT, DELETE"
        Header always set Access-Control-Allow-Headers "Content-Type, Authorization, X-Requested-With"
    </Location>
    
    # Documentation endpoints
    ProxyPass /docs http://${TRANSQA_BACKEND}/docs connectiontimeout=5 timeout=60
    ProxyPassReverse /docs http://${TRANSQA_BACKEND}/docs
    
    ProxyPass /redoc http://${TRANSQA_BACKEND}/redoc connectiontimeout=5 timeout=60
    ProxyPassReverse /redoc http://${TRANSQA_BACKEND}/redoc
    
    ProxyPass /openapi.json http://${TRANSQA_BACKEND}/openapi.json connectiontimeout=5 timeout=60
    ProxyPassReverse /openapi.json http://${TRANSQA_BACKEND}/openapi.json
    
    # Main application (catch-all)
    ProxyPass / http://${TRANSQA_BACKEND}/ connectiontimeout=10 timeout=60
    ProxyPassReverse / http://${TRANSQA_BACKEND}/
    
    # Security: Block access to sensitive files
    <Files ~ "^\.(htaccess|htpasswd|env|log|conf)$">
        Require all denied
    </Files>
    
    <DirectoryMatch "^(.*/)?\.">
        Require all denied
    </DirectoryMatch>
    
    # Custom error pages
    ErrorDocument 500 "Internal Server Error - Please try again later"
    ErrorDocument 502 "Service Temporarily Unavailable - Please try again later"
    ErrorDocument 503 "Service Temporarily Unavailable - Please try again later"
    ErrorDocument 504 "Gateway Timeout - Please try again later"
    
    # Robots.txt
    RewriteEngine On
    RewriteRule ^/robots\.txt$ - [L]
    RewriteRule ^robots\.txt$ - [L,E=robots:1]
    <If "%{ENV:robots} == '1'">
        Header set Content-Type "text/plain"
    </If>
    
</VirtualHost>

# Redirect www to non-www
<VirtualHost *:80>
    ServerName www.${TRANSQA_DOMAIN}
    Redirect permanent / http://${TRANSQA_DOMAIN}/
</VirtualHost>

# Balancer manager (optional, for monitoring)
<Location "/balancer-manager">
    SetHandler balancer-manager
    # Restrict access to localhost only
    Require local
</Location>
ProxyPass /balancer-manager !

EOF

# Replace placeholders in the configuration
sed -i "s/DOMAIN_PLACEHOLDER/$DOMAIN/g" /etc/apache2/sites-available/transqa.conf
sed -i "s|PROJECT_PLACEHOLDER|$PROJECT_DIR|g" /etc/apache2/sites-available/transqa.conf

# Create robots.txt in document root
mkdir -p $PROJECT_DIR/landing-page-app
cat > $PROJECT_DIR/landing-page-app/robots.txt << EOF
User-agent: *
Disallow: /api/
Allow: /

Sitemap: http://$DOMAIN/sitemap.xml
EOF

# Enable the site
a2ensite transqa.conf

# Disable default site
a2dissite 000-default.conf || echo "Default site already disabled"

# Test configuration
echo "🧪 Testing Apache configuration..."
apache2ctl configtest

if [ $? -eq 0 ]; then
    echo "✅ Apache configuration is valid"
    
    # Reload Apache
    systemctl reload apache2
    systemctl status apache2 --no-pager
    
    echo ""
    echo "🎉 Apache configuration completed!"
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
    echo "   sudo certbot --apache -d $DOMAIN"
    echo ""
    echo "4. Monitor logs:"
    echo "   sudo tail -f /var/log/apache2/transqa_access.log"
    echo "   sudo docker-compose -f docker-compose.prod.yml logs -f"
    echo ""
    echo "5. View balancer status (optional):"
    echo "   http://$DOMAIN/balancer-manager"
    
else
    echo "❌ Apache configuration has errors. Please check and fix them."
    exit 1
fi
