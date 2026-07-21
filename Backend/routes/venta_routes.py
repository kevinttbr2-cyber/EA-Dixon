# Backend/routes/venta_routes.py
from flask import Blueprint, request, jsonify
from database import get_connection, get_cursor
from utils.seguridad import sanitizar_input, sanitizar_numero, validar_filtro
from utils.fecha_utils import get_fecha_hora_chile, get_fecha_chile
from services.notification_service import enviar_notificacion_push
from services.pago_service import PagoService
import json
import logging
from datetime import timedelta

logger = logging.getLogger(__name__)
venta_bp = Blueprint('venta', __name__, url_prefix='/api')

@venta_bp.route('/venta_rapida', methods=['POST'])
def venta_rapida():
    try:
        data = request.json
        
        if not data.get('nombre') or not data.get('monto'):
            return jsonify({"error": "Nombre y monto son obligatorios"}), 400
        
        conn = get_connection()
        cur = conn.cursor()
        
        fecha_chile, hora_chile = get_fecha_hora_chile()
        detalles_repuestos = data.get('detalles_repuestos', [])
        
        # 🔥 NUEVO: Obtener descuento
        descuento_aplicado = sanitizar_numero(data.get('descuento_aplicado', 0), min_val=0)
        if descuento_aplicado > 0:
            logger.info(f"💰 Descuento aplicado en venta rápida: ${descuento_aplicado}")
        
        for item in detalles_repuestos:
            nombre = sanitizar_input(item.get('nombre', '').strip())
            cantidad = int(sanitizar_numero(item.get('cantidad', 1), min_val=1))
            costo_unitario = sanitizar_numero(item.get('costo_unitario', 0), min_val=0)
            
            if nombre and costo_unitario > 0:
                cur.execute("SELECT id, stock, costo_proveedor FROM repuestos WHERE nombre = %s", (nombre,))
                existente = cur.fetchone()
                
                if existente:
                    id_repuesto, stock_actual, costo_prov = existente
                    
                    if stock_actual is not None and stock_actual < cantidad:
                        cur.close()
                        conn.close()
                        return jsonify({
                            "error": f"Stock insuficiente para '{nombre}'. Disponible: {stock_actual}, Solicitado: {cantidad}"
                        }), 400
                    
                    nuevo_stock = (stock_actual or 0) - cantidad
                    cur.execute("""
                        UPDATE repuestos 
                        SET stock = %s,
                            updated_at = NOW() AT TIME ZONE 'America/Santiago'
                        WHERE id = %s
                    """, (nuevo_stock, id_repuesto))
                else:
                    cur.execute("""
                        INSERT INTO repuestos (nombre, costo_proveedor, margen_ganancia, costo_venta_final, 
                                               proveedor, stock, costo_proveedor_pendiente, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, 
                                NOW() AT TIME ZONE 'America/Santiago', 
                                NOW() AT TIME ZONE 'America/Santiago')
                    """, (
                        nombre, 0, 30, costo_unitario, 'Desde Venta Rápida',
                        0, True
                    ))
        
        # 🔥 MODIFICADO: Agregar descuento_aplicado al INSERT
        cur.execute("""
            INSERT INTO pagos 
            (nombre, monto, fecha, hora, estado, tipo_venta, producto_vendido, 
             atendido_por, observaciones_pago, telefono, forma_pago, detalles_repuestos,
             descuento_aplicado)
            VALUES (%s, %s, %s, %s, 'pagado', 'directa', %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            sanitizar_input(data.get('nombre')),
            sanitizar_numero(data.get('monto', 0), min_val=0),
            fecha_chile,
            hora_chile,
            sanitizar_input(data.get('producto_vendido', '')),
            sanitizar_input(data.get('atendido_por', 'Técnico')),
            sanitizar_input(data.get('observaciones', '')),
            sanitizar_input(data.get('telefono', '')),
            sanitizar_input(data.get('forma_pago', 'efectivo')),
            json.dumps(detalles_repuestos),
            descuento_aplicado  # 🔥 NUEVO: Descuento
        ))
        
        id_reg = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        
        # 🔥 MODIFICADO: Mensaje de notificación con descuento
        mensaje_notificacion = f"Cliente: {data.get('nombre')}\nTotal: ${float(data.get('monto', 0)):,.0f}"
        if descuento_aplicado > 0:
            mensaje_notificacion += f"\nDescuento: -${descuento_aplicado:,.0f}"
        
        enviar_notificacion_push(
            titulo="⚡ Venta Rápida",
            mensaje=mensaje_notificacion,
            url="/balance_ventas"
        )
        
        return jsonify({
            "success": True, 
            "id": id_reg,
            "descuento_aplicado": descuento_aplicado
        })
    except Exception as e:
        logger.error(f"Error en venta_rapida: {e}")
        return jsonify({"error": str(e)}), 500

# ============================================
# BALANCE DE VENTAS (SIN CAMBIOS - IGUAL)
# ============================================
@venta_bp.route('/balance_ventas', methods=['GET'])
def balance_ventas():
    try:
        filtro = request.args.get('filtro', 'hoy')
        
        if not validar_filtro(filtro):
            return jsonify({"error": "Filtro inválido"}), 400
        
        hoy = get_fecha_chile()
        registros = PagoService.obtener_balance_ventas(filtro, hoy)
        
        if not registros:
            return jsonify({
                "registros": [],
                "total_ventas": 0,
                "total_trabajo": 0,
                "total_directa": 0,
                "ganancia_trabajo": 0,
                "ganancia_directa": 0,
                "ganancia_neta": 0,
                "total_repuestos_trabajo": 0,
                "total_repuestos_directa": 0
            })
        
        # Procesar registros
        for r in registros:
            total = 0
            detalles = r.get('detalles_repuestos', [])
            for item in detalles:
                cantidad = item.get('cantidad', 1)
                precio = item.get('costo_unitario', 0) or item.get('costo', 0)
                total += cantidad * precio
            r['total_repuestos'] = total
        
        trabajo = []
        directa = []
        
        for r in registros:
            tiene_vehiculo = r.get('marca') and r.get('marca').strip() != '' and r.get('modelo') and r.get('modelo').strip() != ''
            es_directa = r.get('tipo_venta') == 'directa' or not tiene_vehiculo
            
            if es_directa:
                directa.append(r)
            else:
                trabajo.append(r)
        
        conn, cur = get_cursor()
        
        def calcular_venta_repuestos(registros):
            total = 0
            for r in registros:
                detalles = r.get('detalles_repuestos', [])
                if detalles and len(detalles) > 0:
                    for item in detalles:
                        cantidad = int(item.get('cantidad', 1) or 1)
                        precio_venta = float(item.get('costo_unitario', 0) or item.get('costo', 0) or 0)
                        total += cantidad * precio_venta
                else:
                    total += float(r.get('costo_repuestos_real', 0) or 0)
            return total
        
        def calcular_costo_repuestos(registros):
            total = 0
            for r in registros:
                detalles = r.get('detalles_repuestos', [])
                if detalles and len(detalles) > 0:
                    for item in detalles:
                        nombre = item.get('nombre', '')
                        cantidad = int(item.get('cantidad', 1) or 1)
                        
                        if nombre:
                            cur.execute("SELECT costo_proveedor FROM repuestos WHERE nombre = %s", (nombre,))
                            resultado = cur.fetchone()
                            if resultado:
                                costo_prov = float(resultado[0] or 0)
                                total += costo_prov * cantidad
                            else:
                                precio = float(item.get('costo_unitario', 0) or item.get('costo', 0) or 0)
                                total += precio * cantidad
                        else:
                            precio = float(item.get('costo_unitario', 0) or item.get('costo', 0) or 0)
                            total += precio * cantidad
                else:
                    total += float(r.get('costo_repuestos_real', 0) or 0)
            return total
        
        total_ventas = calcular_venta_repuestos(registros)
        total_trabajo = calcular_venta_repuestos(trabajo)
        total_directa = calcular_venta_repuestos(directa)
        
        costo_trabajo = calcular_costo_repuestos(trabajo)
        costo_directa = calcular_costo_repuestos(directa)
        
        ganancia_trabajo = total_trabajo - costo_trabajo
        ganancia_directa = total_directa - costo_directa
        ganancia_neta = ganancia_trabajo + ganancia_directa
        
        cur.close()
        conn.close()
        
        return jsonify({
            "registros": registros,
            "total_ventas": total_ventas,
            "total_trabajo": total_trabajo,
            "total_directa": total_directa,
            "ganancia_trabajo": round(ganancia_trabajo, 2),
            "ganancia_directa": round(ganancia_directa, 2),
            "ganancia_neta": round(ganancia_neta, 2),
            "total_repuestos_trabajo": round(costo_trabajo, 2),
            "total_repuestos_directa": round(costo_directa, 2)
        })
    except Exception as e:
        logger.error(f"Error en balance_ventas: {e}")
        return jsonify({"error": str(e)}), 500
