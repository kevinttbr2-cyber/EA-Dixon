# Backend/services/pago_service.py
from repositories.pago_repo import PagoRepository
from models.pago import Pago
from datetime import datetime
from utils.fecha_utils import get_fecha_chile, get_hora_chile, now_santiago
from utils.seguridad import sanitizar_input, sanitizar_patente, sanitizar_numero, validar_filtro
import logging

logger = logging.getLogger(__name__)

class PagoService:
    
    @staticmethod
    def crear_pago(data):
        try:
            fecha = data.get('fecha') or get_fecha_chile().strftime('%Y-%m-%d')
            hora = data.get('hora') or get_hora_chile().strftime('%H:%M:%S')
            
            pago = Pago(
                nombre=data.get('nombre'),
                fecha=fecha,
                hora=hora,
                patente=data.get('patente'),
                marca=data.get('marca'),
                modelo=data.get('modelo'),
                usuario=data.get('usuario'),
                observaciones_cliente=data.get('observaciones', ''),
                telefono=data.get('telefono', ''),
                flota=data.get('flota'),
                frecuente=bool(data.get('flota')),
                kilometraje=data.get('kilometraje', 0),
                anio=data.get('anio', 0),
                estado='pendiente',
                estado_pago='pendiente'
            )
            return PagoRepository.insertar(pago)
        except Exception as e:
            logger.error(f"Error en crear_pago: {e}")
            return None
    
    @staticmethod
    def procesar_pago(id_reg, data):
        try:
            pago = PagoRepository.obtener_por_id(id_reg)
            if not pago:
                return None
            
            pago.monto = data.get('monto', 0)
            pago.estado = 'pagado'
            pago.estado_pago = 'pagado'
            pago.observaciones_pago = data.get('observaciones_pago', '')
            pago.hora_pago = get_hora_chile().strftime("%H:%M:%S")
            pago.atendido_por = data.get('atendido_por', 'Técnico')
            pago.diagnostico = data.get('diagnostico', '')
            pago.reparacion = data.get('reparacion', 'Reparación realizada')
            pago.resultado = data.get('resultado', 'reparado')
            pago.tiempo_estimado = data.get('tiempo_estimado', '00:00:00')
            pago.forma_pago = data.get('forma_pago', 'efectivo')
            pago.fecha_pago_real = get_fecha_chile()
            
            if PagoRepository.actualizar(id_reg, pago):
                return pago
            return None
        except Exception as e:
            logger.error(f"Error en procesar_pago: {e}")
            return None
    
    @staticmethod
    def obtener_pendientes():
        return PagoRepository.obtener_pendientes()
    
    @staticmethod
    def obtener_pagados_hoy():
        return PagoRepository.obtener_pagados_hoy()
    
    @staticmethod
    def obtener_todos_pagados():
        return PagoRepository.obtener_todos_pagados()
    
    @staticmethod
    def obtener_por_id(id_reg):
        return PagoRepository.obtener_por_id(id_reg)
    
    @staticmethod
    def obtener_flotas():
        return PagoRepository.obtener_flotas()
    
    # ============================================
    # 🆕 NUEVAS FUNCIONES AGREGADAS
    # ============================================
    
    @staticmethod
    def obtener_flotas_pendientes():
        """Obtiene flotas pendientes de pago"""
        return PagoRepository.obtener_flotas_pendientes()
    
    @staticmethod
    def obtener_pagados_por_filtro(filtro, fecha):
        """Obtiene pagos pagados según filtro"""
        return PagoRepository.obtener_pagados_por_filtro(filtro, fecha)
    
    @staticmethod
    def verificar_duplicado(nombre, patente):
        """Verifica si existe un duplicado"""
        return PagoRepository.verificar_duplicado(nombre, patente)
    
    @staticmethod
    def obtener_balance_ventas(filtro, fecha):
        """Obtiene datos para el balance de ventas"""
        return PagoRepository.obtener_balance_ventas(filtro, fecha)
