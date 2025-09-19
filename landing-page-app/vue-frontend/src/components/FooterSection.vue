<template>
  <footer class="footer">
    <div class="container">
      <div class="footer-content">
        <div class="footer-section">
          <div class="footer-logo">
            <i class="fas fa-language"></i>
            <span>TransQA</span>
          </div>
          <p class="footer-description">
            Professional translation quality assurance tool for detecting language issues, 
            grammar errors, and ensuring perfect translations.
          </p>
          <div class="social-links">
            <a href="https://github.com/ferchovzla/missing-translation-app" target="_blank">
              <i class="fab fa-github"></i>
            </a>
          </div>
        </div>
        
        <div class="footer-section">
          <h4>Product</h4>
          <ul>
            <li><a href="#features">Features</a></li>
            <li><a href="#demo">Try Demo</a></li>
            <li><a :href="docsUrl" :target="docsTarget">API Documentation</a></li>
            <li><a :href="redocUrl" :target="redocTarget">API Reference</a></li>
          </ul>
        </div>
        
        <div class="footer-section">
          <h4>Support</h4>
          <ul>
            <li><a href="https://github.com/ferchovzla/missing-translation-app/issues" target="_blank">Report Issues</a></li>
            <li><a href="https://github.com/ferchovzla/missing-translation-app/blob/main/CONTRIBUTING.md" target="_blank">Contributing</a></li>
            <li><a href="https://github.com/ferchovzla/missing-translation-app/blob/main/landing-page-app/README-DEPLOY.md" target="_blank">Deployment Guide</a></li>
          </ul>
        </div>
        
        <div class="footer-section">
          <h4>Languages</h4>
          <ul>
            <li><span class="flag">🇪🇸</span> Spanish (Español)</li>
            <li><span class="flag">🇺🇸</span> English</li>
            <li><span class="flag">🇳🇱</span> Dutch (Nederlands)</li>
          </ul>
        </div>
      </div>
      
      <div class="footer-bottom">
        <div class="footer-copyright">
          <p>&copy; {{ currentYear }} TransQA. Released under the MIT License.</p>
        </div>
        <div class="footer-links">
          <a href="https://github.com/ferchovzla/missing-translation-app/blob/main/LICENSE" target="_blank">License</a>
          <a href="https://github.com/ferchovzla/missing-translation-app/blob/main/CODE_OF_CONDUCT.md" target="_blank">Code of Conduct</a>
        </div>
      </div>
    </div>
  </footer>
</template>

<script setup>
import { computed, inject } from 'vue'

const isStaticMode = inject('isStaticMode')

const currentYear = new Date().getFullYear()

const docsUrl = computed(() => {
  return isStaticMode ? '#' : '/docs'
})

const redocUrl = computed(() => {
  return isStaticMode ? '#' : '/redoc'
})

const docsTarget = computed(() => {
  return isStaticMode ? '_self' : '_blank'
})

const redocTarget = computed(() => {
  return isStaticMode ? '_self' : '_blank'
})
</script>

