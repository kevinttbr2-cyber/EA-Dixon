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
# NUEVA RUTA: EXPORTAR Y BORRAR DB
# ============================
@app.route('/exportar_y_borrar', methods=['POST'])
def exportar_y_borrar():
    """Exporta todos los registros a Excel y luego los elimina"""
    try:
        from services.pago_service import PagoService
        from database import db
        
        # 1. Obtener todos los registros
        registros = PagoService.obtener_todos()  # Tu función
        
        if not registros:
            return jsonify({'error': 'No hay registros para exportar'}), 400
        
        # 2. Crear DataFrame para Excel
        datos = []
        for r in registros:
            datos.append({
                'ID': r.id,
                'Cliente': r.nombre,
                'Monto': r.monto,
                'Fecha': r.fecha,
                'Hora': r.hora,
                'Patente': r.patente,
                'Marca': r.marca,
                'Modelo': r.modelo,
                'Atendido por': r.atendido_por or r.usuario,
                'Estado': r.estado,
                'Observaciones Cliente': r.observaciones_cliente,
                'Observaciones Pago': r.observaciones_pago,
                'Diagnóstico': r.diagnostico,
                'Reparación': r.reparacion,
                'Resultado': r.resultado,
                'Costo Repuestos': r.costo_repuestos_real,
                'Costo Mano Obra': r.costo_mano_obra_real,
                'Costo Diagnóstico': r.costo_diagnostico_real,
                'Ganancia Neta': r.ganancia_neta,
            })
        
        df = pd.DataFrame(datos)
        
        # 3. Crear archivo Excel en memoria
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Backup', index=False)
            
            # Formatear columnas
            workbook = writer.book
            worksheet = writer.sheets['Backup']
            
            # Autoajustar ancho de columnas
            for i, col in enumerate(df.columns):
                column_width = max(df[col].astype(str).map(len).max(), len(col)) + 2
                worksheet.set_column(i, i, min(column_width, 50))
        
        output.seek(0)
        
        # 4. Crear respuesta con el archivo
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        response.headers['Content-Disposition'] = 'attachment; filename=backup_antes_borrar.xlsx'
        
        # 5. BORRAR TODOS LOS REGISTROS (después de generar el archivo)
        try:
            PagoService.eliminar_todos()  # Tu función
        except Exception as e:
            print(f"⚠️ Error al borrar registros: {e}")
            # No fallamos la exportación si el borrado falla
        
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
