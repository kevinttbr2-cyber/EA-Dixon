from flask import Blueprint, request, jsonify
from services.pago_service import PagoService
from database import get_connection, get_cursor

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
# REGISTROS CON FILTROS
# ============================
@pago_bp.route('/registros', methods=['GET'])
def get_registros():
    filtro = request.args.get('filtro', 'todos')
    hoy = datetime.now().date()
    
    try:
        conn, cur = get_cursor()
        
        # Base query
        query = "SELECT * FROM pagos WHERE estado = 'pagado'"
        params = []
        
        if filtro == 'hoy':
            query += " AND fecha = %s"
            params.append(hoy.strftime('%Y-%m-%d'))
        elif filtro == '7d':
            fecha_7d = hoy - timedelta(days=7)
            query += " AND fecha >= %s"
            params.append(fecha_7d.strftime('%Y-%m-%d'))
        elif filtro == 'mes':
            fecha_mes = hoy - timedelta(days=30)
            query += " AND fecha >= %s"
            params.append(fecha_mes.strftime('%Y-%m-%d'))
        
        query += " ORDER BY fecha DESC, hora DESC"
        
        cur.execute(query, params)
        rows = cur.fetchall()
        registros = [dict(row) for row in rows]
        
        # Agregar firma para PDF
        from services.pdf_service import PDFService
        for r in registros:
            r['firma'] = PDFService.generar_firma(r['id'])
        
        cur.close()
        conn.close()
        return jsonify(registros)
    except Exception as e:
        print(f"Error en get_registros: {e}")
        return jsonify({"error": str(e)}), 500


# ============================
# EDITAR REGISTRO
# ============================
@pago_bp.route('/editar_registro/<int:id_reg>', methods=['POST'])
def editar_registro(id_reg):
    data = request.json
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            UPDATE pagos 
            SET nombre = %s,
                monto = %s,
                patente = %s,
                marca = %s,
                modelo = %s,
                observaciones_cliente = %s
            WHERE id = %s
        """, (
            data.get('nombre'),
            data.get('monto', 0),
            data.get('patente'),
            data.get('marca'),
            data.get('modelo'),
            data.get('observaciones'),
            id_reg
        ))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        print(f"Error en editar_registro: {e}")
        return jsonify({"error": str(e)}), 500


# ============================
# ELIMINAR REGISTRO
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
# BALANCE DE GANANCIA
# ============================
@pago_bp.route('/balance', methods=['GET'])
def get_balance():
    filtro = request.args.get('filtro', 'hoy')
    hoy = datetime.now().date()
    
    try:
        conn, cur = get_cursor()
        
        query = """
            SELECT * FROM pagos 
            WHERE estado = 'pagado' AND validado = TRUE
        """
        params = []
        
        if filtro == 'hoy':
            query += " AND fecha = %s"
            params.append(hoy.strftime('%Y-%m-%d'))
        elif filtro == '7d':
            fecha_7d = hoy - timedelta(days=7)
            query += " AND fecha >= %s"
            params.append(fecha_7d.strftime('%Y-%m-%d'))
        elif filtro == 'mes':
            fecha_mes = hoy - timedelta(days=30)
            query += " AND fecha >= %s"
            params.append(fecha_mes.strftime('%Y-%m-%d'))
        
        query += " ORDER BY fecha DESC, hora DESC"
        
        cur.execute(query, params)
        rows = cur.fetchall()
        registros = [dict(row) for row in rows]
        
        # Calcular totales
        total_pagado = sum(r.get('monto', 0) for r in registros)
        total_repuestos = sum(r.get('costo_repuestos_real', 0) for r in registros)
        total_mano_obra = sum(r.get('costo_mano_obra_real', 0) for r in registros)
        total_diagnostico = sum(r.get('costo_diagnostico_real', 0) for r in registros)
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
# 3. OBTENER TODOS LOS REGISTROS PAGADOS
# ============================
@pago_bp.route('/registros', methods=['GET'])
def get_registros():
    pagados = PagoService.obtener_todos_pagados()
    return jsonify([p.to_dict() for p in pagados])


# ============================
# 4. AGREGAR CLIENTE (PAGO EXPRESS - PASO 1)
# ============================
@pago_bp.route('/agregar', methods=['POST'])
def agregar_pago():
    data = request.json
    id_reg = PagoService.crear_pago(data)
    if id_reg:
        return jsonify({"success": True, "id": id_reg})
    return jsonify({"success": False, "error": "Error al guardar"}), 500


# ============================
# 5. PROCESAR PAGO (PASO 1 - PAGO EXPRESS)
# ============================
@pago_bp.route('/pagar/<int:id_reg>', methods=['POST'])
def pagar(id_reg):
    data = request.json
    pago = PagoService.procesar_pago(id_reg, data)
    if pago:
        return jsonify({"success": True, "pago": pago.to_dict()})
    return jsonify({"success": False, "error": "Error al procesar"}), 500


# ============================
# 6. PENDIENTES DE VALIDACIÓN (PASO 2 - PENDIENTES)
# ============================
@pago_bp.route('/pendientes_validacion', methods=['GET'])
def get_pendientes_validacion():
    """Obtiene pagos pendientes de validación"""
    try:
        conn, cur = get_cursor()
        
        # Pagos pagados pero NO validados
        cur.execute("""
            SELECT * FROM pagos 
            WHERE estado = 'pagado' AND (validado IS NULL OR validado = FALSE)
            ORDER BY fecha DESC, hora DESC
        """)
        pendientes = [dict(row) for row in cur.fetchall()]
        
        # Pagos ya validados
        cur.execute("""
            SELECT * FROM pagos 
            WHERE estado = 'pagado' AND validado = TRUE
            ORDER BY fecha DESC, hora DESC
        """)
        validados = [dict(row) for row in cur.fetchall()]
        
        # Total pagado (solo pagos validados)
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
# 7. VALIDAR PAGO (PASO 2 - VALIDACIÓN DE COSTOS)
# ============================
import json

@pago_bp.route('/validar_pago/<int:id_reg>', methods=['POST'])
def validar_pago(id_reg):
    data = request.json
    print(f"📥 Datos recibidos: {data}")
    print(f"📦 Detalles repuestos: {data.get('detalles_repuestos', [])}")
    try:
        conn = get_connection()
        cur = conn.cursor()

        detalles_json = json.dumps(data.get('detalles_repuestos', []))

        cur.execute("""
            UPDATE pagos 
            SET costo_repuestos_real = %s,
                costo_mano_obra_real = %s,
                costo_diagnostico_real = %s,
                ganancia_neta = %s,
                observaciones_pago = %s,
                validado = TRUE,
                validado_por = %s,
                fecha_validacion = CURRENT_TIMESTAMP,
                diagnostico = %s,
                reparacion = %s,
                resultado = %s,
                tiempo_estimado = %s,
                detalles_repuestos = %s::jsonb
            WHERE id = %s
        """, (
            data.get('costo_repuestos_real', 0),
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
            id_reg
        ))

        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        print(f"Error en validar_pago: {e}")
        return jsonify({"error": str(e)}), 500
