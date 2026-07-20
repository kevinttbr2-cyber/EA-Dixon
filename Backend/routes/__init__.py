# Backend/routes/__init__.py
from .auth_routes import auth_bp
from .pago_routes import pago_bp
from .catalogo_routes import catalogo_bp
from .flota_routes import flota_bp
from .pdf_routes import pdf_bp
from .auditoria_routes import auditoria_bp
from .gasto_routes import gasto_bp
from .cierre_routes import cierre_bp
from .deudor_routes import deudor_bp
from .venta_routes import venta_bp
from .export_routes import export_bp
from .categoria_routes import categoria_bp
from .reporte_routes import reporte_bp
from .scanner_routes import scanner_bp

__all__ = [
    'auth_bp', 'pago_bp', 'catalogo_bp', 'flota_bp', 
    'pdf_bp', 'auditoria_bp', 'gasto_bp', 'cierre_bp',
    'deudor_bp', 'venta_bp', 'export_bp', 'categoria_bp',
    'reporte_bp', 'scanner_bp'
]
