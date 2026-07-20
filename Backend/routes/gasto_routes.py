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
        
        # ✅ CONSULTA CORRECTA CON ZONA HORARIA CHILE
        cur.execute("""
            INSERT INTO gastos 
            (categoria, monto, metodo_pago, descripcion, proveedor, folio, 
             fecha, hora, registrado_por, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, 
                    NOW() AT TIME ZONE 'America/Santiago'::date, 
                    NOW() AT TIME ZONE 'America/Santiago'::time, 
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
        
        logger.info(f"✅ Gasto registrado ID: {id_gasto} - Fecha Chile: {datetime.now().astimezone(pytz.timezone('America/Santiago')).strftime('%Y-%m-%d')}")
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
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        gastos = []
        for row in rows:
            g = dict(row)
            if g.get('hora') and hasattr(g['hora'], 'strftime'):
                g['hora'] = g['hora'].strftime('%H:%M:%S')
            if g.get('fecha') and hasattr(g['fecha'], 'strftime'):
                g['fecha'] = g['fecha'].strftime('%Y-%m-%d')
            if g.get('created_at') and hasattr(g['created_at'], 'strftime'):
                g['created_at'] = g['created_at'].strftime('%Y-%m-%d %H:%M:%S')
            if g.get('updated_at') and hasattr(g['updated_at'], 'strftime'):
                g['updated_at'] = g['updated_at'].strftime('%Y-%m-%d %H:%M:%S')
            gastos.append(g)
        
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
        
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        gastos = []
        for row in rows:
            g = dict(row)
            if g.get('hora') and hasattr(g['hora'], 'strftime'):
                g['hora'] = g['hora'].strftime('%H:%M:%S')
            if g.get('fecha') and hasattr(g['fecha'], 'strftime'):
                g['fecha'] = g['fecha'].strftime('%Y-%m-%d')
            if g.get('created_at') and hasattr(g['created_at'], 'strftime'):
                g['created_at'] = g['created_at'].strftime('%Y-%m-%d %H:%M:%S')
            if g.get('updated_at') and hasattr(g['updated_at'], 'strftime'):
                g['updated_at'] = g['updated_at'].strftime('%Y-%m-%d %H:%M:%S')
            gastos.append(g)
        
        logger.info(f"📊 Gastos obtenidos: {len(gastos)} en el rango {fecha_inicio} - {fecha_fin}")
        return jsonify(gastos)
        
    except Exception as e:
        logger.error(f"Error en obtener_gastos_balance: {e}")
        return jsonify([])

@gasto_bp.route('/gastos/<int:id_gasto>', methods=['DELETE'])
def eliminar_gasto(id_gasto):
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        cur.execute("SELECT id FROM gastos WHERE id = %s", (id_gasto,))
        if cur.fetchone() is None:
            cur.close()
            conn.close()
            return jsonify({"error": "Gasto no encontrado"}), 404
        
        cur.execute("DELETE FROM gastos WHERE id = %s", (id_gasto,))
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info(f"✅ Gasto eliminado: ID {id_gasto}")
        return jsonify({"success": True})
        
    except Exception as e:
        logger.error(f"Error en eliminar_gasto: {e}")
        return jsonify({"error": str(e)}), 500
