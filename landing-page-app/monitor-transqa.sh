#!/bin/bash

# 📊 TransQA Monitoring and Management Script

DOMAIN=${1:-"localhost"}
PROJECT_DIR="/opt/transqa"

show_status() {
    echo "📊 TransQA System Status"
    echo "========================"
    
    # System resources
    echo ""
    echo "💻 System Resources:"
    echo "   CPU Usage: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)%"
    echo "   Memory: $(free -h | awk 'NR==2{printf "%.1f%% (%s/%s)\n", $3*100/$2, $3, $2}')"
    echo "   Disk: $(df -h / | awk 'NR==2{printf "%s/%s (%s)\n", $3, $2, $5}')"
    
    # Docker services
    echo ""
    echo "🐳 Docker Services:"
    cd $PROJECT_DIR/landing-page-app 2>/dev/null || cd .
    if [ -f "docker-compose.prod.yml" ]; then
        docker-compose -f docker-compose.prod.yml ps
    else
        echo "   ❌ docker-compose.prod.yml not found"
    fi
    
    # Web server status
    echo ""
    echo "🌐 Web Server:"
    if systemctl is-active --quiet nginx; then
        echo "   ✅ Nginx: $(systemctl is-active nginx) ($(systemctl is-enabled nginx))"
    elif systemctl is-active --quiet apache2; then
        echo "   ✅ Apache: $(systemctl is-active apache2) ($(systemctl is-enabled apache2))"
    else
        echo "   ❌ No web server detected"
    fi
    
    # Application health
    echo ""
    echo "🏥 Application Health:"
    if curl -s -f http://localhost:8000/health >/dev/null 2>&1; then
        HEALTH_RESPONSE=$(curl -s http://localhost:8000/health)
        echo "   ✅ TransQA API: Healthy"
        echo "   📋 Health Info: $HEALTH_RESPONSE"
    else
        echo "   ❌ TransQA API: Not responding"
    fi
    
    if curl -s -f http://localhost:8081/v2/languages >/dev/null 2>&1; then
        echo "   ✅ LanguageTool: Healthy"
    else
        echo "   ❌ LanguageTool: Not responding"
    fi
    
    # SSL certificate status
    if [ "$DOMAIN" != "localhost" ]; then
        echo ""
        echo "🔐 SSL Certificate:"
        if command -v openssl >/dev/null && openssl s_client -connect $DOMAIN:443 -servername $DOMAIN </dev/null 2>/dev/null | openssl x509 -noout -dates 2>/dev/null; then
            EXPIRY=$(openssl s_client -connect $DOMAIN:443 -servername $DOMAIN </dev/null 2>/dev/null | openssl x509 -noout -enddate 2>/dev/null | cut -d= -f2)
            echo "   ✅ Certificate expires: $EXPIRY"
        else
            echo "   ❌ SSL certificate check failed"
        fi
    fi
    
    # Recent errors
    echo ""
    echo "⚠️  Recent Errors (last 10):"
    if [ -f "/var/log/nginx/transqa_error.log" ]; then
        tail -10 /var/log/nginx/transqa_error.log 2>/dev/null || echo "   No Nginx errors"
    elif [ -f "/var/log/apache2/transqa_error.log" ]; then
        tail -10 /var/log/apache2/transqa_error.log 2>/dev/null || echo "   No Apache errors"
    fi
    
    cd $PROJECT_DIR/landing-page-app 2>/dev/null || cd .
    if [ -f "docker-compose.prod.yml" ]; then
        echo "   Docker errors:"
        docker-compose -f docker-compose.prod.yml logs --tail=5 2>/dev/null | grep -i error || echo "   No Docker errors"
    fi
}

show_logs() {
    echo "📋 Live Logs (Press Ctrl+C to stop)"
    echo "===================================="
    
    # Run logs in parallel
    (
        if [ -f "/var/log/nginx/transqa_access.log" ]; then
            tail -f /var/log/nginx/transqa_access.log | sed 's/^/[NGINX] /' &
        elif [ -f "/var/log/apache2/transqa_access.log" ]; then
            tail -f /var/log/apache2/transqa_access.log | sed 's/^/[APACHE] /' &
        fi
        
        cd $PROJECT_DIR/landing-page-app 2>/dev/null || cd .
        if [ -f "docker-compose.prod.yml" ]; then
            docker-compose -f docker-compose.prod.yml logs -f | sed 's/^/[DOCKER] /' &
        fi
        
        wait
    )
}

restart_services() {
    echo "🔄 Restarting TransQA services..."
    
    cd $PROJECT_DIR/landing-page-app 2>/dev/null || {
        echo "❌ Cannot find project directory"
        exit 1
    }
    
    if [ -f "docker-compose.prod.yml" ]; then
        echo "🐳 Restarting Docker services..."
        docker-compose -f docker-compose.prod.yml restart
        
        echo "⏳ Waiting for services to be ready..."
        sleep 10
        
        # Health check
        for i in {1..30}; do
            if curl -s -f http://localhost:8000/health >/dev/null 2>&1; then
                echo "✅ Services are ready!"
                break
            fi
            echo "⏳ Waiting... ($i/30)"
            sleep 2
        done
    else
        echo "❌ docker-compose.prod.yml not found"
        exit 1
    fi
    
    # Restart web server
    if systemctl is-active --quiet nginx; then
        echo "🔄 Restarting Nginx..."
        systemctl restart nginx
    elif systemctl is-active --quiet apache2; then
        echo "🔄 Restarting Apache..."
        systemctl restart apache2
    fi
    
    echo "✅ All services restarted"
}

backup_data() {
    echo "💾 Creating backup..."
    
    BACKUP_DIR="/opt/transqa-backups"
    BACKUP_FILE="transqa-backup-$(date +%Y%m%d-%H%M%S).tar.gz"
    
    mkdir -p $BACKUP_DIR
    
    cd $PROJECT_DIR
    tar -czf "$BACKUP_DIR/$BACKUP_FILE" \
        --exclude='*.log' \
        --exclude='venv' \
        --exclude='__pycache__' \
        --exclude='.git' \
        . 2>/dev/null
    
    echo "✅ Backup created: $BACKUP_DIR/$BACKUP_FILE"
    echo "📁 Backup size: $(du -h $BACKUP_DIR/$BACKUP_FILE | cut -f1)"
    
    # Keep only last 7 backups
    cd $BACKUP_DIR
    ls -t transqa-backup-*.tar.gz | tail -n +8 | xargs -r rm --
    echo "🗂️  Cleanup: Keeping last 7 backups"
}

test_endpoints() {
    echo "🧪 Testing API Endpoints"
    echo "========================"
    
    BASE_URL="http://localhost:8000"
    
    # Health check
    echo -n "🏥 Health endpoint: "
    if curl -s -f $BASE_URL/health >/dev/null; then
        echo "✅ OK"
    else
        echo "❌ FAIL"
    fi
    
    # Info endpoint
    echo -n "ℹ️  Info endpoint: "
    if curl -s -f $BASE_URL/info >/dev/null; then
        echo "✅ OK"
    else
        echo "❌ FAIL"
    fi
    
    # Languages endpoint
    echo -n "🌍 Languages endpoint: "
    if curl -s -f $BASE_URL/api/languages >/dev/null; then
        echo "✅ OK"
    else
        echo "❌ FAIL"
    fi
    
    # Documentation
    echo -n "📚 Swagger docs: "
    if curl -s -f $BASE_URL/docs >/dev/null; then
        echo "✅ OK"
    else
        echo "❌ FAIL"
    fi
    
    # Test analysis (with a simple URL)
    echo -n "🔍 Analysis endpoint: "
    ANALYSIS_RESULT=$(curl -s -X POST $BASE_URL/api/analyze \
        -H "Content-Type: application/json" \
        -d '{"url": "https://httpbin.org/html", "target_language": "en", "render_js": false}' \
        2>/dev/null)
    
    if echo "$ANALYSIS_RESULT" | grep -q "success"; then
        echo "✅ OK"
    else
        echo "❌ FAIL"
    fi
}

show_help() {
    echo "📊 TransQA Monitoring Script"
    echo "Usage: $0 [DOMAIN] [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  status    - Show system status (default)"
    echo "  logs      - Show live logs"
    echo "  restart   - Restart all services"
    echo "  backup    - Create backup"
    echo "  test      - Test API endpoints"
    echo "  help      - Show this help"
    echo ""
    echo "Examples:"
    echo "  $0 transqa.com status"
    echo "  $0 localhost logs"
    echo "  $0 restart"
}

# Main logic
COMMAND=${2:-"status"}

case $COMMAND in
    "status")
        show_status
        ;;
    "logs")
        show_logs
        ;;
    "restart")
        restart_services
        ;;
    "backup")
        backup_data
        ;;
    "test")
        test_endpoints
        ;;
    "help"|"-h"|"--help")
        show_help
        ;;
    *)
        echo "❌ Unknown command: $COMMAND"
        show_help
        exit 1
        ;;
esac
