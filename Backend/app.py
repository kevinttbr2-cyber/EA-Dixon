import os 
from flask import Flask, jsonify, make_response, request
from flask_cors import CORS
from config import Config
from routes import auth_bp, pago_bp, catalogo_bp, flota_bp, pdf_bp, auditoria_bp
from services.auth_service import AuthService
import time

# Establecer zona horaria a Chile (UTC-3)
os.environ['TZ'] = 'America/Santiago'
time.tzset()

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
# RUTA 1: EXPORTAR DB (SIN BORRAR) - SIN PANDAS
# ============================
@app.route('/exportar_datos', methods=['GET'])
def exportar_datos():
    """Exporta todos los registros a Excel SIN borrar nada"""
    try:
        from database import db
        from models import Pago
        from openpyxl import Workbook
        from io import BytesIO
        
        registros = Pago.query.all()
        
        if not registros:
            return jsonify({'error': 'No hay registros para exportar'}), 400
        
        wb = Workbook()
        ws = wb.active
        ws.title = "Exportacion"
        
        headers = [
            'ID', 'Cliente', 'Teléfono', 'Monto', 'Fecha', 'Hora',
            'Patente', 'Marca', 'Modelo', 'Año', 'Flota',
            'Atendido por', 'Estado', 'Observaciones Cliente',
            'Observaciones Pago', 'Diagnóstico', 'Reparación',
            'Resultado', 'Tiempo Estimado', 'Costo Repuestos',
            'Costo Mano Obra', 'Costo Diagnóstico', 'Ganancia Neta',
            'Validado', 'Validado por', 'Firma'
        ]
        ws.append(headers)
        
        for r in registros:
            ws.append([
                r.id,
                r.nombre,
                getattr(r, 'telefono', ''),
                r.monto,
                r.fecha,
                r.hora,
                r.patente,
                r.marca,
                r.modelo,
                getattr(r, 'anio', ''),
                getattr(r, 'flota', ''),
                r.atendido_por or r.usuario,
                r.estado,
                getattr(r, 'observaciones_cliente', ''),
                getattr(r, 'observaciones_pago', ''),
                getattr(r, 'diagnostico', ''),
                getattr(r, 'reparacion', ''),
                getattr(r, 'resultado', ''),
                getattr(r, 'tiempo_estimado', ''),
                getattr(r, 'costo_repuestos_real', 0),
                getattr(r, 'costo_mano_obra_real', 0),
                getattr(r, 'costo_diagnostico_real', 0),
                getattr(r, 'ganancia_neta', 0),
                getattr(r, 'validado', False),
                getattr(r, 'validado_por', ''),
                getattr(r, 'firma', ''),
            ])
        
        output = BytesIO()
        wb.save(output)
        output.seek(0)
        
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        response.headers['Content-Disposition'] = 'attachment; filename=exportacion_db.xlsx'
        
        return response
        
    except Exception as e:
        print(f"❌ Error en exportar_datos: {e}")
        return jsonify({'error': str(e)}), 500


# ============================
# RUTA 2: EXPORTAR Y BORRAR DB - SIN PANDAS
# ============================
@app.route('/exportar_y_borrar', methods=['POST'])
def exportar_y_borrar():
    """Exporta todos los registros a Excel y luego los elimina"""
    try:
        from database import db
        from models import Pago
        from openpyxl import Workbook
        from io import BytesIO
        
        registros = Pago.query.all()
        
        if not registros:
            return jsonify({'error': 'No hay registros para exportar'}), 400
        
        wb = Workbook()
        ws = wb.active
        ws.title = "Backup"
        
        headers = [
            'ID', 'Cliente', 'Teléfono', 'Monto', 'Fecha', 'Hora',
            'Patente', 'Marca', 'Modelo', 'Año', 'Flota',
            'Atendido por', 'Estado', 'Observaciones Cliente',
            'Observaciones Pago', 'Diagnóstico', 'Reparación',
            'Resultado', 'Tiempo Estimado', 'Costo Repuestos',
            'Costo Mano Obra', 'Costo Diagnóstico', 'Ganancia Neta',
            'Validado', 'Validado por', 'Firma'
        ]
        ws.append(headers)
        
        for r in registros:
            ws.append([
                r.id,
                r.nombre,
                getattr(r, 'telefono', ''),
                r.monto,
                r.fecha,
                r.hora,
                r.patente,
                r.marca,
                r.modelo,
                getattr(r, 'anio', ''),
                getattr(r, 'flota', ''),
                r.atendido_por or r.usuario,
                r.estado,
                getattr(r, 'observaciones_cliente', ''),
                getattr(r, 'observaciones_pago', ''),
                getattr(r, 'diagnostico', ''),
                getattr(r, 'reparacion', ''),
                getattr(r, 'resultado', ''),
                getattr(r, 'tiempo_estimado', ''),
                getattr(r, 'costo_repuestos_real', 0),
                getattr(r, 'costo_mano_obra_real', 0),
                getattr(r, 'costo_diagnostico_real', 0),
                getattr(r, 'ganancia_neta', 0),
                getattr(r, 'validado', False),
                getattr(r, 'validado_por', ''),
                getattr(r, 'firma', ''),
            ])
        
        output = BytesIO()
        wb.save(output)
        output.seek(0)
        
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        response.headers['Content-Disposition'] = 'attachment; filename=backup_antes_borrar.xlsx'
        
        try:
            Pago.query.delete()
            db.session.commit()
            print(f"✅ {len(registros)} registros eliminados correctamente")
        except Exception as e:
            db.session.rollback()
            print(f"⚠️ Error al borrar registros: {e}")
        
        return response
        
    except Exception as e:
        print(f"❌ Error en exportar_y_borrar: {e}")
        return jsonify({'error': str(e)}), 500


# ============================
# RUTA DE PRUEBA PARA NOTIFICACIONES
# ============================
@app.route('/api/test_notificacion', methods=['GET'])
def test_notificacion():
    """Ruta para probar notificaciones push desde el backend"""
    try:
        from services.notification_service import enviar_notificacion_push
        
        enviados = enviar_notificacion_push(
            titulo="🔔 Notificación de Prueba (Backend)",
            mensaje="¡Las notificaciones push funcionan correctamente desde el backend!",
            url="/estado"
        )
        
        if enviados > 0:
            return jsonify({
                "success": True,
                "mensaje": f"Notificación enviada a {enviados} dispositivos"
            })
        else:
            return jsonify({
                "success": False,
                "mensaje": "No hay dispositivos suscritos."
            })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ============================
# CREAR ADMIN AL INICIAR
# ============================
AuthService.crear_admin()

# ============================
# INICIAR
# ============================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
