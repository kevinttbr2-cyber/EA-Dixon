from flask import Blueprint, jsonify
from services.pago_service import PagoService

flota_bp = Blueprint('flota', __name__, url_prefix='/api')

@flota_bp.route('/flotas', methods=['GET'])
def get_flotas():
    flotas = PagoService.obtener_flotas()
    return jsonify(flotas)
# 1. Exportar flota a PDF (que estaba en pago_routes.py original)
@flota_bp.route('/exportar_flota_pdf/<flota>', methods=['POST'])
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
        
        # ... (resto del código PDF que ya tenías)
        
    except Exception as e:
        logger.error(f"Error en exportar_flota_pdf: {e}")
        return jsonify({"error": str(e)}), 500
