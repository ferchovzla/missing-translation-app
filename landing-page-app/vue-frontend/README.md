# TransQA Vue.js Frontend

Modern Vue.js 3 frontend for the TransQA Translation Quality Assurance tool.

## Features

- **Vue.js 3** with Composition API
- **Vite** for lightning-fast development
- **Dual Mode**: Static demo + Full functionality
- **Responsive Design** with modern CSS
- **TypeScript Ready** (can be enabled)

## Quick Start

```bash
# Install dependencies
npm install

# Development server (http://localhost:3000)
npm run dev

# Build for production
npm run build

# Build for GitHub Pages (static demo)
npm run build-static

# Preview production build
npm run preview
```

## Project Structure

```
src/
├── components/          # Vue components
│   ├── NavBar.vue
│   ├── HeroSection.vue
│   ├── FeaturesSection.vue
│   ├── DemoSection.vue
│   ├── AnalysisResults.vue
│   └── FooterSection.vue
├── views/               # Page views
│   └── Home.vue
├── services/            # API services
│   └── transqaApi.js
├── composables/         # Vue composables
│   └── useTransQA.js
├── assets/              # Static assets
│   └── css/
│       └── main.css
├── App.vue              # Root component
└── main.js              # App entry point
```

## Configuration

The app automatically detects its mode:

- **Static Mode**: When `__STATIC_MODE__` is true (GitHub Pages)
- **Full Mode**: When connected to TransQA backend API

## API Integration

```javascript
// Using the composable
import { useTransQA } from '@/composables/useTransQA.js'

const {
  isAnalyzing,
  analysisResult,
  analyzeUrl,
  clearResults
} = useTransQA()

// Analyze a URL
await analyzeUrl('https://example.com', 'es', false)
```

## Development

### With Backend API

1. Start the backend API (port 8000)
2. Run `npm run dev` (port 3000)
3. Backend API calls will be proxied automatically

### Static Mode Testing

1. Run `npm run build-static`
2. Run `npm run preview`
3. Test with mock data

## Deployment

### GitHub Pages (Automatic)
Push to `main` branch - GitHub Actions will build and deploy automatically.

### With Docker
Use the parent directory's `deploy-vue.sh` script for full deployment.

## Build Outputs

- **`npm run build`**: Production build for backend integration
- **`npm run build-static`**: Static build for GitHub Pages
- Output directory: `../static-dist` (static) or `../dist` (full)

## Environment Variables

The build uses these compile-time constants:

- `__STATIC_MODE__`: Boolean indicating static mode
- `__API_BASE_URL__`: Base URL for API calls

## Browser Support

- Chrome/Edge 88+
- Firefox 78+
- Safari 14+
- Mobile browsers with ES2020 support

