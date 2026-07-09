from flask import Blueprint, request, jsonify, send_file
from services.pago_service import PagoService
from services.pdf_service import PDFService
from repositories.pago_repo import PagoRepository

pdf_bp = Blueprint('pdf', __name__, url_prefix='/api')

@pdf_bp.route('/pdf/<int:id_reg>/<firma>', methods=['GET'])
def descargar_pdf(id_reg, firma):
    # Verificar firma
    if not PDFService.verificar_firma(id_reg, firma):
        return jsonify({"error": "Firma inválida"}), 403
    
    # Obtener registro
    pago = PagoService.obtener_por_id(id_reg)
    if not pago:
        return jsonify({"error": "Registro no encontrado"}), 404
    
    # Generar PDF
    buffer = PDFService.generar_pdf(pago)
    if not buffer:
        return jsonify({"error": "Error generando PDF"}), 500
    
    # Registrar descarga
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    user_agent = request.headers.get('User-Agent', '')
    
    try:
        from database import get_connection
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO auditoria_descargas (id_registro, usuario, rol, tipo, ip, user_agent)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (id_reg, "cliente", "cliente", "cliente", ip, user_agent))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error registrando descarga: {e}")
    
    return send_file(
        buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'OT_{id_reg}.pdf'
    )