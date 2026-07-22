# Backend/routes/pdf_routes.py
from flask import Blueprint, request, jsonify, send_file
from services.pago_service import PagoService
from services.pdf_service import PDFService
from database import get_connection, get_cursor
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
        
        # ✅ OBTENER REGISTRO COMPLETO
        pago = PagoService.obtener_por_id(id_reg)
        if not pago:
            return jsonify({"error": "Registro no encontrado"}), 404
        
        # ✅ CONVERTIR pago.to_dict() a diccionario
        registro_dict = pago.to_dict()
        
        # ✅ CONVERTIR CAMPOS A STRING
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
        
        # ✅ AGREGAR CAMPOS ADICIONALES
        if 'empresa' not in registro_dict:
            registro_dict['empresa'] = 'DIXON'
        if 'empresa_sub' not in registro_dict:
            registro_dict['empresa_sub'] = 'Electricidad Automotriz'
        if 'direccion' not in registro_dict:
            registro_dict['direccion'] = 'Neptuno 163, Local C, Lo Prado'
        if 'telefono' not in registro_dict:
            registro_dict['telefono'] = '+569 9855 0331'
        
        # ============================================
        # ✅ OBTENER DATOS DEL USUARIO QUE DESCARGA
        # ============================================
        ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        user_agent = request.headers.get('User-Agent', '')
        
        # ✅ Obtener usuario y tipo desde la URL
        usuario = request.args.get('usuario', 'Sistema')
        tipo_usuario = request.args.get('tipo_usuario', 'usuario')
        
        # ✅ Si el tipo_usuario es 'usuario' o no viene, detectar automáticamente
        if not tipo_usuario or tipo_usuario == 'usuario':
            try:
                conn2, cur2 = get_cursor()
                cur2.execute("SELECT rol FROM usuarios WHERE username = %s", (usuario,))
                result = cur2.fetchone()
                if result:
                    tipo_usuario = result[0]  # 'admin', 'operador', 'basico'
                cur2.close()
                conn2.close()
            except:
                tipo_usuario = 'usuario'
        
        # ✅ Obtener el nombre del cliente del registro
        nombre_cliente = registro_dict.get('nombre', 'N/A')
        
        # ✅ GUARDAR EN AUDITORÍA CON DATOS CORRECTOS
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO auditoria_descargas 
                (id_registro, nombre_cliente, monto, usuario_descarga, tipo_usuario, ip, user_agent, fecha_descarga)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW() AT TIME ZONE 'America/Santiago')
            """, (
                id_reg,
                nombre_cliente,
                float(registro_dict.get('monto', 0)),
                usuario,
                tipo_usuario,
                ip,
                user_agent
            ))
            conn.commit()
            cur.close()
            conn.close()
            logger.info(f"✅ Auditoría de descarga registrada: OT #{id_reg}, Usuario: {usuario}, Rol: {tipo_usuario}")
        except Exception as e:
            logger.error(f"Error registrando descarga: {e}")
        
        # ✅ ENVIAR NOTIFICACIÓN PUSH
        enviar_notificacion_push(
            titulo="📄 PDF Descargado",
            mensaje=f"📄 Cliente: {nombre_cliente}\n💰 ${float(registro_dict.get('monto', 0)):,.0f}\n👤 Descargado por: {usuario}\n📌 Rol: {tipo_usuario}",
            url="/auditoria_descargas",
            id=id_reg
        )
        
        # ✅ GENERAR PDF
        buffer = PDFService.generar_pdf_formal(registro_dict)
        if not buffer:
            return jsonify({"error": "Error generando PDF"}), 500
        
        # ✅ NOMBRE DEL ARCHIVO
        nombre_cliente_limpio = str(nombre_cliente).replace(' ', '_').replace('/', '_').replace('\\', '_')
        fecha = str(registro_dict.get('fecha', '')).replace('-', '')[:8] or 'sin_fecha'
        download_name = f'OT_{id_reg}_{nombre_cliente_limpio}_{fecha}.pdf'
        
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
        if not PDFService.verificar_firma(id_reg, firma):
            return jsonify({"error": "Firma inválida"}), 403
        
        pdf_url = f"https://ea-dixon-production.up.railway.app/api/pdf/{id_reg}/{firma}"
        
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(pdf_url)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="#00ff66", back_color="#0a0a0a")
        
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        return jsonify({"qr": f"data:image/png;base64,{img_base64}"})
    except Exception as e:
        logger.error(f"❌ Error en generar_qr: {e}")
        return jsonify({"error": str(e)}), 500
