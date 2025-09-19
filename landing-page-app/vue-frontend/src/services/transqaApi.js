import axios from 'axios'

// Mock data for static mode
const mockAnalysisResult = {
  url: 'https://example.com',
  target_language: 'es',
  success: true,
  processing_time: 2.5,
  page_title: 'Ejemplo de Análisis - TransQA Demo',
  issues: [
    {
      id: 'demo-1',
      type: 'language_leakage',
      severity: 'high',
      message: 'English text detected in Spanish page',
      suggestion: 'Translate "Welcome to our website" to "Bienvenido a nuestro sitio web"',
      snippet: 'Welcome to our website',
      xpath: '//div[@class="header"]/h1',
      confidence: 0.95
    },
    {
      id: 'demo-2',
      type: 'grammar_error',
      severity: 'medium',
      message: 'Possible grammar error detected',
      suggestion: 'Consider changing "están" to "está"',
      snippet: 'Los usuarios están contentos',
      xpath: '//p[1]',
      confidence: 0.78
    },
    {
      id: 'demo-3',
      type: 'placeholder_error',
      severity: 'high',
      message: 'Untranslated placeholder detected',
      suggestion: 'Translate placeholder {{username}} context',
      snippet: 'Hello {{username}}, welcome!',
      xpath: '//div[@class="greeting"]',
      confidence: 0.92
    }
  ],
  stats: {
    total_issues: 3,
    issues_by_severity: {
      high: 2,
      medium: 1,
      low: 0
    },
    issues_by_type: {
      language_leakage: 1,
      grammar_error: 1,
      placeholder_error: 1
    },
    total_text_blocks: 25,
    target_language_percentage: 87.5,
    detected_languages: {
      es: 87.5,
      en: 12.5
    }
  }
}

class TransQAApi {
  constructor(baseUrl = '', isStatic = false) {
    this.isStatic = isStatic
    this.api = axios.create({
      baseURL: baseUrl,
      timeout: 180000, // 3 minutes for analysis
      headers: {
        'Content-Type': 'application/json'
      }
    })
  }

  async analyzeUrl(url, targetLanguage, renderJs = false) {
    if (this.isStatic) {
      // Return mock data with a delay to simulate real API
      return new Promise(resolve => {
        setTimeout(() => {
          resolve({
            ...mockAnalysisResult,
            url: url,
            target_language: targetLanguage,
            processing_time: Math.random() * 3 + 1 // 1-4 seconds
          })
        }, 2000) // 2 second delay
      })
    }

    try {
      const response = await this.api.post('/analyze', {
        url,
        target_language: targetLanguage,
        render_js: renderJs
      })
      return response.data
    } catch (error) {
      throw new Error(error.response?.data?.detail || error.message || 'Analysis failed')
    }
  }

  async getHealth() {
    if (this.isStatic) {
      return {
        status: 'demo',
        timestamp: new Date().toISOString(),
        uptime: 0,
        components: {
          demo: 'healthy'
        }
      }
    }

    try {
      const response = await this.api.get('/health')
      return response.data
    } catch (error) {
      throw new Error('Health check failed')
    }
  }

  async getSystemInfo() {
    if (this.isStatic) {
      return {
        version: '1.0.0',
        supported_languages: ['es', 'en', 'nl'],
        available_fetchers: ['demo'],
        components_status: {
          analyzer: true,
          fetcher: true,
          extractor: true,
          language_detector: true,
          verifier: true
        }
      }
    }

    try {
      const response = await this.api.get('/info')
      return response.data
    } catch (error) {
      throw new Error('Failed to get system info')
    }
  }

  async getSupportedLanguages() {
    return [
      { code: 'es', name: 'Spanish', native_name: 'Español' },
      { code: 'en', name: 'English', native_name: 'English' },
      { code: 'nl', name: 'Dutch', native_name: 'Nederlands' }
    ]
  }
}

export default TransQAApi

