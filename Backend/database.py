# Backend/database.py
import os
import psycopg2
import psycopg2.extras
import time
from config import Config

# Establecer zona horaria a Chile
os.environ['TZ'] = 'America/Santiago'
time.tzset()

def get_connection():
    """Obtiene conexión a Neon con SSL requerido y zona horaria Chile"""
    try:
        conn = psycopg2.connect(Config.DATABASE_URL, sslmode='require')
        
        # Establecer zona horaria en la conexión
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
