# Backend/services/factura_sii_service.py
from repositories.factura_sii_repo import FacturaSIIRepository
from models.factura_sii import FacturaSII
import logging

logger = logging.getLogger(__name__)

class FacturaSIIService:
    
    @staticmethod
    def registrar_factura(data):
        try:
            factura = FacturaSII(
                rut_emisor=data.get('rut_emisor'),
                rut_receptor=data.get('rut_receptor'),
                folio=data.get('folio'),
                tipo_documento=data.get('tipo_documento', 'Factura'),
                fecha=data.get('fecha'),
                monto=data.get('monto', 0),
                codigo_autorizacion=data.get('codigo_autorizacion'),
                razon_social_emisor=data.get('razon_social_emisor'),
                razon_social_receptor=data.get('razon_social_receptor'),
                texto_original=data.get('texto_original'),
                usuario=data.get('usuario', 'Sistema')
            )
            return FacturaSIIRepository.insertar(factura)
        except Exception as e:
            logger.error(f"Error en registrar_factura: {e}")
            return None
    
    @staticmethod
    def obtener_facturas(filtro='todos', fecha_inicio=None, fecha_fin=None):
        return FacturaSIIRepository.obtener_por_filtro(filtro, fecha_inicio, fecha_fin)
    
    @staticmethod
    def obtener_por_folio(folio):
        return FacturaSIIRepository.obtener_por_folio(folio)
    
    @staticmethod
    def obtener_por_rut(rut):
        return FacturaSIIRepository.obtener_por_rut(rut)
