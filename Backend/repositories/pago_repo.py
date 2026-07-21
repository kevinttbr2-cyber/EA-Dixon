# Backend/repositories/pago_repo.py
from database import get_connection, get_cursor
from models.pago import Pago
from datetime import datetime, timedelta
from utils.seguridad import sanitizar_input, sanitizar_patente, sanitizar_numero, validar_filtro
import json
import logging

logger = logging.getLogger(__name__)

class PagoRepository:
    
    # ============================================
    # FUNCIONES CRUD BÁSICAS
    # ============================================
    
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
                 estado_pago, forma_pago, tipo_venta, producto_vendido, descuento_aplicado)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                pago.estado_pago, pago.forma_pago, pago.tipo_venta, pago.producto_vendido,
                pago.descuento_aplicado if hasattr(pago, 'descuento_aplicado') else 0
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
                    tiempo_estimado=%s, forma_pago=%s, estado_pago=%s,
                    costo_repuestos_real=%s, costo_mano_obra_real=%s,
                    costo_diagnostico_real=%s, ganancia_neta=%s,
                    validado=%s, validado_por=%s, fecha_validacion=%s,
                    detalles_repuestos=%s, tipo_venta=%s, producto_vendido=%s,
                    descuento_aplicado=%s
                WHERE id=%s
            """, (
                pago.monto, pago.estado, pago.observaciones_pago, pago.hora_pago,
                pago.atendido_por, pago.diagnostico, pago.reparacion, pago.resultado,
                pago.tiempo_estimado, pago.forma_pago, pago.estado_pago,
                pago.costo_repuestos_real, pago.costo_mano_obra_real,
                pago.costo_diagnostico_real, pago.ganancia_neta,
                pago.validado, pago.validado_por, pago.fecha_validacion,
                pago.detalles_repuestos, pago.tipo_venta, pago.producto_vendido,
                pago.descuento_aplicado if hasattr(pago, 'descuento_aplicado') else 0,
                id_reg
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
    def eliminar(id_reg):
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("DELETE FROM pagos WHERE id = %s", (id_reg,))
            conn.commit()
            cur.close()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error eliminar pago: {e}")
            return False
    
    # ============================================
    # FUNCIONES DE CONSULTA
    # ============================================
    
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
    # FUNCIONES PARA FILTROS Y BALANCES
    # ============================================
    
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
    def obtener_balance_completo(filtro, fecha):
        """Obtiene el balance completo con totales"""
        try:
            if not validar_filtro(filtro):
                filtro = 'todos'
            
            conn, cur = get_cursor()
            query = """
                SELECT 
                    *,
                    COALESCE(SUM(monto) OVER(), 0) as total_pagado,
                    COALESCE(SUM(costo_repuestos_real) OVER(), 0) as total_repuestos,
                    COALESCE(SUM(costo_mano_obra_real) OVER(), 0) as total_mano_obra,
                    COALESCE(SUM(costo_diagnostico_real) OVER(), 0) as total_diagnostico,
                    COALESCE(SUM(descuento_aplicado) OVER(), 0) as total_descuentos
                FROM pagos 
                WHERE estado = 'pagado' AND estado_pago = 'pagado'
            """
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
            logger.error(f"Error obtener balance completo: {e}")
            return []
    
    @staticmethod
    def obtener_balance_ventas(filtro, fecha):
        """Obtiene datos para el balance de ventas con gastos y descuentos"""
        try:
            if not validar_filtro(filtro):
                filtro = 'todos'
            
            conn, cur = get_cursor()
            
            # ============================================
            # 1. OBTENER VENTAS CON DESCUENTO
            # ============================================
            query_ventas = """
                SELECT 
                    *,
                    COALESCE(descuento_aplicado, 0) as descuento_aplicado,
                    COALESCE(costo_repuestos_real, 0) as costo_repuestos_real,
                    COALESCE(costo_mano_obra_real, 0) as costo_mano_obra_real,
                    COALESCE(costo_diagnostico_real, 0) as costo_diagnostico_real
                FROM pagos 
                WHERE estado = 'pagado' AND estado_pago = 'pagado'
            """
            params = []
            
            if filtro == 'hoy':
                query_ventas += " AND fecha = %s"
                params.append(fecha.strftime('%Y-%m-%d'))
            elif filtro == '7d':
                query_ventas += " AND fecha >= %s"
                params.append((fecha - timedelta(days=7)).strftime('%Y-%m-%d'))
            elif filtro == 'mes':
                query_ventas += " AND fecha >= %s"
                params.append((fecha - timedelta(days=30)).strftime('%Y-%m-%d'))
            
            query_ventas += " ORDER BY fecha DESC, hora DESC"
            cur.execute(query_ventas, params)
            rows = cur.fetchall()
            ventas = [dict(row) for row in rows]
            
            # ============================================
            # 2. CALCULAR FECHAS PARA GASTOS
            # ============================================
            if filtro == 'hoy':
                fecha_inicio = fecha.strftime('%Y-%m-%d')
                fecha_fin = fecha.strftime('%Y-%m-%d')
            elif filtro == '7d':
                fecha_inicio = (fecha - timedelta(days=7)).strftime('%Y-%m-%d')
                fecha_fin = fecha.strftime('%Y-%m-%d')
            elif filtro == 'mes':
                fecha_inicio = (fecha - timedelta(days=30)).strftime('%Y-%m-%d')
                fecha_fin = fecha.strftime('%Y-%m-%d')
            else:
                fecha_inicio = '2020-01-01'
                fecha_fin = fecha.strftime('%Y-%m-%d')
            
            # ============================================
            # 3. OBTENER GASTOS OPERATIVOS
            # ============================================
            cur.execute("""
                SELECT 
                    id,
                    categoria,
                    descripcion,
                    monto,
                    metodo_pago,
                    fecha,
                    hora,
                    created_at
                FROM gastos 
                WHERE fecha BETWEEN %s AND %s
                ORDER BY fecha DESC, hora DESC
            """, (fecha_inicio, fecha_fin))
            
            gastos_rows = cur.fetchall()
            gastos = []
            total_gastos = 0
            
            for row in gastos_rows:
                g = dict(row)
                if g.get('hora') and hasattr(g['hora'], 'strftime'):
                    g['hora'] = g['hora'].strftime('%H:%M:%S')
                if g.get('fecha') and hasattr(g['fecha'], 'strftime'):
                    g['fecha'] = g['fecha'].strftime('%Y-%m-%d')
                if g.get('created_at') and hasattr(g['created_at'], 'strftime'):
                    g['created_at'] = g['created_at'].strftime('%Y-%m-%d %H:%M:%S')
                gastos.append(g)
                total_gastos += float(g.get('monto', 0) or 0)
            
            cur.close()
            conn.close()
            
            return {
                'ventas': ventas,
                'gastos': gastos,
                'total_gastos': total_gastos
            }
        except Exception as e:
            logger.error(f"Error obtener balance ventas: {e}")
            return {'ventas': [], 'gastos': [], 'total_gastos': 0}
    
    # ============================================
    # FUNCIONES PARA FLOTAS
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
    
    @staticmethod
    def obtener_flotas_disponibles():
        """Obtiene todas las flotas registradas (nombres únicos)"""
        try:
            conn, cur = get_cursor()
            cur.execute("""
                SELECT DISTINCT flota FROM pagos 
                WHERE flota IS NOT NULL AND flota != '' 
                ORDER BY flota
            """)
            flotas = [row[0] for row in cur.fetchall()]
            cur.close()
            conn.close()
            return flotas
        except Exception as e:
            logger.error(f"Error obtener flotas disponibles: {e}")
            return []
    
    # ============================================
    # FUNCIONES PARA VALIDACIONES
    # ============================================
    
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
    def actualizar_repuestos_venta(id_reg, data):
        """Actualiza solo los repuestos y costos de una venta"""
        try:
            conn = get_connection()
            cur = conn.cursor()
            
            cur.execute("""
                UPDATE pagos 
                SET detalles_repuestos = %s::jsonb,
                    costo_repuestos_real = %s,
                    costo_mano_obra_real = %s,
                    costo_diagnostico_real = %s,
                    ganancia_neta = %s,
                    monto = %s,
                    descuento_aplicado = %s,
                    actualizado_en = NOW() AT TIME ZONE 'America/Santiago'
                WHERE id = %s
            """, (
                json.dumps(data.get('detalles_repuestos', [])),
                data.get('costo_repuestos_real', 0),
                data.get('costo_mano_obra_real', 0),
                data.get('costo_diagnostico_real', 0),
                data.get('ganancia_neta', 0),
                data.get('monto', 0),
                data.get('descuento_aplicado', 0),
                id_reg
            ))
            
            conn.commit()
            cur.close()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error actualizar repuestos venta: {e}")
            return False
    
    # ============================================
    # FUNCIONES PARA DASHBOARD
    # ============================================
    
    @staticmethod
    def obtener_dashboard_data(fecha_desde):
        """Obtiene datos para el dashboard"""
        try:
            conn, cur = get_cursor()
            
            # Totales
            cur.execute("""
                SELECT 
                    COALESCE(SUM(monto), 0) as total_facturado,
                    COALESCE(SUM(costo_repuestos_real), 0) as total_repuestos,
                    COALESCE(SUM(costo_mano_obra_real), 0) as total_mano_obra,
                    COALESCE(SUM(costo_diagnostico_real), 0) as total_diagnostico,
                    COALESCE(SUM(descuento_aplicado), 0) as total_descuentos,
                    COUNT(*) as total_servicios
                FROM pagos 
                WHERE estado = 'pagado' 
                AND estado_pago = 'pagado'
                AND fecha >= %s
            """, (fecha_desde,))
            totales = cur.fetchone()
            
            # Ventas diarias
            cur.execute("""
                SELECT 
                    fecha,
                    COALESCE(SUM(monto), 0) as total
                FROM pagos 
                WHERE estado = 'pagado' 
                AND estado_pago = 'pagado'
                AND fecha >= %s
                GROUP BY fecha
                ORDER BY fecha ASC
            """, (fecha_desde,))
            ventas = cur.fetchall()
            
            # Ganancia acumulada
            cur.execute("""
                SELECT 
                    fecha,
                    COALESCE(SUM(monto - COALESCE(costo_repuestos_real, 0) - COALESCE(costo_mano_obra_real, 0) - COALESCE(costo_diagnostico_real, 0)), 0) as ganancia
                FROM pagos 
                WHERE estado = 'pagado' 
                AND estado_pago = 'pagado'
                AND fecha >= %s
                GROUP BY fecha
                ORDER BY fecha ASC
            """, (fecha_desde,))
            ganancias = cur.fetchall()
            
            # Top clientes
            cur.execute("""
                SELECT 
                    nombre,
                    COALESCE(SUM(monto), 0) as total_gastado
                FROM pagos 
                WHERE estado = 'pagado' 
                AND estado_pago = 'pagado'
                AND nombre IS NOT NULL
                AND fecha >= %s
                GROUP BY nombre
                ORDER BY total_gastado DESC
                LIMIT 5
            """, (fecha_desde,))
            clientes = cur.fetchall()
            
            # Promedio diario
            cur.execute("""
                SELECT 
                    COALESCE(AVG(monto), 0) as promedio_diario
                FROM pagos 
                WHERE estado = 'pagado' 
                AND estado_pago = 'pagado'
                AND fecha >= %s
            """, (fecha_desde,))
            promedio = cur.fetchone()
            
            cur.close()
            conn.close()
            
            return {
                'totales': totales,
                'ventas': ventas,
                'ganancias': ganancias,
                'clientes': clientes,
                'promedio_diario': promedio[0] if promedio else 0
            }
        except Exception as e:
            logger.error(f"Error obtener dashboard data: {e}")
            return None
    
    @staticmethod
    def obtener_meses_disponibles():
        """Obtiene los meses con datos para el dashboard"""
        try:
            conn, cur = get_cursor()
            cur.execute("""
                SELECT DISTINCT 
                    EXTRACT(YEAR FROM fecha) as anio,
                    EXTRACT(MONTH FROM fecha) as mes
                FROM pagos 
                WHERE estado = 'pagado' 
                AND estado_pago = 'pagado'
                AND fecha IS NOT NULL
                ORDER BY anio DESC, mes DESC
            """)
            meses = []
            for row in cur.fetchall():
                meses.append({
                    'anio': int(row[0]),
                    'mes': int(row[1])
                })
            cur.close()
            conn.close()
            return meses
        except Exception as e:
            logger.error(f"Error obtener meses disponibles: {e}")
            return []
    
    # ============================================
    # FUNCIONES PARA GASTOS
    # ============================================
    
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
    
    # ============================================
    # FUNCIONES PARA CIERRE DE CAJA
    # ============================================
    
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
    
    # ============================================
    # FUNCIONES PARA REPUESTOS
    # ============================================
    
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
