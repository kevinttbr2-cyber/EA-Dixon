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
