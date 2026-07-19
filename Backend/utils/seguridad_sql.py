
# Nuevo archivo: Backend/utils/seguridad_sql.py

import re
from typing import Any, List, Tuple, Union

def sanitizar_sql_valor(valor: Any) -> Any:
    """
    Sanitiza un valor para evitar inyección SQL.
    - Strings: escapa caracteres peligrosos
    - Otros tipos: valida que sean del tipo esperado
    """
    if valor is None:
        return None
    
    if isinstance(valor, str):
        # Eliminar caracteres peligrosos
        valor = re.sub(r'[\'";\\]', '', valor)
        # Limitar longitud
        valor = valor[:500]
        return valor
    
    if isinstance(valor, (int, float, bool)):
        return valor
    
    if isinstance(valor, (list, tuple)):
        return [sanitizar_sql_valor(v) for v in valor]
    
    return str(valor)

def validar_fecha(fecha: str) -> bool:
    """Valida que una fecha tenga formato YYYY-MM-DD"""
    import re
    patron = r'^\d{4}-\d{2}-\d{2}$'
    return bool(re.match(patron, fecha))

def validar_filtro(filtro: str) -> bool:
    """Valida que el filtro sea uno de los permitidos"""
    filtros_permitidos = ['todos', 'hoy', '7d', 'mes', 'anio']
    return filtro in filtros_permitidos

def validar_metodo_pago(metodo: str) -> bool:
    """Valida que el método de pago sea válido"""
    metodos_permitidos = ['efectivo', 'tarjeta', 'transferencia']
    return metodo in metodos_permitidos

def validar_forma_pago(forma: str) -> bool:
    """Valida que la forma de pago sea válida"""
    formas_permitidas = ['efectivo', 'tarjeta', 'transferencia']
    return forma in formas_permitidas
