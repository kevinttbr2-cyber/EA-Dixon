# Backend/models/factura_sii.py
class FacturaSII:
    def __init__(self, id=None, rut_emisor=None, rut_receptor=None, folio=None,
                 tipo_documento=None, fecha=None, monto=0, codigo_autorizacion=None,
                 razon_social_emisor=None, razon_social_receptor=None,
                 texto_original=None, usuario=None, fecha_escaneo=None,
                 created_at=None):
        
        self.id = id
        self.rut_emisor = rut_emisor
        self.rut_receptor = rut_receptor
        self.folio = folio
        self.tipo_documento = tipo_documento or 'Factura'
        self.fecha = fecha
        self.monto = monto
        self.codigo_autorizacion = codigo_autorizacion
        self.razon_social_emisor = razon_social_emisor
        self.razon_social_receptor = razon_social_receptor
        self.texto_original = texto_original
        self.usuario = usuario or 'Sistema'
        self.fecha_escaneo = fecha_escaneo
        self.created_at = created_at

    def to_dict(self):
        return {
            "id": self.id,
            "rut_emisor": self.rut_emisor,
            "rut_receptor": self.rut_receptor,
            "folio": self.folio,
            "tipo_documento": self.tipo_documento,
            "fecha": self.fecha.strftime('%Y-%m-%d') if self.fecha else None,
            "monto": self.monto,
            "codigo_autorizacion": self.codigo_autorizacion,
            "razon_social_emisor": self.razon_social_emisor,
            "razon_social_receptor": self.razon_social_receptor,
            "texto_original": self.texto_original,
            "usuario": self.usuario,
            "fecha_escaneo": self.fecha_escaneo.strftime('%Y-%m-%d %H:%M:%S') if self.fecha_escaneo else None,
            "created_at": self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }

    @staticmethod
    def from_db_row(row):
        if not row:
            return None
        return FacturaSII(
            id=row.get('id'),
            rut_emisor=row.get('rut_emisor'),
            rut_receptor=row.get('rut_receptor'),
            folio=row.get('folio'),
            tipo_documento=row.get('tipo_documento', 'Factura'),
            fecha=row.get('fecha'),
            monto=row.get('monto', 0),
            codigo_autorizacion=row.get('codigo_autorizacion'),
            razon_social_emisor=row.get('razon_social_emisor'),
            razon_social_receptor=row.get('razon_social_receptor'),
            texto_original=row.get('texto_original'),
            usuario=row.get('usuario', 'Sistema'),
            fecha_escaneo=row.get('fecha_escaneo'),
            created_at=row.get('created_at')
        )
