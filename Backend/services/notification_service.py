# Backend/services/notification_service.py
import os
import json
import logging
import psycopg2
from pywebpush import webpush, WebPushException
from config import Config

logger = logging.getLogger(__name__)

def enviar_notificacion_push(titulo, mensaje, url="/estado", id=None):
    """Envía notificaciones push a todos los dispositivos suscritos"""
    
    VAPID_PRIVATE_KEY = os.environ.get("VAPID_PRIVATE_KEY", "")
    VAPID_PUBLIC_KEY = os.environ.get("VAPID_PUBLIC_KEY", "")
    VAPID_EMAIL = os.environ.get("VAPID_EMAIL", "admin@dixon.cl")
    
    if not VAPID_PRIVATE_KEY or not VAPID_PUBLIC_KEY:
        logger.warning("VAPID keys no configuradas")
        return 0
    
    try:
        conn = psycopg2.connect(Config.DATABASE_URL)
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
        
        if not suscripciones:
            logger.info("No hay suscripciones push")
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
                webpush(
                    subscription_info=sub,
                    data=json.dumps(data),
                    vapid_private_key=VAPID_PRIVATE_KEY,
                    vapid_claims={
                        "sub": f"mailto:{VAPID_EMAIL}"
                    },
                    timeout=30
                )
                enviados += 1
            except WebPushException as e:
                logger.error(f"Error WebPush: {e}")
            except Exception as e:
                logger.error(f"Error inesperado: {e}")
        
        logger.info(f"Notificaciones enviadas: {enviados} de {len(suscripciones)}")
        return enviados
        
    except Exception as e:
        logger.error(f"Error enviando notificaciones: {e}")
        return 0
