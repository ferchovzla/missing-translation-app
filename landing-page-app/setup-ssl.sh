#!/bin/bash

# 🔐 SSL Setup Script for TransQA (Works with both Apache and Nginx)
DOMAIN=${1:-"transqa.local"}
EMAIL=${2:-"admin@$DOMAIN"}
WEBSERVER=${3:-"nginx"}  # nginx or apache

if [[ $EUID -ne 0 ]]; then
   echo "❌ This script must be run as root"
   exit 1
fi

echo "🔐 Setting up SSL certificate for TransQA"
echo "📍 Domain: $DOMAIN"
echo "📧 Email: $EMAIL"
echo "🌐 Web Server: $WEBSERVER"

# Validate inputs
if [[ ! "$DOMAIN" =~ ^[a-zA-Z0-9][a-zA-Z0-9-]*[a-zA-Z0-9]*\.[a-zA-Z]{2,}$ ]]; then
    echo "❌ Invalid domain format: $DOMAIN"
    echo "💡 Example: transqa.yourdomain.com"
    exit 1
fi

if [[ "$WEBSERVER" != "nginx" && "$WEBSERVER" != "apache" ]]; then
    echo "❌ Unsupported web server: $WEBSERVER"
    echo "💡 Use: nginx or apache"
    exit 1
fi

# Check if domain resolves to this server
echo "🌐 Checking domain resolution..."
DOMAIN_IP=$(dig +short $DOMAIN)
SERVER_IP=$(curl -s https://ipv4.icanhazip.com/)

if [[ -z "$DOMAIN_IP" ]]; then
    echo "⚠️  Warning: Domain $DOMAIN does not resolve to any IP"
    echo "💡 Make sure DNS A record points to: $SERVER_IP"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
elif [[ "$DOMAIN_IP" != "$SERVER_IP" ]]; then
    echo "⚠️  Warning: Domain resolves to $DOMAIN_IP but server IP is $SERVER_IP"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo "✅ Domain resolution is correct"
fi

# Check if services are running
echo "🔍 Checking services..."
if ! systemctl is-active --quiet $WEBSERVER; then
    echo "❌ $WEBSERVER is not running"
    echo "💡 Start it with: systemctl start $WEBSERVER"
    exit 1
fi

if ! docker-compose -f /opt/transqa/landing-page-app/docker-compose.prod.yml ps | grep -q "Up"; then
    echo "⚠️  Warning: TransQA services don't appear to be running"
    echo "💡 Start them with: cd /opt/transqa/landing-page-app && docker-compose -f docker-compose.prod.yml up -d"
fi

# Test HTTP access before SSL
echo "🧪 Testing HTTP access..."
if curl -s -f http://$DOMAIN/health > /dev/null; then
    echo "✅ HTTP access is working"
else
    echo "❌ Cannot access http://$DOMAIN/health"
    echo "💡 Check your web server configuration and TransQA services"
    exit 1
fi

# Install SSL certificate
echo "🔐 Installing SSL certificate..."
if [[ "$WEBSERVER" == "nginx" ]]; then
    certbot --nginx -d $DOMAIN --non-interactive --agree-tos --email $EMAIL --redirect
elif [[ "$WEBSERVER" == "apache" ]]; then
    certbot --apache -d $DOMAIN --non-interactive --agree-tos --email $EMAIL --redirect
fi

if [ $? -eq 0 ]; then
    echo "✅ SSL certificate installed successfully!"
    
    # Test HTTPS access
    echo "🧪 Testing HTTPS access..."
    sleep 5  # Give services time to reload
    
    if curl -s -f https://$DOMAIN/health > /dev/null; then
        echo "✅ HTTPS access is working"
    else
        echo "⚠️  HTTPS test failed, but certificate was installed"
        echo "💡 This might be normal during initial setup"
    fi
    
    # Setup automatic renewal
    echo "🔄 Setting up automatic renewal..."
    (crontab -l 2>/dev/null; echo "0 12 * * * /usr/bin/certbot renew --quiet") | crontab -
    
    # Create renewal check script
    cat > /etc/cron.daily/certbot-renewal-check << 'EOF'
#!/bin/bash
# Check SSL certificate renewal status
DOMAIN_LIST=$(certbot certificates --quiet | grep "Certificate Name:" | cut -d: -f2 | tr -d ' ')

for domain in $DOMAIN_LIST; do
    if ! openssl x509 -checkend 604800 -noout -in /etc/letsencrypt/live/$domain/cert.pem; then
        echo "Certificate for $domain will expire within a week"
        /usr/bin/certbot renew --quiet --cert-name $domain
        systemctl reload nginx apache2 2>/dev/null || true
    fi
done
EOF
    chmod +x /etc/cron.daily/certbot-renewal-check
    
    echo ""
    echo "🎉 SSL setup completed successfully!"
    echo ""
    echo "📋 Certificate Information:"
    certbot certificates --cert-name $DOMAIN
    echo ""
    echo "🔗 Your secure site is now available at:"
    echo "   https://$DOMAIN"
    echo "   https://$DOMAIN/docs (API Documentation)"
    echo "   https://$DOMAIN/redoc (API Reference)"
    echo ""
    echo "🔄 Auto-renewal is configured and will run daily"
    echo "💡 You can test renewal with: sudo certbot renew --dry-run"
    
else
    echo "❌ SSL certificate installation failed"
    echo "💡 Common issues:"
    echo "   - Domain not pointing to this server"
    echo "   - Port 80 or 443 blocked by firewall"
    echo "   - Web server configuration errors"
    echo "   - Rate limits (try again in an hour)"
    exit 1
fi

# Additional security recommendations
echo ""
echo "🛡️  Security Recommendations:"
echo "1. Enable HTTP/2 in your web server configuration"
echo "2. Consider adding HSTS headers"
echo "3. Monitor SSL certificate expiration"
echo "4. Regular security updates: apt update && apt upgrade"
echo "5. Monitor application logs regularly"

echo ""
echo "📊 Monitoring commands:"
echo "   sudo tail -f /var/log/nginx/transqa_access.log  # Nginx logs"
echo "   sudo tail -f /var/log/apache2/transqa_access.log  # Apache logs"
echo "   cd /opt/transqa/landing-page-app && docker-compose -f docker-compose.prod.yml logs -f"
