import os
import psycopg2
import psycopg2.extras
import time

# ============================
# CONFIGURAR ZONA HORARIA (Chile)
# ============================
# Establecer zona horaria a Chile (UTC-3)
os.environ['TZ'] = 'America/Santiago'
time.tzset()


def get_connection():
    """Obtiene conexión a Neon con SSL requerido y zona horaria Chile"""
    DATABASE_URL = os.environ.get("DATABASE_URL")
    
    if not DATABASE_URL:
        raise Exception("❌ DATABASE_URL no configurada")
    
    try:
        # Conexión directa con la URL completa y SSL requerido
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        
        # ✅ ESTABLECER ZONA HORARIA EN LA CONEXIÓN
        cur = conn.cursor()
        cur.execute("SET TIME ZONE 'America/Santiago';")
        cur.close()
        
        return conn
    except Exception as e:
        print(f"❌ Error conectando a Neon: {e}")
        raise

def get_cursor():
    """Obtiene un cursor con DictCursor para resultados como diccionarios"""
    conn = get_connection()
    return conn, conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
