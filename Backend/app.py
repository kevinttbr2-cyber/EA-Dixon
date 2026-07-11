import os 
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
FRONTEND_URL = os.environ.get("FRONTEND_URL", "https://ea-dixon.vercel.app")

CORS(app, origins=[
    FRONTEND_URL,
    "https://ea-dixon-ktb2.vercel.app",
    "https://ea-dixon-oz4bkkn90-ktb2.vercel.app",
    "https://*.vercel.app",
    "http://localhost:3000",
    "http://localhost:5000"
])
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
# RUTA: AUDITORÍA DE DESCARGAS (BACKEND)
# ============================
@app.route("/api/auditoria_descargas")
@login_required
@requiere_roles("admin", "operador")
def api_auditoria_descargas():
    """API para obtener el historial de descargas"""
    try:
        from database import obtener_historial_descargas
        
        print(f"🔍 [api_auditoria_descargas] Obteniendo historial...")
        historial = obtener_historial_descargas(200)
        
        print(f"🔍 [api_auditoria_descargas] Historial obtenido: {len(historial)} registros")
        
        # Convertir fechas a string para JSON
        for item in historial:
            if item.get('fecha'):
                item['fecha'] = item['fecha'].isoformat()
        
        return jsonify({
            "success": True,
            "historial": historial
        })
        
    except Exception as e:
        import traceback
        print(f"❌ Error en api_auditoria_descargas: {e}")
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ============================
# RUTA: AUDITORÍA PÚBLICA (PARA PRUEBAS - OPCIONAL)
# ============================
@app.route("/auditoria_simple")
@login_required
@requiere_roles("admin", "operador")
def auditoria_simple():
    """Vista simple de auditoría para diagnóstico (solo backend)"""
    from database import obtener_historial_descargas
    historial = obtener_historial_descargas(200)
    
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Auditoría Simple</title>
        <style>
            body { background: #0a0a0a; color: #fff; font-family: Arial, sans-serif; padding: 20px; }
            table { width: 100%; border-collapse: collapse; }
            th { background: #00ff66; color: #000; padding: 10px; }
            td { padding: 8px; border-bottom: 1px solid #333; }
            .total { background: rgba(0,255,102,0.1); padding: 10px; border-radius: 8px; margin-bottom: 20px; }
            .error { color: #ff6b6b; background: rgba(255,107,107,0.1); padding: 15px; border-radius: 8px; }
        </style>
    </head>
    <body>
        <h1 style="color: #00ff66;">📊 Auditoría de Descargas (Diagnóstico)</h1>
        <div class="total">
            <strong>Total registros:</strong> """ + str(len(historial)) + """
        </div>
    """
    
    if historial:
        html += """
        <table>
            <tr>
                <th>#</th>
                <th>OT</th>
                <th>Cliente</th>
                <th>Usuario</th>
                <th>Rol</th>
                <th>Tipo</th>
                <th>Fecha</th>
                <th>Firma</th>
                <th>Enlace</th>
            </tr>
        """
        for i, item in enumerate(historial, 1):
            enlace = f"/orden_trabajo_publico/{item['id_registro']}/{item.get('firma', '')}" if item.get('id_registro') else '#'
            html += f"""
            <tr>
                <td>{i}</td>
                <td>#{item.get('id_registro', 'N/A')}</td>
                <td>{item.get('cliente', 'N/A')}</td>
                <td>{item.get('usuario', 'N/A')}</td>
                <td>{item.get('rol', 'N/A')}</td>
                <td>{item.get('tipo', 'N/A')}</td>
                <td>{item.get('fecha', '').strftime('%d/%m/%Y %H:%M') if item.get('fecha') else ''}</td>
                <td style="font-size: 10px; font-family: monospace;">{item.get('firma', 'SIN FIRMA')}</td>
                <td><a href="{enlace}" target="_blank" style="color: #00ff66;">🔗 Ver</a></td>
            </tr>
            """
        html += "</table>"
    else:
        html += '<div class="error">⚠️ No hay descargas registradas en la base de datos</div>'
    
    html += """
        <p><a href="/estado" style="color: #00ff66;">← Volver al Estado</a></p>
    </body>
    </html>
    """
    
    return html


# ============================
# INICIAR
# ============================
if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
