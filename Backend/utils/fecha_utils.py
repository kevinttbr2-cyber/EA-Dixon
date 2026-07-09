from datetime import datetime
import pytz
from config import Config

def now_santiago():
    tz = pytz.timezone(Config.TIMEZONE)
    return datetime.now(tz)

def formatear_fecha(fecha, formato='%d/%m/%Y'):
    if not fecha:
        return ''
    return fecha.strftime(formato)

def formatear_hora(hora):
    if not hora:
        return ''
    return hora[:5] if len(hora) >= 5 else hora