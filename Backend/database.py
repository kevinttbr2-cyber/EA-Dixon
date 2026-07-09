import psycopg2
import psycopg2.extras
from config import Config

def get_connection():
    """Obtiene conexión a Neon con SSL requerido"""
    if not Config.DATABASE_URL:
        raise Exception("❌ DATABASE_URL no configurada")
    return psycopg2.connect(Config.DATABASE_URL, sslmode='require')

def get_cursor():
    """Obtiene un cursor con DictCursor para resultados como diccionarios"""
    conn = get_connection()
    return conn, conn.cursor(cursor_factory=psycopg2.extras.DictCursor)