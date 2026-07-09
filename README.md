# 🚗 Dixon Electricidad Automotriz

Sistema de gestión de taller automotriz con arquitectura moderna.

## 🏗️ Arquitectura

- **Frontend**: Vercel (Flask + HTML/CSS/JS)
- **Backend**: Railway (Flask API)
- **Base de datos**: Neon (PostgreSQL)

## 📁 Estructura del Proyecto
/
├── backend/ # API para Railway
│ ├── app.py # Punto de entrada
│ ├── config.py # Configuración
│ ├── requirements.txt
│ ├── runtime.txt
│ └── .env.example
│
├── frontend/ # Frontend para Vercel
│ ├── app.py # Renderiza HTML
│ ├── vercel.json # Config Vercel
│ ├── requirements.txt
│ ├── runtime.txt
│ ├── static/ # CSS, JS, imágenes
│ └── templates/ # Templates HTML
│
├── catalogo.txt # Catálogo de vehículos
├── .gitignore
└── README.md

## 🚀 Despliegue

### 1. Base de datos (Neon)

1. Crear cuenta en [Neon](https://neon.tech)
2. Crear proyecto y obtener `DATABASE_URL`
3. Ejecutar el SQL de creación de tablas

### 2. Backend (Railway)

1. Conectar repositorio a Railway
2. Seleccionar carpeta `backend/`
3. Configurar variables de entorno:
   - `DATABASE_URL`
   - `SECRET_KEY`
   - `PDF_SECRET_KEY`
   - `ADMIN_PASSWORD`
   - `FRONTEND_URL`

### 3. Frontend (Vercel)

1. Conectar repositorio a Vercel
2. Seleccionar carpeta `frontend/`
3. Configurar variable de entorno:
   - `BACKEND_URL` = URL de Railway

## 🔑 Credenciales por defecto

- **Usuario**: `admin`
- **Contraseña**: `admin123`

## 📱 Funcionalidades

- ✅ Gestión de clientes
- ✅ Registro de pagos
- ✅ Generación de PDF (Orden de Trabajo)
- ✅ WhatsApp automático
- ✅ Dashboard de ventas
- ✅ Gestión de flotas
- ✅ Auditoría de descargas
- ✅ PWA (Progressive Web App)

## 🛠️ Tecnologías

- Flask 3.0
- PostgreSQL (Neon)
- Bootstrap 5
- ReportLab (PDFs)
- Twilio (WhatsApp)
- Bcrypt (Seguridad)

## 📧 Contacto

**Dixon Electricidad Automotriz**
📱 +569 9855 0331
📍 Neptuno 163, Local C, Lo Prado, RM, Chile