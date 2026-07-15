from flask import Blueprint, request, jsonify, send_file
from services.pago_service import PagoService
from database import get_connection, get_cursor
from datetime import datetime, timedelta
from services.pdf_service import PDFService
import json
import io
import os
import traceback
import psycopg2.extras
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import pytz 
import math

# ============================
# ZONA HORARIA CHILE
# ============================
CHILE_TZ = pytz.timezone('America/Santiago')

def get_fecha_hora_chile():
    """Retorna fecha y hora actual en zona horaria Chile"""
    ahora = datetime.now(CHILE_TZ)
    return ahora.date(), ahora.time()

def get_fecha_chile():
    """Retorna fecha actual en zona horaria Chile"""
    return datetime.now(CHILE_TZ).date()

def get_hora_chile():
    """Retorna hora actual en zona horaria Chile"""
    return datetime.now(CHILE_TZ).time()

# ============================
# BLUEPRINT
# ============================
pago_bp = Blueprint('pago', __name__, url_prefix='/api')


# ============================
# 1. ESTADO (PENDIENTES + PAGADOS HOY)
# ============================
@pago_bp.route('/estado', methods=['GET'])
def get_estado():
    pendientes = PagoService.obtener_pendientes()
    pagados = PagoService.obtener_pagados_hoy()
    return jsonify({
        "pendientes": [p.to_dict() for p in pendientes],
        "pagados_hoy": [p.to_dict() for p in pagados],
        "total_pendientes": len(pendientes),
        "total_pagados_hoy": len(pagados)
    })


# ============================
# 1.5 OBTENER REGISTRO POR ID (RUTA EXACTA QUE USA JAVASCRIPT)
# ============================
@pago_bp.route('/registro/<int:id>', methods=['GET'])
def get_registro_js(id):
    """Ruta exacta que usa el JavaScript para editar/detalle"""
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("SELECT * FROM pagos WHERE id = %s", (id,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        
        if not row:
            return jsonify({"error": "Registro no encontrado"}), 404
        
        return jsonify(dict(row))
    except Exception as e:
        print(f"❌ Error en get_registro_js: {e}")
        return jsonify({"error": str(e)}), 500


# ============================
# 2. OBTENER REGISTRO POR ID (VERSIÓN CON PAGOSERVICE)
# ============================
@pago_bp.route('/registro/<int:id_reg>', methods=['GET'])
def get_registro(id_reg):
    pago = PagoService.obtener_por_id(id_reg)
    if pago:
        return jsonify(pago.to_dict())
    return jsonify({"error": "No encontrado"}), 404


# ============================
# 3. REGISTROS CON FILTROS (CORREGIDO)
# ============================
@pago_bp.route('/registros', methods=['GET'])
def get_registros_filtrados():
    filtro = request.args.get('filtro', 'todos')
    hoy = get_fecha_chile()
    
    try:
        conn, cur = get_cursor()
        # ✅ SOLO REGISTROS CON estado_pago = 'pagado'
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
        print(f"Error en get_registros_filtrados: {e}")
        return jsonify({"error": str(e)}), 500


# ============================
# 4. EDITAR REGISTRO COMPLETO
# ============================
@pago_bp.route('/editar_completo/<int:id_reg>', methods=['POST'])
def editar_completo(id_reg):
    data = request.json
    try:
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
            data.get('nombre'),
            data.get('telefono'),
            data.get('patente'),
            data.get('marca'),
            data.get('modelo'),
            data.get('anio', 0),
            data.get('flota'),
            data.get('fecha'),
            data.get('hora'),
            data.get('monto', 0),  # ✅ DEBE ESTAR AQUÍ
            data.get('observaciones_cliente'),
            data.get('diagnostico'),
            data.get('reparacion', 'Reparación realizada'),
            data.get('resultado', 'reparado'),
            data.get('tiempo_estimado', '00:00:00'),
            data.get('costo_repuestos_real', 0),
            data.get('costo_mano_obra_real', 0),
            data.get('costo_diagnostico_real', 0),
            data.get('ganancia_neta', 0),
            data.get('observaciones_pago'),
            data.get('validado_por'),
            data.get('atendido_por'),
            data.get('validado', False),
            id_reg
        ))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        print(f"❌ Error en editar_completo: {e}")
        return jsonify({"error": str(e)}), 500
# ============================
# EDITAR REPUESTOS DE VENTA (ACTUALIZAR SOLO REPUESTOS Y COSTOS)
# ============================
@pago_bp.route('/editar_repuestos_venta/<int:id_reg>', methods=['POST'])
def editar_repuestos_venta(id_reg):
    try:
        data = request.json
        detalles_repuestos = data.get('detalles_repuestos', [])
        costo_repuestos = float(data.get('costo_repuestos_real', 0))
        mano_obra = float(data.get('costo_mano_obra_real', 0))
        diagnostico = float(data.get('costo_diagnostico_real', 0))
        ganancia_neta = float(data.get('ganancia_neta', 0))
        monto = float(data.get('monto', 0))  # ✅ AGREGAR ESTO
        
        conn = get_connection()
        cur = conn.cursor()
        
        # ✅ AGREGAR monto al UPDATE
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
            json.dumps(detalles_repuestos),
            costo_repuestos,
            mano_obra,
            diagnostico,
            ganancia_neta,
            monto,  # ✅ AGREGAR ESTO
            id_reg
        ))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({"success": True})
    except Exception as e:
        print(f"❌ Error en editar_repuestos_venta: {e}")
        return jsonify({"error": str(e)}), 500

# ============================
# 5. ELIMINAR REGISTRO
# ============================
@pago_bp.route('/eliminar_registro/<int:id_reg>', methods=['DELETE'])
def eliminar_registro(id_reg):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM pagos WHERE id = %s", (id_reg,))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        print(f"Error en eliminar_registro: {e}")
        return jsonify({"error": str(e)}), 500


# ============================
# 6. BALANCE DE GANANCIA
# ============================
# ============================
# 6. BALANCE DE GANANCIA (CORREGIDO - CON estado_pago)
# ============================
@pago_bp.route('/balance', methods=['GET'])
def get_balance():
    filtro = request.args.get('filtro', 'hoy')
    hoy = get_fecha_chile()
    
    try:
        conn, cur = get_cursor()
        
        # ✅ SOLO REGISTROS CON estado_pago = 'pagado'
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
        
        cur.close()
        conn.close()
        
        return jsonify({
            "registros": registros,
            "total_pagado": total_pagado,
            "total_repuestos": total_repuestos,
            "total_mano_obra": total_mano_obra,
            "total_diagnostico": total_diagnostico,
            "ganancia_neta": ganancia_neta
        })
    except Exception as e:
        print(f"Error en get_balance: {e}")
        return jsonify({"error": str(e)}), 500


# ============================
# 7. AGREGAR CLIENTE (CON FLOTA)
# ============================
@pago_bp.route('/agregar', methods=['POST'])
def agregar_pago():
    data = request.json
    if data.get('flota') == '__nueva__':
        data['flota'] = data.get('flota_nueva', '').strip()
    if not data.get('flota'):
        data['flota'] = None
    id_reg = PagoService.crear_pago(data)
    if id_reg:
        return jsonify({"success": True, "id": id_reg})
    return jsonify({"success": False, "error": "Error al guardar"}), 500


# ============================
# 8. PROCESAR PAGO (PASO 1 - PAGO EXPRESS)
# ============================
@pago_bp.route('/pagar/<int:id_reg>', methods=['POST'])
def pagar(id_reg):
    data = request.json
    
    print("=" * 60)
    print("📥 DATOS RECIBIDOS - REQUEST.JSON:")
    print(f"  - monto: {data.get('monto')}")
    print(f"  - forma_pago: {data.get('forma_pago')}")
    print(f"  - diagnostico: {data.get('diagnostico')}")
    print(f"  - reparacion: {data.get('reparacion')}")
    print(f"  - observaciones_pago: {data.get('observaciones_pago')}")
    print(f"  - resultado: {data.get('resultado')}")
    print("=" * 60)
    
    data['estado_ot'] = data.get('estado_ot', 'Pendiente')
    data['forma_pago'] = data.get('forma_pago', 'efectivo')
    data['atendido_por'] = data.get('atendido_por', 'Técnico')
    
    print(f"✅ DATA final: {data}")
    
    pago = PagoService.procesar_pago(id_reg, data)
    if pago:
        print(f"✅ Pago procesado - forma_pago: {pago.forma_pago}")
        return jsonify({"success": True, "pago": pago.to_dict()})
    return jsonify({"success": False, "error": "Error al procesar"}), 500


# ============================
# 9. PENDIENTES DE VALIDACIÓN
# ============================
@pago_bp.route('/pendientes_validacion', methods=['GET'])
def get_pendientes_validacion():
    """Obtiene pagos pendientes de validación"""
    try:
        conn, cur = get_cursor()
        
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
            SELECT SUM(monto) as total FROM pagos 
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
        print(f"Error en get_pendientes_validacion: {e}")
        return jsonify({"error": str(e)}), 500


# ============================
# 10. VALIDAR PAGO (CORREGIDO CON estado_pago)
# ============================
@pago_bp.route('/validar_pago/<int:id_reg>', methods=['POST'])
def validar_pago(id_reg):
    data = request.json
    print(f"📥 Datos recibidos: {data}")
    
    costo_repuestos = float(data.get('costo_repuestos', 0) or 0)
    detalles_repuestos = data.get('detalles_repuestos', [])
    
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        # ✅ OBTENER EL REGISTRO PARA SABER SI TIENE FLOTA
        cur.execute("SELECT flota FROM pagos WHERE id = %s", (id_reg,))
        registro = cur.fetchone()
        es_flota = registro and registro[0] and registro[0].strip() != ''
        
        # ✅ DETERMINAR estado_pago
        # Si es flota → queda pendiente de pago
        # Si no es flota → queda pagado
        estado_pago = 'pendiente' if es_flota else 'pagado'
        fecha_pago_real = None if es_flota else get_fecha_chile().strftime('%Y-%m-%d')
        
        print(f"🚛 ¿Es flota? {es_flota} → estado_pago: {estado_pago}")
        
        # ✅ GUARDAR REPUESTOS CON CANTIDAD
        for item in detalles_repuestos:
            nombre = item.get('nombre', '').strip()
            cantidad = int(item.get('cantidad', 1) or 1)
            costo_unitario = float(item.get('costo_unitario', 0) or 0)
            subtotal = cantidad * costo_unitario
            
            if nombre:
                cur.execute("SELECT id, costo_proveedor, costo_venta_final FROM repuestos WHERE nombre = %s", (nombre,))
                existente = cur.fetchone()
                
                if existente:
                    id_existente, costo_prov, costo_venta_existente = existente
                    if costo_venta_existente == 0 and costo_unitario > 0:
                        cur.execute("""
                            UPDATE repuestos 
                            SET costo_venta_final = %s, 
                                updated_at = NOW() AT TIME ZONE 'America/Santiago'
                            WHERE id = %s
                        """, (costo_unitario, id_existente))
                        print(f"✅ Repuesto '{nombre}' actualizado con costo_venta_final: ${costo_unitario}")
                else:
                    iva = 1.19
                    costo_proveedor_estimado = int(costo_unitario / 1.19 / 1.3) if costo_unitario > 0 else 0
                    
                    cur.execute("""
                        INSERT INTO repuestos 
                        (nombre, costo_proveedor, margen_ganancia, costo_venta_final, proveedor, costo_proveedor_pendiente, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, 
                                NOW() AT TIME ZONE 'America/Santiago', 
                                NOW() AT TIME ZONE 'America/Santiago')
                        RETURNING id
                    """, (
                        nombre,
                        costo_proveedor_estimado,
                        30,
                        costo_unitario,
                        'Desde Validación',
                        costo_proveedor_estimado == 0
                    ))
                    id_nuevo = cur.fetchone()[0]
                    print(f"✅ Repuesto '{nombre}' creado con costo_venta_final: ${costo_unitario} (ID: {id_nuevo})")
        
        # ✅ Guardar detalles con cantidad
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
            data.get('costo_mano_obra_real', 0),
            data.get('costo_diagnostico_real', 0),
            data.get('ganancia_neta', 0),
            data.get('observaciones_pago', ''),
            data.get('validado_por', 'Sistema'),
            data.get('diagnostico', ''),
            data.get('reparacion', 'Reparación realizada'),
            data.get('resultado', 'reparado'),
            data.get('tiempo_estimado', '00:00:00'),
            detalles_json,
            estado_pago,
            fecha_pago_real,
            id_reg
        ))
        
        conn.commit()
        cur.close()
        conn.close()
        
        print(f"✅ Validación completada para ID {id_reg} - estado_pago: {estado_pago}")
        return jsonify({"success": True, "estado_pago": estado_pago})
    except Exception as e:
        print(f"❌ Error en validar_pago: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# ============================
# 11. REPUESTOS - OBTENER LISTA
# ============================
@pago_bp.route('/repuestos', methods=['GET'])
def get_repuestos_lista():
    try:
        query = request.args.get('q', '').strip()
        conn, cur = get_cursor()
        
        if query and len(query) >= 2:
            cur.execute("""
                SELECT 
                    id, 
                    nombre, 
                    COALESCE(costo_venta_final, 0) as costo,
                    proveedor,
                    costo_proveedor_pendiente
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
                    costo_proveedor_pendiente
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
                    'costo_proveedor_pendiente': row[6] or False
                })
        
        cur.close()
        conn.close()
        return jsonify(repuestos)
    except Exception as e:
        print(f"Error en get_repuestos_lista: {e}")
        return jsonify([])


# ============================
# 12. REPUESTOS - CREAR
# ============================
@pago_bp.route('/repuestos', methods=['POST'])
def crear_repuesto():
    try:
        data = request.json
        nombre = data.get('nombre', '').strip()
        costo_proveedor = float(data.get('costo_proveedor', 0))
        margen_ganancia = float(data.get('margen_ganancia', 30))
        proveedor = data.get('proveedor', '').strip()
        costo_venta_final = float(data.get('costo_venta_final', 0))
        
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
            (nombre, costo_proveedor, margen_ganancia, proveedor, costo_venta_final, costo_proveedor_pendiente, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, 
                    NOW() AT TIME ZONE 'America/Santiago', 
                    NOW() AT TIME ZONE 'America/Santiago')
            RETURNING id
        """, (nombre, costo_proveedor, margen_ganancia, proveedor, costo_venta_final, costo_proveedor_pendiente))
        id_repuesto = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({"success": True, "id": id_repuesto, "costo_venta_final": costo_venta_final})
    except Exception as e:
        print(f"Error en crear_repuesto: {e}")
        return jsonify({"error": str(e)}), 500


# ============================
# 13. REPUESTOS - ACTUALIZAR
# ============================
@pago_bp.route('/repuestos/<int:id_repuesto>', methods=['PUT'])
def actualizar_repuesto(id_repuesto):
    try:
        data = request.json
        nombre = data.get('nombre', '').strip()
        costo_proveedor = float(data.get('costo_proveedor', 0))
        margen_ganancia = float(data.get('margen_ganancia', 30))
        proveedor = data.get('proveedor', '').strip()
        
        if not nombre:
            return jsonify({"error": "El nombre es obligatorio"}), 400
        
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
                costo_proveedor_pendiente = %s,
                updated_at = NOW() AT TIME ZONE 'America/Santiago'
            WHERE id = %s
        """, (nombre, costo_proveedor, margen_ganancia, proveedor, costo_venta_final, costo_proveedor_pendiente, id_repuesto))
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({"success": True})
    except Exception as e:
        print(f"Error en actualizar_repuesto: {e}")
        return jsonify({"error": str(e)}), 500


# ============================
# 14. REPUESTOS - ELIMINAR
# ============================
@pago_bp.route('/repuestos/<int:id_repuesto>', methods=['DELETE'])
def eliminar_repuesto(id_repuesto):
    """Elimina un repuesto por ID"""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM repuestos WHERE id = %s", (id_repuesto,))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        print(f"Error en eliminar_repuesto: {e}")
        return jsonify({"error": str(e)}), 500


# ============================
# 15. REPUESTOS - BUSCAR (AUTOCOMPLETADO)
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
        print(f"Error en buscar_repuestos: {e}")
        return jsonify([])


# ============================
# 16. FLOTAS DISPONIBLES
# ============================
@pago_bp.route('/flotas_disponibles', methods=['GET'])
def get_flotas_disponibles():
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
        return jsonify(flotas)
    except Exception as e:
        print(f"Error en get_flotas_disponibles: {e}")
        return jsonify([])


# ============================
# 17. EXPORTAR FLOTA A PDF
# ============================
@pago_bp.route('/exportar_flota_pdf/<flota>', methods=['POST'])
def exportar_flota_pdf(flota):
    """Genera un PDF con los servicios de una flota en un rango de fechas"""
    try:
        data = request.json
        fecha_desde = data.get('fecha_desde')
        fecha_hasta = data.get('fecha_hasta')
        
        if not fecha_desde or not fecha_hasta:
            return jsonify({"error": "Debes seleccionar ambas fechas"}), 400
        
        conn = get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        cursor.execute("""
            SELECT 
                patente,
                marca,
                modelo,
                nombre as trabajador,
                fecha,
                monto,
                observaciones_pago,
                hora_pago
            FROM pagos
            WHERE flota = %s
            AND estado = 'pagado'
            AND fecha BETWEEN %s AND %s
            ORDER BY fecha DESC
        """, (flota, fecha_desde, fecha_hasta))
        
        datos = cursor.fetchall()
        
        cursor.execute("""
            SELECT SUM(monto) as total
            FROM pagos
            WHERE flota = %s
            AND estado = 'pagado'
            AND fecha BETWEEN %s AND %s
        """, (flota, fecha_desde, fecha_hasta))
        
        total = cursor.fetchone()['total'] or 0
        conn.close()
        
        if not datos:
            return jsonify({"error": "No hay datos en el rango seleccionado"}), 400
        
        buffer = io.BytesIO()
        
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=120,
            bottomMargin=100
        )
        
        styles = getSampleStyleSheet()
        
        negro = colors.black
        verde_muy_oscuro = colors.HexColor('#1a4d2e')
        verde_oscuro = colors.HexColor('#2a6d44')
        gris = colors.HexColor('#666666')
        gris_claro = colors.HexColor('#f5f5f5')
        
        titulo_style = ParagraphStyle(
            'Titulo',
            parent=styles['Heading1'],
            fontSize=22,
            textColor=negro,
            alignment=1,
            spaceAfter=6,
            fontName='Helvetica-Bold'
        )
        
        subtitulo_style = ParagraphStyle(
            'Subtitulo',
            parent=styles['Normal'],
            fontSize=12,
            textColor=gris,
            alignment=1,
            spaceAfter=20,
            fontName='Helvetica'
        )
        
        intro_style = ParagraphStyle(
            'Introduccion',
            parent=styles['Normal'],
            fontSize=11,
            textColor=negro,
            alignment=0,
            spaceAfter=16,
            fontName='Helvetica'
        )
        
        total_style = ParagraphStyle(
            'Total',
            parent=styles['Normal'],
            fontSize=16,
            textColor=negro,
            alignment=2,
            spaceBefore=12,
            spaceAfter=10,
            fontName='Helvetica-Bold'
        )
        
        pie_style = ParagraphStyle(
            'Pie',
            parent=styles['Normal'],
            fontSize=9,
            textColor=gris,
            alignment=1,
            spaceBefore=30,
            fontName='Helvetica'
        )
        
        elementos = []
        
        logo_path = os.path.join('static', 'images', 'dixon-logo.png')
        if os.path.exists(logo_path):
            try:
                logo = Image(logo_path, width=0.8*inch, height=0.8*inch)
                logo_table = Table([[logo]], colWidths=[7*inch])
                logo_table.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ]))
                elementos.append(logo_table)
                elementos.append(Spacer(1, 0.05 * inch))
            except Exception as e:
                print(f"⚠️ Error al cargar logo: {e}")
                elementos.append(Paragraph("DIXON ELECTRICIDAD AUTOMOTRIZ", 
                    ParagraphStyle('LogoTexto', parent=styles['Normal'], fontSize=12, textColor=verde_muy_oscuro, fontName='Helvetica-Bold')))
                elementos.append(Spacer(1, 0.1 * inch))
        else:
            elementos.append(Paragraph("DIXON ELECTRICIDAD AUTOMOTRIZ", 
                ParagraphStyle('LogoTexto', parent=styles['Normal'], fontSize=12, textColor=verde_muy_oscuro, fontName='Helvetica-Bold')))
            elementos.append(Spacer(1, 0.1 * inch))
        
        titulo = Paragraph(f"REPORTE DE FLOTA: {flota.upper()}", titulo_style)
        elementos.append(titulo)
        
        linea = Table([['']], colWidths=[4*inch])
        linea.setStyle(TableStyle([
            ('LINEABOVE', (0, 0), (-1, -1), 1.5, verde_muy_oscuro),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ]))
        elementos.append(linea)
        elementos.append(Spacer(1, 0.05 * inch))
        
        fecha_desde_obj = datetime.strptime(fecha_desde, "%Y-%m-%d")
        fecha_hasta_obj = datetime.strptime(fecha_hasta, "%Y-%m-%d")
        fecha_desde_str = fecha_desde_obj.strftime('%d/%m/%Y')
        fecha_hasta_str = fecha_hasta_obj.strftime('%d/%m/%Y')
        subtitulo = Paragraph(f"Período: {fecha_desde_str} - {fecha_hasta_str}", subtitulo_style)
        elementos.append(subtitulo)
        elementos.append(Spacer(1, 0.1 * inch))
        
        intro_text = f"""
        El presente documento detalla los servicios realizados para la flota <b>"{flota}"</b> 
        durante el período comprendido entre el <b>{fecha_desde_str}</b> y el <b>{fecha_hasta_str}</b>.<br/><br/>
        Se han registrado un total de <b>{len(datos)} servicios</b> para los siguientes vehículos:
        """
        introduccion = Paragraph(intro_text, intro_style)
        elementos.append(introduccion)
        elementos.append(Spacer(1, 0.15 * inch))
        
        table_data = [
            ['Patente', 'Marca', 'Modelo', 'Trabajador', 'Fecha', 'Monto ($)']
        ]
        
        for row in datos:
            fecha_str = row['fecha'].strftime('%d/%m/%Y') if row['fecha'] else ''
            table_data.append([
                row['patente'] or '',
                row['marca'] or '',
                row['modelo'] or '',
                row['trabajador'] or '',
                fecha_str,
                f"{row['monto']:,.0f}"
            ])
        
        tabla = Table(table_data, colWidths=[1.0*inch, 0.9*inch, 0.9*inch, 1.2*inch, 0.8*inch, 1.0*inch])
        tabla.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), verde_oscuro),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ('TOPPADDING', (0, 0), (-1, 0), 6),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ALIGN', (5, 1), (5, -1), 'RIGHT'),
            ('VALIGN', (0, 1), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, verde_muy_oscuro),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, gris_claro]),
        ]))
        elementos.append(tabla)
        elementos.append(Spacer(1, 0.2 * inch))
        
        total_text = f"MONTO TOTAL: ${total:,.0f}"
        total_paragraph = Paragraph(total_text, total_style)
        elementos.append(total_paragraph)
        
        linea_final = Table([['']], colWidths=[4*inch])
        linea_final.setStyle(TableStyle([
            ('LINEABOVE', (0, 0), (-1, -1), 1, verde_muy_oscuro),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ]))
        elementos.append(Spacer(1, 0.1 * inch))
        elementos.append(linea_final)
        elementos.append(Spacer(1, 0.15 * inch))
        
        ahora_chile = datetime.now(CHILE_TZ)
        pie_text = f"""
        <b>Dixon Electricidad Automotriz</b><br/>
        +569 9855 0331 · Neptuno 163, Local C, Lo Prado, RM, Chile<br/>
        Reporte generado automáticamente el {ahora_chile.strftime('%d/%m/%Y %H:%M')}
        """
        pie = Paragraph(pie_text, pie_style)
        elementos.append(pie)
        
        elementos.append(Spacer(1, 0.1 * inch))
        num_pagina = Paragraph("Página 1", 
            ParagraphStyle('NumPagina', parent=styles['Normal'], fontSize=8, textColor=gris, alignment=1))
        elementos.append(num_pagina)
        
        doc.build(elementos)
        
        buffer.seek(0)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        nombre_archivo = f'reporte_flota_{flota}_{timestamp}.pdf'
        
        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=nombre_archivo
        )
        
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"❌ Error en exportar_flota_pdf: {error_trace}")
        return jsonify({"error": str(e)}), 500


# ============================
# 18. VENTA RÁPIDA (CON CANTIDAD)
# ============================
@pago_bp.route('/venta_rapida', methods=['POST'])
def venta_rapida():
    try:
        data = request.json
        
        if not data.get('nombre') or not data.get('monto'):
            return jsonify({"error": "Nombre y monto son obligatorios"}), 400
        
        conn = get_connection()
        cur = conn.cursor()
        
        fecha_chile, hora_chile = get_fecha_hora_chile()
        
        detalles_repuestos = data.get('detalles_repuestos', [])
        for item in detalles_repuestos:
            nombre = item.get('nombre', '').strip()
            cantidad = int(item.get('cantidad', 1) or 1)
            costo_unitario = float(item.get('costo_unitario', 0) or 0)
            subtotal = cantidad * costo_unitario
            
            if nombre and costo_unitario > 0:
                cur.execute("SELECT id FROM repuestos WHERE nombre = %s", (nombre,))
                if not cur.fetchone():
                    cur.execute("""
                        INSERT INTO repuestos (nombre, costo_proveedor, margen_ganancia, costo_venta_final, proveedor, costo_proveedor_pendiente, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """, (nombre, 0, 30, costo_unitario, 'Desde Venta Rápida', True))
                else:
                    cur.execute("""
                        UPDATE repuestos 
                        SET costo_venta_final = %s,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE nombre = %s AND (costo_venta_final = 0 OR costo_venta_final IS NULL)
                    """, (costo_unitario, nombre))
        
        cur.execute("""
            INSERT INTO pagos 
            (nombre, monto, fecha, hora, estado, tipo_venta, producto_vendido, 
             atendido_por, observaciones_pago, telefono, forma_pago, detalles_repuestos)
            VALUES (%s, %s, %s, %s, 'pagado', 'directa', %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            data.get('nombre'),
            data.get('monto'),
            fecha_chile,
            hora_chile,
            data.get('producto_vendido', ''),
            data.get('atendido_por', 'Técnico'),
            data.get('observaciones', ''),
            data.get('telefono', ''),
            data.get('forma_pago', 'efectivo'),
            json.dumps(detalles_repuestos)
        ))
        
        id_reg = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({"success": True, "id": id_reg})
    except Exception as e:
        print(f"❌ Error en venta_rapida: {e}")
        return jsonify({"error": str(e)}), 500


# ============================
# 19. BALANCE DE VENTAS (CORREGIDO - CON total_repuestos)
# ============================
# ============================
# 19. BALANCE DE VENTAS (CORREGIDO - CON estado_pago)
# ============================
@pago_bp.route('/balance_ventas', methods=['GET'])
def balance_ventas():
    try:
        filtro = request.args.get('filtro', 'hoy')
        hoy = get_fecha_chile()
        
        conn, cur = get_cursor()
        
        # ✅ SOLO REGISTROS CON estado_pago = 'pagado'
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
        
        # ✅ CALCULAR TOTAL REPUESTOS POR REGISTRO
        for r in registros:
            total = 0
            detalles = r.get('detalles_repuestos', [])
            for item in detalles:
                cantidad = item.get('cantidad', 1)
                precio = item.get('costo_unitario', 0) or item.get('costo', 0)
                total += cantidad * precio
            r['total_repuestos'] = total
        
        # ✅ SEPARAR TRABAJO vs DIRECTA
        trabajo = []
        directa = []
        
        for r in registros:
            tiene_vehiculo = r.get('marca') and r.get('marca').strip() != '' and r.get('modelo') and r.get('modelo').strip() != ''
            es_directa = r.get('tipo_venta') == 'directa' or not tiene_vehiculo
            
            if es_directa:
                directa.append(r)
            else:
                trabajo.append(r)
        
        # ============================
        # FUNCIONES PARA CALCULAR SOLO REPUESTOS
        # ============================
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
        
        # ============================
        # FUNCIÓN: Calcular Margen Promedio
        # ============================
        def calcular_margen_promedio(registros):
            """Calcula el margen promedio de los repuestos vendidos"""
            margenes = []
            for r in registros:
                detalles = r.get('detalles_repuestos', [])
                for item in detalles:
                    nombre = item.get('nombre', '')
                    if nombre:
                        cur.execute("SELECT margen_ganancia FROM repuestos WHERE nombre ILIKE %s", (nombre,))
                        resultado = cur.fetchone()
                        if resultado and resultado[0] is not None and resultado[0] > 0:
                            margenes.append(float(resultado[0]))
            if margenes:
                return sum(margenes) / len(margenes)
            return 0
        
        # ============================
        # CALCULAR TOTALES
        # ============================
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
        print(f"❌ Error en balance_ventas: {e}")
        return jsonify({"error": str(e)}), 500


# ============================
# 20. DASHBOARD (CORREGIDO - CON estado_pago)
# ============================
@pago_bp.route('/dashboard', methods=['GET'])
def get_dashboard():
    """Devuelve datos agregados para el dashboard con filtros"""
    try:
        filtro = request.args.get('filtro', '7d')
        mes = request.args.get('mes')
        anio = request.args.get('anio')
        
        from datetime import timedelta
        hoy = get_fecha_chile()
        
        fecha_desde = None
        
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
        
        conn, cur = get_cursor()
        
        # ✅ SOLO REGISTROS CON estado_pago = 'pagado'
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
        
        cur.execute("""
            SELECT 
                COALESCE(AVG(monto), 0) as promedio_diario
            FROM pagos 
            WHERE estado = 'pagado' 
            AND estado_pago = 'pagado'
            AND fecha >= %s
        """, (fecha_desde,))
        promedio = cur.fetchone()
        promedio_diario = float(promedio[0]) if promedio and promedio[0] else 0
        
        cur.close()
        conn.close()
        
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
        
        conn2, cur2 = get_cursor()
        cur2.execute("""
            SELECT DISTINCT 
                EXTRACT(YEAR FROM fecha) as anio,
                EXTRACT(MONTH FROM fecha) as mes
            FROM pagos 
            WHERE estado = 'pagado' 
            AND estado_pago = 'pagado'
            AND fecha IS NOT NULL
            ORDER BY anio DESC, mes DESC
        """)
        meses_disponibles = []
        for row in cur2.fetchall():
            meses_disponibles.append({
                'anio': int(row[0]),
                'mes': int(row[1])
            })
        cur2.close()
        conn2.close()
        
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
            "anio_actual": anio
        })
    except Exception as e:
        print(f"Error en get_dashboard: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
# ============================
# 21. FLOTAS PENDIENTES DE COBRO
# ============================
@pago_bp.route('/flotas_pendientes', methods=['GET'])
def get_flotas_pendientes():
    """Obtiene todas las flotas que están pendientes de pago"""
    try:
        conn, cur = get_cursor()
        
        cur.execute("""
            SELECT * FROM pagos 
            WHERE estado = 'pagado' 
            AND estado_pago = 'pendiente'
            AND flota IS NOT NULL 
            AND flota != ''
            ORDER BY fecha DESC
        """)
        
        rows = cur.fetchall()
        flotas = [dict(row) for row in rows]
        
        cur.close()
        conn.close()
        
        return jsonify(flotas)
    except Exception as e:
        print(f"❌ Error en get_flotas_pendientes: {e}")
        return jsonify({"error": str(e)}), 500
# ============================
# 23. VALIDAR PAGO DE FLOTA (MARCAR COMO PAGADO)
# ============================
@pago_bp.route('/validar_flota/<int:id_reg>', methods=['POST'])
def validar_flota(id_reg):
    try:
        data = request.json
        fecha_pago = data.get('fecha_pago')
        forma_pago = data.get('forma_pago', 'transferencia')
        monto_pagado = float(data.get('monto_pagado', 0))
        
        if not fecha_pago:
            return jsonify({"error": "La fecha de pago es obligatoria"}), 400
        
        conn = get_connection()
        cur = conn.cursor()
        
        # ✅ Verificar que existe y está pendiente
        cur.execute("""
            SELECT id, estado_pago FROM pagos 
            WHERE id = %s AND estado_pago = 'pendiente'
        """, (id_reg,))
        registro = cur.fetchone()
        
        if not registro:
            cur.close()
            conn.close()
            return jsonify({"error": "Registro no encontrado o ya está pagado"}), 404
        
        # ✅ Actualizar a pagado
        cur.execute("""
            UPDATE pagos 
            SET estado_pago = 'pagado',
                fecha_pago_real = %s,
                forma_pago = %s,
                monto = %s,
                actualizado_en = NOW() AT TIME ZONE 'America/Santiago'
            WHERE id = %s
        """, (fecha_pago, forma_pago, monto_pagado, id_reg))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({"success": True})
    except Exception as e:
        print(f"❌ Error en validar_flota: {e}")
        return jsonify({"error": str(e)}), 500


# ============================
# 22. CONTADOR DE FLOTAS PENDIENTES
# ============================
@pago_bp.route('/flotas_pendientes_count', methods=['GET'])
def get_flotas_pendientes_count():
    """Devuelve el número de flotas pendientes de cobro"""
    try:
        conn, cur = get_cursor()
        
        cur.execute("""
            SELECT COUNT(*) FROM pagos 
            WHERE estado = 'pagado' 
            AND estado_pago = 'pendiente'
            AND flota IS NOT NULL 
            AND flota != ''
        """)
        
        count = cur.fetchone()[0] or 0
        
        cur.close()
        conn.close()
        
        return jsonify({"count": count})
    except Exception as e:
        print(f"❌ Error en get_flotas_pendientes_count: {e}")
        return jsonify({"count": 0}), 500
# ============================
# 24. FLOTAS PENDIENTES AGRUPADAS
# ============================
@pago_bp.route('/flotas_pendientes_agrupadas', methods=['GET'])
def get_flotas_pendientes_agrupadas():
    """Devuelve flotas pendientes agrupadas por nombre"""
    try:
        conn, cur = get_cursor()
        
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
        
        # ✅ AGRUPAR POR FLOTA
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
        
        # Convertir a lista
        resultado = list(flotas_agrupadas.values())
        
        cur.close()
        conn.close()
        
        return jsonify(resultado)
    except Exception as e:
        print(f"❌ Error en get_flotas_pendientes_agrupadas: {e}")
        return jsonify({"error": str(e)}), 500
# ============================
# 25. VALIDAR TODA LA FLOTA (MARCAR TODOS COMO PAGADOS)
# ============================
@pago_bp.route('/validar_flota_completa/<nombre_flota>', methods=['POST'])
def validar_flota_completa(nombre_flota):
    try:
        data = request.json
        fecha_pago = data.get('fecha_pago')
        forma_pago = data.get('forma_pago', 'transferencia')
        
        if not fecha_pago:
            return jsonify({"error": "La fecha de pago es obligatoria"}), 400
        
        conn = get_connection()
        cur = conn.cursor()
        
        # ✅ Obtener todos los servicios pendientes de esta flota
        cur.execute("""
            SELECT id, monto FROM pagos 
            WHERE flota = %s 
            AND estado = 'pagado' 
            AND estado_pago = 'pendiente'
        """, (nombre_flota,))
        
        servicios = cur.fetchall()
        
        if not servicios:
            cur.close()
            conn.close()
            return jsonify({"error": "No hay servicios pendientes para esta flota"}), 404
        
        # ✅ Calcular total
        total_pagado = sum(float(s[1] or 0) for s in servicios)
        
        # ✅ Marcar TODOS como pagados
        cur.execute("""
            UPDATE pagos 
            SET estado_pago = 'pagado',
                fecha_pago_real = %s,
                forma_pago = %s,
                actualizado_en = NOW() AT TIME ZONE 'America/Santiago'
            WHERE flota = %s 
            AND estado = 'pagado' 
            AND estado_pago = 'pendiente'
        """, (fecha_pago, forma_pago, nombre_flota))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({
            "success": True, 
            "total_pagado": total_pagado,
            "servicios_actualizados": len(servicios)
        })
    except Exception as e:
        print(f"❌ Error en validar_flota_completa: {e}")
        return jsonify({"error": str(e)}), 500
# ============================
# VERIFICAR DUPLICADO (ANTES DE AGREGAR)
# ============================
@pago_bp.route('/verificar_duplicado', methods=['GET'])
def verificar_duplicado():
    nombre = request.args.get('nombre', '').strip()
    patente = request.args.get('patente', '').strip().upper()
    
    if not nombre or not patente:
        return jsonify({"duplicado": False})
    
    try:
        conn, cur = get_cursor()
        
        # Buscar registros con el mismo nombre y patente en los últimos 5 minutos
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
        print(f"❌ Error en verificar_duplicado: {e}")
        return jsonify({"duplicado": False}), 500
