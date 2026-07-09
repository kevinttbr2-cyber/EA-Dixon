import secrets
import hmac
import hashlib
from config import Config

def generar_csrf():
    return secrets.token_hex(32)

def verificar_csrf(token_recibido, token_guardado):
    if not token_recibido or not token_guardado:
        return False
    return hmac.compare_digest(token_recibido, token_guardado)

def generar_firma_pdf(id_reg):
    return hmac.new(
        Config.PDF_SECRET_KEY.encode(),
        str(id_reg).encode(),
        hashlib.sha256
    ).hexdigest()[:16]

def verificar_firma_pdf(id_reg, firma):
    return firma == generar_firma_pdf(id_reg)