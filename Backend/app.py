import os 
from flask import Flask, jsonify, make_response, request
from flask_cors import CORS
from config import Config
from routes import auth_bp, pago_bp, catalogo_bp, flota_bp, pdf_bp, auditoria_bp
from services.auth_service import AuthService
from models import Pago  # Importa tu modelo
import pandas as pd
from io import BytesIO

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
# RUTA 1: EXPORTAR DB (SIN BORRAR)
# ============================
@app.route('/exportar_datos', methods=['GET'])
def exportar_datos():
    """Exporta todos los registros a Excel SIN borrar nada"""
    try:
        from database import db
        from models import Pago
        import pandas as pd
        from io import BytesIO
        
        # Obtener todos los registros
        registros = Pago.query.all()
        
        if not registros:
            return jsonify({'error': 'No hay registros para exportar'}), 400
        
        # Crear DataFrame
        datos = []
        for r in registros:
            datos.append({
                'ID': r.id,
                'Cliente': r.nombre,
                'Teléfono': getattr(r, 'telefono', ''),
                'Monto': r.monto,
                'Fecha': r.fecha,
                'Hora': r.hora,
                'Patente': r.patente,
                'Marca': r.marca,
                'Modelo': r.modelo,
                'Año': getattr(r, 'anio', ''),
                'Flota': getattr(r, 'flota', ''),
                'Atendido por': r.atendido_por or r.usuario,
                'Estado': r.estado,
                'Observaciones Cliente': getattr(r, 'observaciones_cliente', ''),
                'Observaciones Pago': getattr(r, 'observaciones_pago', ''),
                'Diagnóstico': getattr(r, 'diagnostico', ''),
                'Reparación': getattr(r, 'reparacion', ''),
                'Resultado': getattr(r, 'resultado', ''),
                'Tiempo Estimado': getattr(r, 'tiempo_estimado', ''),
                'Costo Repuestos': getattr(r, 'costo_repuestos_real', 0),
                'Costo Mano Obra': getattr(r, 'costo_mano_obra_real', 0),
                'Costo Diagnóstico': getattr(r, 'costo_diagnostico_real', 0),
                'Ganancia Neta': getattr(r, 'ganancia_neta', 0),
                'Validado': getattr(r, 'validado', False),
                'Validado por': getattr(r, 'validado_por', ''),
                'Firma': getattr(r, 'firma', ''),
            })
        
        df = pd.DataFrame(datos)
        output = BytesIO()
        
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Exportacion', index=False)
            
            # Formatear columnas
            workbook = writer.book
            worksheet = writer.sheets['Exportacion']
            for i, col in enumerate(df.columns):
                column_width = max(df[col].astype(str).map(len).max(), len(col)) + 2
                worksheet.set_column(i, i, min(column_width, 50))
        
        output.seek(0)
        
        # Crear respuesta con el archivo
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        response.headers['Content-Disposition'] = 'attachment; filename=exportacion_db.xlsx'
        
        return response
        
    except Exception as e:
        print(f"❌ Error en exportar_datos: {e}")
        return jsonify({'error': str(e)}), 500


# ============================
# RUTA 2: EXPORTAR Y BORRAR DB
# ============================
@app.route('/exportar_y_borrar', methods=['POST'])
def exportar_y_borrar():
    """Exporta todos los registros a Excel y luego los elimina"""
    try:
        from database import db
        from models import Pago
        import pandas as pd
        from io import BytesIO
        
        # Obtener todos los registros
        registros = Pago.query.all()
        
        if not registros:
            return jsonify({'error': 'No hay registros para exportar'}), 400
        
        # Crear DataFrame
        datos = []
        for r in registros:
            datos.append({
                'ID': r.id,
                'Cliente': r.nombre,
                'Teléfono': getattr(r, 'telefono', ''),
                'Monto': r.monto,
                'Fecha': r.fecha,
                'Hora': r.hora,
                'Patente': r.patente,
                'Marca': r.marca,
                'Modelo': r.modelo,
                'Año': getattr(r, 'anio', ''),
                'Flota': getattr(r, 'flota', ''),
                'Atendido por': r.atendido_por or r.usuario,
                'Estado': r.estado,
                'Observaciones Cliente': getattr(r, 'observaciones_cliente', ''),
                'Observaciones Pago': getattr(r, 'observaciones_pago', ''),
                'Diagnóstico': getattr(r, 'diagnostico', ''),
                'Reparación': getattr(r, 'reparacion', ''),
                'Resultado': getattr(r, 'resultado', ''),
                'Tiempo Estimado': getattr(r, 'tiempo_estimado', ''),
                'Costo Repuestos': getattr(r, 'costo_repuestos_real', 0),
                'Costo Mano Obra': getattr(r, 'costo_mano_obra_real', 0),
                'Costo Diagnóstico': getattr(r, 'costo_diagnostico_real', 0),
                'Ganancia Neta': getattr(r, 'ganancia_neta', 0),
                'Validado': getattr(r, 'validado', False),
                'Validado por': getattr(r, 'validado_por', ''),
                'Firma': getattr(r, 'firma', ''),
            })
        
        df = pd.DataFrame(datos)
        output = BytesIO()
        
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Backup', index=False)
            
            workbook = writer.book
            worksheet = writer.sheets['Backup']
            for i, col in enumerate(df.columns):
                column_width = max(df[col].astype(str).map(len).max(), len(col)) + 2
                worksheet.set_column(i, i, min(column_width, 50))
        
        output.seek(0)
        
        # Crear respuesta con el archivo
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        response.headers['Content-Disposition'] = 'attachment; filename=backup_antes_borrar.xlsx'
        
        # BORRAR TODOS LOS REGISTROS
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
