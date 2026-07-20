# Backend/routes/auth_routes.py
from flask import Blueprint, request, jsonify
from services.auth_service import AuthService
import logging

logger = logging.getLogger(__name__)
auth_bp = Blueprint('auth', __name__, url_prefix='/api')

@auth_bp.route('/login', methods=['POST'])
def login():
    try:
        data = request.json
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({"success": False, "error": "Usuario y contraseña son obligatorios"}), 400
        
        usuario = AuthService.login(username, password)
        if usuario:
            return jsonify({
                "success": True,
                "user": {
                    "username": usuario.username,
                    "rol": usuario.rol,
                    "nombre_completo": usuario.nombre_completo
                }
            })
        return jsonify({"success": False, "error": "Credenciales incorrectas"}), 401
    except Exception as e:
        logger.error(f"Error en login: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@auth_bp.route('/usuarios', methods=['GET'])
def get_usuarios():
    try:
        usuarios = AuthService.obtener_usuarios()
        return jsonify([u.to_dict() for u in usuarios])
    except Exception as e:
        logger.error(f"Error en get_usuarios: {e}")
        return jsonify({"error": str(e)}), 500

@auth_bp.route('/crear_usuario', methods=['POST'])
def crear_usuario():
    try:
        data = request.json
        username = data.get('username')
        password = data.get('password')
        rol = data.get('rol', 'basico')
        nombre_completo = data.get('nombre_completo', '')
        
        if not username or not password:
            return jsonify({"error": "Usuario y contraseña son obligatorios"}), 400
        
        if len(password) < 6:
            return jsonify({"error": "La contraseña debe tener al menos 6 caracteres"}), 400
        
        if AuthService.registrar_usuario(username, password, rol, nombre_completo):
            logger.info(f"Usuario {username} creado con rol {rol}")
            return jsonify({"success": True})
        return jsonify({"error": "Error al crear usuario"}), 500
    except Exception as e:
        logger.error(f"Error en crear_usuario: {e}")
        return jsonify({"error": str(e)}), 500

@auth_bp.route('/eliminar_usuario/<int:id_usuario>', methods=['DELETE'])
def eliminar_usuario(id_usuario):
    try:
        if AuthService.eliminar_usuario(id_usuario):
            logger.info(f"Usuario {id_usuario} eliminado")
            return jsonify({"success": True})
        return jsonify({"success": False, "error": "Error al eliminar"}), 500
    except Exception as e:
        logger.error(f"Error en eliminar_usuario: {e}")
        return jsonify({"error": str(e)}), 500

@auth_bp.route('/cambiar_password', methods=['POST'])
def cambiar_password():
    try:
        data = request.json
        username = data.get('username')
        password_actual = data.get('password_actual')
        password_nueva = data.get('password_nueva')
        
        if not username or not password_actual or not password_nueva:
            return jsonify({"error": "Todos los campos son obligatorios"}), 400
        
        if len(password_nueva) < 6:
            return jsonify({"error": "La nueva contraseña debe tener al menos 6 caracteres"}), 400
        
        usuario = AuthService.login(username, password_actual)
        if not usuario:
            return jsonify({"error": "Contraseña actual incorrecta"}), 401
        
        if AuthService.cambiar_password(username, password_nueva):
            logger.info(f"Contraseña cambiada para {username}")
            return jsonify({"success": True})
        return jsonify({"error": "Error al cambiar contraseña"}), 500
    except Exception as e:
        logger.error(f"Error en cambiar_password: {e}")
        return jsonify({"error": str(e)}), 500
