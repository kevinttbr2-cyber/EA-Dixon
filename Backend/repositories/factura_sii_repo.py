# Backend/repositories/factura_sii_repo.py
from database import get_connection, get_cursor
from models.factura_sii import FacturaSII
import logging

logger = logging.getLogger(__name__)

class FacturaSIIRepository:
    
    @staticmethod
    def insertar(factura):
        try:
            conn = get_connection()
            cur = conn.cursor()
            
            cur.execute("""
                INSERT INTO facturas_sii 
                (rut_emisor, rut_receptor, folio, tipo_documento, fecha, monto,
                 codigo_autorizacion, razon_social_emisor, razon_social_receptor,
                 texto_original, usuario, fecha_escaneo, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 
                        NOW() AT TIME ZONE 'America/Santiago',
                        NOW() AT TIME ZONE 'America/Santiago')
                RETURNING id
            """, (
                factura.rut_emisor,
                factura.rut_receptor,
                factura.folio,
                factura.tipo_documento,
                factura.fecha,
                factura.monto,
                factura.codigo_autorizacion,
                factura.razon_social_emisor,
                factura.razon_social_receptor,
                factura.texto_original,
                factura.usuario
            ))
            
            id_factura = cur.fetchone()[0]
            conn.commit()
            cur.close()
            conn.close()
            return id_factura
            
        except Exception as e:
            logger.error(f"Error insertar factura SII: {e}")
            return None
    
    @staticmethod
    def obtener_por_filtro(filtro='todos', fecha_inicio=None, fecha_fin=None):
        try:
            conn, cur = get_cursor()
            
            query = """
                SELECT * FROM facturas_sii
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
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Error obtener facturas SII: {e}")
            return []
    
    @staticmethod
    def obtener_por_folio(folio):
        try:
            conn, cur = get_cursor()
            cur.execute("SELECT * FROM facturas_sii WHERE folio = %s", (folio,))
            row = cur.fetchone()
            cur.close()
            conn.close()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error obtener factura por folio: {e}")
            return None
    
    @staticmethod
    def obtener_por_rut(rut):
        try:
            conn, cur = get_cursor()
            cur.execute("SELECT * FROM facturas_sii WHERE rut_emisor = %s OR rut_receptor = %s", (rut, rut))
            rows = cur.fetchall()
            cur.close()
            conn.close()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error obtener facturas por RUT: {e}")
            return []
