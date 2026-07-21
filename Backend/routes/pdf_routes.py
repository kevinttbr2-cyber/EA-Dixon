# Backend/routes/pdf_routes.py
from flask import Blueprint, request, jsonify, send_file
from services.pago_service import PagoService
from services.pdf_service import PDFService
from database import get_connection
import qrcode
from io import BytesIO
import base64
import logging
from datetime import datetime

logger = logging.getLogger(__name__)
pdf_bp = Blueprint('pdf', __name__, url_prefix='/api')

@pdf_bp.route('/firma/<int:id_reg>', methods=['GET'])
def get_firma(id_reg):
    """Devuelve la firma para un ID de registro"""
    firma = PDFService.generar_firma(id_reg)
    return jsonify({"firma": firma})

@pdf_bp.route('/pdf/<int:id_reg>/<firma>', methods=['GET'])
def descargar_pdf(id_reg, firma):
    try:
        # Verificar firma
        if not PDFService.verificar_firma(id_reg, firma):
            return jsonify({"error": "Firma inválida"}), 403
        
        # Obtener registro
        pago = PagoService.obtener_por_id(id_reg)
        if not pago:
            return jsonify({"error": "Registro no encontrado"}), 404
        
        # ✅ CONVERTIR pago.to_dict() a un diccionario con todos los campos como string
        registro_dict = pago.to_dict()
        
        # ✅ CONVERTIR CAMPOS A STRING PARA EVITAR ERRORES EN PDF
        for key, value in registro_dict.items():
            if value is None:
                registro_dict[key] = ''
            elif isinstance(value, int):
                registro_dict[key] = str(value)
            elif isinstance(value, float):
                registro_dict[key] = str(value)
            elif isinstance(value, datetime):
                registro_dict[key] = value.strftime('%Y-%m-%d')
            elif isinstance(value, dict) or isinstance(value, list):
                registro_dict[key] = str(value)
        
        # ✅ AGREGAR CAMPOS ADICIONALES SI FALTAN
        if 'empresa' not in registro_dict:
            registro_dict['empresa'] = 'DIXON'
        if 'empresa_sub' not in registro_dict:
            registro_dict['empresa_sub'] = 'Electricidad Automotriz'
        if 'direccion' not in registro_dict:
            registro_dict['direccion'] = 'Neptuno 163, Local C, Lo Prado'
        if 'telefono' not in registro_dict:
            registro_dict['telefono'] = '+569 9855 0331'
        
        # Generar PDF
        buffer = PDFService.generar_pdf_formal(registro_dict)
        if not buffer:
            return jsonify({"error": "Error generando PDF"}), 500
        
        # Registrar descarga en auditoría
        ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        user_agent = request.headers.get('User-Agent', '')
        
        try:
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
            logger.error(f"Error registrando descarga: {e}")
        
        # ✅ NOMBRE DEL ARCHIVO - CONVERTIR TODO A STRING Y LIMPIAR
        nombre_cliente = registro_dict.get('nombre', 'cliente')
        if nombre_cliente:
            nombre_cliente = str(nombre_cliente).replace(' ', '_').replace('/', '_').replace('\\', '_')
        else:
            nombre_cliente = 'cliente'
        
        # ✅ FECHA - ASEGURAR QUE ES STRING
        fecha = registro_dict.get('fecha', '')
        if fecha:
            fecha = str(fecha).replace('-', '')[:8]
        else:
            fecha = 'sin_fecha'
        
        download_name = f'OT_{id_reg}_{nombre_cliente}_{fecha}.pdf'
        
        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=download_name
        )
    except Exception as e:
        logger.error(f"❌ Error en descargar_pdf: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@pdf_bp.route('/qr/<int:id_reg>/<firma>', methods=['GET'])
def generar_qr(id_reg, firma):
    """Genera un código QR con la URL del PDF"""
    try:
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
    except Exception as e:
        logger.error(f"❌ Error en generar_qr: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
