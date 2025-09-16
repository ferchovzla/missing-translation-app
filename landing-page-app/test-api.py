#!/usr/bin/env python3
"""Quick test script for TransQA Landing Page API."""

import sys
from pathlib import Path

# Add parent directory to path for TransQA imports
sys.path.append(str(Path(__file__).parent.parent))

def test_imports():
    """Test that all required imports work."""
    print("🔍 Testing imports...")
    
    try:
        # Test FastAPI imports
        import fastapi
        import uvicorn
        import jinja2
        print("✅ FastAPI dependencies imported successfully")
        
        # Test TransQA imports
        from transqa.models.config import TransQAConfig
        from transqa.core.analyzer import TransQAAnalyzer
        from transqa.core.fetchers import FetcherFactory
        print("✅ TransQA core imports successful")
        
        # Test API models
        from api.models import AnalysisRequest, AnalysisResponse
        print("✅ API models imported successfully")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_config_loading():
    """Test loading TransQA configuration."""
    print("\n🔧 Testing configuration loading...")
    
    try:
        # Try to load config from parent directory
        config_path = Path(__file__).parent.parent / "transqa.toml"
        
        if config_path.exists():
            from transqa.models.config import TransQAConfig
            config = TransQAConfig.from_file(config_path)
            print(f"✅ Configuration loaded from {config_path}")
            print(f"   Target languages: {config.target.language}")
            return True
        else:
            print(f"⚠️  Configuration file not found at {config_path}")
            print("   Using default configuration...")
            
            # Create default config for testing
            from transqa.models.config import TransQAConfig
            config = TransQAConfig()
            print("✅ Default configuration created")
            return True
            
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        return False

def test_analyzer_creation():
    """Test creating TransQA analyzer."""
    print("\n🚀 Testing analyzer creation...")
    
    try:
        from transqa.models.config import TransQAConfig
        from transqa.core.analyzer import TransQAAnalyzer
        
        config_path = Path(__file__).parent.parent / "transqa.toml"
        
        if config_path.exists():
            config = TransQAConfig.from_file(config_path)
        else:
            config = TransQAConfig()
        
        # Create analyzer (don't initialize to avoid heavy dependencies)
        analyzer = TransQAAnalyzer(config)
        print("✅ TransQA analyzer created successfully")
        print(f"   Analysis timeout: {analyzer.analysis_timeout}s")
        print(f"   Max analysis time: {analyzer.max_analysis_time}s")
        
        return True
        
    except Exception as e:
        print(f"❌ Analyzer creation error: {e}")
        return False

def test_api_models():
    """Test API model validation."""
    print("\n📋 Testing API models...")
    
    try:
        from api.models import AnalysisRequest, AnalysisResponse, LanguageEnum
        
        # Test request model
        request = AnalysisRequest(
            url="https://example.com",
            target_language=LanguageEnum.SPANISH,
            render_js=False
        )
        print("✅ AnalysisRequest model validation works")
        
        # Test response model components
        from api.models import IssueResponse, AnalysisStatsResponse
        
        stats = AnalysisStatsResponse(
            total_issues=0,
            issues_by_severity={},
            issues_by_type={},
            total_text_blocks=0,
            target_language_percentage=100.0,
            detected_languages={"es": 100.0}
        )
        print("✅ AnalysisStatsResponse model validation works")
        
        response = AnalysisResponse(
            url="https://example.com",
            target_language="es",
            success=True,
            processing_time=1.23,
            issues=[],
            stats=stats
        )
        print("✅ AnalysisResponse model validation works")
        
        return True
        
    except Exception as e:
        print(f"❌ API model error: {e}")
        return False

def main():
    """Run all tests."""
    print("🧪 TransQA Landing Page API - Test Suite\n")
    
    tests = [
        test_imports,
        test_config_loading,
        test_analyzer_creation,
        test_api_models
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
            failed += 1
    
    print(f"\n📊 Test Results:")
    print(f"   ✅ Passed: {passed}")
    print(f"   ❌ Failed: {failed}")
    print(f"   📈 Success rate: {passed/(passed+failed)*100:.1f}%")
    
    if failed == 0:
        print("\n🎉 All tests passed! The API should work correctly.")
        print("\n🚀 You can now start the server with:")
        print("   ./start-web.sh")
        print("   or")
        print("   docker-compose up --build")
    else:
        print("\n⚠️  Some tests failed. Please fix the issues before starting the server.")
        
    return failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
