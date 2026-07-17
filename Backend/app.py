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
# RUTA DE PRUEBA PARA NOTIFICACIONES (CORREGIDA)
# ============================
@app.route('/api/test_notificacion', methods=['GET'])
def test_notificacion():
    """Ruta para probar notificaciones push desde el navegador"""
    try:
        from services.notification_service import enviar_notificacion_push
        
        print("📨 TEST_NOTIFICACION - Iniciando prueba...")
        
        enviados = enviar_notificacion_push(
            titulo="🔔 Notificación de Prueba (Backend)",
            mensaje="¡Las notificaciones push funcionan correctamente desde el backend!",
            url="/estado"
        )
        
        print(f"📱 TEST_NOTIFICACION - Enviados: {enviados}")
        
        if enviados > 0:
            return jsonify({
                "success": True,
                "mensaje": f"Notificación enviada a {enviados} dispositivos"
            })
        else:
            return jsonify({
                "success": False,
                "mensaje": "No hay dispositivos suscritos. Acepta las notificaciones en tu navegador."
            })
    except Exception as e:
        print(f"❌ TEST_NOTIFICACION - Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
# ============================================
# RUTAS PARA GESTIÓN DE GASTOS Y CIERRE DE CAJA
# ============================================

# ============================================
# REGISTRAR GASTO (VERSIÓN ACTUALIZADA)
# ============================================
@app.route('/api/gastos', methods=['POST'])
def registrar_gasto():
    """Registra un nuevo gasto (efectivo o transferencia) con datos de factura"""
    try:
        data = request.json
        
        # Validar datos obligatorios
        if not data.get('categoria') or not data.get('monto'):
            return jsonify({"error": "Categoría y monto son obligatorios"}), 400
        
        # Obtener conexión a la base de datos
        from database import get_connection
        conn = get_connection()
        cur = conn.cursor()
        
        # Insertar gasto (con nuevos campos)
        cur.execute("""
            INSERT INTO gastos 
            (categoria, monto, metodo_pago, descripcion, proveedor, folio, fecha, hora, registrado_por)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            data.get('categoria'),
            float(data.get('monto', 0)),
            data.get('metodo_pago', 'efectivo'),
            data.get('descripcion', ''),
            data.get('proveedor', ''),
            data.get('folio', ''),
            data.get('fecha'),
            data.get('hora'),
            data.get('registrado_por', 'Sistema')
        ))
        
        id_gasto = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        
        print(f"✅ Gasto registrado ID: {id_gasto}")
        return jsonify({"success": True, "id": id_gasto})
        
    except Exception as e:
        print(f"❌ Error en registrar_gasto: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# ============================================
# 2. OBTENER GASTOS POR FECHA
# ============================================
@app.route('/api/gastos', methods=['GET'])
def obtener_gastos():
    """Obtiene todos los gastos de una fecha específica"""
    try:
        fecha = request.args.get('fecha')
        if not fecha:
            return jsonify({"error": "Fecha requerida"}), 400
        
        from database import get_cursor
        conn, cur = get_cursor()
        
        cur.execute("""
            SELECT * FROM gastos 
            WHERE fecha = %s 
            ORDER BY hora DESC
        """, (fecha,))
        
        gastos = [dict(row) for row in cur.fetchall()]
        cur.close()
        conn.close()
        
        return jsonify(gastos)
        
    except Exception as e:
        print(f"❌ Error en obtener_gastos: {e}")
        return jsonify({"error": str(e)}), 500


# ============================================
# 3. INICIAR CIERRE DE CAJA
# ============================================
@app.route('/api/cierre_caja', methods=['POST'])
def iniciar_cierre_caja():
    """Crea o actualiza el cierre de caja del día"""
    try:
        data = request.json
        fecha = data.get('fecha')
        efectivo_inicial = float(data.get('efectivo_inicial', 0))
        
        if not fecha:
            return jsonify({"error": "Fecha requerida"}), 400
        
        from database import get_connection
        conn = get_connection()
        cur = conn.cursor()
        
        # Verificar si ya existe cierre para hoy
        cur.execute("SELECT id FROM cierres_caja WHERE fecha = %s", (fecha,))
        existente = cur.fetchone()
        
        if existente:
            # Actualizar si ya existe
            cur.execute("""
                UPDATE cierres_caja 
                SET efectivo_inicial = %s, 
                    estado = 'abierto',
                    updated_at = NOW() AT TIME ZONE 'America/Santiago'
                WHERE fecha = %s
                RETURNING id
            """, (efectivo_inicial, fecha))
        else:
            # Crear nuevo
            cur.execute("""
                INSERT INTO cierres_caja (fecha, efectivo_inicial, estado)
                VALUES (%s, %s, 'abierto')
                RETURNING id
            """, (fecha, efectivo_inicial))
        
        id_cierre = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({"success": True, "id": id_cierre})
        
    except Exception as e:
        print(f"❌ Error en iniciar_cierre_caja: {e}")
        return jsonify({"error": str(e)}), 500


# ============================================
# 4. OBTENER CIERRE DE CAJA
# ============================================
@app.route('/api/cierre_caja/<fecha>', methods=['GET'])
def obtener_cierre_caja(fecha):
    """Obtiene los datos del cierre de caja para una fecha"""
    try:
        from database import get_cursor
        conn, cur = get_cursor()
        
        # Obtener cierre
        cur.execute("SELECT * FROM cierres_caja WHERE fecha = %s", (fecha,))
        cierre = cur.fetchone()
        
        if not cierre:
            cur.close()
            conn.close()
            return jsonify({"error": "No hay cierre para esta fecha"}), 404
        
        cierre_dict = dict(cierre)
        
        # Calcular ventas en efectivo del día
        cur.execute("""
            SELECT COALESCE(SUM(monto), 0) as total
            FROM pagos 
            WHERE fecha = %s AND forma_pago = 'efectivo' AND estado = 'pagado'
        """, (fecha,))
        ventas_efectivo = cur.fetchone()[0] or 0
        
        # Calcular gastos en efectivo del día
        cur.execute("""
            SELECT COALESCE(SUM(monto), 0) as total
            FROM gastos 
            WHERE fecha = %s AND metodo_pago = 'efectivo'
        """, (fecha,))
        gastos_efectivo = cur.fetchone()[0] or 0
        
        # Calcular efectivo esperado
        efectivo_esperado = float(cierre_dict.get('efectivo_inicial', 0)) + float(ventas_efectivo) - float(gastos_efectivo)
        
        cur.close()
        conn.close()
        
        return jsonify({
            "cierre": cierre_dict,
            "ventas_efectivo": ventas_efectivo,
            "gastos_efectivo": gastos_efectivo,
            "efectivo_esperado": efectivo_esperado
        })
        
    except Exception as e:
        print(f"❌ Error en obtener_cierre_caja: {e}")
        return jsonify({"error": str(e)}), 500


# ============================================
# 5. CERRAR CAJA DEL DÍA
# ============================================
@app.route('/api/cierre_caja/<fecha>/cerrar', methods=['POST'])
def cerrar_caja(fecha):
    """Cierra la caja del día con el efectivo real contado"""
    try:
        data = request.json
        efectivo_real = float(data.get('efectivo_real', 0))
        observaciones = data.get('observaciones', '')
        cerrado_por = data.get('cerrado_por', 'Sistema')
        
        from database import get_connection
        conn = get_connection()
        cur = conn.cursor()
        
        # Obtener cierre
        cur.execute("SELECT * FROM cierres_caja WHERE fecha = %s AND estado = 'abierto'", (fecha,))
        cierre = cur.fetchone()
        
        if not cierre:
            cur.close()
            conn.close()
            return jsonify({"error": "No hay cierre abierto para esta fecha"}), 404
        
        cierre_dict = dict(cierre)
        
        # Recalcular
        cur.execute("""
            SELECT COALESCE(SUM(monto), 0) as total
            FROM pagos 
            WHERE fecha = %s AND forma_pago = 'efectivo' AND estado = 'pagado'
        """, (fecha,))
        ventas_efectivo = cur.fetchone()[0] or 0
        
        cur.execute("""
            SELECT COALESCE(SUM(monto), 0) as total
            FROM gastos 
            WHERE fecha = %s AND metodo_pago = 'efectivo'
        """, (fecha,))
        gastos_efectivo = cur.fetchone()[0] or 0
        
        efectivo_esperado = float(cierre_dict['efectivo_inicial']) + float(ventas_efectivo) - float(gastos_efectivo)
        diferencia = float(efectivo_real) - float(efectivo_esperado)
        
        # Actualizar cierre
        cur.execute("""
            UPDATE cierres_caja 
            SET ventas_efectivo = %s,
                gastos_efectivo = %s,
                efectivo_esperado = %s,
                efectivo_real = %s,
                diferencia = %s,
                estado = 'cerrado',
                cerrado_por = %s,
                cerrado_en = NOW() AT TIME ZONE 'America/Santiago',
                observaciones = %s
            WHERE fecha = %s AND estado = 'abierto'
        """, (
            ventas_efectivo,
            gastos_efectivo,
            efectivo_esperado,
            efectivo_real,
            diferencia,
            cerrado_por,
            observaciones,
            fecha
        ))
        
        conn.commit()
        cur.close()
        conn.close()
        
        mensaje = "✅ Caja cerrada correctamente"
        if diferencia > 0:
            mensaje += f" (Sobrante: ${diferencia:,.0f})"
        elif diferencia < 0:
            mensaje += f" (Faltante: ${abs(diferencia):,.0f})"
        else:
            mensaje += " - ¡Caja perfectamente cuadrada!"
        
        return jsonify({
            "success": True,
            "mensaje": mensaje,
            "efectivo_esperado": efectivo_esperado,
            "efectivo_real": efectivo_real,
            "diferencia": diferencia
        })
        
    except Exception as e:
        print(f"❌ Error en cerrar_caja: {e}")
        return jsonify({"error": str(e)}), 500


# ============================================
# 6. HISTORIAL DE CIERRES
# ============================================
@app.route('/api/historial_cierres', methods=['GET'])
def historial_cierres():
    """Obtiene el historial de cierres de caja"""
    try:
        from database import get_cursor
        conn, cur = get_cursor()
        
        cur.execute("""
            SELECT * FROM cierres_caja 
            WHERE estado = 'cerrado'
            ORDER BY fecha DESC
            LIMIT 30
        """)
        
        historial = [dict(row) for row in cur.fetchall()]
        cur.close()
        conn.close()
        
        return jsonify(historial)
        
    except Exception as e:
        print(f"❌ Error en historial_cierres: {e}")
        return jsonify({"error": str(e)}), 500



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
