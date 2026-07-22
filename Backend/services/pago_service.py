# Backend/services/pago_service.py
from repositories.pago_repo import PagoRepository
from models.pago import Pago
from datetime import datetime, timedelta
from utils.fecha_utils import get_fecha_chile, get_hora_chile, now_santiago
from utils.seguridad import sanitizar_input, sanitizar_patente, sanitizar_numero, validar_filtro
import logging

logger = logging.getLogger(__name__)

class PagoService:
    
    # ============================================
    # FUNCIONES CRUD BÁSICAS
    # ============================================
    
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
                estado_pago='pendiente',
                tipo_venta=data.get('tipo_venta', 'servicio')
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
                logger.error(f"❌ Pago ID {id_reg} no encontrado")
                return None
        
            # Asignar valores
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
            pago.fecha_pago = get_fecha_chile()  # ✅ Cambiar a fecha_pago (sin _real)
        
        # Log para depuración
            logger.info(f"📝 Procesando pago ID {id_reg}: Monto=${pago.monto}, Atendido por={pago.atendido_por}")
        
            if PagoRepository.actualizar(id_reg, pago):
                logger.info(f"✅ Pago ID {id_reg} actualizado correctamente")
                return pago
        
            logger.error(f"❌ Error al actualizar pago ID {id_reg} en el repositorio")
            return None
        
        except Exception as e:
            logger.error(f"❌ Error en procesar_pago ID {id_reg}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    @staticmethod
    def eliminar_pago(id_reg):
        """Elimina un pago por ID"""
        return PagoRepository.eliminar(id_reg)
    
    # ============================================
    # FUNCIONES DE CONSULTA
    # ============================================
    
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
    # FUNCIONES PARA FILTROS Y BALANCES
    # ============================================
    
    @staticmethod
    def obtener_pagados_por_filtro(filtro, fecha):
        """Obtiene pagos pagados según filtro"""
        return PagoRepository.obtener_pagados_por_filtro(filtro, fecha)
    
    @staticmethod
    def obtener_balance_completo(filtro, fecha):
        """Obtiene el balance completo con totales"""
        return PagoRepository.obtener_balance_completo(filtro, fecha)
    
    @staticmethod
    def obtener_balance_ventas(filtro, fecha):
        """Obtiene datos para el balance de ventas con gastos incluidos"""
        try:
            from database import get_cursor
            
            if not validar_filtro(filtro):
                filtro = 'todos'
            
            hoy = get_fecha_chile()
            
            # 🔥 CALCULAR FECHAS EN ZONA CHILE
            if filtro == 'hoy':
                fecha_inicio = hoy.strftime('%Y-%m-%d')
                fecha_fin = hoy.strftime('%Y-%m-%d')
            elif filtro == '7d':
                fecha_inicio = (hoy - timedelta(days=7)).strftime('%Y-%m-%d')
                fecha_fin = hoy.strftime('%Y-%m-%d')
            elif filtro == 'mes':
                fecha_inicio = (hoy - timedelta(days=30)).strftime('%Y-%m-%d')
                fecha_fin = hoy.strftime('%Y-%m-%d')
            else:
                fecha_inicio = '2020-01-01'
                fecha_fin = hoy.strftime('%Y-%m-%d')
            
            conn, cur = get_cursor()
            
            # ============================================
            # 1. OBTENER VENTAS (usando fecha en zona Chile)
            # ============================================
            query_ventas = """
                SELECT 
                    *,
                    COALESCE(descuento_aplicado, 0) as descuento_aplicado,
                    COALESCE(costo_repuestos_real, 0) as costo_repuestos_real,
                    COALESCE(costo_mano_obra_real, 0) as costo_mano_obra_real,
                    COALESCE(costo_diagnostico_real, 0) as costo_diagnostico_real
                FROM pagos 
                WHERE estado = 'pagado' 
                AND estado_pago = 'pagado'
                AND fecha BETWEEN %s AND %s
                ORDER BY fecha DESC, hora DESC
            """
            cur.execute(query_ventas, (fecha_inicio, fecha_fin))
            rows = cur.fetchall()
            ventas = [dict(row) for row in rows]
            
            # ============================================
            # 2. OBTENER GASTOS (usando fecha en zona Chile)
            # ============================================
            cur.execute("""
                SELECT 
                    id,
                    categoria,
                    descripcion,
                    monto,
                    metodo_pago,
                    proveedor,
                    folio,
                    tipo_gasto,
                    registrado_por,
                    fecha,
                    hora,
                    created_at AT TIME ZONE 'UTC' AT TIME ZONE 'America/Santiago' as created_at_chile
                FROM gastos 
                WHERE fecha BETWEEN %s AND %s
                ORDER BY fecha DESC, hora DESC
            """, (fecha_inicio, fecha_fin))
            
            gastos_rows = cur.fetchall()
            gastos = []
            total_gastos = 0
            
            for row in gastos_rows:
                g = dict(row)
                if g.get('hora') and hasattr(g['hora'], 'strftime'):
                    g['hora'] = g['hora'].strftime('%H:%M:%S')
                if g.get('fecha') and hasattr(g['fecha'], 'strftime'):
                    g['fecha'] = g['fecha'].strftime('%Y-%m-%d')
                if g.get('created_at_chile'):
                    g['created_at'] = g['created_at_chile'].strftime('%Y-%m-%d %H:%M:%S')
                g.pop('created_at_chile', None)
                gastos.append(g)
                total_gastos += float(g.get('monto', 0) or 0)
            
            cur.close()
            conn.close()
            
            return {
                'ventas': ventas,
                'gastos': gastos,
                'total_gastos': total_gastos
            }
        except Exception as e:
            logger.error(f"Error obtener balance ventas: {e}")
            return {'ventas': [], 'gastos': [], 'total_gastos': 0}
    @staticmethod
def registrar_descarga_pdf(id_reg, usuario, tipo_usuario="usuario", ip=None):
    """Registra la descarga de un PDF"""
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        # Obtener datos del pago
        cur.execute("SELECT nombre, monto FROM pagos WHERE id = %s", (id_reg,))
        pago = cur.fetchone()
        
        if not pago:
            return False
        
        # Insertar registro de auditoría de descarga
        cur.execute("""
            INSERT INTO auditoria_descargas 
            (id_registro, nombre_cliente, monto, usuario_descarga, tipo_usuario, ip, fecha_descarga)
            VALUES (%s, %s, %s, %s, %s, %s, NOW() AT TIME ZONE 'America/Santiago')
        """, (
            id_reg,
            pago[0],
            float(pago[1]),
            usuario,
            tipo_usuario,
            ip
        ))
        
        conn.commit()
        cur.close()
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Error registrando descarga PDF: {e}")
        return False
    
    # ============================================
    # FUNCIONES PARA FLOTAS
    # ============================================
    
    @staticmethod
    def obtener_flotas_pendientes():
        """Obtiene flotas pendientes de pago"""
        return PagoRepository.obtener_flotas_pendientes()
    
    @staticmethod
    def obtener_flotas_pendientes_count():
        """Obtiene el número de flotas pendientes de pago"""
        return PagoRepository.obtener_flotas_pendientes_count()
    
    @staticmethod
    def obtener_flotas_disponibles():
        """Obtiene todas las flotas registradas"""
        return PagoRepository.obtener_flotas_disponibles()
    
    # ============================================
    # FUNCIONES PARA VALIDACIONES
    # ============================================
    
    @staticmethod
    def verificar_duplicado(nombre, patente):
        """Verifica si existe un duplicado"""
        return PagoRepository.verificar_duplicado(nombre, patente)
    
    @staticmethod
    def actualizar_repuestos_venta(id_reg, data):
        """Actualiza solo los repuestos y costos de una venta"""
        return PagoRepository.actualizar_repuestos_venta(id_reg, data)
    
    # ============================================
    # FUNCIONES PARA DASHBOARD
    # ============================================
    
    @staticmethod
    def obtener_dashboard_data(fecha_desde):
        """Obtiene datos para el dashboard"""
        return PagoRepository.obtener_dashboard_data(fecha_desde)
    
    @staticmethod
    def obtener_meses_disponibles():
        """Obtiene los meses con datos para el dashboard"""
        return PagoRepository.obtener_meses_disponibles()
    
    # ============================================
    # FUNCIONES PARA GASTOS
    # ============================================
    
    @staticmethod
    def obtener_gastos_balance(fecha_inicio, fecha_fin):
        """Obtiene gastos para el balance"""
        return PagoRepository.obtener_gastos_balance(fecha_inicio, fecha_fin)
    
    # ============================================
    # FUNCIONES PARA CIERRE DE CAJA
    # ============================================
    
    @staticmethod
    def obtener_cierre_caja(fecha):
        """Obtiene el cierre de caja para una fecha"""
        return PagoRepository.obtener_cierre_caja(fecha)
    
    @staticmethod
    def crear_cierre_caja(fecha, efectivo_inicial):
        """Crea un nuevo cierre de caja"""
        return PagoRepository.crear_cierre_caja(fecha, efectivo_inicial)
    
    @staticmethod
    def cerrar_cierre_caja(fecha, data):
        """Cierra un cierre de caja"""
        return PagoRepository.cerrar_cierre_caja(fecha, data)
    
    @staticmethod
    def obtener_historial_cierres(limit=30):
        """Obtiene el historial de cierres de caja"""
        return PagoRepository.obtener_historial_cierres(limit)
    
    # ============================================
    # FUNCIONES PARA REPUESTOS
    # ============================================
    
    @staticmethod
    def obtener_repuestos_con_stock(stock_minimo=5, proveedor=None):
        """Obtiene repuestos con stock bajo"""
        return PagoRepository.obtener_repuestos_con_stock(stock_minimo, proveedor)
    
    @staticmethod
    def obtener_proveedores_repuestos():
        """Obtiene la lista de proveedores de repuestos"""
        return PagoRepository.obtener_proveedores_repuestos()
