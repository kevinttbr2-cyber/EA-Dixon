from repositories.usuario_repo import UsuarioRepository

class AuthService:
    
    @staticmethod
    def login(username, password):
        return UsuarioRepository.verificar_credenciales(username, password)
    
    @staticmethod
    def registrar_usuario(username, password, rol, nombre_completo=None):
        return UsuarioRepository.crear(username, password, rol, nombre_completo)
    
    @staticmethod
    def obtener_usuarios():
        return UsuarioRepository.obtener_todos()
    
    @staticmethod
    def eliminar_usuario(id_usuario):
        return UsuarioRepository.eliminar(id_usuario)
    
    @staticmethod
    def crear_admin():
        return UsuarioRepository.crear_admin_si_no_existe()

    @staticmethod
    def cambiar_password(username, nueva_password):
        return UsuarioRepository.cambiar_password(username, nueva_password)
