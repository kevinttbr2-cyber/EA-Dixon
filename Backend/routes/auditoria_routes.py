from flask import Blueprint, jsonify
from repositories.pago_repo import PagoRepository
from services.pdf_service import PDFService
from database import get_connection

auditoria_bp = Blueprint('auditoria', __name__, url_prefix='/api')

@auditoria_bp.route('/auditoria', methods=['GET'])
def get_auditoria():
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT a.*, p.nombre as cliente, p.patente, p.marca, p.modelo
            FROM auditoria_descargas a
            LEFT JOIN pagos p ON a.id_registro = p.id
            ORDER BY a.fecha DESC
            LIMIT 100
        """)
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        resultado = []
        for row in rows:
            item = {
                "id": row[0],
                "id_registro": row[1],
                "usuario": row[2],
                "rol": row[3],
                "tipo": row[4],
                "fecha": row[5].isoformat() if row[5] else None,
                "ip": row[6],
                "cliente": row[8] if len(row) > 8 else None,
                "patente": row[9] if len(row) > 9 else None,
                "marca": row[10] if len(row) > 10 else None,
                "modelo": row[11] if len(row) > 11 else None,
                "firma": PDFService.generar_firma(row[1]) if row[1] else None
            }
            resultado.append(item)
        
        return jsonify(resultado)
    except Exception as e:
        return jsonify({"error": str(e)}), 500