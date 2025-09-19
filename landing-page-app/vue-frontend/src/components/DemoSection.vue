<template>
  <section id="demo" class="demo">
    <div class="container">
      <div class="section-header">
        <h2>Try TransQA Demo</h2>
        <p v-if="isStaticMode" class="demo-notice">
          <i class="fas fa-info-circle"></i>
          This is a demo with sample data. For full functionality, deploy TransQA with the backend API.
        </p>
        <p v-else>Enter a URL and target language to analyze translation quality</p>
      </div>

      <div class="demo-container">
        <form @submit.prevent="handleSubmit" class="demo-form">
          <div class="form-group">
            <label for="url">Website URL</label>
            <input
              id="url"
              v-model="formData.url"
              type="url"
              placeholder="https://example.com"
              required
              :disabled="isAnalyzing"
            />
          </div>

          <div class="form-group">
            <label for="language">Target Language</label>
            <select
              id="language"
              v-model="formData.language"
              required
              :disabled="isAnalyzing"
            >
              <option value="">Select language...</option>
              <option
                v-for="lang in supportedLanguages"
                :key="lang.code"
                :value="lang.code"
              >
                {{ lang.name }} ({{ lang.native_name }})
              </option>
            </select>
          </div>

          <div class="form-group checkbox-group">
            <label class="checkbox-label">
              <input
                v-model="formData.renderJs"
                type="checkbox"
                :disabled="isAnalyzing"
              />
              <span class="checkbox-custom"></span>
              Render JavaScript (for SPAs)
            </label>
          </div>

          <button
            type="submit"
            class="btn btn-primary btn-large"
            :disabled="!canSubmit"
          >
            <i v-if="isAnalyzing" class="fas fa-spinner fa-spin"></i>
            <i v-else class="fas fa-search"></i>
            {{ isAnalyzing ? 'Analyzing...' : 'Analyze Website' }}
          </button>
        </form>

        <!-- Loading State -->
        <div v-if="isAnalyzing" class="loading-section">
          <div class="loading-spinner">
            <div class="spinner"></div>
          </div>
          <h3>Analyzing Website...</h3>
          <p>This may take a few moments while we analyze your content.</p>
          <div class="progress-steps">
            <div class="step" :class="{ active: progressStep >= 1 }">
              <i class="fas fa-download"></i>
              Fetching content
            </div>
            <div class="step" :class="{ active: progressStep >= 2 }">
              <i class="fas fa-language"></i>
              Detecting languages
            </div>
            <div class="step" :class="{ active: progressStep >= 3 }">
              <i class="fas fa-spell-check"></i>
              Checking grammar
            </div>
            <div class="step" :class="{ active: progressStep >= 4 }">
              <i class="fas fa-check"></i>
              Generating report
            </div>
          </div>
        </div>

        <!-- Error State -->
        <div v-if="analysisError" class="error-section">
          <div class="error-content">
            <i class="fas fa-exclamation-triangle"></i>
            <h3>Analysis Failed</h3>
            <p>{{ analysisError }}</p>
            <button @click="clearResults" class="btn btn-secondary">
              <i class="fas fa-redo"></i>
              Try Again
            </button>
          </div>
        </div>

        <!-- Results Section -->
        <AnalysisResults
          v-if="analysisResult"
          :result="analysisResult"
          @clear="clearResults"
        />
      </div>
    </div>
  </section>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useTransQA } from '../composables/useTransQA.js'
import AnalysisResults from './AnalysisResults.vue'

const {
  isAnalyzing,
  analysisResult,
  analysisError,
  isStaticMode,
  analyzeUrl,
  getSupportedLanguages,
  clearResults
} = useTransQA()

const formData = ref({
  url: '',
  language: '',
  renderJs: false
})

const supportedLanguages = ref([])
const progressStep = ref(0)

const canSubmit = computed(() => {
  return formData.value.url && 
         formData.value.language && 
         !isAnalyzing.value
})

// Load supported languages on mount
onMounted(async () => {
  supportedLanguages.value = await getSupportedLanguages()
  
  // Set default demo URL for static mode
  if (isStaticMode) {
    formData.value.url = 'https://example.com'
    formData.value.language = 'es'
  }
})

// Progress simulation for loading state
watch(isAnalyzing, (analyzing) => {
  if (analyzing) {
    progressStep.value = 0
    const interval = setInterval(() => {
      if (progressStep.value < 4 && isAnalyzing.value) {
        progressStep.value++
      } else {
        clearInterval(interval)
      }
    }, 500)
  }
})

const handleSubmit = async () => {
  try {
    await analyzeUrl(
      formData.value.url,
      formData.value.language,
      formData.value.renderJs
    )
  } catch (error) {
    console.error('Analysis failed:', error)
  }
}
</script>

