from flask import Blueprint, request, jsonify, send_file
from services.pago_service import PagoService
from services.pdf_service import PDFService
from repositories.pago_repo import PagoRepository
import qrcode
from io import BytesIO
import base64

pdf_bp = Blueprint('pdf', __name__, url_prefix='/api')

@pdf_bp.route('/firma/<int:id_reg>', methods=['GET'])
def get_firma(id_reg):
    """Devuelve la firma para un ID de registro"""
    firma = PDFService.generar_firma(id_reg)
    return jsonify({"firma": firma})

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
    buffer = PDFService.generar_pdf_formal(pago.to_dict())
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
    
    # 🔥 NOMBRE DEL ARCHIVO CON CLIENTE Y FECHA (MANEJANDO STRING O DATETIME)
    nombre_cliente = pago.nombre.replace(' ', '_').replace('/', '_') if pago.nombre else 'cliente'
    
    # Manejar fecha (puede ser string o datetime)
    if pago.fecha:
        if hasattr(pago.fecha, 'strftime'):
            fecha = pago.fecha.strftime('%Y%m%d')
        else:
            # Si es string, tomar los primeros 10 caracteres (YYYY-MM-DD)
            fecha = str(pago.fecha)[:10].replace('-', '')
    else:
        fecha = 'sin_fecha'
    
    download_name = f'OT_{id_reg}_{nombre_cliente}_{fecha}.pdf'
    
    return send_file(
        buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=download_name
    )

@pdf_bp.route('/qr/<int:id_reg>/<firma>', methods=['GET'])
def generar_qr(id_reg, firma):
    """Genera un código QR con la URL del PDF"""
    # Verificar firma
    if not PDFService.verificar_firma(id_reg, firma):
        return jsonify({"error": "Firma inválida"}), 403
    
    # Construir la URL del PDF
    pdf_url = f"https://ea-dixon-production.up.railway.app/api/pdf/{id_reg}/{firma}"
    
    # Generar QR
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(pdf_url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="#00ff66", back_color="#0a0a0a")
    
    # Convertir a base64
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    return jsonify({"qr": f"data:image/png;base64,{img_base64}"})
