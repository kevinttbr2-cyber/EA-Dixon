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
        
        cur.execute("""
            INSERT INTO gastos 
            (categoria, monto, metodo_pago, descripcion, proveedor, folio, fecha, hora, registrado_por)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            sanitizar_input(data.get('categoria')),
            sanitizar_numero(data.get('monto', 0), min_val=0),
            sanitizar_input(data.get('metodo_pago', 'efectivo')),
            sanitizar_input(data.get('descripcion', '')),
            sanitizar_input(data.get('proveedor', '')),
            sanitizar_input(data.get('folio', '')),
            data.get('fecha'),
            data.get('hora'),
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

@gasto_bp.route('/gastos', methods=['GET'])
def obtener_gastos():
    try:
        fecha = request.args.get('fecha')
        if not fecha:
            return jsonify({"error": "Fecha requerida"}), 400
        
        conn, cur = get_cursor()
        cur.execute("SELECT * FROM gastos WHERE fecha = %s ORDER BY hora DESC", (fecha,))
        gastos = [dict(row) for row in cur.fetchall()]
        cur.close()
        conn.close()
        
        return jsonify(gastos)
        
    except Exception as e:
        logger.error(f"Error en obtener_gastos: {e}")
        return jsonify({"error": str(e)}), 500

@gasto_bp.route('/gastos_balance', methods=['GET'])
def obtener_gastos_balance():
    try:
        fecha_inicio = request.args.get('fecha_inicio')
        fecha_fin = request.args.get('fecha_fin')
        
        if not fecha_inicio or not fecha_fin:
            return jsonify({"error": "Fechas requeridas"}), 400
        
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
        logger.error(f"Error en obtener_gastos_balance: {e}")
        return jsonify([])
