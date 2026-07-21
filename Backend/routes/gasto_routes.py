# Backend/routes/gasto_routes.py
from flask import Blueprint, request, jsonify
from database import get_connection, get_cursor
from utils.seguridad import sanitizar_input, sanitizar_numero
import logging
from services.factura_sii_service import FacturaSIIService

logger = logging.getLogger(__name__)
gasto_bp = Blueprint('gasto', __name__, url_prefix='/api')

# ============================================
# RUTA GET - OBTENER GASTOS POR FECHA (CORREGIDO)
# ============================================
@gasto_bp.route('/gastos', methods=['GET'])
def obtener_gastos():
    try:
        fecha = request.args.get('fecha')
        if not fecha:
            return jsonify({"error": "Fecha requerida"}), 400
        
        conn, cur = get_cursor()
        cur.execute("""
            SELECT 
                id,
                categoria,
                descripcion,
                monto,
                metodo_pago,
                proveedor,
                folio,
                tipo_gasto,
                registrado_por,
                fecha,
                hora,
                created_at AT TIME ZONE 'UTC' AT TIME ZONE 'America/Santiago' as created_at_chile,
                updated_at AT TIME ZONE 'UTC' AT TIME ZONE 'America/Santiago' as updated_at_chile
            FROM gastos 
            WHERE fecha = %s 
            ORDER BY hora DESC
        """, (fecha,))
        
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
            if g.get('created_at_chile'):
                g['created_at'] = g['created_at_chile'].strftime('%Y-%m-%d %H:%M:%S')
            if g.get('updated_at_chile'):
                g['updated_at'] = g['updated_at_chile'].strftime('%Y-%m-%d %H:%M:%S')
            g.pop('created_at_chile', None)
            g.pop('updated_at_chile', None)
            gastos.append(g)
        
        return jsonify(gastos)
        
    except Exception as e:
        logger.error(f"Error en obtener_gastos: {e}")
        return jsonify({"error": str(e)}), 500

# ============================================
# RUTA POST - REGISTRAR GASTO (CON TIPO_GASTO)
# ============================================
@gasto_bp.route('/gastos', methods=['POST'])
def registrar_gasto():
    try:
        data = request.json
        
        if not data.get('categoria') or not data.get('monto'):
            return jsonify({"error": "Categoría y monto son obligatorios"}), 400
        
        tipo_gasto = sanitizar_input(data.get('tipo_gasto', 'general').strip())
        if tipo_gasto not in ['venta', 'trabajo', 'general']:
            tipo_gasto = 'general'
        
        conn = get_connection()
        cur = conn.cursor()
        
        # 🔥 AHORA CON ZONA HORARIA CHILE PARA TODOS LOS CAMPOS
        cur.execute("""
            INSERT INTO gastos 
            (categoria, monto, metodo_pago, descripcion, proveedor, folio, 
             fecha, hora, registrado_por, tipo_gasto, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, 
                    CAST(NOW() AT TIME ZONE 'America/Santiago' AS date), 
                    CAST(NOW() AT TIME ZONE 'America/Santiago' AS time), 
                    %s, %s,
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
            sanitizar_input(data.get('registrado_por', 'Sistema')),
            tipo_gasto
        ))
        
        id_gasto = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info(f"✅ Gasto registrado ID: {id_gasto} - Tipo: {tipo_gasto}")
        return jsonify({"success": True, "id": id_gasto})
        
    except Exception as e:
        logger.error(f"Error en registrar_gasto: {e}")
        return jsonify({"error": str(e)}), 500

@gasto_bp.route('/gastos_balance', methods=['GET'])
def obtener_gastos_balance():
    try:
        fecha_inicio = request.args.get('fecha_inicio')
        fecha_fin = request.args.get('fecha_fin')
        
        if not fecha_inicio or not fecha_fin:
            return jsonify({"error": "Fechas requeridas"}), 400
        
        conn, cur = get_cursor()
        
        # 🔥 CORREGIDO: Usar fecha (que está en Chile) para el filtro
        cur.execute("""
            SELECT 
                id,
                categoria,
                descripcion,
                monto,
                metodo_pago,
                proveedor,
                folio,
                tipo_gasto,
                registrado_por,
                fecha,
                hora,
                created_at AT TIME ZONE 'UTC' AT TIME ZONE 'America/Santiago' as created_at_chile
            FROM gastos 
            WHERE fecha BETWEEN %s AND %s
            ORDER BY fecha DESC, hora DESC
        """, (fecha_inicio, fecha_fin))
        
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        gastos = []
        for row in rows:
            g = dict(row)
            # Convertir fecha y hora a string
            if g.get('hora') and hasattr(g['hora'], 'strftime'):
                g['hora'] = g['hora'].strftime('%H:%M:%S')
            if g.get('fecha') and hasattr(g['fecha'], 'strftime'):
                g['fecha'] = g['fecha'].strftime('%Y-%m-%d')
            if g.get('created_at_chile'):
                g['created_at'] = g['created_at_chile'].strftime('%Y-%m-%d %H:%M:%S')
            g.pop('created_at_chile', None)
            gastos.append(g)
        
        logger.info(f"📊 Gastos obtenidos: {len(gastos)} en el rango {fecha_inicio} - {fecha_fin}")
        return jsonify(gastos)
        
    except Exception as e:
        logger.error(f"Error en obtener_gastos_balance: {e}")
        return jsonify([])

# ============================================
# RUTA DELETE - ELIMINAR GASTO
# ============================================
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
# ============================================
# RUTA POST - REGISTRAR FACTURA SII
# ============================================
@gasto_bp.route('/facturas_sii', methods=['POST'])
def registrar_factura_sii():
    try:
        data = request.json
        
        if not data.get('rut_emisor') or not data.get('folio'):
            return jsonify({"error": "RUT emisor y folio son obligatorios"}), 400
        
        conn = get_connection()
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO facturas_sii 
            (rut_emisor, rut_receptor, folio, tipo_documento, fecha, monto, 
             codigo_autorizacion, razon_social_emisor, razon_social_receptor, 
             texto_original, usuario, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 
                    NOW() AT TIME ZONE 'America/Santiago')
            RETURNING id
        """, (
            sanitizar_input(data.get('rut_emisor')),
            sanitizar_input(data.get('rut_receptor')),
            sanitizar_input(data.get('folio')),
            sanitizar_input(data.get('tipo_documento', 'Factura')),
            data.get('fecha'),
            sanitizar_numero(data.get('monto', 0), min_val=0),
            sanitizar_input(data.get('codigo_autorizacion')),
            sanitizar_input(data.get('razon_social_emisor')),
            sanitizar_input(data.get('razon_social_receptor')),
            data.get('texto_original', ''),
            sanitizar_input(data.get('usuario', 'Sistema'))
        ))
        
        id_factura = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info(f"✅ Factura SII registrada ID: {id_factura} - Folio: {data.get('folio')}")
        return jsonify({"success": True, "id": id_factura})
        
    except Exception as e:
        logger.error(f"Error en registrar_factura_sii: {e}")
        return jsonify({"error": str(e)}), 500


# ============================================
# RUTA GET - OBTENER FACTURAS SII
# ============================================
@gasto_bp.route('/facturas_sii', methods=['GET'])
def obtener_facturas_sii():
    try:
        filtro = request.args.get('filtro', 'todos')
        fecha_inicio = request.args.get('fecha_inicio')
        fecha_fin = request.args.get('fecha_fin')
        
        conn, cur = get_cursor()
        
        query = """
            SELECT id, rut_emisor, rut_receptor, folio, tipo_documento, fecha, monto,
                   codigo_autorizacion, razon_social_emisor, razon_social_receptor,
                   usuario, created_at, fecha_escaneo
            FROM facturas_sii
            WHERE 1=1
        """
        params = []
        
        if fecha_inicio and fecha_fin:
            query += " AND fecha BETWEEN %s AND %s"
            params.append(fecha_inicio)
            params.append(fecha_fin)
        elif filtro == 'hoy':
            query += " AND fecha = CURRENT_DATE"
        elif filtro == '7d':
            query += " AND fecha >= CURRENT_DATE - INTERVAL '7 days'"
        elif filtro == 'mes':
            query += " AND fecha >= CURRENT_DATE - INTERVAL '30 days'"
        
        query += " ORDER BY fecha DESC, created_at DESC"
        
        cur.execute(query, params)
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        facturas = []
        for row in rows:
            f = dict(row)
            if f.get('fecha') and hasattr(f['fecha'], 'strftime'):
                f['fecha'] = f['fecha'].strftime('%Y-%m-%d')
            if f.get('created_at') and hasattr(f['created_at'], 'strftime'):
                f['created_at'] = f['created_at'].strftime('%Y-%m-%d %H:%M:%S')
            facturas.append(f)
        
        return jsonify(facturas)
        
    except Exception as e:
        logger.error(f"Error en obtener_facturas_sii: {e}")
        return jsonify([])
