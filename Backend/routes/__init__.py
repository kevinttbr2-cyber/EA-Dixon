from routes.auth_routes import auth_bp
from routes.pago_routes import pago_bp
from routes.catalogo_routes import catalogo_bp
from routes.flota_routes import flota_bp
from routes.pdf_routes import pdf_bp
from routes.auditoria_routes import auditoria_bp

__all__ = ['auth_bp', 'pago_bp', 'catalogo_bp', 'flota_bp', 'pdf_bp', 'auditoria_bp']