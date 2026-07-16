# backend/services/notification_service.py
import os
import json
import logging
import psycopg2
import base64
from pywebpush import webpush, WebPushException

logger = logging.getLogger(__name__)

def enviar_notificacion_push(titulo, mensaje, url="/estado", id=None):
    """Envía notificaciones push a todos los dispositivos suscritos"""
    
    VAPID_PRIVATE_KEY = os.environ.get("VAPID_PRIVATE_KEY", "")
    VAPID_PUBLIC_KEY = os.environ.get("VAPID_PUBLIC_KEY", "")
    VAPID_EMAIL = os.environ.get("VAPID_EMAIL", "admin@dixon.cl")
    
    logger.info(f"🔑 VAPID_PRIVATE_KEY longitud: {len(VAPID_PRIVATE_KEY)}")
    logger.info(f"🔑 VAPID_PUBLIC_KEY longitud: {len(VAPID_PUBLIC_KEY)}")
    
    if not VAPID_PRIVATE_KEY or not VAPID_PUBLIC_KEY:
        logger.warning("⚠️ VAPID keys no configuradas")
        return 0
    
    # Cargar suscripciones desde Neon
    try:
        DATABASE_URL = os.environ.get("DATABASE_URL")
        if not DATABASE_URL:
            logger.error("❌ DATABASE_URL no configurada")
            return 0
        
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("SELECT endpoint, auth_key, p256dh_key FROM push_subscriptions")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        suscripciones = []
        for row in rows:
            suscripciones.append({
                'endpoint': row[0],
                'keys': {
                    'auth': row[1],
                    'p256dh': row[2]
                }
            })
    except Exception as e:
        logger.error(f"❌ Error cargando suscripciones: {e}")
        return 0
    
    if not suscripciones:
        logger.info("ℹ️ No hay suscripciones push")
        return 0
    
    data = {
        "title": titulo,
        "body": mensaje,
        "url": url,
        "id": id
    }
    
    enviados = 0
    for sub in suscripciones:
        try:
            # ✅ IMPORTANTE: La clave privada debe pasarse como string directamente
            webpush(
                subscription_info=sub,
                data=json.dumps(data),
                vapid_private_key=VAPID_PRIVATE_KEY,  # ✅ String directo
                vapid_claims={
                    "sub": f"mailto:{VAPID_EMAIL}"
                }
            )
            enviados += 1
            logger.info(f"✅ Notificación enviada exitosamente")
        except WebPushException as e:
            logger.error(f"❌ Error enviando push: {e}")
            if hasattr(e, 'response') and e.response:
                logger.error(f"Detalles: {e.response.text}")
        except Exception as e:
            logger.error(f"❌ Error inesperado: {e}")
    
    logger.info(f"📱 Notificaciones enviadas a {enviados} dispositivos")
    return enviados
