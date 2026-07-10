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
# 2. OBTENER REGISTRO POR ID (¡ESTA ES LA QUE FALTABA!)
# ============================
@pago_bp.route('/registro/<int:id_reg>', methods=['GET'])
def get_registro(id_reg):
    pago = PagoService.obtener_por_id(id_reg)
    if pago:
        return jsonify(pago.to_dict())
    return jsonify({"error": "No encontrado"}), 404


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
