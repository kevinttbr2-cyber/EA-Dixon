import os

class Config:
    """Configuración centralizada para el backend"""
    
    # Claves de seguridad
    SECRET_KEY = os.environ.get("SECRET_KEY", "clave_backend_2025")
    PDF_SECRET_KEY = os.environ.get("PDF_SECRET_KEY", "clave_pdf_2025")
    
    # Base de datos (Neon)
    DATABASE_URL = os.environ.get("postgresql://neondb_owner:npg_PZQ3mC5tXLTx@ep-curly-union-atldi73v-pooler.c-9.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require")
    
    # WhatsApp / Twilio
    TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
    TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
    TWILIO_WHATSAPP_FROM = os.environ.get("TWILIO_WHATSAPP_FROM")
    
    # Admin por defecto
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")
    
    # CORS - URLs permitidas
    FRONTEND_URL = os.environ.get("FRONTEND_URL", "https://dixon-e-automotriz.vercel.app")
    CORS_ORIGINS = [
        FRONTEND_URL,
        "http://localhost:3000",
        "http://localhost:5000"
    ]
    
    # Zona horaria
    TIMEZONE = "America/Santiago"
    
    # Modo debug
    DEBUG = os.environ.get("FLASK_DEBUG", "False").lower() == "true"