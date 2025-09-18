# 🚀 **Guía Completa de Despliegue - TransQA con Docker Compose + Apache/Nginx**

Esta guía te llevará paso a paso para desplegar la landing page de TransQA en producción usando **Docker Compose** con **Apache** o **Nginx** como proxy reverso.

## 📋 **Índice**
1. [Requisitos Previos](#requisitos-previos)
2. [Despliegue Rápido (Automatizado)](#despliegue-rápido-automatizado)
3. [Despliegue Manual Paso a Paso](#despliegue-manual-paso-a-paso)
4. [Configuración SSL](#configuración-ssl)
5. [Monitoreo y Mantenimiento](#monitoreo-y-mantenimiento)
6. [Troubleshooting](#troubleshooting)

---

## 📚 **Requisitos Previos**

### **Sistema Operativo**
- Ubuntu 20.04+ o Debian 11+
- Acceso root (sudo)
- Al menos 2GB RAM y 20GB espacio libre

### **Dominio**
- Un dominio o subdominio apuntando a tu servidor
- Registro DNS tipo A configurado
- Puertos 80 y 443 abiertos

### **Accesos**
- SSH al servidor
- Permisos de administrador
- Git configurado (si vas a clonar el repositorio)

---

## ⚡ **Despliegue Rápido (Automatizado)**

### **Opción 1: Script Todo-en-Uno**

```bash
# Descargar y ejecutar el script de despliegue
curl -fsSL https://raw.githubusercontent.com/tu-usuario/missing-translation-app/main/landing-page-app/quick-deploy.sh -o quick-deploy.sh
chmod +x quick-deploy.sh

# Ejecutar (reemplaza con tu dominio)
sudo ./quick-deploy.sh transqa.tudominio.com nginx admin@tudominio.com
```

### **Opción 2: Clonar y Ejecutar**

```bash
# 1. Clonar el repositorio
git clone https://github.com/tu-usuario/missing-translation-app.git
cd missing-translation-app/landing-page-app

# 2. Ejecutar despliegue automático
sudo chmod +x *.sh
sudo ./quick-deploy.sh transqa.tudominio.com nginx admin@tudominio.com
```

**¡Listo!** En 10-15 minutos tendrás TransQA funcionando con SSL.

---

## 🔧 **Despliegue Manual Paso a Paso**

### **Paso 1: Preparación del Sistema**

```bash
# Actualizar sistema
sudo apt update && sudo apt upgrade -y

# Instalar dependencias básicas
sudo apt install -y curl wget git unzip htop ufw fail2ban

# Configurar firewall
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
```

### **Paso 2: Instalar Docker y Docker Compose**

```bash
# Instalar Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Instalar Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verificar instalación
docker --version
docker-compose --version
```

### **Paso 3: Configurar el Proyecto**

```bash
# Crear usuario del servicio
sudo useradd -r -s /bin/false transqa

# Crear directorios
sudo mkdir -p /opt/transqa
sudo mkdir -p /var/log/transqa
sudo chown -R transqa:transqa /opt/transqa
sudo chown -R transqa:transqa /var/log/transqa

# Clonar proyecto
sudo git clone https://github.com/tu-usuario/missing-translation-app.git /opt/transqa
cd /opt/transqa/landing-page-app

# Dar permisos a scripts
sudo chmod +x *.sh
```

### **Paso 4A: Configuración con Nginx**

```bash
# Instalar Nginx
sudo apt install -y nginx

# Habilitar módulos necesarios
sudo systemctl enable nginx

# Configurar Nginx para TransQA
sudo ./configure-nginx.sh tu-dominio.com

# Verificar configuración
sudo nginx -t
sudo systemctl reload nginx
```

### **Paso 4B: Configuración con Apache (Alternativa)**

```bash
# Instalar Apache
sudo apt install -y apache2

# Habilitar módulos necesarios
sudo a2enmod proxy proxy_http proxy_balancer lbmethod_byrequests
sudo a2enmod rewrite ssl headers expires deflate
sudo systemctl enable apache2

# Configurar Apache para TransQA
sudo ./configure-apache.sh tu-dominio.com

# Verificar configuración
sudo apache2ctl configtest
sudo systemctl reload apache2
```

### **Paso 5: Iniciar Servicios Docker**

```bash
# Ir al directorio del proyecto
cd /opt/transqa/landing-page-app

# Construir e iniciar servicios
sudo docker-compose -f docker-compose.prod.yml up -d --build

# Verificar que los servicios estén corriendo
sudo docker-compose -f docker-compose.prod.yml ps

# Verificar logs
sudo docker-compose -f docker-compose.prod.yml logs -f
```

### **Paso 6: Verificar el Despliegue**

```bash
# Verificar que la aplicación responde
curl -I http://tu-dominio.com/health

# Debería devolver: HTTP/1.1 200 OK
```

---

## 🔐 **Configuración SSL**

### **Instalar Certbot**

```bash
# Instalar Certbot
sudo apt install -y certbot

# Para Nginx
sudo apt install -y python3-certbot-nginx

# Para Apache
sudo apt install -y python3-certbot-apache
```

### **Obtener Certificado SSL**

```bash
# Ejecutar script de SSL automatizado
sudo ./setup-ssl.sh tu-dominio.com admin@tudominio.com nginx

# O manualmente:

# Para Nginx
sudo certbot --nginx -d tu-dominio.com

# Para Apache
sudo certbot --apache -d tu-dominio.com
```

### **Configurar Auto-renovación**

```bash
# Verificar auto-renovación
sudo certbot renew --dry-run

# La auto-renovación ya está configurada por el script
```

---

## 📊 **Monitoreo y Mantenimiento**

### **Script de Monitoreo**

```bash
# Ver estado general
sudo bash /opt/transqa/landing-page-app/monitor-transqa.sh tu-dominio.com status

# Ver logs en tiempo real
sudo bash /opt/transqa/landing-page-app/monitor-transqa.sh tu-dominio.com logs

# Reiniciar servicios
sudo bash /opt/transqa/landing-page-app/monitor-transqa.sh tu-dominio.com restart

# Hacer backup
sudo bash /opt/transqa/landing-page-app/monitor-transqa.sh tu-dominio.com backup

# Probar endpoints
sudo bash /opt/transqa/landing-page-app/monitor-transqa.sh tu-dominio.com test
```

### **Comandos Útiles**

```bash
# Ver estado de servicios Docker
cd /opt/transqa/landing-page-app
sudo docker-compose -f docker-compose.prod.yml ps

# Ver logs específicos
sudo docker-compose -f docker-compose.prod.yml logs transqa-web
sudo docker-compose -f docker-compose.prod.yml logs languagetool

# Reiniciar servicio específico
sudo docker-compose -f docker-compose.prod.yml restart transqa-web

# Actualizar la aplicación
cd /opt/transqa
sudo git pull origin main
cd landing-page-app
sudo docker-compose -f docker-compose.prod.yml up -d --build
```

### **Logs a Monitorear**

```bash
# Logs del web server
sudo tail -f /var/log/nginx/transqa_access.log   # Nginx
sudo tail -f /var/log/apache2/transqa_access.log # Apache

# Logs de la aplicación
sudo tail -f /var/log/transqa/access.log
sudo tail -f /var/log/transqa/error.log

# Logs de Docker
cd /opt/transqa/landing-page-app
sudo docker-compose -f docker-compose.prod.yml logs -f
```

---

## 🔍 **Troubleshooting**

### **Problema: Servicios no inician**

```bash
# Verificar Docker
sudo systemctl status docker

# Verificar puertos
sudo netstat -tlnp | grep -E ':80|:443|:8000|:8081'

# Verificar logs de Docker
cd /opt/transqa/landing-page-app
sudo docker-compose -f docker-compose.prod.yml logs
```

### **Problema: Error 502 Bad Gateway**

```bash
# Verificar que TransQA esté corriendo
curl http://localhost:8000/health

# Si no responde, reiniciar servicios
cd /opt/transqa/landing-page-app
sudo docker-compose -f docker-compose.prod.yml restart

# Verificar configuración del web server
sudo nginx -t  # Para Nginx
sudo apache2ctl configtest  # Para Apache
```

### **Problema: SSL no funciona**

```bash
# Verificar certificado
sudo certbot certificates

# Renovar manualmente si es necesario
sudo certbot renew

# Verificar configuración SSL
sudo ssl-cert-check -c /etc/letsencrypt/live/tu-dominio.com/cert.pem
```

### **Problema: Alto uso de CPU/RAM**

```bash
# Verificar recursos
htop

# Ajustar configuración de LanguageTool
# Editar docker-compose.prod.yml:
# - Java_Xmx=1g  # Reducir memoria si es necesario

# Reiniciar con nueva configuración
cd /opt/transqa/landing-page-app
sudo docker-compose -f docker-compose.prod.yml up -d --force-recreate
```

---

## ✅ **Checklist de Verificación Post-Despliegue**

### **Funcionalidad Básica**
- [ ] ✅ `https://tu-dominio.com` carga correctamente
- [ ] ✅ `https://tu-dominio.com/health` devuelve status 200
- [ ] ✅ `https://tu-dominio.com/docs` muestra Swagger UI
- [ ] ✅ `https://tu-dominio.com/redoc` muestra ReDoc
- [ ] ✅ El demo de análisis funciona desde la landing page

### **Seguridad**
- [ ] ✅ SSL certificado válido y activo
- [ ] ✅ Auto-renovación SSL configurada
- [ ] ✅ Headers de seguridad configurados
- [ ] ✅ Firewall UFW activo y configurado
- [ ] ✅ Fail2ban instalado y activo

### **Performance**
- [ ] ✅ Gzip/Deflate compresión habilitada
- [ ] ✅ Cache de archivos estáticos configurado
- [ ] ✅ Rate limiting configurado para APIs
- [ ] ✅ Logs rotación configurada

### **Monitoreo**
- [ ] ✅ Script de monitoreo funcionando
- [ ] ✅ Backup automatizado configurado
- [ ] ✅ Health checks configurados
- [ ] ✅ Logs accesibles y organizados

---

## 🎉 **¡Felicidades!**

Tu instalación de TransQA está completa y lista para producción. 

### **URLs Importantes:**
- 🌐 **Landing Page**: https://tu-dominio.com
- 📋 **API Docs**: https://tu-dominio.com/docs
- 📖 **API Reference**: https://tu-dominio.com/redoc
- 🏥 **Health Check**: https://tu-dominio.com/health

### **Soporte:**
- 📖 [Documentación](../README.md)
- 🐛 [Reportar Issues](https://github.com/tu-usuario/missing-translation-app/issues)
- 💡 [Solicitar Features](https://github.com/tu-usuario/missing-translation-app/discussions)

**¡Gracias por usar TransQA!** 🚀