<template>
  <section class="hero">
    <div class="hero-container">
      <div class="hero-content">
        <h1>Translation Quality Assurance Made Simple</h1>
        <p class="hero-subtitle">
          Automatically detect translation errors, language leakage, and quality issues in your web content.
          Support for Spanish, English, and Dutch.
        </p>
        <div class="hero-buttons">
          <button class="btn btn-primary" @click="scrollToDemo">
            <i class="fas fa-play"></i>
            Try Demo
          </button>
          <a :href="docsUrl" class="btn btn-secondary" :target="docsTarget">
            <i class="fas fa-book"></i>
            View API
          </a>
        </div>
        <div class="hero-stats">
          <div class="stat">
            <div class="stat-number">3</div>
            <div class="stat-label">Languages</div>
          </div>
          <div class="stat">
            <div class="stat-number">5+</div>
            <div class="stat-label">Issue Types</div>
          </div>
          <div class="stat">
            <div class="stat-number">99%</div>
            <div class="stat-label">Accuracy</div>
          </div>
        </div>
      </div>
      <div class="hero-visual">
        <div class="hero-card">
          <div class="card-header">
            <div class="card-title">
              <i class="fas fa-globe"></i>
              Translation Analysis
            </div>
            <div class="card-status success">
              <i class="fas fa-check-circle"></i>
              Analyzed
            </div>
          </div>
          <div class="card-content">
            <div class="analysis-item">
              <div class="analysis-type error">Language Leakage</div>
              <div class="analysis-count">2 issues</div>
            </div>
            <div class="analysis-item">
              <div class="analysis-type warning">Grammar Errors</div>
              <div class="analysis-count">1 issue</div>
            </div>
            <div class="analysis-item">
              <div class="analysis-type success">Consistency</div>
              <div class="analysis-count">Perfect</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, inject } from 'vue'

const isStaticMode = inject('isStaticMode')

const docsUrl = computed(() => {
  return isStaticMode ? '#' : '/docs'
})

const docsTarget = computed(() => {
  return isStaticMode ? '_self' : '_blank'
})

const scrollToDemo = () => {
  const element = document.getElementById('demo')
  if (element) {
    element.scrollIntoView({ behavior: 'smooth' })
  }
}
</script>

