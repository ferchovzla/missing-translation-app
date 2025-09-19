import { createApp } from 'vue'
import { createRouter, createWebHistory, createWebHashHistory } from 'vue-router'
import App from './App.vue'

// Import global styles
import './assets/css/main.css'

// Import components
import Home from './views/Home.vue'

// Create router with conditional history mode
const router = createRouter({
  // Use hash mode for static deployment (GitHub Pages), history mode for full deployment
  history: __STATIC_MODE__ 
    ? createWebHashHistory(import.meta.env.BASE_URL)
    : createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: Home
    }
  ]
})

const app = createApp(App)

// Provide global configuration
app.provide('isStaticMode', __STATIC_MODE__)
app.provide('apiBaseUrl', __API_BASE_URL__)

app.use(router)
app.mount('#app')
