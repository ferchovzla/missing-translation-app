"""FastAPI server for TransQA Landing Page and API."""

import sys
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

# Add parent directory to path to import TransQA modules
sys.path.append(str(Path(__file__).parent.parent.parent))

from transqa.models.config import TransQAConfig
from transqa.core.analyzer import TransQAAnalyzer
from transqa.core.fetchers import FetcherFactory
from api.models import (
    AnalysisRequest, AnalysisResponse, IssueResponse, 
    AnalysisStatsResponse, SystemInfoResponse, HealthResponse
)

# FastAPI app configuration
app = FastAPI(
    title="TransQA - Translation Quality Assurance",
    description="""
    **TransQA** is a comprehensive web translation quality assurance tool that detects:
    
    - **Language leakage**: Untranslated content in wrong languages
    - **Grammar issues**: Grammar and spelling errors using LanguageTool
    - **Consistency problems**: Inconsistent terminology and formatting
    - **Placeholder validation**: Missing or malformed placeholders
    
    ## Features
    
    - 🌍 **Multi-language support**: Spanish (es), English (en), Dutch (nl)
    - 🚀 **Real-time analysis**: Fast web page processing with progress tracking
    - 🎯 **Accurate detection**: Advanced NLP and heuristic rules
    - 📊 **Detailed reporting**: Comprehensive analysis with suggestions
    - 🔧 **Flexible configuration**: Customizable rules and thresholds
    
    ## Demo
    
    Try the live demo at the root URL to analyze any website for translation quality!
    """,
    version="1.0.0",
    contact={
        "name": "TransQA Team",
        "url": "https://github.com/transqa/transqa",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Global variables for caching
_transqa_analyzer = None
_app_start_time = time.time()


def get_analyzer() -> TransQAAnalyzer:
    """Get or create TransQA analyzer instance."""
    global _transqa_analyzer
    
    if _transqa_analyzer is None:
        # Load configuration from parent directory
        config_path = Path(__file__).parent.parent.parent / "transqa.toml"
        config = TransQAConfig.from_file(config_path)
        _transqa_analyzer = TransQAAnalyzer(config)
        _transqa_analyzer.initialize()
    
    return _transqa_analyzer


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def landing_page(request: Request):
    """Serve the landing page with demo interface."""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "title": "TransQA - Translation Quality Assurance",
        "supported_languages": ["es", "en", "nl"]
    })


@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """
    Health check endpoint.
    
    Returns the current status of the TransQA service and its components.
    """
    try:
        analyzer = get_analyzer()
        components = {
            "fetcher": "healthy" if analyzer.fetcher else "unavailable",
            "extractor": "healthy" if analyzer.extractor else "unavailable", 
            "language_detector": "healthy" if analyzer.language_detector else "unavailable",
            "verifier": "healthy" if analyzer.verifier else "unavailable",
        }
        
        return HealthResponse(
            status="healthy",
            timestamp=datetime.utcnow().isoformat(),
            uptime=time.time() - _app_start_time,
            components=components
        )
    except Exception as e:
        return HealthResponse(
            status="unhealthy", 
            timestamp=datetime.utcnow().isoformat(),
            uptime=time.time() - _app_start_time,
            components={"error": str(e)}
        )


@app.get("/info", response_model=SystemInfoResponse, tags=["System"])
async def system_info():
    """
    Get system information and capabilities.
    
    Returns information about TransQA version, supported languages, and available components.
    """
    try:
        analyzer = get_analyzer()
        
        # Get available fetchers
        available_fetchers = FetcherFactory.get_available_fetchers()
        
        components_status = {
            "analyzer": bool(analyzer),
            "fetcher": bool(analyzer.fetcher) if analyzer else False,
            "extractor": bool(analyzer.extractor) if analyzer else False,
            "language_detector": bool(analyzer.language_detector) if analyzer else False,
            "verifier": bool(analyzer.verifier) if analyzer else False,
        }
        
        return SystemInfoResponse(
            version="1.0.0",
            supported_languages=["es", "en", "nl"],
            available_fetchers=available_fetchers,
            components_status=components_status
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get system info: {str(e)}")


@app.post("/api/analyze", response_model=AnalysisResponse, tags=["Analysis"])
async def analyze_url(request: AnalysisRequest):
    """
    Analyze a URL for translation quality issues.
    
    This endpoint processes a web page and returns detailed analysis including:
    - Detected translation quality issues
    - Language leakage detection  
    - Grammar and spelling problems
    - Consistency issues
    - Statistical summary
    
    The analysis supports three target languages: Spanish (es), English (en), and Dutch (nl).
    """
    start_time = time.time()
    
    try:
        analyzer = get_analyzer()
        
        # Perform analysis
        result = analyzer.analyze_url(
            url=str(request.url),
            target_lang=request.target_language.value,
            render_js=request.render_js
        )
        
        processing_time = time.time() - start_time
        
        # Convert issues to response format
        issues = [
            IssueResponse(
                id=issue.id,
                type=issue.type,
                severity=issue.severity,
                message=issue.message,
                suggestion=issue.suggestion,
                snippet=issue.snippet,
                xpath=issue.xpath,
                confidence=issue.confidence
            )
            for issue in result.issues
        ]
        
        # Convert stats to response format
        stats = AnalysisStatsResponse(
            total_issues=result.stats.total_issues,
            issues_by_severity=result.stats.issues_by_severity,
            issues_by_type=result.stats.issues_by_type,
            total_text_blocks=result.stats.total_text_blocks,
            target_language_percentage=result.stats.target_language_percentage,
            detected_languages=result.stats.detected_languages
        )
        
        return AnalysisResponse(
            url=result.url,
            target_language=result.target_language,
            success=result.success,
            processing_time=processing_time,
            page_title=result.page_title,
            issues=issues,
            stats=stats,
            error_message=result.error_message if not result.success else None,
            error_type=None  # Could be enhanced to include error types
        )
        
    except Exception as e:
        processing_time = time.time() - start_time
        
        return AnalysisResponse(
            url=str(request.url),
            target_language=request.target_language.value,
            success=False,
            processing_time=processing_time,
            page_title=None,
            issues=[],
            stats=AnalysisStatsResponse(
                total_issues=0,
                issues_by_severity={},
                issues_by_type={},
                total_text_blocks=0,
                target_language_percentage=0.0,
                detected_languages={}
            ),
            error_message=str(e),
            error_type=type(e).__name__
        )


@app.get("/api/languages", response_model=List[Dict[str, str]], tags=["Configuration"])
async def get_supported_languages():
    """
    Get list of supported target languages.
    
    Returns a list of languages that can be used as target languages for analysis.
    """
    return [
        {"code": "es", "name": "Spanish", "native_name": "Español"},
        {"code": "en", "name": "English", "native_name": "English"}, 
        {"code": "nl", "name": "Dutch", "native_name": "Nederlands"}
    ]


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
