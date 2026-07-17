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
# ============================================
# RUTAS PARA PROVEEDORES
# ============================================

@app.route('/api/proveedores', methods=['GET'])
def obtener_proveedores():
    try:
        from database import get_cursor
        conn, cur = get_cursor()
        cur.execute("SELECT * FROM proveedores ORDER BY nombre")
        proveedores = [dict(row) for row in cur.fetchall()]
        cur.close()
        conn.close()
        return jsonify(proveedores)
    except Exception as e:
        print(f"❌ Error en obtener_proveedores: {e}")
        return jsonify([])

@app.route('/api/proveedores', methods=['POST'])
def crear_proveedor():
    try:
        data = request.json
        from database import get_connection
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO proveedores (nombre, rut, telefono, email, direccion, giro)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            data.get('nombre'),
            data.get('rut'),
            data.get('telefono'),
            data.get('email'),
            data.get('direccion'),
            data.get('giro', 'repuestos')
        ))
        id_proveedor = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"success": True, "id": id_proveedor})
    except Exception as e:
        print(f"❌ Error en crear_proveedor: {e}")
        return jsonify({"error": str(e)}), 500

# ============================================
# RUTAS PARA EMPLEADOS / PLANILLA DE SUELDOS
# ============================================

@app.route('/api/empleados', methods=['GET'])
def obtener_empleados():
    try:
        from database import get_cursor
        conn, cur = get_cursor()
        cur.execute("SELECT * FROM empleados WHERE activo = TRUE ORDER BY nombre")
        empleados = [dict(row) for row in cur.fetchall()]
        cur.close()
        conn.close()
        return jsonify(empleados)
    except Exception as e:
        print(f"❌ Error en obtener_empleados: {e}")
        return jsonify([])

@app.route('/api/empleados', methods=['POST'])
def crear_empleado():
    try:
        data = request.json
        from database import get_connection
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO empleados (nombre, rut, cargo, sueldo_base)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """, (
            data.get('nombre'),
            data.get('rut'),
            data.get('cargo'),
            data.get('sueldo_base', 0)
        ))
        id_empleado = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"success": True, "id": id_empleado})
    except Exception as e:
        print(f"❌ Error en crear_empleado: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/planilla_sueldos', methods=['POST'])
def registrar_planilla():
    try:
        data = request.json
        from database import get_connection
        conn = get_connection()
        cur = conn.cursor()
        
        for empleado in data.get('empleados', []):
            cur.execute("""
                INSERT INTO planilla_sueldos 
                (empleado_id, mes, anio, sueldo_base, comision, horas_extras, bonos, descuentos, sueldo_neto, pagado, fecha_pago)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                empleado.get('id'),
                data.get('mes'),
                data.get('anio'),
                empleado.get('sueldo_base', 0),
                empleado.get('comision', 0),
                empleado.get('horas_extras', 0),
                empleado.get('bonos', 0),
                empleado.get('descuentos', 0),
                empleado.get('sueldo_neto', 0),
                data.get('pagado', False),
                data.get('fecha_pago')
            ))
        
        conn.commit()
        cur.close()
        conn.close()
        
        # Registrar el gasto total como un gasto de sueldos
        total_sueldos = sum(e.get('sueldo_neto', 0) for e in data.get('empleados', []))
        if total_sueldos > 0:
            # Llamar a la función de registrar gasto
            registrar_gasto_interno({
                'categoria': 'Sueldos',
                'monto': total_sueldos,
                'metodo_pago': 'transferencia',
                'descripcion': f"Planilla {data.get('mes')}/{data.get('anio')}",
                'fecha': data.get('fecha_pago'),
                'hora': datetime.now().strftime('%H:%M:%S'),
                'registrado_por': data.get('registrado_por', 'Sistema'),
                'es_planilla': True
            })
        
        return jsonify({"success": True})
    except Exception as e:
        print(f"❌ Error en registrar_planilla: {e}")
        return jsonify({"error": str(e)}), 500
# ============================================
# ELIMINAR EMPLEADO
# ============================================
@app.route('/api/empleados/<int:id_empleado>', methods=['DELETE'])
def eliminar_empleado(id_empleado):
    """Elimina un empleado (borrado lógico)"""
    try:
        from database import get_connection
        conn = get_connection()
        cur = conn.cursor()
        
        # Verificar si existe
        cur.execute("SELECT id FROM empleados WHERE id = %s", (id_empleado,))
        if not cur.fetchone():
            cur.close()
            conn.close()
            return jsonify({"error": "Empleado no encontrado"}), 404
        
        # Eliminar (borrado lógico)
        cur.execute("""
            UPDATE empleados 
            SET activo = FALSE, 
                updated_at = NOW() AT TIME ZONE 'America/Santiago'
            WHERE id = %s
        """, (id_empleado,))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({"success": True, "mensaje": "Empleado eliminado correctamente"})
        
    except Exception as e:
        print(f"❌ Error en eliminar_empleado: {e}")
        return jsonify({"error": str(e)}), 500


# ============================================
# ELIMINAR EMPLEADO DE LA PLANILLA (borrado físico)
# ============================================
@app.route('/api/planilla_sueldos/empleado/<int:id_empleado>', methods=['DELETE'])
def eliminar_empleado_planilla(id_empleado):
    """Elimina un empleado de la planilla actual (borrado físico)"""
    try:
        from database import get_connection
        conn = get_connection()
        cur = conn.cursor()
        
        # Verificar si existe en la planilla
        cur.execute("""
            SELECT id FROM planilla_sueldos 
            WHERE empleado_id = %s AND mes = %s AND anio = %s
        """, (
            id_empleado, 
            datetime.now().month, 
            datetime.now().year
        ))
        
        if cur.fetchone():
            # Eliminar de la planilla
            cur.execute("""
                DELETE FROM planilla_sueldos 
                WHERE empleado_id = %s AND mes = %s AND anio = %s
            """, (
                id_empleado, 
                datetime.now().month, 
                datetime.now().year
            ))
            conn.commit()
        
        # También podemos desactivar al empleado
        cur.execute("""
            UPDATE empleados 
            SET activo = FALSE,
                updated_at = NOW() AT TIME ZONE 'America/Santiago'
            WHERE id = %s
        """, (id_empleado,))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({"success": True, "mensaje": "Empleado eliminado de la planilla"})
        
    except Exception as e:
        print(f"❌ Error en eliminar_empleado_planilla: {e}")
        return jsonify({"error": str(e)}), 500
# ============================================
# OBTENER EMPLEADOS ACTIVOS
# ============================================
@app.route('/api/empleados/activos', methods=['GET'])
def obtener_empleados_activos():
    try:
        from database import get_cursor
        conn, cur = get_cursor()
        cur.execute("""
            SELECT * FROM empleados 
            WHERE activo = TRUE 
            ORDER BY nombre
        """)
        empleados = [dict(row) for row in cur.fetchall()]
        cur.close()
        conn.close()
        return jsonify(empleados)
    except Exception as e:
        print(f"❌ Error en obtener_empleados_activos: {e}")
        return jsonify([])


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
