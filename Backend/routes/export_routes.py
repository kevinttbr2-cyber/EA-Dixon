# Backend/routes/export_routes.py
from flask import Blueprint, request, jsonify, make_response
from database import get_connection, get_cursor
import logging
from io import BytesIO

logger = logging.getLogger(__name__)
export_bp = Blueprint('export', __name__, url_prefix='/api')

@export_bp.route('/exportar_datos', methods=['GET'])
def exportar_datos():
    """Exporta todos los registros a Excel SIN borrar nada"""
    try:
        from openpyxl import Workbook
        
        conn, cur = get_cursor()
        cur.execute("SELECT * FROM pagos ORDER BY fecha DESC, hora DESC")
        registros = cur.fetchall()
        cur.close()
        conn.close()
        
        if not registros:
            return jsonify({'error': 'No hay registros para exportar'}), 400
        
        wb = Workbook()
        ws = wb.active
        ws.title = "Exportacion"
        
        headers = [
            'ID', 'Cliente', 'Teléfono', 'Monto', 'Fecha', 'Hora',
            'Patente', 'Marca', 'Modelo', 'Año', 'Flota',
            'Atendido por', 'Estado', 'Observaciones Cliente',
            'Observaciones Pago', 'Diagnóstico', 'Reparación',
            'Resultado', 'Tiempo Estimado', 'Costo Repuestos',
            'Costo Mano Obra', 'Costo Diagnóstico', 'Ganancia Neta',
            'Validado', 'Validado por'
        ]
        ws.append(headers)
        
        for r in registros:
            ws.append([
                r[0], r[1], r[6], r[2], r[3], r[4],
                r[5], r[7], r[8], r[9], r[10],
                r[11] or 'Sistema', r[12], r[13],
                r[14], r[15], r[16], r[17], r[18],
                r[19] or 0, r[20] or 0, r[21] or 0, r[22] or 0,
                r[23] or False, r[24] or ''
            ])
        
        output = BytesIO()
        wb.save(output)
        output.seek(0)
        
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        response.headers['Content-Disposition'] = 'attachment; filename=exportacion_db.xlsx'
        return response
        
    except Exception as e:
        logger.error(f"Error en exportar_datos: {e}")
        return jsonify({'error': str(e)}), 500

@export_bp.route('/exportar_y_borrar', methods=['POST'])
def exportar_y_borrar():
    """Exporta todos los registros a Excel y luego los elimina"""
    try:
        from openpyxl import Workbook
        
        conn, cur = get_cursor()
        cur.execute("SELECT * FROM pagos ORDER BY fecha DESC, hora DESC")
        registros = cur.fetchall()
        
        if not registros:
            cur.close()
            conn.close()
            return jsonify({'error': 'No hay registros para exportar'}), 400
        
        wb = Workbook()
        ws = wb.active
        ws.title = "Backup"
        
        headers = [
            'ID', 'Cliente', 'Teléfono', 'Monto', 'Fecha', 'Hora',
            'Patente', 'Marca', 'Modelo', 'Año', 'Flota',
            'Atendido por', 'Estado', 'Observaciones Cliente',
            'Observaciones Pago', 'Diagnóstico', 'Reparación',
            'Resultado', 'Tiempo Estimado', 'Costo Repuestos',
            'Costo Mano Obra', 'Costo Diagnóstico', 'Ganancia Neta',
            'Validado', 'Validado por'
        ]
        ws.append(headers)
        
        for r in registros:
            ws.append([
                r[0], r[1], r[6], r[2], r[3], r[4],
                r[5], r[7], r[8], r[9], r[10],
                r[11] or 'Sistema', r[12], r[13],
                r[14], r[15], r[16], r[17], r[18],
                r[19] or 0, r[20] or 0, r[21] or 0, r[22] or 0,
                r[23] or False, r[24] or ''
            ])
        
        output = BytesIO()
        wb.save(output)
        output.seek(0)
        
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        response.headers['Content-Disposition'] = 'attachment; filename=backup_antes_borrar.xlsx'
        
        # Eliminar registros
        cur.execute("DELETE FROM pagos")
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info(f"✅ {len(registros)} registros eliminados correctamente")
        return response
        
    except Exception as e:
        logger.error(f"Error en exportar_y_borrar: {e}")
        return jsonify({'error': str(e)}), 500
