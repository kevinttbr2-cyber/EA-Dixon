# Backend/repositories/__init__.py
from .usuario_repo import UsuarioRepository
from .pago_repo import PagoRepository
from .base_repository import BaseRepository

__all__ = ['UsuarioRepository', 'PagoRepository', 'BaseRepository']
