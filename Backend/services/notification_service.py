import os
import json
import logging
import psycopg2
from pywebpush import webpush, WebPushException

logger = logging.getLogger(__name__)

def enviar_notificacion_push(titulo, mensaje, url="/estado", id=None):
    """Envía notificaciones push a todos los dispositivos suscritos"""
    
    VAPID_PRIVATE_KEY = os.environ.get("VAPID_PRIVATE_KEY", "")
    VAPID_PUBLIC_KEY = os.environ.get("VAPID_PUBLIC_KEY", "")
    VAPID_EMAIL = os.environ.get("VAPID_EMAIL", "admin@dixon.cl")
    
    print(f"🔑 VAPID_PRIVATE_KEY configurada: {'✅' if VAPID_PRIVATE_KEY else '❌'}")
    print(f"🔑 VAPID_PUBLIC_KEY configurada: {'✅' if VAPID_PUBLIC_KEY else '❌'}")
    
    if not VAPID_PRIVATE_KEY or not VAPID_PUBLIC_KEY:
        print("⚠️ VAPID keys no configuradas")
        return 0
    
    # Cargar suscripciones desde Neon
    try:
        DATABASE_URL = os.environ.get("DATABASE_URL")
        if not DATABASE_URL:
            print("❌ DATABASE_URL no configurada")
            return 0
        
        print(f"📡 Conectando a base de datos...")
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        # ✅ VERIFICAR QUE LA TABLA EXISTE
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'push_subscriptions'
            )
        """)
        table_exists = cur.fetchone()[0]
        print(f"📋 Tabla push_subscriptions existe: {table_exists}")
        
        if not table_exists:
            print("❌ La tabla no existe. Creándola...")
            cur.execute("""
                CREATE TABLE push_subscriptions (
                    id SERIAL PRIMARY KEY,
                    endpoint TEXT NOT NULL UNIQUE,
                    auth_key TEXT NOT NULL,
                    p256dh_key TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
            print("✅ Tabla creada")
        
        # ✅ CONTAR SUSCRIPCIONES
        cur.execute("SELECT COUNT(*) FROM push_subscriptions")
        count = cur.fetchone()[0]
        print(f"📱 Suscripciones en BD: {count}")
        
        # ✅ OBTENER TODAS LAS SUSCRIPCIONES
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
        
        print(f"📱 Suscripciones cargadas: {len(suscripciones)}")
        
    except Exception as e:
        print(f"❌ Error cargando suscripciones: {e}")
        import traceback
        traceback.print_exc()
        return 0
    
    if not suscripciones:
        print("ℹ️ No hay suscripciones push")
        return 0
    
    data = {
        "title": titulo,
        "body": mensaje,
        "url": url,
        "id": id
    }
    
    enviados = 0
    for idx, sub in enumerate(suscripciones, 1):
        try:
            print(f"📤 Enviando notificación {idx}/{len(suscripciones)}...")
            webpush(
                subscription_info=sub,
                data=json.dumps(data),
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims={"sub": f"mailto:{VAPID_EMAIL}"},
                timeout=30
            )
            enviados += 1
            print(f"✅ Notificación {idx} enviada")
        except WebPushException as e:
            print(f"❌ Error WebPush {idx}: {e}")
            if hasattr(e, 'response') and e.response:
                print(f"📄 Status: {e.response.status_code}")
                print(f"📄 Respuesta: {e.response.text}")
        except Exception as e:
            print(f"❌ Error inesperado {idx}: {e}")
    
    print(f"📱 Notificaciones enviadas: {enviados} de {len(suscripciones)}")
    return enviados
