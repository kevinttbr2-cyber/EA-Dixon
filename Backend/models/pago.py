class Pago:
    def __init__(self, id=None, nombre=None, monto=0, fecha=None, hora=None,
                 patente=None, marca=None, modelo=None, usuario=None, estado='pendiente',
                 observaciones_cliente=None, observaciones_pago=None, telefono=None,
                 hora_pago=None, atendido_por=None, flota=None, frecuente=False,
                 kilometraje=0, diagnostico=None, reparacion=None, resultado='pendiente',
                 tiempo_estimado='00:00:00'):
        self.id = id
        self.nombre = nombre
        self.monto = monto
        self.fecha = fecha
        self.hora = hora
        self.patente = patente
        self.marca = marca
        self.modelo = modelo
        self.usuario = usuario
        self.estado = estado
        self.observaciones_cliente = observaciones_cliente
        self.observaciones_pago = observaciones_pago
        self.telefono = telefono
        self.hora_pago = hora_pago
        self.atendido_por = atendido_por
        self.flota = flota
        self.frecuente = frecuente
        self.kilometraje = kilometraje
        self.diagnostico = diagnostico
        self.reparacion = reparacion
        self.resultado = resultado
        self.tiempo_estimado = tiempo_estimado
    
    def to_dict(self):
        return {
            "id": self.id,
            "nombre": self.nombre,
            "monto": self.monto,
            "fecha": self.fecha.strftime('%Y-%m-%d') if self.fecha else None,
            "hora": self.hora,
            "patente": self.patente,
            "marca": self.marca,
            "modelo": self.modelo,
            "usuario": self.usuario,
            "estado": self.estado,
            "observaciones_cliente": self.observaciones_cliente,
            "observaciones_pago": self.observaciones_pago,
            "telefono": self.telefono,
            "hora_pago": self.hora_pago,
            "atendido_por": self.atendido_por,
            "flota": self.flota,
            "frecuente": self.frecuente,
            "kilometraje": self.kilometraje,
            "diagnostico": self.diagnostico,
            "reparacion": self.reparacion,
            "resultado": self.resultado,
            "tiempo_estimado": self.tiempo_estimado
        }
    
    @staticmethod
    def from_db_row(row):
        return Pago(
            id=row.get('id'),
            nombre=row.get('nombre'),
            monto=row.get('monto', 0),
            fecha=row.get('fecha'),
            hora=row.get('hora'),
            patente=row.get('patente'),
            marca=row.get('marca'),
            modelo=row.get('modelo'),
            usuario=row.get('usuario'),
            estado=row.get('estado', 'pendiente'),
            observaciones_cliente=row.get('observaciones_cliente'),
            observaciones_pago=row.get('observaciones_pago'),
            telefono=row.get('telefono'),
            hora_pago=row.get('hora_pago'),
            atendido_por=row.get('atendido_por'),
            flota=row.get('flota'),
            frecuente=row.get('frecuente', False),
            kilometraje=row.get('kilometraje', 0),
            diagnostico=row.get('diagnostico'),
            reparacion=row.get('reparacion'),
            resultado=row.get('resultado', 'pendiente'),
            tiempo_estimado=row.get('tiempo_estimado', '00:00:00')
        )