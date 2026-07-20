# Backend/utils/seguridad.py
import secrets
import hmac
import hashlib
import re
from config import Config
from typing import Any, Dict, List, Optional, Union
from datetime import datetime

# ============================================
# FUNCIONES EXISTENTES
# ============================================

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

# ============================================
# FUNCIONES DE SANITIZACIÓN
# ============================================

def sanitizar_input(texto: Optional[str], max_len: int = 500) -> str:
    """
    Sanitiza un string eliminando caracteres peligrosos
    
    Args:
        texto: String a sanitizar
        max_len: Longitud máxima permitida
    
    Returns:
        String sanitizado
    """
    if not texto:
        return ''
    
    # Eliminar etiquetas HTML
    texto = re.sub(r'<[^>]+>', '', texto)
    
    # Eliminar caracteres peligrosos para SQL
    texto = re.sub(r'[\'";\\]', '', texto)
    
    # Eliminar caracteres de control
    texto = re.sub(r'[\x00-\x1f\x7f]', '', texto)
    
    # Limitar longitud
    return texto[:max_len].strip()

def sanitizar_patente(patente: Optional[str]) -> str:
    """
    Limpia y formatea una patente
    
    Args:
        patente: String con la patente
    
    Returns:
        Patente formateada (mayúsculas, sin caracteres especiales)
    """
    if not patente:
        return ''
    
    # Solo letras y números
    patente = re.sub(r'[^A-Za-z0-9]', '', patente)
    
    # Mayúsculas y limitar longitud
    return patente.upper()[:10]

def sanitizar_numero(valor: Any, default: float = 0, min_val: float = None, max_val: float = None) -> float:
    """
    Convierte y valida un valor numérico
    
    Args:
        valor: Valor a convertir
        default: Valor por defecto si no se puede convertir
        min_val: Valor mínimo permitido
        max_val: Valor máximo permitido
    
    Returns:
        Número validado
    """
    try:
        num = float(valor)
        
        if min_val is not None and num < min_val:
            num = min_val
        if max_val is not None and num > max_val:
            num = max_val
            
        return num
    except (ValueError, TypeError):
        return default

def sanitizar_booleano(valor: Any) -> bool:
    """
    Convierte un valor a booleano
    
    Args:
        valor: Valor a convertir
    
    Returns:
        Booleano
    """
    if isinstance(valor, bool):
        return valor
    if isinstance(valor, str):
        return valor.lower() in ('true', '1', 'yes', 'si', 'sí')
    return bool(valor)

def sanitizar_dict(data: Dict) -> Dict:
    """
    Sanitiza recursivamente todos los valores de un diccionario
    
    Args:
        data: Diccionario a sanitizar
    
    Returns:
        Diccionario sanitizado
    """
    if not data:
        return {}
    
    sanitizado = {}
    for key, value in data.items():
        if isinstance(value, str):
            sanitizado[key] = sanitizar_input(value)
        elif isinstance(value, dict):
            sanitizado[key] = sanitizar_dict(value)
        elif isinstance(value, list):
            sanitizado[key] = [
                sanitizar_dict(item) if isinstance(item, dict)
                else sanitizar_input(item) if isinstance(item, str)
                else item
                for item in value
            ]
        else:
            sanitizado[key] = value
    
    return sanitizado

# ============================================
# FUNCIONES DE VALIDACIÓN
# ============================================

def validar_filtro(filtro: str) -> bool:
    """
    Valida que el filtro sea uno de los permitidos
    
    Args:
        filtro: String con el filtro
    
    Returns:
        True si es válido, False en caso contrario
    """
    filtros_permitidos = ['todos', 'hoy', '7d', 'mes', 'anio', 'semana']
    return filtro in filtros_permitidos

def validar_metodo_pago(metodo: str) -> bool:
    """
    Valida que el método de pago sea válido
    
    Args:
        metodo: String con el método de pago
    
    Returns:
        True si es válido, False en caso contrario
    """
    metodos_permitidos = ['efectivo', 'tarjeta', 'transferencia', 'debito', 'credito']
    return metodo in metodos_permitidos

def validar_estado(estado: str) -> bool:
    """
    Valida que el estado sea válido
    
    Args:
        estado: String con el estado
    
    Returns:
        True si es válido, False en caso contrario
    """
    estados_permitidos = ['pendiente', 'pagado', 'reparado', 'derivado', 'cancelado']
    return estado in estados_permitidos

def validar_fecha(fecha: str) -> bool:
    """
    Valida que una fecha tenga formato YYYY-MM-DD
    
    Args:
        fecha: String con la fecha
    
    Returns:
        True si es válida, False en caso contrario
    """
    if not fecha:
        return False
    patron = r'^\d{4}-\d{2}-\d{2}$'
    return bool(re.match(patron, fecha))

def validar_hora(hora: str) -> bool:
    """
    Valida que una hora tenga formato HH:MM:SS
    
    Args:
        hora: String con la hora
    
    Returns:
        True si es válida, False en caso contrario
    """
    if not hora:
        return False
    patron = r'^\d{2}:\d{2}:\d{2}$'
    return bool(re.match(patron, hora))

def validar_email(email: str) -> bool:
    """
    Valida que el email tenga formato correcto
    
    Args:
        email: String con el email
    
    Returns:
        True si es válido, False en caso contrario
    """
    if not email:
        return False
    patron = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(patron, email))

def validar_telefono(telefono: str) -> bool:
    """
    Valida que el teléfono tenga formato correcto
    
    Args:
        telefono: String con el teléfono
    
    Returns:
        True si es válido, False en caso contrario
    """
    if not telefono:
        return False
    patron = r'^\+?[0-9\s\-]{8,15}$'
    return bool(re.match(patron, telefono.strip()))
