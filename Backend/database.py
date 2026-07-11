import os
import psycopg2
import psycopg2.extras

def get_connection():
    """Obtiene conexión a Neon con SSL requerido"""
    DATABASE_URL = os.environ.get("DATABASE_URL")
    
    if not DATABASE_URL:
        raise Exception("❌ DATABASE_URL no configurada")
    
    try:
        # Conexión directa con la URL completa y SSL requerido
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        return conn
    except Exception as e:
        print(f"❌ Error conectando a Neon: {e}")
        raise

def get_cursor():
    """Obtiene un cursor con DictCursor para resultados como diccionarios"""
    conn = get_connection()
    return conn, conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
def obtener_historial_descargas(limite=100):
    """Obtiene el historial de descargas con firma HMAC para cada registro"""
    try:
        PDF_SECRET_KEY = os.environ.get("PDF_SECRET_KEY", "mi_clave_secreta_para_pdfs_2024")
        
        conn = get_connection()
        cur = conn.cursor()
        
        # Primero obtener la firma para cada registro
        cur.execute("""
            SELECT 
                a.id,
                a.id_registro,
                a.usuario,
                a.rol,
                a.tipo,
                a.fecha,
                a.ip,
                p.nombre as cliente,
                p.patente,
                p.marca,
                p.modelo,
                p.monto
            FROM auditoria_descargas a
            LEFT JOIN pagos p ON a.id_registro = p.id
            ORDER BY a.fecha DESC
            LIMIT %s
        """, (limite,))
        
        resultados = cur.fetchall()
        cur.close()
        conn.close()
        
        # Convertir a lista de diccionarios con firma
        lista_resultados = []
        for row in resultados:
            item = {
                'id': row[0],
                'id_registro': row[1],
                'usuario': row[2],
                'rol': row[3],
                'tipo': row[4],
                'fecha': row[5],
                'ip': row[6],
                'cliente': row[7],
                'patente': row[8],
                'marca': row[9],
                'modelo': row[10],
                'monto': row[11]
            }
            
            # Generar firma HMAC para el enlace seguro
            if item['id_registro']:
                firma = hmac.new(
                    PDF_SECRET_KEY.encode(),
                    str(item['id_registro']).encode(),
                    hashlib.sha256
                ).hexdigest()[:16]
                item['firma'] = firma
            else:
                item['firma'] = ''
            
            lista_resultados.append(item)
        
        return lista_resultados
        
    except Exception as e:
        print(f"❌ Error al obtener historial: {e}")
        import traceback
        traceback.print_exc()
        return []
