# Backend/routes/cierre_routes.py
from flask import Blueprint, request, jsonify
from database import get_connection, get_cursor
from utils.seguridad import sanitizar_input, sanitizar_numero
import logging

logger = logging.getLogger(__name__)
cierre_bp = Blueprint('cierre', __name__, url_prefix='/api')

@cierre_bp.route('/cierre_caja', methods=['POST'])
def iniciar_cierre_caja():
    try:
        data = request.json
        fecha = data.get('fecha')
        efectivo_inicial = sanitizar_numero(data.get('efectivo_inicial', 0), min_val=0)
        
        if not fecha:
            return jsonify({"error": "Fecha requerida"}), 400
        
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
        logger.error(f"Error en iniciar_cierre_caja: {e}")
        return jsonify({"error": str(e)}), 500

@cierre_bp.route('/cierre_caja/<fecha>', methods=['GET'])
def obtener_cierre_caja(fecha):
    try:
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
        logger.error(f"Error en obtener_cierre_caja: {e}")
        return jsonify({"error": str(e)}), 500

@cierre_bp.route('/cierre_caja/<fecha>/cerrar', methods=['POST'])
def cerrar_caja(fecha):
    try:
        data = request.json
        efectivo_real = sanitizar_numero(data.get('efectivo_real', 0), min_val=0)
        observaciones = sanitizar_input(data.get('observaciones', ''))
        cerrado_por = sanitizar_input(data.get('cerrado_por', 'Sistema'))
        
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
        logger.error(f"Error en cerrar_caja: {e}")
        return jsonify({"error": str(e)}), 500

@cierre_bp.route('/historial_cierres', methods=['GET'])
def historial_cierres():
    try:
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
        logger.error(f"Error en historial_cierres: {e}")
        return jsonify({"error": str(e)}), 500
