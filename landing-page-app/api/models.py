"""API models for TransQA Landing Page."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, HttpUrl
from enum import Enum


class LanguageEnum(str, Enum):
    """Supported target languages."""
    SPANISH = "es"
    ENGLISH = "en"  
    DUTCH = "nl"


class AnalysisRequest(BaseModel):
    """Request model for URL analysis."""
    
    url: HttpUrl = Field(..., description="URL to analyze for translation quality")
    target_language: LanguageEnum = Field(..., description="Expected target language")
    render_js: bool = Field(False, description="Whether to render JavaScript content")
    
    class Config:
        schema_extra = {
            "example": {
                "url": "https://example.com",
                "target_language": "es", 
                "render_js": False
            }
        }


class IssueResponse(BaseModel):
    """Response model for a detected issue."""
    
    id: str = Field(..., description="Unique issue identifier")
    type: str = Field(..., description="Type of issue detected")
    severity: str = Field(..., description="Severity level (info, warning, error, critical)")
    message: str = Field(..., description="Human-readable description")
    suggestion: Optional[str] = Field(None, description="Suggested correction")
    snippet: str = Field(..., description="Text snippet containing the issue")
    xpath: str = Field(..., description="XPath location in DOM")
    confidence: float = Field(..., description="Detection confidence (0.0-1.0)")
    

class AnalysisStatsResponse(BaseModel):
    """Response model for analysis statistics."""
    
    total_issues: int = Field(..., description="Total number of issues detected")
    issues_by_severity: Dict[str, int] = Field(..., description="Issues grouped by severity")
    issues_by_type: Dict[str, int] = Field(..., description="Issues grouped by type")
    total_text_blocks: int = Field(..., description="Total text blocks analyzed")
    target_language_percentage: float = Field(..., description="Percentage of content in target language")
    detected_languages: Dict[str, float] = Field(..., description="Detected languages with percentages")


class AnalysisResponse(BaseModel):
    """Response model for complete analysis."""
    
    url: str = Field(..., description="Analyzed URL")
    target_language: str = Field(..., description="Target language")
    success: bool = Field(..., description="Whether analysis completed successfully")
    processing_time: float = Field(..., description="Processing time in seconds")
    page_title: Optional[str] = Field(None, description="Page title")
    
    # Analysis results
    issues: List[IssueResponse] = Field(default_factory=list, description="Detected issues")
    stats: AnalysisStatsResponse = Field(..., description="Analysis statistics")
    
    # Error information (if success=False)
    error_message: Optional[str] = Field(None, description="Error message if analysis failed")
    error_type: Optional[str] = Field(None, description="Type of error encountered")
    

class SystemInfoResponse(BaseModel):
    """Response model for system information."""
    
    version: str = Field(..., description="TransQA version")
    supported_languages: List[str] = Field(..., description="Supported target languages")
    available_fetchers: Dict[str, bool] = Field(..., description="Available content fetchers")
    components_status: Dict[str, bool] = Field(..., description="Component initialization status")


class HealthResponse(BaseModel):
    """Response model for health check."""
    
    status: str = Field(..., description="Service status")
    timestamp: str = Field(..., description="Response timestamp")
    uptime: float = Field(..., description="Service uptime in seconds")
    components: Dict[str, str] = Field(..., description="Component health status")
