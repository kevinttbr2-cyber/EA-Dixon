# Backend/routes/cierre_routes.py
from flask import Blueprint, request, jsonify
from database import get_connection, get_cursor
from utils.seguridad import sanitizar_input, sanitizar_numero
from services.pago_service import PagoService
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
        
        id_cierre = PagoService.crear_cierre_caja(fecha, efectivo_inicial)
        if id_cierre:
            return jsonify({"success": True, "id": id_cierre})
        return jsonify({"error": "Error al crear cierre"}), 500
        
    except Exception as e:
        logger.error(f"Error en iniciar_cierre_caja: {e}")
        return jsonify({"error": str(e)}), 500

@cierre_bp.route('/cierre_caja/<fecha>', methods=['GET'])
def obtener_cierre_caja(fecha):
    try:
        cierre = PagoService.obtener_cierre_caja(fecha)
        
        if not cierre:
            return jsonify({"error": "No hay cierre para esta fecha"}), 404
        
        # Obtener ventas y gastos en efectivo
        conn, cur = get_cursor()
        
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
        
        cur.close()
        conn.close()
        
        efectivo_esperado = float(cierre.get('efectivo_inicial', 0)) + float(ventas_efectivo) - float(gastos_efectivo)
        
        return jsonify({
            "cierre": cierre,
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
        
        # Obtener cierre actual
        cierre = PagoService.obtener_cierre_caja(fecha)
        if not cierre or cierre.get('estado') != 'abierto':
            return jsonify({"error": "No hay cierre abierto para esta fecha"}), 404
        
        # Calcular totales
        conn, cur = get_cursor()
        
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
        
        cur.close()
        conn.close()
        
        efectivo_esperado = float(cierre.get('efectivo_inicial', 0)) + float(ventas_efectivo) - float(gastos_efectivo)
        diferencia = float(efectivo_real) - float(efectivo_esperado)
        
        # Preparar datos para cerrar
        data_cierre = {
            'ventas_efectivo': ventas_efectivo,
            'gastos_efectivo': gastos_efectivo,
            'efectivo_esperado': efectivo_esperado,
            'efectivo_real': efectivo_real,
            'diferencia': diferencia,
            'cerrado_por': cerrado_por,
            'observaciones': observaciones
        }
        
        if PagoService.cerrar_cierre_caja(fecha, data_cierre):
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
        
        return jsonify({"error": "Error al cerrar caja"}), 500
        
    except Exception as e:
        logger.error(f"Error en cerrar_caja: {e}")
        return jsonify({"error": str(e)}), 500

@cierre_bp.route('/historial_cierres', methods=['GET'])
def historial_cierres():
    try:
        historial = PagoService.obtener_historial_cierres(30)
        return jsonify(historial)
    except Exception as e:
        logger.error(f"Error en historial_cierres: {e}")
        return jsonify({"error": str(e)}), 500
