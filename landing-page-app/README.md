# TransQA Landing Page & API

Professional landing page and REST API for the TransQA translation quality assurance tool.

## Features

### 🌐 **Landing Page**
- Modern, responsive design with smooth animations
- Interactive demo interface for real-time URL analysis
- Comprehensive feature showcase
- Mobile-optimized layout

### 🚀 **REST API**
- **FastAPI** with automatic OpenAPI documentation
- **Real-time analysis** endpoints
- **Comprehensive error handling** with detailed responses
- **CORS support** for frontend integration
- **Health monitoring** endpoints

### 📋 **API Documentation**
- **Swagger UI**: Interactive API documentation at `/docs`
- **ReDoc**: Alternative documentation at `/redoc`
- **OpenAPI 3.0** specification with detailed examples

## Quick Start

### Option 1: Local Development

```bash
# Navigate to the landing page directory
cd landing-page-app

# Run the startup script
./start-web.sh
```

### Option 2: Docker Compose

```bash
# Build and start all services
cd landing-page-app
docker-compose up --build

# Or run in background
docker-compose up -d --build
```

### Access Points

- **Landing Page**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs  
- **API Reference**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

## API Endpoints

### Core Analysis

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/analyze` | POST | Analyze URL for translation quality |
| `/api/languages` | GET | Get supported languages |

### System Information

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Service health check |
| `/info` | GET | System capabilities |

### Example API Usage

```bash
# Analyze a website
curl -X POST "http://localhost:8000/api/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "target_language": "es",
    "render_js": false
  }'

# Get supported languages
curl "http://localhost:8000/api/languages"

# Health check
curl "http://localhost:8000/health"
```

## Development

### Project Structure

```
landing-page-app/
├── api/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   └── models.py            # Pydantic models
├── static/
│   ├── css/
│   │   └── style.css        # Main stylesheet
│   ├── js/
│   │   └── main.js          # Frontend JavaScript
│   └── images/              # Organized image assets
├── templates/
│   └── index.html           # Landing page template
├── requirements-web.txt     # Python dependencies
├── start-web.sh            # Development startup script
├── docker-compose.yml      # Docker services
└── Dockerfile              # Container build
```

### Dependencies

- **FastAPI**: Modern web framework
- **Uvicorn**: ASGI server
- **Jinja2**: Template engine
- **Pydantic**: Data validation
- **aiofiles**: Async file handling

### Configuration

The application uses the main TransQA configuration file (`../transqa.toml`).

### Customization

#### Landing Page Content
- Edit `templates/index.html` for content changes
- Modify `static/css/style.css` for styling
- Update `static/js/main.js` for functionality

#### API Behavior
- Configure endpoints in `api/main.py`
- Add/modify models in `api/models.py`
- Adjust TransQA settings in `../transqa.toml`

## Demo Interface

The landing page includes an interactive demo that allows users to:

1. **Enter any URL** for analysis
2. **Select target language** (Spanish, English, Dutch)
3. **Choose JavaScript rendering** option
4. **View detailed results** including:
   - Translation quality issues
   - Language distribution analysis
   - Processing statistics
   - Actionable suggestions

## API Response Format

### Analysis Response
```json
{
  "url": "https://example.com",
  "target_language": "es",
  "success": true,
  "processing_time": 2.34,
  "page_title": "Example Site",
  "issues": [
    {
      "id": "uuid-here",
      "type": "language_leak",
      "severity": "error",
      "message": "Untranslated English text detected",
      "suggestion": "Translate to Spanish",
      "snippet": "Hello World",
      "xpath": "//div[@id='content']/p[1]",
      "confidence": 0.95
    }
  ],
  "stats": {
    "total_issues": 1,
    "issues_by_severity": {"error": 1},
    "issues_by_type": {"language_leak": 1},
    "total_text_blocks": 15,
    "target_language_percentage": 87.5,
    "detected_languages": {"es": 87.5, "en": 12.5}
  }
}
```

## Deployment

### Production Considerations

1. **Environment Variables**:
   ```bash
   export TRANSQA_CONFIG_PATH=/path/to/transqa.toml
   export CORS_ORIGINS="https://yourdomain.com"
   ```

2. **Reverse Proxy** (Nginx example):
   ```nginx
   location / {
       proxy_pass http://localhost:8000;
       proxy_set_header Host $host;
       proxy_set_header X-Real-IP $remote_addr;
   }
   ```

3. **SSL/HTTPS**: Use certificates for production

4. **Rate Limiting**: Implement API rate limits

### Docker Production

```bash
# Build production image
docker build -t transqa-web:latest .

# Run with environment config
docker run -d \
  -p 8000:8000 \
  -v /path/to/transqa.toml:/app/transqa.toml:ro \
  --name transqa-web \
  transqa-web:latest
```

## Monitoring

- **Health Endpoint**: `/health` for uptime monitoring
- **System Info**: `/info` for capability checking
- **Logs**: Application logs via uvicorn
- **Metrics**: Can integrate with Prometheus/Grafana

## Contributing

1. Follow the existing code style
2. Add tests for new features
3. Update documentation
4. Ensure responsive design works on all devices

## License

Same as TransQA main project (MIT License).
