import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

export default defineConfig(({ mode }) => ({
  plugins: [vue()],
  
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },

  // Configuration for different modes
  define: {
    __STATIC_MODE__: mode === 'static',
    __API_BASE_URL__: mode === 'static' 
      ? JSON.stringify('') // No API in static mode
      : JSON.stringify('/api'), // Use relative API path in full deployment
  },

  // Build configuration
  build: {
    outDir: mode === 'static' ? '../static-dist' : '../dist',
    assetsDir: 'assets',
    sourcemap: false,
    
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['vue', 'vue-router', 'axios'],
        },
      },
    },
  },

  // Dev server configuration
  server: {
    port: 3000,
    proxy: mode !== 'static' ? {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    } : undefined,
  },

  // Base URL for different deployments
  base: mode === 'static' 
    ? '/missing-translation-app/' // GitHub Pages repository name
    : '/', // Root for full deployment
}))
