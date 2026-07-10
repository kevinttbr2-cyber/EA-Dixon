import bcrypt
from database import get_connection, get_cursor
from models.usuario import Usuario

class UsuarioRepository:
    
    @staticmethod
    def crear(username, password, rol, nombre_completo=None):
        try:
            conn = get_connection()
            cur = conn.cursor()
            hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            hash_str = hashed.decode('utf-8')
            
            cur.execute("""
                INSERT INTO usuarios (username, password, rol, nombre_completo)
                VALUES (%s, %s, %s, %s)
            """, (username, hash_str, rol, nombre_completo or username))
            
            conn.commit()
            cur.close()
            conn.close()
            return True
        except Exception as e:
            print(f"Error crear usuario: {e}")
            return False
    
    @staticmethod
    def obtener_por_username(username):
        try:
            conn, cur = get_cursor()
            cur.execute("SELECT * FROM usuarios WHERE username = %s", (username,))
            row = cur.fetchone()
            cur.close()
            conn.close()
            return Usuario.from_db_row(row) if row else None
        except Exception as e:
            print(f"Error obtener usuario: {e}")
            return None
    
    @staticmethod
    def obtener_todos():
        try:
            conn, cur = get_cursor()
            cur.execute("SELECT id, username, rol, nombre_completo FROM usuarios ORDER BY id")
            rows = cur.fetchall()
            cur.close()
            conn.close()
            return [Usuario.from_db_row(row) for row in rows]
        except Exception as e:
            print(f"Error obtener usuarios: {e}")
            return []
    
    @staticmethod
    def eliminar(id_usuario):
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("DELETE FROM usuarios WHERE id = %s", (id_usuario,))
            conn.commit()
            cur.close()
            conn.close()
            return True
        except Exception as e:
            print(f"Error eliminar usuario: {e}")
            return False
    
    @staticmethod
    def verificar_credenciales(username, password):
        usuario = UsuarioRepository.obtener_por_username(username)
        if usuario and usuario.password:
            try:
                if bcrypt.checkpw(password.encode('utf-8'), usuario.password.encode('utf-8')):
                    return usuario
            except Exception as e:
                print(f"Error verificando password: {e}")
        return None
    
    @staticmethod
    def crear_admin_si_no_existe():
        try:
            from config import Config
            usuario = UsuarioRepository.obtener_por_username('admin')
            if not usuario:
                UsuarioRepository.crear('admin', Config.ADMIN_PASSWORD, 'admin', 'Administrador')
                print(f"✅ Admin creado: admin / {Config.ADMIN_PASSWORD}")
            return True
        except Exception as e:
            print(f"Error creando admin: {e}")
            return False
    
    @staticmethod
    def cambiar_password(username, nueva_password):
        try:
            import bcrypt
            conn = get_connection()
            cur = conn.cursor()
            
            cur.execute("UPDATE usuarios SET password = %s WHERE username = %s", 
                        (bcrypt.hashpw(nueva_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8'), username))
            conn.commit()
            cur.close()
            conn.close()
            return True
        except Exception as e:
            print(f"Error cambiar password: {e}")
            return False
