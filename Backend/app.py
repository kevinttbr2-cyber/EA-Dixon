# ============================================
# AGREGAR ESTAS IMPORTACIONES AL INICIO
# ============================================
import os
from flask import Flask, jsonify, make_response, request, send_file
from flask_cors import CORS
from config import Config
from routes import auth_bp, pago_bp, catalogo_bp, flota_bp, pdf_bp, auditoria_bp
from services.auth_service import AuthService
import time
import math
import json
import re
from datetime import datetime
import unicodedata  # ← NUEVO: Para normalizar tildes

# Establecer zona horaria a Chile (UTC-3)
os.environ['TZ'] = 'America/Santiago'
time.tzset()

# ============================
# CREAR APP
# ============================
app = Flask(__name__)
app.secret_key = Config.SECRET_KEY

# ============================
# CORS - CONFIGURACIÓN SEGURA
# ============================
FRONTEND_URL = os.environ.get("FRONTEND_URL", "https://ea-dixon.vercel.app")

# Lista de orígenes permitidos (SOLO estos pueden acceder)
ALLOWED_ORIGINS = [
    FRONTEND_URL,
    "https://ea-dixon-ktb2.vercel.app",
    "https://ea-dixon-m56l0hrmg-ktb2.vercel.app",
    "https://ea-dixon-oz4bkkn90-ktb2.vercel.app",
    "https://ea-dixon-git-main-ktb2.vercel.app",
    "https://ea-dixon.vercel.app",
    "http://localhost:3000",
    "http://localhost:5000"
]

# Configurar CORS con la lista de orígenes permitidos
CORS(app, 
     origins=ALLOWED_ORIGINS,
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


# ================================================================
# ==================== RUTAS AGREGADAS ===========================
# ================================================================

# ============================================
# RUTAS PARA GESTIÓN DE GASTOS Y CIERRE DE CAJA
# ============================================

# ============================================
# REGISTRAR GASTO
# ============================================
@app.route('/api/gastos', methods=['POST'])
def registrar_gasto():
    """Registra un nuevo gasto (efectivo o transferencia) con datos de factura"""
    try:
        data = request.json
        
        if not data.get('categoria') or not data.get('monto'):
            return jsonify({"error": "Categoría y monto son obligatorios"}), 400
        
        from database import get_connection
        conn = get_connection()
        cur = conn.cursor()
        
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
# OBTENER GASTOS POR FECHA
# ============================================
@app.route('/api/gastos', methods=['GET'])
def obtener_gastos():
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
# INICIAR CIERRE DE CAJA
# ============================================
@app.route('/api/cierre_caja', methods=['POST'])
def iniciar_cierre_caja():
    try:
        data = request.json
        fecha = data.get('fecha')
        efectivo_inicial = float(data.get('efectivo_inicial', 0))
        
        if not fecha:
            return jsonify({"error": "Fecha requerida"}), 400
        
        from database import get_connection
        conn = get_connection()
        cur = conn.cursor()
        
        cur.execute("SELECT id FROM cierres_caja WHERE fecha = %s", (fecha,))
        existente = cur.fetchone()
        
        if existente:
            cur.execute("""
                UPDATE cierres_caja 
                SET efectivo_inicial = %s, 
                    estado = 'abierto',
                    updated_at = NOW() AT TIME ZONE 'America/Santiago'
                WHERE fecha = %s
                RETURNING id
            """, (efectivo_inicial, fecha))
        else:
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
# OBTENER CIERRE DE CAJA
# ============================================
@app.route('/api/cierre_caja/<fecha>', methods=['GET'])
def obtener_cierre_caja(fecha):
    try:
        from database import get_cursor
        conn, cur = get_cursor()
        
        cur.execute("SELECT * FROM cierres_caja WHERE fecha = %s", (fecha,))
        cierre = cur.fetchone()
        
        if not cierre:
            cur.close()
            conn.close()
            return jsonify({"error": "No hay cierre para esta fecha"}), 404
        
        cierre_dict = dict(cierre)
        
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
# CERRAR CAJA DEL DÍA
# ============================================
@app.route('/api/cierre_caja/<fecha>/cerrar', methods=['POST'])
def cerrar_caja(fecha):
    try:
        data = request.json
        efectivo_real = float(data.get('efectivo_real', 0))
        observaciones = data.get('observaciones', '')
        cerrado_por = data.get('cerrado_por', 'Sistema')
        
        from database import get_connection
        conn = get_connection()
        cur = conn.cursor()
        
        cur.execute("SELECT * FROM cierres_caja WHERE fecha = %s AND estado = 'abierto'", (fecha,))
        cierre = cur.fetchone()
        
        if not cierre:
            cur.close()
            conn.close()
            return jsonify({"error": "No hay cierre abierto para esta fecha"}), 404
        
        cierre_dict = dict(cierre)
        
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
# HISTORIAL DE CIERRES
# ============================================
@app.route('/api/historial_cierres', methods=['GET'])
def historial_cierres():
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


# ============================================
# REGISTRAR PLANILLA DE SUELDOS
# ============================================
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
        
        total_sueldos = sum(e.get('sueldo_neto', 0) for e in data.get('empleados', []))
        if total_sueldos > 0:
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
    try:
        from database import get_connection
        conn = get_connection()
        cur = conn.cursor()
        
        cur.execute("SELECT id FROM empleados WHERE id = %s", (id_empleado,))
        if not cur.fetchone():
            cur.close()
            conn.close()
            return jsonify({"error": "Empleado no encontrado"}), 404
        
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
# ELIMINAR EMPLEADO DE LA PLANILLA
# ============================================
@app.route('/api/planilla_sueldos/empleado/<int:id_empleado>', methods=['DELETE'])
def eliminar_empleado_planilla(id_empleado):
    try:
        from database import get_connection
        conn = get_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT id FROM planilla_sueldos 
            WHERE empleado_id = %s AND mes = %s AND anio = %s
        """, (
            id_empleado, 
            datetime.now().month, 
            datetime.now().year
        ))
        
        if cur.fetchone():
            cur.execute("""
                DELETE FROM planilla_sueldos 
                WHERE empleado_id = %s AND mes = %s AND anio = %s
            """, (
                id_empleado, 
                datetime.now().month, 
                datetime.now().year
            ))
            conn.commit()
        
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


# ============================================
# PROCESAR PRODUCTO DESDE ESCÁNER
# ============================================
@app.route('/api/repuestos/from_scan', methods=['POST'])
def procesar_producto_escaner():
    try:
        data = request.json
        texto_escaneado = data.get('texto', '')
        
        try:
            producto_data = json.loads(texto_escaneado) if isinstance(texto_escaneado, str) else texto_escaneado
        except:
            producto_data = {'nombre': 'Producto escaneado', 'precio': 0}
        
        nombre = producto_data.get('nombre', 'Producto escaneado')
        precio = producto_data.get('precio', 0)
        proveedor = producto_data.get('proveedor', 'Escáner')
        cantidad = producto_data.get('cantidad', 1)
        codigo = producto_data.get('codigo', '')
        
        if not nombre or precio == 0:
            lineas = texto_escaneado.split('\n')
            for linea in lineas:
                if linea.strip() and not linea.startswith('http'):
                    nombre = linea.strip()
                    break
            
            match = re.search(r'([\d.,]+)\s*$', texto_escaneado)
            if match:
                precio = float(match.group(1).replace('.', '').replace(',', '.'))
        
        if not nombre or precio == 0:
            return jsonify({"error": "No se pudo extraer información del producto"}), 400
        
        from database import get_connection
        conn = get_connection()
        cur = conn.cursor()
        
        cur.execute("SELECT id, costo_venta_final, stock FROM repuestos WHERE nombre ILIKE %s", (nombre,))
        existente = cur.fetchone()
        
        if existente:
            nuevo_stock = (existente[2] or 0) + cantidad
            cur.execute("""
                UPDATE repuestos 
                SET stock = %s,
                    costo_proveedor = %s,
                    proveedor = %s,
                    updated_at = NOW() AT TIME ZONE 'America/Santiago'
                WHERE id = %s
            """, (nuevo_stock, precio, proveedor, existente[0]))
            mensaje = f"✅ Producto actualizado: {nombre}\n📦 Nuevo stock: {nuevo_stock}\n💰 Costo proveedor: ${precio:,.0f}"
        else:
            margen = 30
            iva = 1.19
            costo_con_iva = precio * iva
            precio_venta = costo_con_iva * (1 + (margen / 100))
            
            cur.execute("""
                INSERT INTO repuestos 
                (nombre, costo_proveedor, margen_ganancia, costo_venta_final, proveedor, stock, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, 
                        NOW() AT TIME ZONE 'America/Santiago', 
                        NOW() AT TIME ZONE 'America/Santiago')
                RETURNING id
            """, (
                nombre,
                precio,
                margen,
                math.floor(precio_venta),
                proveedor,
                cantidad
            ))
            id_repuesto = cur.fetchone()[0]
            mensaje = f"✅ Nuevo repuesto agregado: {nombre}\n💰 Costo: ${precio:,.0f}\n💰 Precio venta: ${math.floor(precio_venta):,.0f}"
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({
            "success": True, 
            "mensaje": mensaje,
            "producto": {
                'nombre': nombre,
                'costo_proveedor': precio,
                'stock': cantidad
            }
        })
        
    except Exception as e:
        print(f"❌ Error en procesar_producto_escaner: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ============================================
# REPORTE DE STOCK BAJO EN PDF
# ============================================
@app.route('/api/reporte_stock_bajo', methods=['POST'])
def generar_reporte_stock_bajo():
    try:
        from database import get_cursor
        from reportlab.lib.pagesizes import letter, landscape
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        import io
        from datetime import datetime
        import pytz
        
        data = request.json
        proveedor_filtro = data.get('proveedor', 'todos')
        stock_minimo = data.get('stock_minimo', 5)
        
        chile_tz = pytz.timezone('America/Santiago')
        ahora = datetime.now(chile_tz)
        
        conn, cur = get_cursor()
        
        query = """
            SELECT id, nombre, stock, costo_proveedor, costo_venta_final, 
                   margen_ganancia, proveedor, costo_proveedor_pendiente
            FROM repuestos 
            WHERE stock IS NOT NULL AND stock <= %s AND stock > 0
        """
        params = [stock_minimo]
        
        if proveedor_filtro != 'todos':
            query += " AND proveedor = %s"
            params.append(proveedor_filtro)
        
        query += " ORDER BY stock ASC, nombre ASC"
        
        cur.execute(query, params)
        productos = [dict(row) for row in cur.fetchall()]
        
        cur.execute("SELECT DISTINCT proveedor FROM repuestos WHERE proveedor IS NOT NULL AND proveedor != '' ORDER BY proveedor")
        proveedores = [row[0] for row in cur.fetchall()]
        
        cur.close()
        conn.close()
        
        if not productos:
            return jsonify({
                "error": f"No hay productos con stock menor o igual a {stock_minimo}",
                "proveedores": proveedores
            }), 404
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(letter),
            rightMargin=40,
            leftMargin=40,
            topMargin=40,
            bottomMargin=40
        )
        
        styles = getSampleStyleSheet()
        elementos = []
        
        titulo_style = ParagraphStyle(
            'Titulo',
            parent=styles['Heading1'],
            fontSize=22,
            textColor=colors.HexColor('#1a4d2e'),
            alignment=1,
            spaceAfter=6,
            fontName='Helvetica-Bold'
        )
        
        subtitulo_style = ParagraphStyle(
            'Subtitulo',
            parent=styles['Normal'],
            fontSize=12,
            textColor=colors.HexColor('#666666'),
            alignment=1,
            spaceAfter=20,
            fontName='Helvetica'
        )
        
        titulo = Paragraph("DIXON ELECTRICIDAD AUTOMOTRIZ", titulo_style)
        elementos.append(titulo)
        
        subtitulo = Paragraph("Reporte de Stock Bajo", subtitulo_style)
        elementos.append(subtitulo)
        
        info_style = ParagraphStyle(
            'Info',
            parent=styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#333333'),
            alignment=0,
            spaceAfter=8,
            fontName='Helvetica'
        )
        
        fecha_str = ahora.strftime('%d/%m/%Y %H:%M')
        info_text = f"""
        <b>Fecha de emisión:</b> {fecha_str}<br/>
        <b>Stock mínimo:</b> {stock_minimo} unidades<br/>
        <b>Proveedor filtrado:</b> {proveedor_filtro if proveedor_filtro != 'todos' else 'Todos'}<br/>
        <b>Total de productos con stock bajo:</b> {len(productos)}
        """
        info = Paragraph(info_text, info_style)
        elementos.append(info)
        elementos.append(Spacer(1, 0.15 * inch))
        
        table_data = [
            ['ID', 'Producto', 'Stock', 'Costo Proveedor ($)', 'Margen (%)', 'Precio Venta ($)', 'Proveedor']
        ]
        
        for p in productos:
            table_data.append([
                str(p['id']),
                p['nombre'][:30] + '...' if len(p['nombre']) > 30 else p['nombre'],
                str(p['stock'] or 0),
                f"{p['costo_proveedor']:,.0f}" if p['costo_proveedor'] else 'Pendiente',
                f"{p['margen_ganancia']:.1f}%" if p['margen_ganancia'] else '0%',
                f"{p['costo_venta_final']:,.0f}" if p['costo_venta_final'] else 'N/A',
                p['proveedor'] or 'Sin proveedor'
            ])
        
        col_widths = [0.5*inch, 2.5*inch, 0.7*inch, 1.0*inch, 0.8*inch, 1.0*inch, 1.2*inch]
        tabla = Table(table_data, colWidths=col_widths, repeatRows=1)
        tabla.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a4d2e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ('TOPPADDING', (0, 0), (-1, 0), 6),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ALIGN', (2, 1), (2, -1), 'CENTER'),
            ('ALIGN', (3, 1), (5, -1), 'RIGHT'),
            ('VALIGN', (0, 1), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#2e3138')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')]),
        ]))
        
        elementos.append(tabla)
        elementos.append(Spacer(1, 0.2 * inch))
        
        total_productos = len(productos)
        stock_total = sum(p.get('stock', 0) for p in productos)
        
        resumen_style = ParagraphStyle(
            'Resumen',
            parent=styles['Normal'],
            fontSize=12,
            textColor=colors.HexColor('#1a4d2e'),
            alignment=2,
            spaceBefore=10,
            fontName='Helvetica-Bold'
        )
        
        resumen_text = f"""
        <b>Resumen del Reporte</b><br/>
        Total de productos con stock bajo: {total_productos}<br/>
        Stock total de estos productos: {stock_total} unidades
        """
        resumen = Paragraph(resumen_text, resumen_style)
        elementos.append(resumen)
        
        pie_style = ParagraphStyle(
            'Pie',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#666666'),
            alignment=1,
            spaceBefore=30,
            fontName='Helvetica'
        )
        
        pie_text = f"""
        <b>Dixon Electricidad Automotriz</b><br/>
        Neptuno 163, Local C, Lo Prado, RM, Chile<br/>
        +569 9855 0331<br/>
        Reporte generado automáticamente el {ahora.strftime('%d/%m/%Y %H:%M')}
        """
        pie = Paragraph(pie_text, pie_style)
        elementos.append(pie)
        
        doc.build(elementos)
        
        buffer.seek(0)
        
        nombre_archivo = f'reporte_stock_bajo_{ahora.strftime("%Y%m%d_%H%M")}.pdf'
        
        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=nombre_archivo
        )
        
    except Exception as e:
        print(f"❌ Error en generar_reporte_stock_bajo: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ============================================
# GANANCIA REAL (VENTAS - COSTOS - GASTOS)
# ============================================
@app.route('/api/ganancia_real', methods=['GET'])
def get_ganancia_real():
    try:
        from database import get_cursor
        filtro = request.args.get('filtro', 'hoy')
        fecha_inicio = request.args.get('fecha_inicio')
        fecha_fin = request.args.get('fecha_fin')
        
        conn, cur = get_cursor()
        
        query_ventas = """
            SELECT 
                COALESCE(SUM(monto), 0) as total_ventas,
                COALESCE(SUM(costo_repuestos_real), 0) as total_costos_repuestos,
                COALESCE(SUM(costo_mano_obra_real), 0) as total_mano_obra,
                COALESCE(SUM(costo_diagnostico_real), 0) as total_diagnostico,
                COALESCE(SUM(ganancia_neta), 0) as ganancia_neta
            FROM pagos 
            WHERE estado = 'pagado' AND estado_pago = 'pagado'
        """
        
        if filtro == 'hoy':
            query_ventas += " AND fecha = CURRENT_DATE"
        elif filtro == '7d':
            query_ventas += " AND fecha >= CURRENT_DATE - INTERVAL '7 days'"
        elif filtro == 'mes':
            query_ventas += " AND fecha >= DATE_TRUNC('month', CURRENT_DATE)"
        elif filtro == 'anio':
            query_ventas += " AND fecha >= DATE_TRUNC('year', CURRENT_DATE)"
        elif fecha_inicio and fecha_fin:
            query_ventas += " AND fecha BETWEEN %s AND %s"
            cur.execute(query_ventas, (fecha_inicio, fecha_fin))
            ventas_data = cur.fetchone()
        else:
            cur.execute(query_ventas)
            ventas_data = cur.fetchone()
            cur.close()
            conn.close()
            return jsonify({"error": "Filtro no válido"}), 400
        
        if not fecha_inicio or not fecha_fin:
            cur.execute(query_ventas)
            ventas_data = cur.fetchone()
        
        query_gastos = """
            SELECT 
                COALESCE(SUM(CASE WHEN metodo_pago = 'efectivo' THEN monto ELSE 0 END), 0) as gastos_efectivo,
                COALESCE(SUM(CASE WHEN metodo_pago = 'transferencia' THEN monto ELSE 0 END), 0) as gastos_transferencia,
                COALESCE(SUM(monto), 0) as total_gastos,
                COALESCE(SUM(CASE WHEN categoria = 'Sueldos' THEN monto ELSE 0 END), 0) as gastos_sueldos,
                COALESCE(SUM(CASE WHEN categoria = 'Arriendo' THEN monto ELSE 0 END), 0) as gastos_arriendo,
                COALESCE(SUM(CASE WHEN categoria = 'Servicios Públicos' THEN monto ELSE 0 END), 0) as gastos_servicios,
                COALESCE(SUM(CASE WHEN categoria = 'Alimentación' THEN monto ELSE 0 END), 0) as gastos_alimentacion,
                COALESCE(SUM(CASE WHEN categoria = 'Herramientas' THEN monto ELSE 0 END), 0) as gastos_herramientas,
                COALESCE(SUM(CASE WHEN categoria = 'Impuestos' THEN monto ELSE 0 END), 0) as gastos_impuestos,
                COALESCE(SUM(CASE WHEN categoria = 'Otros' THEN monto ELSE 0 END), 0) as gastos_otros
            FROM gastos
        """
        
        if filtro == 'hoy':
            query_gastos += " WHERE fecha = CURRENT_DATE"
        elif filtro == '7d':
            query_gastos += " WHERE fecha >= CURRENT_DATE - INTERVAL '7 days'"
        elif filtro == 'mes':
            query_gastos += " WHERE fecha >= DATE_TRUNC('month', CURRENT_DATE)"
        elif filtro == 'anio':
            query_gastos += " WHERE fecha >= DATE_TRUNC('year', CURRENT_DATE)"
        elif fecha_inicio and fecha_fin:
            query_gastos += " WHERE fecha BETWEEN %s AND %s"
            cur.execute(query_gastos, (fecha_inicio, fecha_fin))
            gastos_data = cur.fetchone()
        else:
            cur.execute(query_gastos)
            gastos_data = cur.fetchone()
        
        if not fecha_inicio or not fecha_fin:
            cur.execute(query_gastos)
            gastos_data = cur.fetchone()
        
        cur.close()
        conn.close()
        
        ventas = {
            'total_ventas': float(ventas_data[0] or 0),
            'total_costos_repuestos': float(ventas_data[1] or 0),
            'total_mano_obra': float(ventas_data[2] or 0),
            'total_diagnostico': float(ventas_data[3] or 0),
            'ganancia_neta': float(ventas_data[4] or 0)
        }
        
        gastos = {
            'gastos_efectivo': float(gastos_data[0] or 0),
            'gastos_transferencia': float(gastos_data[1] or 0),
            'total_gastos': float(gastos_data[2] or 0),
            'gastos_sueldos': float(gastos_data[3] or 0),
            'gastos_arriendo': float(gastos_data[4] or 0),
            'gastos_servicios': float(gastos_data[5] or 0),
            'gastos_alimentacion': float(gastos_data[6] or 0),
            'gastos_herramientas': float(gastos_data[7] or 0),
            'gastos_impuestos': float(gastos_data[8] or 0),
            'gastos_otros': float(gastos_data[9] or 0)
        }
        
        ganancia_real = ventas['total_ventas'] - ventas['total_costos_repuestos'] - gastos['total_gastos']
        
        return jsonify({
            'ventas': ventas,
            'gastos': gastos,
            'ganancia_real': round(ganancia_real, 2),
            'filtro': filtro,
            'fecha_inicio': fecha_inicio,
            'fecha_fin': fecha_fin
        })
        
    except Exception as e:
        print(f"❌ Error en get_ganancia_real: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ============================================
# ACTUALIZAR REPUESTO (NO MODIFICA PRECIO VENTA)
# ============================================
@app.route('/api/repuestos/<int:id_repuesto>', methods=['PUT'])
def actualizar_repuesto(id_repuesto):
    try:
        data = request.json
        from database import get_connection
        conn = get_connection()
        cur = conn.cursor()
        
        cur.execute("SELECT costo_venta_final FROM repuestos WHERE id = %s", (id_repuesto,))
        row = cur.fetchone()
        if not row:
            cur.close()
            conn.close()
            return jsonify({"error": "Repuesto no encontrado"}), 404
        
        precio_venta_actual = row[0]
        costo_venta_final = data.get('costo_venta_final', precio_venta_actual)
        costo_proveedor = data.get('costo_proveedor', 0)
        costo_proveedor_pendiente = costo_proveedor == 0
        
        cur.execute("""
            UPDATE repuestos 
            SET nombre = %s,
                costo_proveedor = %s,
                margen_ganancia = %s,
                proveedor = %s,
                costo_venta_final = %s,
                stock = %s,
                costo_proveedor_pendiente = %s,
                updated_at = NOW() AT TIME ZONE 'America/Santiago'
            WHERE id = %s
            RETURNING id
        """, (
            data.get('nombre'),
            costo_proveedor,
            data.get('margen_ganancia', 30),
            data.get('proveedor', ''),
            costo_venta_final,
            data.get('stock', 0),
            costo_proveedor_pendiente,
            id_repuesto
        ))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({"success": True})
    except Exception as e:
        print(f"❌ Error en actualizar_repuesto: {e}")
        return jsonify({"error": str(e)}), 500


# ============================================
# FUNCIÓN INTERNA PARA REGISTRAR GASTO
# ============================================
def registrar_gasto_interno(data):
    try:
        from database import get_connection
        conn = get_connection()
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO gastos 
            (categoria, monto, metodo_pago, descripcion, fecha, hora, registrado_por, es_planilla)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            data.get('categoria'),
            float(data.get('monto', 0)),
            data.get('metodo_pago', 'transferencia'),
            data.get('descripcion', ''),
            data.get('fecha'),
            data.get('hora'),
            data.get('registrado_por', 'Sistema'),
            data.get('es_planilla', False)
        ))
        
        id_gasto = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        
        print(f"✅ Gasto interno registrado ID: {id_gasto}")
        return True
    except Exception as e:
        print(f"❌ Error en registrar_gasto_interno: {e}")
        return False


# ============================================
# OBTENER GASTOS PARA BALANCE (TODOS)
# ============================================
@app.route('/api/gastos_balance', methods=['GET'])
def obtener_gastos_balance():
    """Obtiene TODOS los gastos operativos para el balance (sueldos, arriendo, etc)"""
    try:
        fecha_inicio = request.args.get('fecha_inicio')
        fecha_fin = request.args.get('fecha_fin')
        
        if not fecha_inicio or not fecha_fin:
            return jsonify({"error": "Fechas requeridas"}), 400
        
        from database import get_cursor
        conn, cur = get_cursor()
        
        cur.execute("""
            SELECT * FROM gastos 
            WHERE fecha BETWEEN %s AND %s
            ORDER BY fecha DESC, hora DESC
        """, (fecha_inicio, fecha_fin))
        
        gastos = [dict(row) for row in cur.fetchall()]
        cur.close()
        conn.close()
        
        return jsonify(gastos)
        
    except Exception as e:
        print(f"❌ Error en obtener_gastos_balance: {e}")
        return jsonify([])


# ============================================
# RUTAS PARA CATEGORÍAS DE REPUESTOS
# ============================================

# Obtener todas las categorías
@app.route('/api/categorias_repuestos', methods=['GET'])
def obtener_categorias_repuestos():
    try:
        from database import get_cursor
        conn, cur = get_cursor()
        cur.execute("""
            SELECT c.*, 
                   (SELECT COUNT(*) FROM subcategorias_repuestos WHERE categoria_id = c.id) as subcategorias_count
            FROM categorias_repuestos c 
            ORDER BY c.nombre
        """)
        categorias = [dict(row) for row in cur.fetchall()]
        cur.close()
        conn.close()
        return jsonify(categorias)
    except Exception as e:
        print(f"❌ Error en obtener_categorias_repuestos: {e}")
        return jsonify([])

# Obtener subcategorías por categoría
@app.route('/api/subcategorias_repuestos/<int:categoria_id>', methods=['GET'])
def obtener_subcategorias_repuestos(categoria_id):
    try:
        from database import get_cursor
        conn, cur = get_cursor()
        cur.execute("""
            SELECT * FROM subcategorias_repuestos 
            WHERE categoria_id = %s 
            ORDER BY nombre
        """, (categoria_id,))
        subcategorias = [dict(row) for row in cur.fetchall()]
        cur.close()
        conn.close()
        return jsonify(subcategorias)
    except Exception as e:
        print(f"❌ Error en obtener_subcategorias_repuestos: {e}")
        return jsonify([])

# Obtener todas las subcategorías
@app.route('/api/subcategorias_repuestos', methods=['GET'])
def obtener_todas_subcategorias_repuestos():
    try:
        from database import get_cursor
        conn, cur = get_cursor()
        cur.execute("""
            SELECT s.*, c.nombre as categoria_nombre 
            FROM subcategorias_repuestos s
            JOIN categorias_repuestos c ON c.id = s.categoria_id
            ORDER BY c.nombre, s.nombre
        """)
        subcategorias = [dict(row) for row in cur.fetchall()]
        cur.close()
        conn.close()
        return jsonify(subcategorias)
    except Exception as e:
        print(f"❌ Error en obtener_todas_subcategorias_repuestos: {e}")
        return jsonify([])

# Asignar categoría a un repuesto
@app.route('/api/repuestos/<int:id_repuesto>/categoria', methods=['PUT'])
def asignar_categoria_repuesto(id_repuesto):
    try:
        data = request.json
        subcategoria_id = data.get('subcategoria_id')
        
        from database import get_connection
        conn = get_connection()
        cur = conn.cursor()
        
        if subcategoria_id:
            # Obtener nombre de la categoría
            cur.execute("""
                SELECT c.nombre 
                FROM subcategorias_repuestos s
                JOIN categorias_repuestos c ON c.id = s.categoria_id
                WHERE s.id = %s
            """, (subcategoria_id,))
            result = cur.fetchone()
            categoria_nombre = result[0] if result else None
            
            cur.execute("""
                UPDATE repuestos 
                SET subcategoria_id = %s, categoria_nombre = %s,
                    updated_at = NOW() AT TIME ZONE 'America/Santiago'
                WHERE id = %s
            """, (subcategoria_id, categoria_nombre, id_repuesto))
        else:
            cur.execute("""
                UPDATE repuestos 
                SET subcategoria_id = NULL, categoria_nombre = NULL,
                    updated_at = NOW() AT TIME ZONE 'America/Santiago'
                WHERE id = %s
            """, (id_repuesto,))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({"success": True})
    except Exception as e:
        print(f"❌ Error en asignar_categoria_repuesto: {e}")
        return jsonify({"error": str(e)}), 500

# Obtener repuestos por categoría
@app.route('/api/repuestos/categoria/<categoria_nombre>', methods=['GET'])
def obtener_repuestos_por_categoria(categoria_nombre):
    try:
        from database import get_cursor
        conn, cur = get_cursor()
        cur.execute("""
            SELECT * FROM repuestos 
            WHERE categoria_nombre = %s 
            ORDER BY nombre
        """, (categoria_nombre,))
        repuestos = [dict(row) for row in cur.fetchall()]
        cur.close()
        conn.close()
        return jsonify(repuestos)
    except Exception as e:
        print(f"❌ Error en obtener_repuestos_por_categoria: {e}")
        return jsonify([])


# ============================================
# IMPORTAR PRODUCTOS CON CATEGORÍAS Y STOCK
# ============================================
@app.route('/api/repuestos/importar', methods=['POST', 'OPTIONS'])
def importar_repuestos():
    """Importa productos desde Excel con categorías, subcategorías y stock"""
    
    # Manejar preflight OPTIONS
    if request.method == 'OPTIONS':
        response = make_response()
        origin = request.headers.get('Origin')
        if origin and (origin in ALLOWED_ORIGINS or origin.endswith('.vercel.app')):
            response.headers['Access-Control-Allow-Origin'] = origin
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With, Accept'
            response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        return response
    
    print("=" * 60)
    print("🚀 IMPORTACIÓN INICIADA")
    print("=" * 60)
    
    try:
        data = request.json
        productos = data.get('productos', [])
        print(f"📦 Productos recibidos: {len(productos)}")
        
        if not productos:
            return jsonify({"error": "No hay productos para importar"}), 400
        
        from database import get_connection
        conn = get_connection()
        cur = conn.cursor()
        
        importados = 0
        actualizados = 0
        errores = []
        exitosos = []
        
        # ============================================
        # FUNCIONES PARA NORMALIZAR TEXTO
        # ============================================
        import unicodedata
        
        def normalizar_texto(texto):
            if not texto:
                return texto
            texto_normalizado = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('ASCII')
            return texto_normalizado.lower().strip()
        
        def limpiar_texto(texto):
            if not texto:
                return texto
            texto_limpio = ''.join(c for c in texto if c.isprintable())
            texto_limpio = ' '.join(texto_limpio.split())
            return texto_limpio.strip()
        
        # ============================================
        # 1. Cargar TODAS las categorías en memoria
        # ============================================
        cur.execute("SELECT id, nombre FROM categorias_repuestos")
        categorias_db = cur.fetchall()
        print(f"📂 Categorías en BD: {len(categorias_db)}")
        for row in categorias_db:
            print(f"   - ID: {row[0]}, Nombre: {row[1]}")
        
        # Crear mapa de búsqueda
        categorias_map = {}
        for row in categorias_db:
            # Guardar por nombre exacto
            categorias_map[row[1]] = row[0]
            # Guardar por nombre normalizado (sin tildes)
            key_normalizado = normalizar_texto(row[1])
            categorias_map[key_normalizado] = row[0]
        
        print(f"📂 Mapa de categorías: {list(categorias_map.keys())}")
        
        # ============================================
        # 2. Procesar productos
        # ============================================
        for idx, item in enumerate(productos):
            try:
                if idx % 10 == 0:
                    print(f"📦 Progreso: {idx+1}/{len(productos)}")
                
                nombre = limpiar_texto(item.get('nombre', '').strip())
                costo_proveedor = float(item.get('costo', 0))
                precio_venta = float(item.get('precio_venta', 0))
                proveedor = limpiar_texto(item.get('proveedor', 'Importado').strip())
                categoria_nombre = limpiar_texto(item.get('categoria', '').strip())
                subcategoria_nombre = limpiar_texto(item.get('subcategoria', '').strip())
                stock = int(item.get('stock', 0))
                
                print(f"\n📦 [{idx+1}] {nombre}")
                print(f"   Categoría recibida: '{categoria_nombre}'")
                print(f"   Subcategoría recibida: '{subcategoria_nombre}'")
                
                if not nombre or costo_proveedor <= 0 or precio_venta <= 0:
                    errores.append({"nombre": nombre or 'Sin nombre', "error": "Faltan datos obligatorios"})
                    continue
                
                # ============================================
                # 3. Buscar o crear CATEGORÍA (FORZADO)
                # ============================================
                categoria_id = None
                categoria_nombre_final = None
                
                if categoria_nombre:
                    # Buscar por nombre exacto
                    if categoria_nombre in categorias_map:
                        categoria_id = categorias_map[categoria_nombre]
                        categoria_nombre_final = categoria_nombre
                        print(f"   ✅ Categoría encontrada: {categoria_nombre} (ID: {categoria_id})")
                    else:
                        # Buscar por nombre normalizado
                        key_normalizado = normalizar_texto(categoria_nombre)
                        if key_normalizado in categorias_map:
                            categoria_id = categorias_map[key_normalizado]
                            # Obtener nombre real
                            for row in categorias_db:
                                if normalizar_texto(row[1]) == key_normalizado:
                                    categoria_nombre_final = row[1]
                                    break
                            print(f"   ✅ Categoría encontrada por normalización: {categoria_nombre} -> {categoria_nombre_final} (ID: {categoria_id})")
                        else:
                            # Crear nueva categoría
                            print(f"   📝 Creando nueva categoría: {categoria_nombre}")
                            cur.execute("""
                                INSERT INTO categorias_repuestos (nombre, descripcion)
                                VALUES (%s, %s) RETURNING id
                            """, (categoria_nombre, f'Categoría importada: {categoria_nombre}'))
                            categoria_id = cur.fetchone()[0]
                            categoria_nombre_final = categoria_nombre
                            # Actualizar caché
                            categorias_map[categoria_nombre] = categoria_id
                            categorias_map[normalizar_texto(categoria_nombre)] = categoria_id
                            categorias_db.append((categoria_id, categoria_nombre))
                            print(f"   ✅ Categoría creada ID: {categoria_id}")
                else:
                    print(f"   ⚠️ No se recibió categoría para: {nombre}")
                
                # ============================================
                # 4. Buscar o crear SUBCATEGORÍA
                # ============================================
                subcategoria_id = None
                if subcategoria_nombre and categoria_id:
                    try:
                        # Buscar subcategoría por nombre normalizado + categoria_id
                        cur.execute("""
                            SELECT id FROM subcategorias_repuestos 
                            WHERE LOWER(nombre) = LOWER(%s) AND categoria_id = %s
                        """, (subcategoria_nombre, categoria_id))
                        result = cur.fetchone()
                        if result:
                            subcategoria_id = result[0]
                            print(f"   ✅ Subcategoría encontrada ID: {subcategoria_id}")
                        else:
                            print(f"   📝 Creando subcategoría: {subcategoria_nombre}")
                            cur.execute("""
                                INSERT INTO subcategorias_repuestos (categoria_id, nombre)
                                VALUES (%s, %s) RETURNING id
                            """, (categoria_id, subcategoria_nombre))
                            subcategoria_id = cur.fetchone()[0]
                            print(f"   ✅ Subcategoría creada ID: {subcategoria_id}")
                    except Exception as e:
                        print(f"   ⚠️ Error con subcategoría: {e}")
                        subcategoria_id = None
                
                # ============================================
                # 5. Calcular margen
                # ============================================
                margen = 30
                if costo_proveedor > 0 and precio_venta > 0:
                    iva = 1.19
                    costo_con_iva = costo_proveedor * iva
                    margen = round(((precio_venta / costo_con_iva) - 1) * 100, 1)
                
                # ============================================
                # 6. Insertar o actualizar REPUESTO (FORZAR CATEGORÍA)
                # ============================================
                # Buscar si el producto ya existe
                cur.execute("SELECT id, stock FROM repuestos WHERE LOWER(nombre) = LOWER(%s)", (nombre,))
                existente = cur.fetchone()
                
                # Si no existe por nombre exacto, buscar por nombre normalizado
                if not existente:
                    nombre_buscar = normalizar_texto(nombre)
                    cur.execute("SELECT id, stock, nombre FROM repuestos")
                    for row in cur.fetchall():
                        if normalizar_texto(row[2]) == nombre_buscar:
                            existente = (row[0], row[1])
                            print(f"   ✅ Producto encontrado por normalización: {row[2]}")
                            break
                
                if existente:
                    nuevo_stock = (existente[1] or 0) + stock
                    print(f"   📝 Actualizando repuesto ID: {existente[0]}")
                    print(f"   📝 Asignando categoría: {categoria_nombre_final or 'NULL'}")
                    cur.execute("""
                        UPDATE repuestos 
                        SET costo_proveedor = %s,
                            costo_venta_final = %s,
                            margen_ganancia = %s,
                            proveedor = %s,
                            stock = %s,
                            subcategoria_id = %s,
                            categoria_nombre = %s,
                            updated_at = NOW() AT TIME ZONE 'America/Santiago'
                        WHERE id = %s
                    """, (
                        costo_proveedor,
                        precio_venta,
                        margen,
                        proveedor,
                        nuevo_stock,
                        subcategoria_id,
                        categoria_nombre_final,  # ✅ FORZAR CATEGORÍA
                        existente[0]
                    ))
                    actualizados += 1
                    exitosos.append(f"{nombre} (stock: {nuevo_stock}, categoría: {categoria_nombre_final})")
                    print(f"   ✅ Repuesto actualizado con categoría: {categoria_nombre_final}")
                else:
                    print(f"   📝 Creando nuevo repuesto")
                    print(f"   📝 Asignando categoría: {categoria_nombre_final or 'NULL'}")
                    cur.execute("""
                        INSERT INTO repuestos 
                        (nombre, costo_proveedor, costo_venta_final, margen_ganancia, proveedor, 
                         subcategoria_id, categoria_nombre, stock, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 
                                NOW() AT TIME ZONE 'America/Santiago',
                                NOW() AT TIME ZONE 'America/Santiago')
                    """, (
                        nombre,
                        costo_proveedor,
                        precio_venta,
                        margen,
                        proveedor,
                        subcategoria_id,
                        categoria_nombre_final,  # ✅ FORZAR CATEGORÍA
                        stock
                    ))
                    importados += 1
                    exitosos.append(f"{nombre} (nuevo, categoría: {categoria_nombre_final})")
                    print(f"   ✅ Nuevo repuesto creado con categoría: {categoria_nombre_final}")
                
                conn.commit()
                
                # Commit cada 20 productos
                if idx % 20 == 0:
                    conn.commit()
                
            except Exception as e:
                print(f"   ❌ Error en producto: {e}")
                import traceback
                traceback.print_exc()
                errores.append({
                    "nombre": item.get('nombre', 'desconocido'),
                    "error": str(e)
                })
                conn.rollback()
                continue
        
        cur.close()
        conn.close()
        
        print("\n" + "=" * 60)
        print(f"✅ IMPORTACIÓN COMPLETADA: {importados} nuevos, {actualizados} actualizados")
        print(f"   Errores: {len(errores)}")
        print("=" * 60)
        
        return jsonify({
            "success": True,
            "importados": importados,
            "actualizados": actualizados,
            "exitosos": exitosos,
            "errores": errores
        })
        
    except Exception as e:
        print(f"❌ ERROR GENERAL: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
# ============================================
# OBTENER TODOS LOS REPUESTOS (CON CATEGORÍA)
# ============================================
@app.route('/api/repuestos', methods=['GET'])
def obtener_repuestos():
    """Obtiene todos los repuestos con sus categorías para la tabla"""
    try:
        from database import get_cursor
        conn, cur = get_cursor()
        
        cur.execute("""
            SELECT id, nombre, stock, costo_proveedor, 
                   costo_proveedor_pendiente, margen_ganancia, 
                   costo_venta_final, proveedor, categoria_nombre
            FROM repuestos 
            ORDER BY id DESC
        """)
        
        repuestos = [dict(row) for row in cur.fetchall()]
        cur.close()
        conn.close()
        
        return jsonify(repuestos)
    except Exception as e:
        print(f"❌ Error en obtener_repuestos: {e}")
        import traceback
        traceback.print_exc()
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
