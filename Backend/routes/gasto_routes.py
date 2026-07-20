# Backend/routes/gasto_routes.py
from flask import Blueprint, request, jsonify
from database import get_connection, get_cursor
from utils.seguridad import sanitizar_input, sanitizar_numero
import logging

logger = logging.getLogger(__name__)
gasto_bp = Blueprint('gasto', __name__, url_prefix='/api')

@gasto_bp.route('/gastos', methods=['POST'])
def registrar_gasto():
    try:
        data = request.json
        
        if not data.get('categoria') or not data.get('monto'):
            return jsonify({"error": "Categoría y monto son obligatorios"}), 400
        
        conn = get_connection()
        cur = conn.cursor()
        
        # ✅ CONSULTA CORRECTA CON CAST
        cur.execute("""
            INSERT INTO gastos 
            (categoria, monto, metodo_pago, descripcion, proveedor, folio, 
             fecha, hora, registrado_por, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, 
                    CAST(NOW() AT TIME ZONE 'America/Santiago' AS date), 
                    CAST(NOW() AT TIME ZONE 'America/Santiago' AS time), 
                    %s,
                    NOW() AT TIME ZONE 'America/Santiago',
                    NOW() AT TIME ZONE 'America/Santiago')
            RETURNING id
        """, (
            sanitizar_input(data.get('categoria')),
            sanitizar_numero(data.get('monto', 0), min_val=0),
            sanitizar_input(data.get('metodo_pago', 'efectivo')),
            sanitizar_input(data.get('descripcion', '')),
            sanitizar_input(data.get('proveedor', '')),
            sanitizar_input(data.get('folio', '')),
            sanitizar_input(data.get('registrado_por', 'Sistema'))
        ))
        
        id_gasto = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info(f"✅ Gasto registrado ID: {id_gasto}")
        return jsonify({"success": True, "id": id_gasto})
        
    except Exception as e:
        logger.error(f"Error en registrar_gasto: {e}")
        return jsonify({"error": str(e)}), 500

# ... resto del código (obtener_gastos, obtener_gastos_balance, eliminar_gasto)
