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
    
    @staticmethod
    def obtener_pagados_por_filtro(filtro, fecha):
        """Obtiene pagos pagados según filtro (SEGURO)"""
        try:
            # Validar filtro
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
    def obtener_flotas_pendientes():
        """Obtiene flotas pendientes de pago (SEGURO)"""
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
    def verificar_duplicado(nombre, patente):
        """Verifica si existe un duplicado (SEGURO)"""
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
