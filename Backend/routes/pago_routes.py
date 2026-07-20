# Backend/routes/pago_routes.py
from flask import Blueprint, request, jsonify, send_file, current_app
from services.pago_service import PagoService
from database import get_connection, get_cursor
from datetime import datetime, timedelta
from services.pdf_service import PDFService
from services.notification_service import enviar_notificacion_push
from utils.seguridad import (
    sanitizar_input, sanitizar_patente, sanitizar_numero, 
    sanitizar_dict, validar_filtro, validar_metodo_pago, validar_fecha
)
from utils.fecha_utils import now_santiago, formatear_fecha
import json
import os
import traceback
import psycopg2.extras
import logging

logger = logging.getLogger(__name__)
pago_bp = Blueprint('pago', __name__, url_prefix='/api')

# ============================================
# FUNCIONES DE FECHA (centralizadas)
# ============================================
def get_fecha_chile():
    return now_santiago().date()

def get_hora_chile():
    return now_santiago().time()

def get_fecha_hora_chile():
    ahora = now_santiago()
    return ahora.date(), ahora.time()
# ============================================
# FUNCIÓN SANITIZAR BOOLEANO
# ============================================
def sanitizar_booleano(valor):
    """Convierte un valor a booleano de forma segura"""
    if valor is None:
        return False
    if isinstance(valor, bool):
        return valor
    if isinstance(valor, str):
        return valor.lower() in ('true', '1', 'yes', 'si', 'sí')
    if isinstance(valor, (int, float)):
        return valor != 0
    return False

# ============================
# 1. ESTADO
# ============================
@pago_bp.route('/estado', methods=['GET'])
def get_estado():
    try:
        pendientes = PagoService.obtener_pendientes()
        pagados = PagoService.obtener_pagados_hoy()
        return jsonify({
            "pendientes": [p.to_dict() for p in pendientes],
            "pagados_hoy": [p.to_dict() for p in pagados],
            "total_pendientes": len(pendientes),
            "total_pagados_hoy": len(pagados)
        })
    except Exception as e:
        logger.error(f"Error en get_estado: {e}")
        return jsonify({"error": str(e)}), 500

# ============================
# 2. REGISTRO POR ID (RUTA JS)
# ============================
@pago_bp.route('/registro/<int:id>', methods=['GET'])
def get_registro_js(id):
    """Ruta exacta que usa el JavaScript para editar/detalle"""
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        # ✅ CONSULTA PARAMETRIZADA
        cur.execute("SELECT * FROM pagos WHERE id = %s", (id,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        
        if not row:
            return jsonify({"error": "Registro no encontrado"}), 404
        
        return jsonify(dict(row))
    except Exception as e:
        logger.error(f"Error en get_registro_js ID {id}: {e}")
        return jsonify({"error": str(e)}), 500

# ============================
# 3. REGISTRO POR ID (VERSIÓN PAGOSERVICE)
# ============================
@pago_bp.route('/registro/<int:id_reg>', methods=['GET'])
def get_registro(id_reg):
    try:
        pago = PagoService.obtener_por_id(id_reg)
        if pago:
            return jsonify(pago.to_dict())
        return jsonify({"error": "No encontrado"}), 404
    except Exception as e:
        logger.error(f"Error en get_registro ID {id_reg}: {e}")
        return jsonify({"error": str(e)}), 500

# ============================
# 4. REGISTROS CON FILTROS (CORREGIDO)
# ============================
@pago_bp.route('/registros', methods=['GET'])
def get_registros_filtrados():
    filtro = request.args.get('filtro', 'todos')
    hoy = get_fecha_chile()
    
    # ✅ VALIDAR FILTRO
    if not validar_filtro(filtro):
        return jsonify({"error": "Filtro inválido"}), 400
    
    try:
        conn, cur = get_cursor()
        # ✅ CONSULTA PARAMETRIZADA
        query = "SELECT * FROM pagos WHERE estado = 'pagado' AND estado_pago = 'pagado'"
        params = []
        
        if filtro == 'hoy':
            query += " AND fecha = %s"
            params.append(hoy.strftime('%Y-%m-%d'))
        elif filtro == '7d':
            query += " AND fecha >= %s"
            params.append((hoy - timedelta(days=7)).strftime('%Y-%m-%d'))
        elif filtro == 'mes':
            query += " AND fecha >= %s"
            params.append((hoy - timedelta(days=30)).strftime('%Y-%m-%d'))
        
        query += " ORDER BY fecha DESC, hora DESC"
        cur.execute(query, params)
        rows = cur.fetchall()
        registros = [dict(row) for row in rows]
        
        for r in registros:
            r['firma'] = PDFService.generar_firma(r['id'])
        
        cur.close()
        conn.close()
        return jsonify(registros)
    except Exception as e:
        logger.error(f"Error en get_registros_filtrados: {e}")
        return jsonify({"error": str(e)}), 500

# ============================
# 5. EDITAR REGISTRO COMPLETO (CON VALIDACIÓN)
# ============================
@pago_bp.route('/editar_completo/<int:id_reg>', methods=['POST'])
def editar_completo(id_reg):
    try:
        data = request.json
        
        # ✅ SANITIZAR TODOS LOS CAMPOS
        data_sanitizada = {
            'nombre': sanitizar_input(data.get('nombre')),
            'telefono': sanitizar_input(data.get('telefono')),
            'patente': sanitizar_patente(data.get('patente')),
            'marca': sanitizar_input(data.get('marca')),
            'modelo': sanitizar_input(data.get('modelo')),
            'anio': sanitizar_numero(data.get('anio', 0), min_val=1900, max_val=datetime.now().year + 1),
            'flota': sanitizar_input(data.get('flota')),
            'fecha': data.get('fecha'),
            'hora': data.get('hora'),
            'monto': sanitizar_numero(data.get('monto', 0), min_val=0),
            'observaciones_cliente': sanitizar_input(data.get('observaciones_cliente')),
            'diagnostico': sanitizar_input(data.get('diagnostico')),
            'reparacion': sanitizar_input(data.get('reparacion', 'Reparación realizada')),
            'resultado': sanitizar_input(data.get('resultado', 'reparado')),
            'tiempo_estimado': data.get('tiempo_estimado', '00:00:00'),
            'costo_repuestos_real': sanitizar_numero(data.get('costo_repuestos_real', 0), min_val=0),
            'costo_mano_obra_real': sanitizar_numero(data.get('costo_mano_obra_real', 0), min_val=0),
            'costo_diagnostico_real': sanitizar_numero(data.get('costo_diagnostico_real', 0), min_val=0),
            'ganancia_neta': sanitizar_numero(data.get('ganancia_neta', 0)),
            'observaciones_pago': sanitizar_input(data.get('observaciones_pago')),
            'validado_por': sanitizar_input(data.get('validado_por')),
            'atendido_por': sanitizar_input(data.get('atendido_por')),
            'validado': sanitizar_booleano(data.get('validado', False))
        }
        
        # ✅ VALIDAR CAMPOS OBLIGATORIOS
        if not data_sanitizada['nombre']:
            return jsonify({"error": "El nombre es obligatorio"}), 400
        
        # ✅ CONSULTA PARAMETRIZADA
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            UPDATE pagos 
            SET nombre = %s,
                telefono = %s,
                patente = %s,
                marca = %s,
                modelo = %s,
                anio = %s,
                flota = %s,
                fecha = %s,
                hora = %s,
                monto = %s,
                observaciones_cliente = %s,
                diagnostico = %s,
                reparacion = %s,
                resultado = %s,
                tiempo_estimado = %s,
                costo_repuestos_real = %s,
                costo_mano_obra_real = %s,
                costo_diagnostico_real = %s,
                ganancia_neta = %s,
                observaciones_pago = %s,
                validado_por = %s,
                atendido_por = %s,
                validado = %s
            WHERE id = %s
        """, (
            data_sanitizada['nombre'],
            data_sanitizada['telefono'],
            data_sanitizada['patente'],
            data_sanitizada['marca'],
            data_sanitizada['modelo'],
            data_sanitizada['anio'],
            data_sanitizada['flota'],
            data_sanitizada['fecha'],
            data_sanitizada['hora'],
            data_sanitizada['monto'],
            data_sanitizada['observaciones_cliente'],
            data_sanitizada['diagnostico'],
            data_sanitizada['reparacion'],
            data_sanitizada['resultado'],
            data_sanitizada['tiempo_estimado'],
            data_sanitizada['costo_repuestos_real'],
            data_sanitizada['costo_mano_obra_real'],
            data_sanitizada['costo_diagnostico_real'],
            data_sanitizada['ganancia_neta'],
            data_sanitizada['observaciones_pago'],
            data_sanitizada['validado_por'],
            data_sanitizada['atendido_por'],
            data_sanitizada['validado'],
            id_reg
        ))
        
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"success": True})
        
    except Exception as e:
        logger.error(f"Error en editar_completo ID {id_reg}: {e}")
        return jsonify({"error": str(e)}), 500

# ============================
# 6. AGREGAR CLIENTE (CON VALIDACIÓN)
# ============================
@pago_bp.route('/agregar', methods=['POST'])
def agregar_pago():
    try:
        data = request.json
        
        # ✅ SANITIZAR DATOS
        flota = data.get('flota')
        if flota == '__nueva__':
            flota = sanitizar_input(data.get('flota_nueva', '').strip())
        
        data_sanitizada = {
            'nombre': sanitizar_input(data.get('nombre', '').strip()),
            'patente': sanitizar_patente(data.get('patente', '').strip()),
            'marca': sanitizar_input(data.get('marca', '').strip()),
            'modelo': sanitizar_input(data.get('modelo', '').strip()),
            'telefono': sanitizar_input(data.get('telefono', '').strip()),
            'flota': flota if flota else None,
            'observaciones': sanitizar_input(data.get('observaciones', '').strip()),
            'kilometraje': sanitizar_numero(data.get('kilometraje', 0), min_val=0),
            'anio': sanitizar_numero(data.get('anio', 0), min_val=1900, max_val=datetime.now().year + 1),
            'usuario': sanitizar_input(data.get('usuario', 'Sistema').strip())
        }
        
        # ✅ VALIDAR CAMPOS OBLIGATORIOS
        if not data_sanitizada['nombre']:
            return jsonify({"error": "El nombre es obligatorio"}), 400
        
        id_reg = PagoService.crear_pago(data_sanitizada)
        if id_reg:
            return jsonify({"success": True, "id": id_reg})
        return jsonify({"success": False, "error": "Error al guardar"}), 500
        
    except Exception as e:
        logger.error(f"Error en agregar_pago: {e}")
        return jsonify({"error": str(e)}), 500

# ============================
# 7. PROCESAR PAGO (CON VALIDACIÓN)
# ============================
@pago_bp.route('/pagar/<int:id_reg>', methods=['POST'])
def pagar(id_reg):
    try:
        data = request.json
        
        # ✅ SANITIZAR DATOS
        data_sanitizada = {
            'monto': sanitizar_numero(data.get('monto', 0), min_val=0.01),
            'forma_pago': sanitizar_input(data.get('forma_pago', 'efectivo')),
            'diagnostico': sanitizar_input(data.get('diagnostico', '')),
            'reparacion': sanitizar_input(data.get('reparacion', 'Reparación realizada')),
            'observaciones_pago': sanitizar_input(data.get('observaciones_pago', '')),
            'resultado': sanitizar_input(data.get('resultado', 'reparado')),
            'estado_ot': sanitizar_input(data.get('estado_ot', 'Pendiente')),
            'atendido_por': sanitizar_input(data.get('atendido_por', 'Técnico'))
        }
        
        # ✅ VALIDAR MONTO
        if data_sanitizada['monto'] <= 0:
            return jsonify({"error": "El monto debe ser mayor a 0"}), 400
        
        # ✅ VALIDAR FORMA DE PAGO
        if not validar_metodo_pago(data_sanitizada['forma_pago']):
            return jsonify({"error": "Forma de pago inválida"}), 400
        
        logger.info(f"💰 Procesando pago ID {id_reg} - Monto: ${data_sanitizada['monto']}")
        
        pago = PagoService.procesar_pago(id_reg, data_sanitizada)
        if pago:
            # Notificación push
            enviar_notificacion_push(
                titulo="💰 Pago Express",
                mensaje=f"Cliente: {pago.nombre}\nMonto: ${float(pago.monto):,.0f}\nForma: {pago.forma_pago}",
                url=f"/pago_exitoso/{id_reg}",
                id=id_reg
            )
            return jsonify({"success": True, "pago": pago.to_dict()})
        return jsonify({"success": False, "error": "Error al procesar"}), 500
        
    except Exception as e:
        logger.error(f"Error en pagar ID {id_reg}: {e}")
        return jsonify({"error": str(e)}), 500

# ============================
# 8. PENDIENTES DE VALIDACIÓN
# ============================
@pago_bp.route('/pendientes_validacion', methods=['GET'])
def get_pendientes_validacion():
    try:
        conn, cur = get_cursor()
        
        # ✅ CONSULTAS PARAMETRIZADAS
        cur.execute("""
            SELECT * FROM pagos 
            WHERE estado = 'pagado' AND (validado IS NULL OR validado = FALSE)
            ORDER BY fecha DESC, hora DESC
        """)
        pendientes = [dict(row) for row in cur.fetchall()]
        
        cur.execute("""
            SELECT * FROM pagos 
            WHERE estado = 'pagado' AND validado = TRUE
            ORDER BY fecha DESC, hora DESC
        """)
        validados = [dict(row) for row in cur.fetchall()]
        
        cur.execute("""
            SELECT COALESCE(SUM(monto), 0) as total FROM pagos 
            WHERE estado = 'pagado' AND validado = TRUE
        """)
        total_pagado = cur.fetchone()[0] or 0
        
        cur.close()
        conn.close()
        
        return jsonify({
            "pendientes": pendientes,
            "validados": validados,
            "total_pagado": total_pagado
        })
    except Exception as e:
        logger.error(f"Error en get_pendientes_validacion: {e}")
        return jsonify({"error": str(e)}), 500
# ============================
# 9. VALIDAR PAGO (CON DESCUENTO DE STOCK Y VALIDACIÓN)
# ============================
@pago_bp.route('/validar_pago/<int:id_reg>', methods=['POST'])
def validar_pago(id_reg):
    try:
        data = request.json
        logger.info(f"📥 Validando pago ID {id_reg}")
        
        # ✅ SANITIZAR DATOS
        detalles_repuestos = data.get('detalles_repuestos', [])
        costo_repuestos = sanitizar_numero(data.get('costo_repuestos', 0), min_val=0)
        costo_mano_obra = sanitizar_numero(data.get('costo_mano_obra_real', 0), min_val=0)
        costo_diagnostico = sanitizar_numero(data.get('costo_diagnostico_real', 0), min_val=0)
        ganancia_neta = sanitizar_numero(data.get('ganancia_neta', 0))
        observaciones_pago = sanitizar_input(data.get('observaciones_pago', ''))
        validado_por = sanitizar_input(data.get('validado_por', 'Sistema'))
        diagnostico = sanitizar_input(data.get('diagnostico', ''))
        reparacion = sanitizar_input(data.get('reparacion', 'Reparación realizada'))
        resultado = sanitizar_input(data.get('resultado', 'reparado'))
        tiempo_estimado = data.get('tiempo_estimado', '00:00:00')
        
        conn = get_connection()
        cur = conn.cursor()
        
        # Verificar si es flota
        cur.execute("SELECT flota FROM pagos WHERE id = %s", (id_reg,))
        registro = cur.fetchone()
        if not registro:
            cur.close()
            conn.close()
            return jsonify({"error": "Registro no encontrado"}), 404
            
        es_flota = registro[0] and registro[0].strip() != ''
        estado_pago = 'pendiente' if es_flota else 'pagado'
        fecha_pago_real = None if es_flota else get_fecha_chile().strftime('%Y-%m-%d')
        
        logger.info(f"🚛 ¿Es flota? {es_flota} → estado_pago: {estado_pago}")
        
        # ============================================
        # ✅ PROCESAR CADA REPUESTO CON VALIDACIÓN DE STOCK (SIEMPRE DESCUENTA)
        # ============================================
        for item in detalles_repuestos:
            nombre = sanitizar_input(item.get('nombre', '').strip())
            cantidad = int(sanitizar_numero(item.get('cantidad', 1), min_val=1))
            costo_unitario = sanitizar_numero(item.get('costo_unitario', 0), min_val=0)
            
            if nombre:
                cur.execute(
                    "SELECT id, stock, costo_proveedor, costo_venta_final FROM repuestos WHERE nombre = %s",
                    (nombre,)
                )
                existente = cur.fetchone()
                
                if existente:
                    id_existente, stock_actual, costo_prov, costo_venta_existente = existente
                    
                    # ✅ VERIFICAR STOCK (SIEMPRE, incluso en flotas)
                    if stock_actual is not None and stock_actual < cantidad:
                        cur.close()
                        conn.close()
                        return jsonify({
                            "error": f"Stock insuficiente para '{nombre}'. Disponible: {stock_actual}, Solicitado: {cantidad}"
                        }), 400
                    
                    # ✅ DESCONTAR STOCK (SIEMPRE, incluso en flotas)
                    nuevo_stock = (stock_actual or 0) - cantidad
                    cur.execute("""
                        UPDATE repuestos 
                        SET stock = %s,
                            updated_at = NOW() AT TIME ZONE 'America/Santiago'
                        WHERE id = %s
                    """, (nuevo_stock, id_existente))
                    logger.info(f"📦 Stock de '{nombre}': {stock_actual} → {nuevo_stock}")
                    
                    # Actualizar costo_venta_final si es 0
                    if costo_venta_existente == 0 and costo_unitario > 0:
                        cur.execute("""
                            UPDATE repuestos 
                            SET costo_venta_final = %s, 
                                updated_at = NOW() AT TIME ZONE 'America/Santiago'
                            WHERE id = %s
                        """, (costo_unitario, id_existente))
                        logger.info(f"✅ Repuesto '{nombre}' actualizado con costo_venta_final: ${costo_unitario}")
                else:
                    # Crear nuevo repuesto
                    iva = 1.19
                    costo_proveedor_estimado = int(costo_unitario / 1.19 / 1.3) if costo_unitario > 0 else 0
                    
                    cur.execute("""
                        INSERT INTO repuestos 
                        (nombre, costo_proveedor, margen_ganancia, costo_venta_final, proveedor, 
                         stock, costo_proveedor_pendiente, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, 
                                NOW() AT TIME ZONE 'America/Santiago', 
                                NOW() AT TIME ZONE 'America/Santiago')
                        RETURNING id
                    """, (
                        nombre,
                        costo_proveedor_estimado,
                        30,
                        costo_unitario,
                        'Desde Validación',
                        0,
                        costo_proveedor_estimado == 0
                    ))
                    id_nuevo = cur.fetchone()[0]
                    logger.info(f"✅ Repuesto '{nombre}' creado con costo_venta_final: ${costo_unitario} (ID: {id_nuevo})")
        
        # ============================================
        # ✅ ACTUALIZAR PAGO
        # ============================================
        detalles_json = json.dumps(detalles_repuestos)
        cur.execute("""
            UPDATE pagos 
            SET costo_repuestos_real = %s,
                costo_mano_obra_real = %s,
                costo_diagnostico_real = %s,
                ganancia_neta = %s,
                observaciones_pago = %s,
                validado = TRUE,
                validado_por = %s,
                fecha_validacion = NOW() AT TIME ZONE 'America/Santiago',
                diagnostico = %s,
                reparacion = %s,
                resultado = %s,
                tiempo_estimado = %s,
                detalles_repuestos = %s::jsonb,
                estado_pago = %s,
                fecha_pago_real = %s
            WHERE id = %s
        """, (
            costo_repuestos,
            costo_mano_obra,
            costo_diagnostico,
            ganancia_neta,
            observaciones_pago,
            validado_por,
            diagnostico,
            reparacion,
            resultado,
            tiempo_estimado,
            detalles_json,
            estado_pago,
            fecha_pago_real,
            id_reg
        ))
        
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info(f"✅ Validación completada para ID {id_reg} - estado_pago: {estado_pago}")
        return jsonify({"success": True, "estado_pago": estado_pago})
        
    except Exception as e:
        logger.error(f"Error en validar_pago ID {id_reg}: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# ============================
# 10. REPUESTOS - OBTENER LISTA
# ============================
@pago_bp.route('/repuestos', methods=['GET'])
def get_repuestos_lista():
    try:
        query = sanitizar_input(request.args.get('q', '').strip())
        conn, cur = get_cursor()
        
        if query and len(query) >= 2:
            # ✅ CONSULTA PARAMETRIZADA
            cur.execute("""
                SELECT 
                    id, 
                    nombre, 
                    COALESCE(costo_venta_final, 0) as costo,
                    proveedor,
                    costo_proveedor_pendiente,
                    categoria_nombre,
                    stock
                FROM repuestos 
                WHERE nombre ILIKE %s 
                ORDER BY nombre 
                LIMIT 10
            """, (f'%{query}%',))
            repuestos = [dict(row) for row in cur.fetchall()]
        else:
            cur.execute("""
                SELECT 
                    id, 
                    nombre, 
                    costo_proveedor, 
                    margen_ganancia,
                    COALESCE(costo_venta_final, 0) as costo_venta_final,
                    proveedor,
                    costo_proveedor_pendiente,
                    categoria_nombre,
                    subcategoria_id,
                    stock
                FROM repuestos 
                ORDER BY nombre
            """)
            rows = cur.fetchall()
            repuestos = []
            for row in rows:
                repuestos.append({
                    'id': row[0],
                    'nombre': row[1],
                    'costo_proveedor': float(row[2] or 0),
                    'margen_ganancia': float(row[3] or 30),
                    'costo_venta_final': float(row[4] or 0),
                    'proveedor': row[5] or '',
                    'costo_proveedor_pendiente': row[6] or False,
                    'categoria_nombre': row[7] if len(row) > 7 else None,
                    'stock': int(row[8]) if len(row) > 8 and row[8] is not None else 0
                })
        
        cur.close()
        conn.close()
        return jsonify(repuestos)
    except Exception as e:
        logger.error(f"Error en get_repuestos_lista: {e}")
        return jsonify([])
# Backend/routes/catalogo_routes.py

# ============================
# 11. FLOTAS PENDIENTES AGRUPADAS
# ============================
@pago_bp.route('/flotas_pendientes_agrupadas', methods=['GET'])
def get_flotas_pendientes_agrupadas():
    try:
        conn, cur = get_cursor()
        
        # ✅ CONSULTA PARAMETRIZADA
        cur.execute("""
            SELECT * FROM pagos 
            WHERE estado = 'pagado' 
            AND estado_pago = 'pendiente'
            AND flota IS NOT NULL 
            AND flota != ''
            ORDER BY flota, fecha DESC
        """)
        
        rows = cur.fetchall()
        registros = [dict(row) for row in rows]
        
        flotas_agrupadas = {}
        for r in registros:
            nombre_flota = r.get('flota', 'Sin flota')
            if nombre_flota not in flotas_agrupadas:
                flotas_agrupadas[nombre_flota] = {
                    'nombre': nombre_flota,
                    'servicios': [],
                    'total_pendiente': 0
                }
            flotas_agrupadas[nombre_flota]['servicios'].append(r)
            flotas_agrupadas[nombre_flota]['total_pendiente'] += float(r.get('monto', 0) or 0)
        
        resultado = list(flotas_agrupadas.values())
        
        cur.close()
        conn.close()
        
        return jsonify(resultado)
    except Exception as e:
        logger.error(f"Error en get_flotas_pendientes_agrupadas: {e}")
        return jsonify({"error": str(e)}), 500

# ============================
# 12. BALANCE DE VENTAS (CORREGIDO)
# ============================
@pago_bp.route('/balance_ventas', methods=['GET'])
def balance_ventas():
    try:
        filtro = request.args.get('filtro', 'hoy')
        
        # ✅ VALIDAR FILTRO
        if not validar_filtro(filtro):
            return jsonify({"error": "Filtro inválido"}), 400
        
        hoy = get_fecha_chile()
        conn, cur = get_cursor()
        
        # ✅ CONSULTA PARAMETRIZADA
        query = "SELECT * FROM pagos WHERE estado = 'pagado' AND estado_pago = 'pagado'"
        params = []
        
        if filtro == 'hoy':
            query += " AND fecha = %s"
            params.append(hoy.strftime('%Y-%m-%d'))
        elif filtro == '7d':
            query += " AND fecha >= %s"
            params.append((hoy - timedelta(days=7)).strftime('%Y-%m-%d'))
        elif filtro == 'mes':
            query += " AND fecha >= %s"
            params.append((hoy - timedelta(days=30)).strftime('%Y-%m-%d'))
        
        query += " ORDER BY fecha DESC, hora DESC"
        cur.execute(query, params)
        rows = cur.fetchall()
        registros = [dict(row) for row in rows]
        
        # ✅ PROCESAR REPUESTOS (CON CONSULTAS PARAMETRIZADAS)
        for r in registros:
            total = 0
            detalles = r.get('detalles_repuestos', [])
            for item in detalles:
                cantidad = item.get('cantidad', 1)
                precio = item.get('costo_unitario', 0) or item.get('costo', 0)
                total += cantidad * precio
            r['total_repuestos'] = total
        
        # ============================================
        # ✅ CLASIFICACIÓN NUEVA (CORREGIDA)
        # ============================================
        trabajo = []
        directa = []
        
        for r in registros:
            # ✅ CALCULAR VENTA DE REPUESTOS
            total_repuestos = 0
            detalles = r.get('detalles_repuestos', [])
            if detalles and len(detalles) > 0:
                for item in detalles:
                    cantidad = int(item.get('cantidad', 1) or 1)
                    precio = float(item.get('costo_unitario', 0) or item.get('costo', 0) or 0)
                    total_repuestos += cantidad * precio
            else:
                total_repuestos = float(r.get('costo_repuestos_real', 0) or 0)
            
            # ✅ CLASIFICAR POR TIPO DE VENTA
            es_directa = r.get('tipo_venta') == 'directa'
            
            if es_directa:
                directa.append(r)
            else:
                trabajo.append(r)
        
        # ============================================
        # ✅ FUNCIONES DE CÁLCULO (FUERA DEL BUCLE)
        # ============================================
        def calcular_venta_repuestos(registros):
            total = 0
            for r in registros:
                detalles = r.get('detalles_repuestos', [])
                if detalles and len(detalles) > 0:
                    for item in detalles:
                        cantidad = int(item.get('cantidad', 1) or 1)
                        precio_venta = float(item.get('costo_unitario', 0) or item.get('costo', 0) or 0)
                        total += cantidad * precio_venta
                else:
                    total += float(r.get('costo_repuestos_real', 0) or 0)
            return total
        
        def calcular_costo_repuestos(registros):
            total = 0
            for r in registros:
                detalles = r.get('detalles_repuestos', [])
                if detalles and len(detalles) > 0:
                    for item in detalles:
                        nombre = item.get('nombre', '')
                        cantidad = int(item.get('cantidad', 1) or 1)
                        
                        if nombre:
                            # ✅ CONSULTA PARAMETRIZADA
                            cur.execute("SELECT costo_proveedor FROM repuestos WHERE nombre = %s", (nombre,))
                            resultado = cur.fetchone()
                            if resultado:
                                costo_prov = float(resultado[0] or 0)
                                total += costo_prov * cantidad
                            else:
                                precio = float(item.get('costo_unitario', 0) or item.get('costo', 0) or 0)
                                total += precio * cantidad
                        else:
                            precio = float(item.get('costo_unitario', 0) or item.get('costo', 0) or 0)
                            total += precio * cantidad
                else:
                    total += float(r.get('costo_repuestos_real', 0) or 0)
            return total
        
        def calcular_margen_promedio(registros):
            margenes = []
            for r in registros:
                detalles = r.get('detalles_repuestos', [])
                for item in detalles:
                    nombre = item.get('nombre', '')
                    if nombre:
                        # ✅ CONSULTA PARAMETRIZADA
                        cur.execute("SELECT margen_ganancia FROM repuestos WHERE nombre ILIKE %s", (nombre,))
                        resultado = cur.fetchone()
                        if resultado and resultado[0] is not None and resultado[0] > 0:
                            margenes.append(float(resultado[0]))
            if margenes:
                return sum(margenes) / len(margenes)
            return 0
        
        # ============================================
        # ✅ CALCULAR TOTALES
        # ============================================
        total_ventas = calcular_venta_repuestos(registros)
        total_trabajo = calcular_venta_repuestos(trabajo)
        total_directa = calcular_venta_repuestos(directa)
        
        costo_trabajo = calcular_costo_repuestos(trabajo)
        costo_directa = calcular_costo_repuestos(directa)
        
        trabajo_margen = calcular_margen_promedio(trabajo)
        directa_margen = calcular_margen_promedio(directa)
        
        ganancia_trabajo = total_trabajo - costo_trabajo
        ganancia_directa = total_directa - costo_directa
        ganancia_neta = ganancia_trabajo + ganancia_directa
        
        cur.close()
        conn.close()
        
        return jsonify({
            "registros": registros,
            "total_ventas": total_ventas,
            "total_trabajo": total_trabajo,
            "total_directa": total_directa,
            "ganancia_trabajo": round(ganancia_trabajo, 2),
            "ganancia_directa": round(ganancia_directa, 2),
            "ganancia_neta": round(ganancia_neta, 2),
            "total_repuestos_trabajo": round(costo_trabajo, 2),
            "total_repuestos_directa": round(costo_directa, 2),
            "trabajo_margen": round(trabajo_margen, 1),
            "directa_margen": round(directa_margen, 1)
        })
    except Exception as e:
        logger.error(f"Error en balance_ventas: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
# ============================
# 13. VERIFICAR DUPLICADO
# ============================
@pago_bp.route('/verificar_duplicado', methods=['GET'])
def verificar_duplicado():
    try:
        nombre = sanitizar_input(request.args.get('nombre', '').strip())
        patente = sanitizar_patente(request.args.get('patente', '').strip())
        
        if not nombre or not patente:
            return jsonify({"duplicado": False})
        
        conn, cur = get_cursor()
        
        # ✅ CONSULTA PARAMETRIZADA
        cur.execute("""
            SELECT COUNT(*) FROM pagos 
            WHERE nombre = %s 
            AND patente = %s 
            AND fecha >= CURRENT_DATE
        """, (nombre, patente))
        
        count = cur.fetchone()[0]
        cur.close()
        conn.close()
        
        return jsonify({"duplicado": count > 0})
    except Exception as e:
        logger.error(f"Error en verificar_duplicado: {e}")
        return jsonify({"duplicado": False}), 500
# 1. obtener_pagados_con_filtro() - Para el balance general
@staticmethod
def obtener_pagados_con_filtro(filtro, fecha):
    """Obtiene pagos pagados con filtro para el balance general"""
    try:
        if not validar_filtro(filtro):
            filtro = 'todos'
        
        conn, cur = get_cursor()
        query = "SELECT * FROM pagos WHERE estado = 'pagado' AND estado_pago = 'pagado'"
        params = []
        
        if filtro == 'hoy':
            query += " AND fecha = %s"
            params.append(fecha.strftime('%Y-%m-%d'))
        elif filtro == '7d':
            query += " AND fecha >= %s"
            params.append((fecha - timedelta(days=7)).strftime('%Y-%m-%d'))
        elif filtro == 'mes':
            query += " AND fecha >= %s"
            params.append((fecha - timedelta(days=30)).strftime('%Y-%m-%d'))
        
        query += " ORDER BY fecha DESC, hora DESC"
        cur.execute(query, params)
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Error obtener pagados con filtro: {e}")
        return []

# 2. obtener_flotas_disponibles() - Para el autocompletado de flotas
@staticmethod
def obtener_flotas_disponibles():
    """Obtiene todas las flotas registradas (nombres únicos)"""
    try:
        conn, cur = get_cursor()
        cur.execute("""
            SELECT DISTINCT flota FROM pagos 
            WHERE flota IS NOT NULL AND flota != '' 
            ORDER BY flota
        """)
        flotas = [row[0] for row in cur.fetchall()]
        cur.close()
        conn.close()
        return flotas
    except Exception as e:
        logger.error(f"Error obtener flotas disponibles: {e}")
        return []

# 3. obtener_balance_completo() - Para el balance con totales
@staticmethod
def obtener_balance_completo(filtro, fecha):
    """Obtiene el balance completo con totales"""
    try:
        if not validar_filtro(filtro):
            filtro = 'todos'
        
        conn, cur = get_cursor()
        query = """
            SELECT 
                *,
                COALESCE(SUM(monto) OVER(), 0) as total_pagado,
                COALESCE(SUM(costo_repuestos_real) OVER(), 0) as total_repuestos,
                COALESCE(SUM(costo_mano_obra_real) OVER(), 0) as total_mano_obra,
                COALESCE(SUM(costo_diagnostico_real) OVER(), 0) as total_diagnostico
            FROM pagos 
            WHERE estado = 'pagado' AND estado_pago = 'pagado'
        """
        params = []
        
        if filtro == 'hoy':
            query += " AND fecha = %s"
            params.append(fecha.strftime('%Y-%m-%d'))
        elif filtro == '7d':
            query += " AND fecha >= %s"
            params.append((fecha - timedelta(days=7)).strftime('%Y-%m-%d'))
        elif filtro == 'mes':
            query += " AND fecha >= %s"
            params.append((fecha - timedelta(days=30)).strftime('%Y-%m-%d'))
        
        query += " ORDER BY fecha DESC, hora DESC"
        cur.execute(query, params)
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Error obtener balance completo: {e}")
        return []

# 4. actualizar_repuestos_venta() - Para editar repuestos de venta
@staticmethod
def actualizar_repuestos_venta(id_reg, data):
    """Actualiza solo los repuestos y costos de una venta"""
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        cur.execute("""
            UPDATE pagos 
            SET detalles_repuestos = %s::jsonb,
                costo_repuestos_real = %s,
                costo_mano_obra_real = %s,
                costo_diagnostico_real = %s,
                ganancia_neta = %s,
                monto = %s,
                actualizado_en = NOW() AT TIME ZONE 'America/Santiago'
            WHERE id = %s
        """, (
            json.dumps(data.get('detalles_repuestos', [])),
            data.get('costo_repuestos_real', 0),
            data.get('costo_mano_obra_real', 0),
            data.get('costo_diagnostico_real', 0),
            data.get('ganancia_neta', 0),
            data.get('monto', 0),
            id_reg
        ))
        
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error actualizar repuestos venta: {e}")
        return False
# ============================
# OBTENER SUBCATEGORÍAS PARA SELECT
# ============================
@pago_bp.route('/subcategorias_repuestos', methods=['GET'])
def get_subcategorias_repuestos():
    """Obtiene todas las subcategorías para el select de edición"""
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT 
                sc.id,
                sc.nombre,
                c.nombre as categoria_nombre
            FROM subcategorias_repuestos sc
            JOIN categorias_repuestos c ON c.id = sc.categoria_id
            ORDER BY c.nombre, sc.nombre
        """)
        
        subcategorias = []
        for row in cur.fetchall():
            subcategorias.append({
                'id': row[0],
                'nombre': row[1],
                'categoria_nombre': row[2]
            })
        
        cur.close()
        conn.close()
        return jsonify(subcategorias)
    except Exception as e:
        logger.error(f"Error en get_subcategorias_repuestos: {e}")
        return jsonify([])
# 5. obtener_dashboard_data() - Para el dashboard
@staticmethod
def obtener_dashboard_data(fecha_desde):
    """Obtiene datos para el dashboard"""
    try:
        conn, cur = get_cursor()
        
        # Totales
        cur.execute("""
            SELECT 
                COALESCE(SUM(monto), 0) as total_facturado,
                COALESCE(SUM(costo_repuestos_real), 0) as total_repuestos,
                COALESCE(SUM(costo_mano_obra_real), 0) as total_mano_obra,
                COALESCE(SUM(costo_diagnostico_real), 0) as total_diagnostico,
                COUNT(*) as total_servicios
            FROM pagos 
            WHERE estado = 'pagado' 
            AND estado_pago = 'pagado'
            AND fecha >= %s
        """, (fecha_desde,))
        totales = cur.fetchone()
        
        # Ventas diarias
        cur.execute("""
            SELECT 
                fecha,
                COALESCE(SUM(monto), 0) as total
            FROM pagos 
            WHERE estado = 'pagado' 
            AND estado_pago = 'pagado'
            AND fecha >= %s
            GROUP BY fecha
            ORDER BY fecha ASC
        """, (fecha_desde,))
        ventas = cur.fetchall()
        
        # Ganancia acumulada
        cur.execute("""
            SELECT 
                fecha,
                COALESCE(SUM(monto - COALESCE(costo_repuestos_real, 0) - COALESCE(costo_mano_obra_real, 0) - COALESCE(costo_diagnostico_real, 0)), 0) as ganancia
            FROM pagos 
            WHERE estado = 'pagado' 
            AND estado_pago = 'pagado'
            AND fecha >= %s
            GROUP BY fecha
            ORDER BY fecha ASC
        """, (fecha_desde,))
        ganancias = cur.fetchall()
        
        # Top clientes
        cur.execute("""
            SELECT 
                nombre,
                COALESCE(SUM(monto), 0) as total_gastado
            FROM pagos 
            WHERE estado = 'pagado' 
            AND estado_pago = 'pagado'
            AND nombre IS NOT NULL
            AND fecha >= %s
            GROUP BY nombre
            ORDER BY total_gastado DESC
            LIMIT 5
        """, (fecha_desde,))
        clientes = cur.fetchall()
        
        # Promedio diario
        cur.execute("""
            SELECT 
                COALESCE(AVG(monto), 0) as promedio_diario
            FROM pagos 
            WHERE estado = 'pagado' 
            AND estado_pago = 'pagado'
            AND fecha >= %s
        """, (fecha_desde,))
        promedio = cur.fetchone()
        
        cur.close()
        conn.close()
        
        return {
            'totales': totales,
            'ventas': ventas,
            'ganancias': ganancias,
            'clientes': clientes,
            'promedio_diario': promedio[0] if promedio else 0
        }
    except Exception as e:
        logger.error(f"Error obtener dashboard data: {e}")
        return None
# ============================
# 6. BALANCE DE GANANCIA (CON GASTOS)
# ============================
@pago_bp.route('/balance', methods=['GET'])
def get_balance():
    filtro = request.args.get('filtro', 'hoy')
    hoy = get_fecha_chile()
    
    try:
        conn, cur = get_cursor()
        
        # ============================================
        # 1. OBTENER VENTAS
        # ============================================
        query = """
            SELECT * FROM pagos 
            WHERE estado = 'pagado' 
            AND estado_pago = 'pagado'
        """
        params = []
        
        if filtro == 'hoy':
            query += " AND fecha = %s"
            params.append(hoy.strftime('%Y-%m-%d'))
        elif filtro == '7d':
            query += " AND fecha >= %s"
            params.append((hoy - timedelta(days=7)).strftime('%Y-%m-%d'))
        elif filtro == 'mes':
            query += " AND fecha >= %s"
            params.append((hoy - timedelta(days=30)).strftime('%Y-%m-%d'))
        
        query += " ORDER BY fecha DESC, hora DESC"
        cur.execute(query, params)
        rows = cur.fetchall()
        registros = [dict(row) for row in rows]
        
        total_pagado = float(sum(r.get('monto', 0) or 0 for r in registros))
        total_repuestos = float(sum(r.get('costo_repuestos_real', 0) or 0 for r in registros))
        total_mano_obra = float(sum(r.get('costo_mano_obra_real', 0) or 0 for r in registros))
        total_diagnostico = float(sum(r.get('costo_diagnostico_real', 0) or 0 for r in registros))
        ganancia_neta = total_pagado - (total_repuestos + total_mano_obra + total_diagnostico)
        
        # ============================================
        # 2. OBTENER GASTOS OPERATIVOS
        # ============================================
        # Definir fechas según el filtro
        if filtro == 'hoy':
            fecha_inicio = hoy.strftime('%Y-%m-%d')
            fecha_fin = hoy.strftime('%Y-%m-%d')
        elif filtro == '7d':
            fecha_inicio = (hoy - timedelta(days=7)).strftime('%Y-%m-%d')
            fecha_fin = hoy.strftime('%Y-%m-%d')
        elif filtro == 'mes':
            fecha_inicio = (hoy - timedelta(days=30)).strftime('%Y-%m-%d')
            fecha_fin = hoy.strftime('%Y-%m-%d')
        else:
            fecha_inicio = '2020-01-01'
            fecha_fin = hoy.strftime('%Y-%m-%d')
        
        # Consultar gastos
        cur.execute("""
            SELECT * FROM gastos 
            WHERE fecha BETWEEN %s AND %s
            ORDER BY fecha DESC, hora DESC
        """, (fecha_inicio, fecha_fin))
        
        gastos_rows = cur.fetchall()
        gastos_operativos = []
        total_gastos = 0
        
        for row in gastos_rows:
            g = dict(row)
            # Convertir time a string
            if g.get('hora') and hasattr(g['hora'], 'strftime'):
                g['hora'] = g['hora'].strftime('%H:%M:%S')
            if g.get('fecha') and hasattr(g['fecha'], 'strftime'):
                g['fecha'] = g['fecha'].strftime('%Y-%m-%d')
            if g.get('created_at') and hasattr(g['created_at'], 'strftime'):
                g['created_at'] = g['created_at'].strftime('%Y-%m-%d %H:%M:%S')
            if g.get('updated_at') and hasattr(g['updated_at'], 'strftime'):
                g['updated_at'] = g['updated_at'].strftime('%Y-%m-%d %H:%M:%S')
            gastos_operativos.append(g)
            total_gastos += float(g.get('monto', 0) or 0)
        
        # ============================================
        # 3. CALCULAR GANANCIA REAL (SIN DIAGNÓSTICO)
        # ============================================
        ganancia_real = total_pagado - total_repuestos - total_mano_obra - total_gastos
        
        cur.close()
        conn.close()
        
        # ============================================
        # 4. RESPUESTA CON GASTOS INCLUIDOS
        # ============================================
        return jsonify({
            "registros": registros,
            "total_pagado": total_pagado,
            "total_repuestos": total_repuestos,
            "total_mano_obra": total_mano_obra,
            "total_diagnostico": total_diagnostico,
            "ganancia_neta": ganancia_neta,
            "total_gastos": total_gastos,
            "gastos_operativos": gastos_operativos,
            "ganancia_real": ganancia_real
        })
    except Exception as e:
        print(f"Error en get_balance: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# 2. Editar repuestos de venta
@pago_bp.route('/editar_repuestos_venta/<int:id_reg>', methods=['POST'])
def editar_repuestos_venta(id_reg):
    """Actualiza solo los repuestos y costos de una venta"""
    try:
        data = request.json
        resultado = PagoService.actualizar_repuestos_venta(id_reg, data)
        if resultado:
            return jsonify({"success": True})
        return jsonify({"error": "Error al actualizar"}), 500
    except Exception as e:
        logger.error(f"Error en editar_repuestos_venta: {e}")
        return jsonify({"error": str(e)}), 500

# 3. Eliminar registro
@pago_bp.route('/eliminar_registro/<int:id_reg>', methods=['DELETE'])
def eliminar_registro(id_reg):
    """Elimina un registro por ID"""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM pagos WHERE id = %s", (id_reg,))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Error en eliminar_registro: {e}")
        return jsonify({"error": str(e)}), 500

# 4. Flotas disponibles (para autocompletado)
@pago_bp.route('/flotas_disponibles', methods=['GET'])
def get_flotas_disponibles():
    """Obtiene todas las flotas registradas para autocompletado"""
    try:
        flotas = PagoService.obtener_flotas_disponibles()
        return jsonify(flotas)
    except Exception as e:
        logger.error(f"Error en get_flotas_disponibles: {e}")
        return jsonify([])
# ============================
# 5. DASHBOARD (COMPLETO CON GASTOS)
# ============================
@pago_bp.route('/dashboard', methods=['GET'])
def get_dashboard():
    """Obtiene datos para el dashboard con gastos incluidos"""
    try:
        filtro = request.args.get('filtro', '7d')
        mes = request.args.get('mes')
        anio = request.args.get('anio')
        
        hoy = get_fecha_chile()
        
        # ============================================
        # 1. DETERMINAR FECHAS SEGÚN FILTRO
        # ============================================
        if filtro == '7d':
            fecha_desde = hoy - timedelta(days=7)
        elif filtro == '30d':
            fecha_desde = hoy - timedelta(days=30)
        elif filtro == '90d':
            fecha_desde = hoy - timedelta(days=90)
        elif filtro == 'mes' and mes and anio:
            try:
                fecha_desde = datetime(int(anio), int(mes), 1).date()
            except:
                fecha_desde = hoy - timedelta(days=30)
        else:
            fecha_desde = hoy - timedelta(days=7)
        
        fecha_desde_str = fecha_desde.strftime('%Y-%m-%d')
        fecha_hasta_str = hoy.strftime('%Y-%m-%d')
        
        conn, cur = get_cursor()
        
        # ============================================
        # 2. OBTENER DATOS DE VENTAS
        # ============================================
        cur.execute("""
            SELECT 
                COALESCE(SUM(monto), 0) as total_facturado,
                COALESCE(SUM(costo_repuestos_real), 0) as total_repuestos,
                COALESCE(SUM(costo_mano_obra_real), 0) as total_mano_obra,
                COALESCE(SUM(costo_diagnostico_real), 0) as total_diagnostico,
                COUNT(*) as total_servicios
            FROM pagos 
            WHERE estado = 'pagado' 
            AND estado_pago = 'pagado'
            AND fecha >= %s
        """, (fecha_desde_str,))
        totales = cur.fetchone()
        
        # Ventas diarias
        cur.execute("""
            SELECT 
                fecha,
                COALESCE(SUM(monto), 0) as total
            FROM pagos 
            WHERE estado = 'pagado' 
            AND estado_pago = 'pagado'
            AND fecha >= %s
            GROUP BY fecha
            ORDER BY fecha ASC
        """, (fecha_desde_str,))
        ventas = cur.fetchall()
        
        # Ganancia acumulada
        cur.execute("""
            SELECT 
                fecha,
                COALESCE(SUM(monto - COALESCE(costo_repuestos_real, 0) - COALESCE(costo_mano_obra_real, 0) - COALESCE(costo_diagnostico_real, 0)), 0) as ganancia
            FROM pagos 
            WHERE estado = 'pagado' 
            AND estado_pago = 'pagado'
            AND fecha >= %s
            GROUP BY fecha
            ORDER BY fecha ASC
        """, (fecha_desde_str,))
        ganancias = cur.fetchall()
        
        # Top clientes
        cur.execute("""
            SELECT 
                nombre,
                COALESCE(SUM(monto), 0) as total_gastado
            FROM pagos 
            WHERE estado = 'pagado' 
            AND estado_pago = 'pagado'
            AND nombre IS NOT NULL
            AND fecha >= %s
            GROUP BY nombre
            ORDER BY total_gastado DESC
            LIMIT 5
        """, (fecha_desde_str,))
        clientes = cur.fetchall()
        
        # Promedio diario
        cur.execute("""
            SELECT 
                COALESCE(AVG(monto), 0) as promedio_diario
            FROM pagos 
            WHERE estado = 'pagado' 
            AND estado_pago = 'pagado'
            AND fecha >= %s
        """, (fecha_desde_str,))
        promedio = cur.fetchone()
        promedio_diario = float(promedio[0]) if promedio and promedio[0] else 0
        
        # ============================================
        # 3. OBTENER REGISTROS PARA TOTAL DIRECTA/TRABAJO
        # ============================================
        cur.execute("""
            SELECT id, monto, marca, modelo, tipo_venta, detalles_repuestos
            FROM pagos 
            WHERE estado = 'pagado' 
            AND estado_pago = 'pagado'
            AND fecha >= %s
        """, (fecha_desde_str,))
        registros_rows = cur.fetchall()
        
        total_directa = 0
        total_trabajo = 0
        
        for row in registros_rows:
            r = dict(row)
            
            # ✅ CALCULAR VENTA DE REPUESTOS PARA CADA REGISTRO
            total_repuestos = 0
            detalles = r.get('detalles_repuestos', [])
            if detalles and len(detalles) > 0:
                for item in detalles:
                    cantidad = int(item.get('cantidad', 1) or 1)
                    precio = float(item.get('costo_unitario', 0) or item.get('costo', 0) or 0)
                    total_repuestos += cantidad * precio
            else:
                total_repuestos = float(r.get('costo_repuestos_real', 0) or 0)
            
            # ✅ CLASIFICAR POR TIPO DE VENTA
            es_directa = r.get('tipo_venta') == 'directa'
            
            if es_directa:
                total_directa += total_repuestos
            else:
                total_trabajo += total_repuestos
        
        # ============================================
        # 4. OBTENER GASTOS DEL PERÍODO
        # ============================================
        cur.execute("""
            SELECT * FROM gastos 
            WHERE fecha BETWEEN %s AND %s
            ORDER BY fecha DESC, hora DESC
        """, (fecha_desde_str, fecha_hasta_str))
        gastos_rows = cur.fetchall()
        
        gastos_operativos = []
        total_gastos = 0
        
        for row in gastos_rows:
            g = dict(row)
            if g.get('hora') and hasattr(g['hora'], 'strftime'):
                g['hora'] = g['hora'].strftime('%H:%M:%S')
            if g.get('fecha') and hasattr(g['fecha'], 'strftime'):
                g['fecha'] = g['fecha'].strftime('%Y-%m-%d')
            if g.get('created_at') and hasattr(g['created_at'], 'strftime'):
                g['created_at'] = g['created_at'].strftime('%Y-%m-%d %H:%M:%S')
            if g.get('updated_at') and hasattr(g['updated_at'], 'strftime'):
                g['updated_at'] = g['updated_at'].strftime('%Y-%m-%d %H:%M:%S')
            gastos_operativos.append(g)
            total_gastos += float(g.get('monto', 0) or 0)
        
        # ============================================
        # 5. GASTOS POR CATEGORÍA
        # ============================================
        from collections import defaultdict
        gastos_dict = defaultdict(float)
        for g in gastos_operativos:
            categoria = g.get('categoria', 'Otros')
            gastos_dict[categoria] += float(g.get('monto', 0) or 0)
        
        gastos_por_categoria = []
        total_gastos_cat = sum(gastos_dict.values())
        for cat, monto in gastos_dict.items():
            porcentaje = round((monto / total_gastos_cat) * 100, 1) if total_gastos_cat > 0 else 0
            gastos_por_categoria.append({
                'categoria': cat,
                'total': monto,
                'porcentaje': porcentaje
            })
        gastos_por_categoria.sort(key=lambda x: x['total'], reverse=True)
        
        # ============================================
        # 6. GASTOS DIARIOS PARA GRÁFICO
        # ============================================
        gastos_dia = defaultdict(float)
        for g in gastos_operativos:
            fecha = g.get('fecha', '')
            if fecha:
                gastos_dia[fecha] += float(g.get('monto', 0) or 0)
        
        gastos_labels = sorted(gastos_dia.keys())
        gastos_diarios = [gastos_dia[f] for f in gastos_labels]
        
        # ============================================
        # 7. PROCESAR DATOS PARA EL FRONTEND
        # ============================================
        labels = []
        ventas_data = []
        for row in ventas:
            if row[0]:
                labels.append(row[0].strftime('%d/%m'))
                ventas_data.append(float(row[1]))
        
        ganancia_data = []
        acumulado = 0
        for row in ganancias:
            acumulado += float(row[1])
            ganancia_data.append(acumulado)
        
        proyeccion = []
        proyeccion_labels = []
        for i in range(1, 8):
            fecha_futura = hoy + timedelta(days=i)
            proyeccion_labels.append(fecha_futura.strftime('%d/%m'))
            proyeccion.append(round(promedio_diario * 0.85, 0))
        
        meses_disponibles = PagoService.obtener_meses_disponibles()
        
        # ============================================
        # 8. CERRAR CONEXIÓN
        # ============================================
        cur.close()
        conn.close()
        
        # ============================================
        # 9. RESPUESTA COMPLETA
        # ============================================
        return jsonify({
            "total_facturado": float(totales[0]),
            "total_repuestos": float(totales[1]),
            "total_mano_obra": float(totales[2]),
            "total_diagnostico": float(totales[3]),
            "total_servicios": totales[4],
            "ganancia_total": float(totales[0]) - float(totales[1]) - float(totales[2]) - float(totales[3]),
            "promedio_diario": promedio_diario,
            "labels": labels,
            "ventas": ventas_data,
            "ganancia_acumulada": ganancia_data,
            "proyeccion_labels": proyeccion_labels,
            "proyeccion": proyeccion,
            "clientes_labels": [row[0] for row in clientes],
            "clientes_data": [float(row[1]) for row in clientes],
            "meses_disponibles": meses_disponibles,
            "filtro_actual": filtro,
            "mes_actual": mes,
            "anio_actual": anio,
            "registros": [dict(row) for row in registros_rows],
            "total_gastos": total_gastos,
            "gastos_operativos": gastos_operativos,
            "ganancia_real": float(totales[0]) - float(totales[1]) - float(totales[2]) - total_gastos,
            "total_directa": total_directa,
            "total_trabajo": total_trabajo,
            "gastos_por_categoria": gastos_por_categoria,
            "gastos_diarios": gastos_diarios,
            "gastos_labels": gastos_labels
        })
    except Exception as e:
        logger.error(f"Error en get_dashboard: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
# ============================
# BUSCAR REPUESTOS (AUTOCOMPLETADO)
# ============================
@pago_bp.route('/repuestos/buscar', methods=['GET'])
def buscar_repuestos():
    """Busca repuestos por nombre (autocompletado) con costo_venta_final"""
    try:
        query = request.args.get('q', '').strip()
        if len(query) < 2:
            return jsonify([])
        
        conn, cur = get_cursor()
        cur.execute("""
            SELECT 
                id, 
                nombre, 
                costo_venta_final as costo,
                proveedor
            FROM repuestos 
            WHERE nombre ILIKE %s 
            ORDER BY nombre 
            LIMIT 10
        """, (f'%{query}%',))
        repuestos = [dict(row) for row in cur.fetchall()]
        cur.close()
        conn.close()
        return jsonify(repuestos)
    except Exception as e:
        logger.error(f"Error en buscar_repuestos: {e}")
        return jsonify([])

# ============================
# TEST NOTIFICACIÓN PUSH
# ============================
@pago_bp.route('/test_notificacion', methods=['GET'])
def test_notificacion():
    """Prueba de notificaciones push"""
    try:
        from services.notification_service import enviar_notificacion_push
        
        logger.info("📨 TEST_NOTIFICACION - Iniciando prueba...")
        
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
                "mensaje": "No hay dispositivos suscritos. Acepta las notificaciones en tu navegador."
            })
    except Exception as e:
        logger.error(f"Error en test_notificacion: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
# ============================
# CREAR REPUESTO
# ============================
@pago_bp.route('/repuestos', methods=['POST'])
def crear_repuesto():
    """Crea un nuevo repuesto en el inventario"""
    try:
        data = request.json
        nombre = sanitizar_input(data.get('nombre', '').strip())
        costo_proveedor = sanitizar_numero(data.get('costo_proveedor', 0), min_val=0)
        margen_ganancia = sanitizar_numero(data.get('margen_ganancia', 30), min_val=0)
        proveedor = sanitizar_input(data.get('proveedor', '').strip())
        costo_venta_final = sanitizar_numero(data.get('costo_venta_final', 0), min_val=0)
        stock = int(sanitizar_numero(data.get('stock', 0), min_val=0))
        categoria_nombre = sanitizar_input(data.get('categoria_nombre', '').strip())
        
        # Si no hay precio de venta, calcularlo
        if costo_venta_final == 0 and costo_proveedor > 0:
            iva = 1.19
            costo_con_iva = costo_proveedor * iva
            costo_venta_final = costo_con_iva * (1 + (margen_ganancia / 100))
            costo_venta_final = int(costo_venta_final)
        
        costo_proveedor_pendiente = costo_proveedor == 0
        
        if not nombre:
            return jsonify({"error": "El nombre es obligatorio"}), 400
        
        conn = get_connection()
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO repuestos 
            (nombre, costo_proveedor, margen_ganancia, proveedor, costo_venta_final, 
             stock, categoria_nombre, costo_proveedor_pendiente, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 
                    NOW() AT TIME ZONE 'America/Santiago', 
                    NOW() AT TIME ZONE 'America/Santiago')
            RETURNING id
        """, (
            nombre, costo_proveedor, margen_ganancia, proveedor, 
            costo_venta_final, stock, categoria_nombre, costo_proveedor_pendiente
        ))
        
        id_repuesto = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info(f"✅ Repuesto creado: {nombre} (ID: {id_repuesto})")
        return jsonify({"success": True, "id": id_repuesto, "costo_venta_final": costo_venta_final})
        
    except Exception as e:
        logger.error(f"Error en crear_repuesto: {e}")
        return jsonify({"error": str(e)}), 500

# ============================
# ACTUALIZAR REPUESTO (CON LOGS Y STOCK CORREGIDO)
# ============================
@pago_bp.route('/repuestos/<int:id_repuesto>', methods=['PUT'])
def actualizar_repuesto(id_repuesto):
    try:
        data = request.json
        logger.info(f"📥 ACTUALIZAR REPUESTO ID {id_repuesto}")
        logger.info(f"📥 Datos recibidos: {data}")
        
        nombre = sanitizar_input(data.get('nombre', '').strip())
        costo_proveedor = sanitizar_numero(data.get('costo_proveedor', 0), min_val=0)
        margen_ganancia = sanitizar_numero(data.get('margen_ganancia', 30), min_val=0)
        proveedor = sanitizar_input(data.get('proveedor', '').strip())
        costo_venta_final = sanitizar_numero(data.get('costo_venta_final', 0), min_val=0)
        stock = int(sanitizar_numero(data.get('stock', 0), min_val=0))
        categoria_nombre = sanitizar_input(data.get('categoria_nombre', '').strip())
        
        subcategoria_id = data.get('subcategoria_id')
        if subcategoria_id:
            subcategoria_id = int(subcategoria_id)
            logger.info(f"📂 subcategoria_id recibido: {subcategoria_id}")
        else:
            subcategoria_id = None
            logger.info(f"📂 Sin subcategoria_id")
        
        logger.info(f"📦 Stock recibido: {stock}")
        
        if not nombre:
            return jsonify({"error": "El nombre es obligatorio"}), 400
        
        if costo_venta_final == 0 and costo_proveedor > 0:
            iva = 1.19
            costo_con_iva = costo_proveedor * iva
            costo_venta_final = costo_con_iva * (1 + (margen_ganancia / 100))
            costo_venta_final = int(costo_venta_final)
        
        costo_proveedor_pendiente = costo_proveedor == 0
        
        conn = get_connection()
        cur = conn.cursor()
        
        cur.execute("""
            UPDATE repuestos 
            SET nombre = %s, 
                costo_proveedor = %s, 
                margen_ganancia = %s, 
                proveedor = %s,
                costo_venta_final = %s,
                stock = %s,
                categoria_nombre = %s,
                subcategoria_id = %s,
                costo_proveedor_pendiente = %s,
                updated_at = NOW() AT TIME ZONE 'America/Santiago'
            WHERE id = %s
            RETURNING id
        """, (
            nombre, costo_proveedor, margen_ganancia, proveedor, 
            costo_venta_final, stock, categoria_nombre, subcategoria_id,
            costo_proveedor_pendiente, id_repuesto
        ))
        
        if cur.fetchone() is None:
            cur.close()
            conn.close()
            return jsonify({"error": "Repuesto no encontrado"}), 404
        
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info(f"✅ Repuesto actualizado: {nombre} (ID: {id_repuesto}) - Stock: {stock} - subcategoria_id: {subcategoria_id}")
        return jsonify({"success": True})
        
    except Exception as e:
        logger.error(f"Error en actualizar_repuesto: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
        
# ============================
# ELIMINAR REPUESTO
# ============================
@pago_bp.route('/repuestos/<int:id_repuesto>', methods=['DELETE'])
def eliminar_repuesto(id_repuesto):
    """Elimina un repuesto por ID"""
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        # Verificar si el repuesto existe
        cur.execute("SELECT id FROM repuestos WHERE id = %s", (id_repuesto,))
        if cur.fetchone() is None:
            cur.close()
            conn.close()
            return jsonify({"error": "Repuesto no encontrado"}), 404
        
        cur.execute("DELETE FROM repuestos WHERE id = %s RETURNING id", (id_repuesto,))
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info(f"✅ Repuesto eliminado: ID {id_repuesto}")
        return jsonify({"success": True})
        
    except Exception as e:
        logger.error(f"Error en eliminar_repuesto: {e}")
        return jsonify({"error": str(e)}), 500

# ============================
# GUARDAR SUSCRIPCIÓN PUSH
# ============================
@pago_bp.route('/guardar_suscripcion', methods=['POST'])
def guardar_suscripcion():
    """Guarda una suscripción push para notificaciones"""
    try:
        data = request.json
        endpoint = data.get('endpoint', '')
        keys = data.get('keys', {})
        auth_key = keys.get('auth', '')
        p256dh_key = keys.get('p256dh', '')
        
        if not endpoint:
            return jsonify({"error": "Endpoint es obligatorio"}), 400
        
        conn = get_connection()
        cur = conn.cursor()
        
        # Eliminar suscripción existente (si la hay)
        cur.execute("DELETE FROM push_subscriptions WHERE endpoint = %s", (endpoint,))
        
        # Insertar nueva suscripción
        cur.execute("""
            INSERT INTO push_subscriptions (endpoint, auth_key, p256dh_key)
            VALUES (%s, %s, %s)
        """, (endpoint, auth_key, p256dh_key))
        
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info(f"✅ Suscripción push guardada")
        return jsonify({"success": True})
        
    except Exception as e:
        logger.error(f"Error en guardar_suscripcion: {e}")
        return jsonify({"error": str(e)}), 500

# ============================
# ENVIAR NOTIFICACIÓN
# ============================
@pago_bp.route('/enviar_notificacion', methods=['POST'])
def enviar_notificacion_desde_frontend():
    """Endpoint para que el frontend envíe notificaciones push"""
    try:
        from services.notification_service import enviar_notificacion_push
        
        data = request.json
        titulo = data.get('titulo', 'Notificación')
        mensaje = data.get('mensaje', '')
        url = data.get('url', '/estado')
        id_reg = data.get('id', None)
        
        logger.info(f"📨 Enviando notificación desde frontend: {titulo}")
        
        enviados = enviar_notificacion_push(titulo, mensaje, url, id_reg)
        
        return jsonify({
            "success": enviados > 0,
            "enviados": enviados,
            "mensaje": f"Notificación enviada a {enviados} dispositivos"
        })
        
    except Exception as e:
        logger.error(f"Error en enviar_notificacion: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

# ============================
# FIN DEL ARCHIVO - NO HAY CÓDIGO FUERA DE FUNCIONES
# ============================
