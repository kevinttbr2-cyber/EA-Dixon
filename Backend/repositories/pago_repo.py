# Backend/repositories/pago_repo.py
from database import get_connection, get_cursor
from models.pago import Pago
from datetime import datetime, timedelta
from utils.seguridad import sanitizar_input, sanitizar_patente, sanitizar_numero, validar_filtro
import logging

logger = logging.getLogger(__name__)

class PagoRepository:
    
    @staticmethod
    def insertar(pago):
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO pagos 
                (nombre, monto, fecha, hora, patente, marca, modelo, usuario, estado,
                 observaciones_cliente, observaciones_pago, telefono, flota, frecuente, 
                 kilometraje, diagnostico, reparacion, resultado, tiempo_estimado, anio,
                 costo_repuestos_real, costo_mano_obra_real, costo_diagnostico_real,
                 ganancia_neta, validado, validado_por, fecha_validacion, detalles_repuestos,
                 estado_pago, forma_pago)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                pago.nombre, pago.monto, pago.fecha, pago.hora, pago.patente,
                pago.marca, pago.modelo, pago.usuario, pago.estado,
                pago.observaciones_cliente, pago.observaciones_pago, pago.telefono,
                pago.flota, pago.frecuente, pago.kilometraje,
                pago.diagnostico, pago.reparacion, pago.resultado, pago.tiempo_estimado,
                pago.anio, pago.costo_repuestos_real, pago.costo_mano_obra_real,
                pago.costo_diagnostico_real, pago.ganancia_neta, pago.validado,
                pago.validado_por, pago.fecha_validacion, pago.detalles_repuestos,
                pago.estado_pago, pago.forma_pago
            ))
            id_reg = cur.fetchone()[0]
            conn.commit()
            cur.close()
            conn.close()
            return id_reg
        except Exception as e:
            logger.error(f"Error insertar pago: {e}")
            return None
    
    @staticmethod
    def actualizar(id_reg, pago):
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("""
                UPDATE pagos 
                SET monto=%s, estado=%s, observaciones_pago=%s, hora_pago=%s,
                    atendido_por=%s, diagnostico=%s, reparacion=%s, resultado=%s,
                    tiempo_estimado=%s, forma_pago=%s, estado_pago=%s
                WHERE id=%s
            """, (
                pago.monto, pago.estado, pago.observaciones_pago, pago.hora_pago,
                pago.atendido_por, pago.diagnostico, pago.reparacion, pago.resultado,
                pago.tiempo_estimado, pago.forma_pago, pago.estado_pago, id_reg
            ))
            conn.commit()
            cur.close()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error actualizar pago: {e}")
            return False
    
    @staticmethod
    def obtener_por_id(id_reg):
        try:
            conn, cur = get_cursor()
            cur.execute("SELECT * FROM pagos WHERE id = %s", (id_reg,))
            row = cur.fetchone()
            cur.close()
            conn.close()
            return Pago.from_db_row(row) if row else None
        except Exception as e:
            logger.error(f"Error obtener pago: {e}")
            return None
    
    @staticmethod
    def obtener_pendientes():
        try:
            conn, cur = get_cursor()
            cur.execute("SELECT * FROM pagos WHERE estado='pendiente' ORDER BY fecha DESC, hora DESC")
            rows = cur.fetchall()
            cur.close()
            conn.close()
            return [Pago.from_db_row(row) for row in rows]
        except Exception as e:
            logger.error(f"Error obtener pendientes: {e}")
            return []
    
    @staticmethod
    def obtener_pagados_hoy():
        try:
            conn, cur = get_cursor()
            cur.execute("""
                SELECT * FROM pagos
                WHERE estado='pagado' AND fecha = CURRENT_DATE
                ORDER BY fecha DESC, hora_pago DESC
            """)
            rows = cur.fetchall()
            cur.close()
            conn.close()
            return [Pago.from_db_row(row) for row in rows]
        except Exception as e:
            logger.error(f"Error obtener pagados hoy: {e}")
            return []
    
    @staticmethod
    def obtener_todos_pagados():
        try:
            conn, cur = get_cursor()
            cur.execute("SELECT * FROM pagos WHERE estado='pagado' ORDER BY fecha DESC")
            rows = cur.fetchall()
            cur.close()
            conn.close()
            return [Pago.from_db_row(row) for row in rows]
        except Exception as e:
            logger.error(f"Error obtener todos pagados: {e}")
            return []
    
    @staticmethod
    def obtener_flotas():
        try:
            conn, cur = get_cursor()
            cur.execute("""
                SELECT 
                    flota as nombre,
                    COUNT(*) as total_servicios,
                    SUM(monto) as total_gastado,
                    COUNT(DISTINCT patente) as total_vehiculos,
                    STRING_AGG(DISTINCT patente, ', ') as patentes
                FROM pagos
                WHERE flota IS NOT NULL AND flota != '' AND estado = 'pagado'
                GROUP BY flota
                ORDER BY total_servicios DESC
            """)
            rows = cur.fetchall()
            cur.close()
            conn.close()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error obtener flotas: {e}")
            return []
    
    # ============================================
    # 🆕 NUEVAS FUNCIONES AGREGADAS
    # ============================================
    
    @staticmethod
    def obtener_flotas_pendientes():
        """Obtiene flotas pendientes de pago"""
        try:
            conn, cur = get_cursor()
            cur.execute("""
                SELECT * FROM pagos 
                WHERE estado = 'pagado' 
                AND estado_pago = 'pendiente'
                AND flota IS NOT NULL 
                AND flota != ''
                ORDER BY flota, fecha DESC
            """)
            rows = cur.fetchall()
            cur.close()
            conn.close()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error obtener flotas pendientes: {e}")
            return []
    
    @staticmethod
    def obtener_pagados_por_filtro(filtro, fecha):
        """Obtiene pagos pagados según filtro"""
        try:
            if not validar_filtro(filtro):
                filtro = 'todos'
            
            conn, cur = get_cursor()
            query = "SELECT * FROM pagos WHERE estado = 'pagado' AND estado_pago = 'pagado'"
            params = []
            
            if filtro == 'hoy':
                query += " AND fecha = %s"
                params.append(fecha.strftime('%Y-%m-%d'))
            elif filtro == '7d':
                query += " AND fecha >= %s"
                params.append((fecha - timedelta(days=7)).strftime('%Y-%m-%d'))
            elif filtro == 'mes':
                query += " AND fecha >= %s"
                params.append((fecha - timedelta(days=30)).strftime('%Y-%m-%d'))
            
            query += " ORDER BY fecha DESC, hora DESC"
            cur.execute(query, params)
            rows = cur.fetchall()
            cur.close()
            conn.close()
            return [Pago.from_db_row(row) for row in rows]
        except Exception as e:
            logger.error(f"Error obtener pagados por filtro: {e}")
            return []
    
    @staticmethod
    def verificar_duplicado(nombre, patente):
        """Verifica si existe un duplicado"""
        try:
            nombre = sanitizar_input(nombre)
            patente = sanitizar_patente(patente)
            
            if not nombre or not patente:
                return False
            
            conn, cur = get_cursor()
            cur.execute("""
                SELECT COUNT(*) FROM pagos 
                WHERE nombre = %s 
                AND patente = %s 
                AND fecha >= CURRENT_DATE
            """, (nombre, patente))
            count = cur.fetchone()[0]
            cur.close()
            conn.close()
            return count > 0
        except Exception as e:
            logger.error(f"Error verificar duplicado: {e}")
            return False
    
    @staticmethod
    def obtener_balance_ventas(filtro, fecha):
        """Obtiene datos para el balance de ventas"""
        try:
            if not validar_filtro(filtro):
                filtro = 'todos'
            
            conn, cur = get_cursor()
            query = "SELECT * FROM pagos WHERE estado = 'pagado' AND estado_pago = 'pagado'"
            params = []
            
            if filtro == 'hoy':
                query += " AND fecha = %s"
                params.append(fecha.strftime('%Y-%m-%d'))
            elif filtro == '7d':
                query += " AND fecha >= %s"
                params.append((fecha - timedelta(days=7)).strftime('%Y-%m-%d'))
            elif filtro == 'mes':
                query += " AND fecha >= %s"
                params.append((fecha - timedelta(days=30)).strftime('%Y-%m-%d'))
            
            query += " ORDER BY fecha DESC, hora DESC"
            cur.execute(query, params)
            rows = cur.fetchall()
            cur.close()
            conn.close()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error obtener balance ventas: {e}")
            return []
# 1. obtener_todos_pagados() - ✅ YA ESTÁ (la tienes)

# 2. obtener_flotas() - ✅ YA ESTÁ (la tienes)

# 3. ❌ FALTA: obtener_balance_ventas() - Para el balance de ventas
@staticmethod
def obtener_balance_ventas(filtro, fecha):
    """Obtiene datos para el balance de ventas"""
    try:
        if not validar_filtro(filtro):
            filtro = 'todos'
        
        conn, cur = get_cursor()
        query = "SELECT * FROM pagos WHERE estado = 'pagado' AND estado_pago = 'pagado'"
        params = []
        
        if filtro == 'hoy':
            query += " AND fecha = %s"
            params.append(fecha.strftime('%Y-%m-%d'))
        elif filtro == '7d':
            query += " AND fecha >= %s"
            params.append((fecha - timedelta(days=7)).strftime('%Y-%m-%d'))
        elif filtro == 'mes':
            query += " AND fecha >= %s"
            params.append((fecha - timedelta(days=30)).strftime('%Y-%m-%d'))
        
        query += " ORDER BY fecha DESC, hora DESC"
        cur.execute(query, params)
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Error obtener balance ventas: {e}")
        return []

# 4. ❌ FALTA: obtener_flotas_pendientes_count() - Para el contador del navbar
@staticmethod
def obtener_flotas_pendientes_count():
    """Obtiene el número de flotas pendientes de pago"""
    try:
        conn, cur = get_cursor()
        cur.execute("""
            SELECT COUNT(*) FROM pagos 
            WHERE estado = 'pagado' 
            AND estado_pago = 'pendiente'
            AND flota IS NOT NULL 
            AND flota != ''
        """)
        count = cur.fetchone()[0] or 0
        cur.close()
        conn.close()
        return count
    except Exception as e:
        logger.error(f"Error obtener flotas pendientes count: {e}")
        return 0

# 5. ❌ FALTA: obtener_gastos_balance() - Para el balance con gastos
@staticmethod
def obtener_gastos_balance(fecha_inicio, fecha_fin):
    """Obtiene gastos para el balance"""
    try:
        conn, cur = get_cursor()
        cur.execute("""
            SELECT * FROM gastos 
            WHERE fecha BETWEEN %s AND %s
            ORDER BY fecha DESC, hora DESC
        """, (fecha_inicio, fecha_fin))
        gastos = [dict(row) for row in cur.fetchall()]
        cur.close()
        conn.close()
        return gastos
    except Exception as e:
        logger.error(f"Error obtener gastos balance: {e}")
        return []

# 6. ❌ FALTA: obtener_cierre_caja() - Para el cierre de caja
@staticmethod
def obtener_cierre_caja(fecha):
    """Obtiene el cierre de caja para una fecha"""
    try:
        conn, cur = get_cursor()
        cur.execute("SELECT * FROM cierres_caja WHERE fecha = %s", (fecha,))
        cierre = cur.fetchone()
        cur.close()
        conn.close()
        return dict(cierre) if cierre else None
    except Exception as e:
        logger.error(f"Error obtener cierre caja: {e}")
        return None

# 7. ❌ FALTA: crear_cierre_caja() - Para iniciar cierre
@staticmethod
def crear_cierre_caja(fecha, efectivo_inicial):
    """Crea un nuevo cierre de caja"""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO cierres_caja (fecha, efectivo_inicial, estado)
            VALUES (%s, %s, 'abierto')
            RETURNING id
        """, (fecha, efectivo_inicial))
        id_cierre = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        return id_cierre
    except Exception as e:
        logger.error(f"Error crear cierre caja: {e}")
        return None

# 8. ❌ FALTA: cerrar_cierre_caja() - Para cerrar caja
@staticmethod
def cerrar_cierre_caja(fecha, data):
    """Cierra un cierre de caja"""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            UPDATE cierres_caja 
            SET ventas_efectivo = %s,
                gastos_efectivo = %s,
                efectivo_esperado = %s,
                efectivo_real = %s,
                diferencia = %s,
                estado = 'cerrado',
                cerrado_por = %s,
                cerrado_en = NOW() AT TIME ZONE 'America/Santiago',
                observaciones = %s
            WHERE fecha = %s AND estado = 'abierto'
        """, (
            data.get('ventas_efectivo', 0),
            data.get('gastos_efectivo', 0),
            data.get('efectivo_esperado', 0),
            data.get('efectivo_real', 0),
            data.get('diferencia', 0),
            data.get('cerrado_por', 'Sistema'),
            data.get('observaciones', ''),
            fecha
        ))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error cerrar cierre caja: {e}")
        return False

# 9. ❌ FALTA: obtener_historial_cierres() - Para el historial
@staticmethod
def obtener_historial_cierres(limit=30):
    """Obtiene el historial de cierres de caja"""
    try:
        conn, cur = get_cursor()
        cur.execute("""
            SELECT * FROM cierres_caja 
            WHERE estado = 'cerrado'
            ORDER BY fecha DESC
            LIMIT %s
        """, (limit,))
        historial = [dict(row) for row in cur.fetchall()]
        cur.close()
        conn.close()
        return historial
    except Exception as e:
        logger.error(f"Error obtener historial cierres: {e}")
        return []

# 10. ❌ FALTA: obtener_repuestos_con_stock() - Para reporte de stock bajo
@staticmethod
def obtener_repuestos_con_stock(stock_minimo=5, proveedor=None):
    """Obtiene repuestos con stock bajo o igual al mínimo"""
    try:
        conn, cur = get_cursor()
        query = """
            SELECT id, nombre, stock, costo_proveedor, costo_venta_final, 
                   margen_ganancia, proveedor, costo_proveedor_pendiente, categoria_nombre
            FROM repuestos 
            WHERE stock IS NOT NULL AND stock <= %s AND stock > 0
        """
        params = [stock_minimo]
        
        if proveedor and proveedor != 'todos':
            query += " AND proveedor = %s"
            params.append(proveedor)
        
        query += " ORDER BY stock ASC, nombre ASC"
        
        cur.execute(query, params)
        productos = [dict(row) for row in cur.fetchall()]
        cur.close()
        conn.close()
        return productos
    except Exception as e:
        logger.error(f"Error obtener repuestos con stock: {e}")
        return []

# 11. ❌ FALTA: obtener_proveedores_repuestos() - Para filtros
@staticmethod
def obtener_proveedores_repuestos():
    """Obtiene la lista de proveedores de repuestos"""
    try:
        conn, cur = get_cursor()
        cur.execute("SELECT DISTINCT proveedor FROM repuestos WHERE proveedor IS NOT NULL AND proveedor != '' ORDER BY proveedor")
        proveedores = [row[0] for row in cur.fetchall()]
        cur.close()
        conn.close()
        return proveedores
    except Exception as e:
        logger.error(f"Error obtener proveedores repuestos: {e}")
        return []
