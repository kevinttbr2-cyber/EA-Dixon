# Backend/app.py - VERSIÓN FINAL LIMPIA
import os
import time
import logging
from flask import Flask, jsonify
from flask_cors import CORS
from config import Config
from routes import (
    auth_bp, pago_bp, catalogo_bp, flota_bp, pdf_bp, 
    auditoria_bp, gasto_bp, cierre_bp, deudor_bp, 
    venta_bp, export_bp
)
from services.auth_service import AuthService

# Establecer zona horaria a Chile
os.environ['TZ'] = 'America/Santiago'
time.tzset()

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================
# CREAR APP
# ============================
app = Flask(__name__)
app.secret_key = Config.SECRET_KEY

# ============================
# CORS
# ============================
CORS(app, 
     origins=Config.CORS_ORIGINS,
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
     allow_headers=["Content-Type", "Authorization", "X-Requested-With", "Accept"],
     supports_credentials=False)

@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response

# ============================
# REGISTRAR BLUEPRINTS
# ============================
app.register_blueprint(auth_bp)
app.register_blueprint(pago_bp)
app.register_blueprint(catalogo_bp)
app.register_blueprint(flota_bp)
app.register_blueprint(pdf_bp)
app.register_blueprint(auditoria_bp)
app.register_blueprint(gasto_bp)
app.register_blueprint(cierre_bp)
app.register_blueprint(deudor_bp)
app.register_blueprint(venta_bp)
app.register_blueprint(export_bp)

# ============================
# HEALTH CHECK
# ============================
@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({
        "status": "ok",
        "service": "backend-dixon",
        "version": "3.0",
        "blueprints": [
            "auth", "pago", "catalogo", "flota", "pdf", 
            "auditoria", "gasto", "cierre", "deudor", "venta", "export"
        ]
    })

# ============================
# CREAR ADMIN
# ============================
AuthService.crear_admin()
logger.info("🚀 Backend Dixon iniciado correctamente")

# ============================
# INICIAR
# ============================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=Config.DEBUG)
