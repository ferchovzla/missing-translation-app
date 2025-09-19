import { ref, inject } from 'vue'
import TransQAApi from '../services/transqaApi.js'

export function useTransQA() {
  const isStaticMode = inject('isStaticMode')
  const apiBaseUrl = inject('apiBaseUrl')
  
  // Create API instance
  const api = new TransQAApi(apiBaseUrl, isStaticMode)
  
  // Reactive state
  const isAnalyzing = ref(false)
  const analysisResult = ref(null)
  const analysisError = ref(null)
  const systemInfo = ref(null)
  
  // Analyze URL function
  const analyzeUrl = async (url, targetLanguage, renderJs = false) => {
    if (!url || !targetLanguage) {
      throw new Error('URL and target language are required')
    }
    
    isAnalyzing.value = true
    analysisError.value = null
    analysisResult.value = null
    
    try {
      const result = await api.analyzeUrl(url, targetLanguage, renderJs)
      analysisResult.value = result
      return result
    } catch (error) {
      analysisError.value = error.message
      throw error
    } finally {
      isAnalyzing.value = false
    }
  }
  
  // Get system info
  const getSystemInfo = async () => {
    try {
      const info = await api.getSystemInfo()
      systemInfo.value = info
      return info
    } catch (error) {
      console.error('Failed to get system info:', error)
      return null
    }
  }
  
  // Get supported languages
  const getSupportedLanguages = async () => {
    try {
      return await api.getSupportedLanguages()
    } catch (error) {
      console.error('Failed to get supported languages:', error)
      return []
    }
  }
  
  // Clear results
  const clearResults = () => {
    analysisResult.value = null
    analysisError.value = null
  }
  
  return {
    // State
    isAnalyzing,
    analysisResult,
    analysisError,
    systemInfo,
    isStaticMode,
    
    // Methods
    analyzeUrl,
    getSystemInfo,
    getSupportedLanguages,
    clearResults,
    
    // API instance for direct access
    api
  }
}

