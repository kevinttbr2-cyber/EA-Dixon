# Backend/config.py
import os

class Config:
    """Configuración centralizada para el backend"""
    
    # Claves de seguridad
    SECRET_KEY = os.environ.get("SECRET_KEY")
    if not SECRET_KEY:
        raise ValueError("❌ SECRET_KEY no configurada en el entorno")
    
    PDF_SECRET_KEY = os.environ.get("PDF_SECRET_KEY")
    if not PDF_SECRET_KEY:
        raise ValueError("❌ PDF_SECRET_KEY no configurada en el entorno")
    
    # Base de datos (Neon)
    DATABASE_URL = os.environ.get("DATABASE_URL")
    if not DATABASE_URL:
        raise ValueError("❌ DATABASE_URL no configurada en el entorno")
    
    # WhatsApp / Twilio (opcional)
    TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
    TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
    TWILIO_WHATSAPP_FROM = os.environ.get("TWILIO_WHATSAPP_FROM")
    
    # Admin por defecto
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")
    
    # CORS - URLs permitidas
    FRONTEND_URL = os.environ.get("FRONTEND_URL", "https://dixon-e-automotriz.vercel.app")
    CORS_ORIGINS = [
        FRONTEND_URL,
        "https://ea-dixon.vercel.app",
        "https://ea-dixon-ktb2.vercel.app",
        "http://localhost:3000",
        "http://localhost:5000"
    ]
    
    # Zona horaria
    TIMEZONE = "America/Santiago"
    
    # Modo debug
    DEBUG = os.environ.get("FLASK_DEBUG", "False").lower() == "true"
