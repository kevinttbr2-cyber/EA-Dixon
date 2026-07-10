from flask import Flask, jsonify
from flask_cors import CORS
from config import Config
from routes import auth_bp, pago_bp, catalogo_bp, flota_bp, pdf_bp, auditoria_bp
from services.auth_service import AuthService

# ============================
# CREAR APP
# ============================
app = Flask(__name__)
app.secret_key = Config.SECRET_KEY

# CORS
CORS(app, resources={r"/api/*": {"origins": "*"}})

# ============================
# REGISTRAR BLUEPRINTS
# ============================
app.register_blueprint(auth_bp)
app.register_blueprint(pago_bp)
app.register_blueprint(catalogo_bp)
app.register_blueprint(flota_bp)
app.register_blueprint(pdf_bp)
app.register_blueprint(auditoria_bp)

# ============================
# RUTA DE HEALTH CHECK
# ============================
@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({
        "status": "ok",
        "service": "backend-dixon",
        "version": "2.0"
    })

# ============================
# CREAR ADMIN AL INICIAR
# ============================
AuthService.crear_admin()

# ============================
# INICIAR
# ============================
if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
