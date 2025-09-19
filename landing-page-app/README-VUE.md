# 🚀 TransQA Vue.js Landing Page

¡Nueva versión moderna de la Landing Page con **Vue.js 3 + Vite**! 

## ✨ **Características**

### 🎯 **Dos Modos de Funcionamiento**
- **🌐 Estático (GitHub Pages)**: Demo con datos mockeados
- **⚡ Completo (Con Backend)**: Funcionalidad real con API

### 🏗️ **Tecnologías**
- **Vue.js 3** con Composition API
- **Vite** para build rápido
- **Responsive Design** con CSS moderno
- **Docker** ready para deployment
- **GitHub Actions** para CI/CD automático

## 🚀 **Deployment Options**

### **Opción 1: GitHub Pages (Estático)**
```bash
# Automático con GitHub Actions al hacer push
git push origin main

# Build manual
cd vue-frontend
npm install
npm run build-static
```

### **Opción 2: Deployment Completo (Con Backend)**
```bash
# Deployment moderno Vue.js + FastAPI
./deploy-vue.sh

# Para producción con dominio
./deploy-vue.sh mi-dominio.com admin@mi-dominio.com
```

### **Opción 3: Deployment Clásico (Compatibilidad)**
```bash
# Versión original Jinja2 + FastAPI  
./deploy-simple.sh
```

## 🔧 **Desarrollo Local**

### **Frontend Vue.js**
```bash
cd vue-frontend
npm install
npm run dev        # http://localhost:3000
```

### **Backend + Frontend**
```bash
# Terminal 1: Backend API
docker-compose -f docker-compose.vue.yml up -d languagetool
cd ../api && uvicorn main:app --reload

# Terminal 2: Frontend Vue.js
cd vue-frontend && npm run dev
```

## 📁 **Estructura del Proyecto**

```
landing-page-app/
├── vue-frontend/              # 🎨 Nueva aplicación Vue.js
│   ├── src/
│   │   ├── components/        # Componentes Vue
│   │   ├── views/            # Vistas principales
│   │   ├── services/         # API y servicios
│   │   └── composables/      # Lógica reutilizable
│   ├── package.json          # Dependencias Node.js
│   └── vite.config.js        # Configuración Vite
├── deploy-vue.sh             # 🚀 Script deployment Vue.js
├── docker-compose.vue.yml    # 🐳 Stack Vue.js + FastAPI
├── Dockerfile.vue           # 🏗️ Build Vue.js + Python
├── nginx/vue.conf           # ⚙️ Config Nginx para SPA
└── README-VUE.md           # 📖 Esta documentación
```

## 🌍 **URLs Disponibles**

### **GitHub Pages (Estático)**
- 🌐 **Demo**: https://ferchovzla.github.io/missing-translation-app/
- ✅ **Características**: UI completa, demo con datos mockeados
- ❌ **Limitaciones**: Sin análisis real

### **Deployment Completo**
- 🌐 **Landing**: http://localhost o http://tu-dominio.com
- 📚 **API Docs**: http://localhost/docs
- 🔍 **API Reference**: http://localhost/redoc
- ⚡ **Funcionalidad**: Análisis real de websites

## 🎛️ **Configuración**

### **Variables de Entorno**
```bash
# Copiar template
cp env.example .env

# Configurar para Vue.js
DOMAIN=localhost
VUE_MODE=production
API_BASE_URL=/api
STATIC_BUILD=false
```

### **Modos de Build**
```bash
# Desarrollo
npm run dev

# Build para deployment con backend
npm run build

# Build estático para GitHub Pages
npm run build-static
```

## 🔄 **Migración desde Versión Anterior**

### **¿Qué cambió?**
- ✅ **Frontend**: Jinja2 templates → Vue.js 3 SPA
- ✅ **Build**: Manual → Vite (ultra rápido)
- ✅ **Estado**: Sin gestión → Reactive Vue.js
- ✅ **API**: Misma FastAPI (compatible)
- ✅ **Docker**: Nuevo Dockerfile.vue optimizado

### **¿Qué se mantiene?**
- ✅ **API Backend**: 100% compatible
- ✅ **Docker Compose**: Ambas versiones disponibles
- ✅ **Nginx**: Configuración adaptada para SPA
- ✅ **Scripts**: deploy-simple.sh sigue funcionando

## 🎯 **Casos de Uso**

### **Para Demos y Portfolios**
```bash
# GitHub Pages automático
git push origin main
# → https://ferchovzla.github.io/missing-translation-app/
```

### **Para Desarrollo y Testing**
```bash
cd vue-frontend
npm run dev
# → http://localhost:3000 con hot-reload
```

### **Para Producción**
```bash
./deploy-vue.sh mi-dominio.com
# → Stack completo con Vue.js optimizado
```

## 🔧 **Comandos Útiles**

### **Gestión de Servicios**
```bash
# Ver logs Vue.js stack
docker-compose -f docker-compose.vue.yml logs -f

# Reiniciar servicios  
docker-compose -f docker-compose.vue.yml restart

# Rebuild completo
docker-compose -f docker-compose.vue.yml up -d --build
```

### **Desarrollo Frontend**
```bash
cd vue-frontend

# Instalar dependencias
npm install

# Desarrollo con hot-reload
npm run dev

# Build para producción
npm run build

# Preview del build
npm run preview
```

## 🚨 **Troubleshooting**

### **Vue.js no carga**
```bash
# Verificar build
cd vue-frontend && npm run build

# Verificar nginx config
docker-compose -f docker-compose.vue.yml logs nginx
```

### **API no funciona**
```bash
# Verificar backend
curl http://localhost:8000/health

# Ver logs API
docker-compose -f docker-compose.vue.yml logs transqa-vue
```

### **GitHub Pages no actualiza**
- Verificar workflow en `.github/workflows/vue-deploy.yml`
- Verificar que el push haya triggereado la action
- Configurar Pages en Settings → Pages → Source: GitHub Actions

## 📊 **Comparación de Versiones**

| Característica | Vue.js | Original |
|---------------|--------|----------|
| **Frontend** | Vue.js 3 SPA | Jinja2 Templates |
| **Build** | Vite (ultra rápido) | Sin build |
| **Desarrollo** | Hot reload | Reload manual |
| **Estado** | Reactive | Sin gestión |
| **GitHub Pages** | ✅ Automático | ❌ No compatible |
| **SEO** | ⚠️ SPA limitations | ✅ Server-side |
| **Performance** | ⚡ Muy rápido | ✅ Rápido |
| **Mantenimiento** | 🎯 Moderno | 📄 Clásico |

## 🎉 **¡Listo para Usar!**

Tu nueva landing page Vue.js está lista con:
- ✅ **Demo estático** en GitHub Pages
- ✅ **Deployment completo** con Docker
- ✅ **Compatibilidad** con versión anterior
- ✅ **Desarrollo moderno** con Vue.js 3
- ✅ **Build optimizado** con Vite

**¡Disfruta tu nueva landing page moderna!** 🚀

