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
        # 1. obtener_pagados_con_filtro()
@staticmethod
def obtener_pagados_con_filtro(filtro, fecha):
    """Obtiene pagos pagados con filtro para el balance general"""
    return PagoRepository.obtener_pagados_con_filtro(filtro, fecha)

# 2. obtener_flotas_disponibles()
@staticmethod
def obtener_flotas_disponibles():
    """Obtiene todas las flotas registradas"""
    return PagoRepository.obtener_flotas_disponibles()

# 3. obtener_balance_completo()
@staticmethod
def obtener_balance_completo(filtro, fecha):
    """Obtiene el balance completo con totales"""
    return PagoRepository.obtener_balance_completo(filtro, fecha)

# 4. actualizar_repuestos_venta()
@staticmethod
def actualizar_repuestos_venta(id_reg, data):
    """Actualiza solo los repuestos y costos de una venta"""
    return PagoRepository.actualizar_repuestos_venta(id_reg, data)

# 5. obtener_dashboard_data()
@staticmethod
def obtener_dashboard_data(fecha_desde):
    """Obtiene datos para el dashboard"""
    return PagoRepository.obtener_dashboard_data(fecha_desde)

# 6. obtener_meses_disponibles() - Para el dashboard
@staticmethod
def obtener_meses_disponibles():
    """Obtiene los meses con datos para el dashboard"""
    try:
        conn, cur = get_cursor()
        cur.execute("""
            SELECT DISTINCT 
                EXTRACT(YEAR FROM fecha) as anio,
                EXTRACT(MONTH FROM fecha) as mes
            FROM pagos 
            WHERE estado = 'pagado' 
            AND estado_pago = 'pagado'
            AND fecha IS NOT NULL
            ORDER BY anio DESC, mes DESC
        """)
        meses = []
        for row in cur.fetchall():
            meses.append({
                'anio': int(row[0]),
                'mes': int(row[1])
            })
        cur.close()
        conn.close()
        return meses
    except Exception as e:
        logger.error(f"Error obtener meses disponibles: {e}")
        return []

# 2. ❌ FALTA: obtener_flotas_pendientes_count()
@staticmethod
def obtener_flotas_pendientes_count():
    """Obtiene el número de flotas pendientes de pago"""
    return PagoRepository.obtener_flotas_pendientes_count()

# 3. ❌ FALTA: obtener_gastos_balance()
@staticmethod
def obtener_gastos_balance(fecha_inicio, fecha_fin):
    """Obtiene gastos para el balance"""
    return PagoRepository.obtener_gastos_balance(fecha_inicio, fecha_fin)

# 4. ❌ FALTA: obtener_cierre_caja()
@staticmethod
def obtener_cierre_caja(fecha):
    """Obtiene el cierre de caja para una fecha"""
    return PagoRepository.obtener_cierre_caja(fecha)

# 5. ❌ FALTA: crear_cierre_caja()
@staticmethod
def crear_cierre_caja(fecha, efectivo_inicial):
    """Crea un nuevo cierre de caja"""
    return PagoRepository.crear_cierre_caja(fecha, efectivo_inicial)

# 6. ❌ FALTA: cerrar_cierre_caja()
@staticmethod
def cerrar_cierre_caja(fecha, data):
    """Cierra un cierre de caja"""
    return PagoRepository.cerrar_cierre_caja(fecha, data)

# 7. ❌ FALTA: obtener_historial_cierres()
@staticmethod
def obtener_historial_cierres(limit=30):
    """Obtiene el historial de cierres de caja"""
    return PagoRepository.obtener_historial_cierres(limit)

# 8. ❌ FALTA: obtener_repuestos_con_stock()
@staticmethod
def obtener_repuestos_con_stock(stock_minimo=5, proveedor=None):
    """Obtiene repuestos con stock bajo"""
    return PagoRepository.obtener_repuestos_con_stock(stock_minimo, proveedor)

# 9. ❌ FALTA: obtener_proveedores_repuestos()
@staticmethod
def obtener_proveedores_repuestos():
    """Obtiene la lista de proveedores de repuestos"""
    return PagoRepository.obtener_proveedores_repuestos()
