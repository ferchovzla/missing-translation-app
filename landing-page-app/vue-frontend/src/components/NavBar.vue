<template>
  <nav class="navbar">
    <div class="nav-container">
      <div class="nav-logo">
        <i class="fas fa-language"></i>
        <span>TransQA</span>
      </div>
      <div class="nav-links">
        <a href="#features" @click="scrollTo('features')">Features</a>
        <a href="#demo" @click="scrollTo('demo')">Demo</a>
        <a :href="docsUrl" target="_blank">API Docs</a>
        <a href="https://github.com/ferchovzla/missing-translation-app" target="_blank">GitHub</a>
      </div>
    </div>
  </nav>
</template>

<script setup>
import { computed, inject } from 'vue'

const isStaticMode = inject('isStaticMode')

const docsUrl = computed(() => {
  return isStaticMode ? '#' : '/docs'
})

const scrollTo = (elementId) => {
  const element = document.getElementById(elementId)
  if (element) {
    element.scrollIntoView({ behavior: 'smooth' })
  }
}
</script>

