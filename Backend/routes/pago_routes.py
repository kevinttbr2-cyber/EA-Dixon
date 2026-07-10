from flask import Blueprint, request, jsonify
from services.pago_service import PagoService

pago_bp = Blueprint('pago', __name__, url_prefix='/api')

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

@pago_bp.route('/registro/<int:id_reg>', methods=['GET'])
def get_registro(id_reg):
    pago = PagoService.obtener_por_id(id_reg)
    if pago:
        return jsonify(pago.to_dict())
    return jsonify({"error": "No encontrado"}), 404

@pago_bp.route('/agregar', methods=['POST'])
def agregar_pago():
    data = request.json
    id_reg = PagoService.crear_pago(data)
    if id_reg:
        return jsonify({"success": True, "id": id_reg})
    return jsonify({"success": False, "error": "Error al guardar"}), 500

@pago_bp.route('/pagar/<int:id_reg>', methods=['POST'])
def pagar(id_reg):
    data = request.json
    pago = PagoService.procesar_pago(id_reg, data)
    if pago:
        return jsonify({"success": True, "pago": pago.to_dict()})
    return jsonify({"success": False, "error": "Error al procesar"}), 500

@pago_bp.route('/registros', methods=['GET'])
def get_registros():
    pagados = PagoService.obtener_todos_pagados()
    return jsonify([p.to_dict() for p in pagados])
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
