# Backend/database.py
import os
import psycopg2
import psycopg2.extras
import time
from config import Config
import logging

logger = logging.getLogger(__name__)

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
        logger.error(f"Error conectando a Neon: {e}")
        raise

def get_cursor():
    """Obtiene un cursor con DictCursor para resultados como diccionarios"""
    conn = get_connection()
    return conn, conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

# ============================================
# 🆕 NUEVA FUNCIÓN AGREGADA
# ============================================

def ejecutar_consulta(query, params=None):
    """
    Ejecuta una consulta SQL con parámetros y retorna los resultados
    
    Args:
        query: Consulta SQL con placeholders %s
        params: Tupla de parámetros
    
    Returns:
        Lista de diccionarios con los resultados (para SELECT)
        o dict con rowcount (para INSERT/UPDATE/DELETE)
    """
    try:
        conn, cur = get_cursor()
        cur.execute(query, params or ())
        
        if query.strip().upper().startswith(('SELECT', 'SHOW')):
            results = [dict(row) for row in cur.fetchall()]
        else:
            conn.commit()
            results = {'rowcount': cur.rowcount}
        
        cur.close()
        conn.close()
        return results
    except Exception as e:
        logger.error(f"Error ejecutando consulta: {e}")
        raise
