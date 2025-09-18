# 🚀 TransQA Simple Deployment Guide

Deploy the complete TransQA Landing Page in **one command**!

## ⚡ Quick Start

### Local Development
```bash
./deploy-simple.sh
```

### Production with Domain
```bash
./deploy-simple.sh yourdomain.com admin@yourdomain.com
```

That's it! Your TransQA service will be running at:
- 🌐 **Website**: http://yourdomain.com
- 📚 **API Docs**: http://yourdomain.com/docs
- 🔍 **API Reference**: http://yourdomain.com/redoc

## 📋 Prerequisites

- ✅ **Docker** and **Docker Compose** installed
- ✅ **Domain pointing to server** (for production)
- ✅ **Ports 80 and 443** open

## 🎛️ Configuration Options

### Environment Variables

Copy `env.example` to `.env` and customize:

```bash
cp env.example .env
```

Key settings:
- `DOMAIN` - Your domain name
- `HTTP_PORT` - HTTP port (default: 80)
- `HTTPS_PORT` - HTTPS port (default: 443)
- `WORKERS` - Number of worker processes (default: 4)
- `LANGUAGETOOL_MEMORY` - Memory for LanguageTool (default: 2g)

## 🔒 SSL Setup (Optional)

For HTTPS, run after deployment:
```bash
./setup-ssl.sh yourdomain.com admin@yourdomain.com
```

## 🛠️ Management Commands

```bash
# View logs
docker-compose -f docker-compose.unified.yml logs -f

# Stop services
docker-compose -f docker-compose.unified.yml down

# Restart services
docker-compose -f docker-compose.unified.yml restart

# Update services
docker-compose -f docker-compose.unified.yml up -d --build

# View status
docker-compose -f docker-compose.unified.yml ps
```

## 🏗️ Architecture

The unified solution includes:

- **TransQA Web App** - FastAPI application with landing page
- **LanguageTool** - Grammar and spell checking service
- **Nginx** - Reverse proxy with SSL support
- **Persistent Storage** - Logs, cache, and models

## 🔧 Advanced Configuration

### Custom Nginx Configuration

Edit `nginx/default.conf` for custom proxy settings.

### Resource Limits

For production, adjust in `docker-compose.unified.yml`:
- CPU limits
- Memory limits
- Restart policies

### External LanguageTool

To use external LanguageTool service:
```bash
echo "LANGUAGETOOL_URL=http://your-server:8010" >> .env
```

## 🚨 Troubleshooting

### Service Won't Start
```bash
# Check logs
docker-compose -f docker-compose.unified.yml logs

# Rebuild from scratch
docker-compose -f docker-compose.unified.yml down --volumes
docker-compose -f docker-compose.unified.yml up -d --build
```

### Port Already in Use
```bash
# Change ports in .env
echo "HTTP_PORT=8080" >> .env
echo "HTTPS_PORT=8443" >> .env
```

### Memory Issues
```bash
# Reduce LanguageTool memory
echo "LANGUAGETOOL_MEMORY=1g" >> .env
```

## 📊 Monitoring

### Health Checks
- **API Health**: http://localhost/health
- **LanguageTool**: http://localhost:8081/v2/languages

### Resource Usage
```bash
docker stats
```

## 🔄 Updates

To update TransQA:
```bash
git pull
./deploy-simple.sh
```

## 📁 File Structure

```
landing-page-app/
├── deploy-simple.sh          # 🚀 One-click deployment
├── docker-compose.unified.yml # 🐳 Complete stack
├── env.example               # ⚙️ Configuration template
├── nginx/
│   ├── nginx.conf           # 🌐 Main nginx config
│   └── default.conf         # 🔧 Proxy configuration
├── setup-ssl.sh             # 🔒 SSL setup script
└── README-DEPLOY.md          # 📖 This guide
```

## 🆚 Comparison with Other Scripts

| Feature | deploy-simple.sh | quick-deploy.sh | Original docker-compose |
|---------|------------------|-----------------|-------------------------|
| **Simplicity** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| **Dependencies** | Docker only | System packages | Docker only |
| **SSL Support** | Via separate script | Built-in | Manual |
| **Nginx Included** | ✅ | ✅ | ❌ |
| **One Command** | ✅ | ✅ | ❌ |
| **Production Ready** | ✅ | ✅ | ⚠️ |

## ⚡ Performance Tips

1. **Increase workers** for high traffic:
   ```bash
   echo "WORKERS=8" >> .env
   ```

2. **Allocate more memory** to LanguageTool:
   ```bash
   echo "LANGUAGETOOL_MEMORY=4g" >> .env
   ```

3. **Enable SSL** for better SEO and security
4. **Use CDN** for static files in production

---

**Need help?** Check the full deployment guide in `DEPLOYMENT-GUIDE.md` or open an issue!
