from database import get_connection, get_cursor
from models.pago import Pago
from datetime import datetime

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
                 kilometraje, diagnostico, reparacion, resultado, tiempo_estimado)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                pago.nombre, pago.monto, pago.fecha, pago.hora, pago.patente,
                pago.marca, pago.modelo, pago.usuario, pago.estado,
                pago.observaciones_cliente, pago.observaciones_pago, pago.telefono,
                pago.flota, pago.frecuente, pago.kilometraje,
                pago.diagnostico, pago.reparacion, pago.resultado, pago.tiempo_estimado
            ))
            id_reg = cur.fetchone()[0]
            conn.commit()
            cur.close()
            conn.close()
            return id_reg
        except Exception as e:
            print(f"Error insertar pago: {e}")
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
                    tiempo_estimado=%s
                WHERE id=%s
            """, (
                pago.monto, pago.estado, pago.observaciones_pago, pago.hora_pago,
                pago.atendido_por, pago.diagnostico, pago.reparacion, pago.resultado,
                pago.tiempo_estimado, id_reg
            ))
            conn.commit()
            cur.close()
            conn.close()
            return True
        except Exception as e:
            print(f"Error actualizar pago: {e}")
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
            print(f"Error obtener pago: {e}")
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
            print(f"Error obtener pendientes: {e}")
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
            print(f"Error obtener pagados hoy: {e}")
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
            print(f"Error obtener todos pagados: {e}")
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
            print(f"Error obtener flotas: {e}")
            return []
