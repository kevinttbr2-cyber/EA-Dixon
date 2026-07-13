from repositories.pago_repo import PagoRepository
from models.pago import Pago
from datetime import datetime

class PagoService:
    
    @staticmethod
    def crear_pago(data):
        pago = Pago(
            nombre=data.get('nombre'),
            fecha=datetime.now().strftime("%Y-%m-%d"),
            hora=datetime.now().strftime("%H:%M:%S"),
            patente=data.get('patente'),
            marca=data.get('marca'),
            modelo=data.get('modelo'),
            usuario=data.get('usuario'),
            observaciones_cliente=data.get('observaciones', ''),
            telefono=data.get('telefono', ''),
            flota=data.get('flota'),
            frecuente=bool(data.get('flota')),
            kilometraje=data.get('kilometraje', 0),
            estado='pendiente'
        )
        return PagoRepository.insertar(pago)
    
    @staticmethod
    def procesar_pago(id_reg, data):
        pago = PagoRepository.obtener_por_id(id_reg)
        if not pago:
            return None
        
        pago.monto = data.get('monto', 0)
        pago.estado = 'pagado'
        pago.estado_ot = data.get('estado_ot', 'Pendiente')
        pago.observaciones_pago = data.get('observaciones_pago', '')
        pago.hora_pago = datetime.now().strftime("%H:%M:%S")
        pago.atendido_por = data.get('atendido_por', 'Técnico')
        pago.diagnostico = data.get('diagnostico', '')
        pago.reparacion = data.get('reparacion', 'Reparación realizada')
        pago.resultado = data.get('resultado', 'reparado')
        pago.tiempo_estimado = data.get('tiempo_estimado', '00:00:00')
        pago.forma_pago = data.get('forma_pago', 'efectivo')
        
        if PagoRepository.actualizar(id_reg, pago):
            return pago
        return None
    
    @staticmethod
    def obtener_pendientes():
        return PagoRepository.obtener_pendientes()
    
    @staticmethod
    def obtener_pagados_hoy():
        return PagoRepository.obtener_pagados_hoy()
    
    @staticmethod
    def obtener_todos_pagados():
        """Obtiene todos los pagos con estado 'pagado'"""
        return PagoRepository.obtener_todos_pagados()
    
    @staticmethod
    def obtener_por_id(id_reg):
        return PagoRepository.obtener_por_id(id_reg)
    
    @staticmethod
    def obtener_flotas():
        return PagoRepository.obtener_flotas()
