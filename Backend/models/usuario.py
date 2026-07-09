from datetime import datetime

class Usuario:
    def __init__(self, id=None, username=None, password=None, rol=None, nombre_completo=None):
        self.id = id
        self.username = username
        self.password = password
        self.rol = rol
        self.nombre_completo = nombre_completo or username
    
    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "rol": self.rol,
            "nombre_completo": self.nombre_completo
        }
    
    @staticmethod
    def from_db_row(row):
        return Usuario(
            id=row.get('id'),
            username=row.get('username'),
            password=row.get('password'),
            rol=row.get('rol'),
            nombre_completo=row.get('nombre_completo')
        )