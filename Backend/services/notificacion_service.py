# backend/services/notificacion_service.py
import os
import json
import psycopg2
from pywebpush import webpush, WebPushException

def enviar_notificacion_push(titulo, mensaje, url="/estado", id=None):
    """Envía notificaciones push a todos los dispositivos suscritos"""
    VAPID_PRIVATE_KEY = os.environ.get("VAPID_PRIVATE_KEY", "")
    VAPID_PUBLIC_KEY = os.environ.get("VAPID_PUBLIC_KEY", "")
    VAPID_EMAIL = os.environ.get("VAPID_EMAIL", "admin@dixon.cl")
    
    if not VAPID_PRIVATE_KEY or not VAPID_PUBLIC_KEY:
        print("⚠️ VAPID keys no configuradas")
        return 0
    
    # Cargar suscripciones desde Neon
    try:
        DATABASE_URL = os.environ.get("DATABASE_URL")
        if not DATABASE_URL:
            print("❌ DATABASE_URL no configurada")
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
        print(f"❌ Error cargando suscripciones: {e}")
        return 0
    
    if not suscripciones:
        print("ℹ️ No hay suscripciones")
        return 0
    
    data = {"title": titulo, "body": mensaje, "url": url, "id": id}
    
    enviados = 0
    for sub in suscripciones:
        try:
            webpush(
                subscription_info=sub,
                data=json.dumps(data),
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims={"sub": f"mailto:{VAPID_EMAIL}"}
            )
            enviados += 1
        except WebPushException as e:
            print(f"❌ Error enviando push: {e}")
    
    print(f"📱 Notificaciones enviadas a {enviados} dispositivos")
    return enviados
