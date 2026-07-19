# Backend/utils/fecha_utils.py
from datetime import datetime, date, time, timedelta
import pytz
from config import Config
from typing import Tuple, Optional

def now_santiago() -> datetime:
    """Retorna datetime actual en zona horaria Chile"""
    tz = pytz.timezone(Config.TIMEZONE)
    return datetime.now(tz)

def get_fecha_chile() -> date:
    """Retorna fecha actual en zona horaria Chile"""
    return now_santiago().date()

def get_hora_chile() -> time:
    """Retorna hora actual en zona horaria Chile"""
    return now_santiago().time()

def get_fecha_hora_chile() -> Tuple[date, time]:
    """Retorna fecha y hora actual en zona horaria Chile"""
    ahora = now_santiago()
    return ahora.date(), ahora.time()

def formatear_fecha(fecha, formato='%d/%m/%Y'):
    """Formatea una fecha a string"""
    if not fecha:
        return ''
    if isinstance(fecha, str):
        try:
            fecha = datetime.strptime(fecha, '%Y-%m-%d')
        except:
            return fecha
    return fecha.strftime(formato)

def formatear_hora(hora):
    """Formatea una hora a string"""
    if not hora:
        return ''
    if isinstance(hora, time):
        return hora.strftime('%H:%M')
    return str(hora)[:5]

def formatear_fecha_espanol(fecha: date) -> str:
    """Formatea una fecha en español: 'Lunes 1 de Enero 2024'"""
    if not fecha:
        return ''
    dias = {0: 'Lunes', 1: 'Martes', 2: 'Miércoles', 3: 'Jueves', 
            4: 'Viernes', 5: 'Sábado', 6: 'Domingo'}
    meses = {1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril', 5: 'Mayo', 6: 'Junio',
             7: 'Julio', 8: 'Agosto', 9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'}
    return f"{dias.get(fecha.weekday(), '')} {fecha.day} de {meses.get(fecha.month, '')} {fecha.year}"
