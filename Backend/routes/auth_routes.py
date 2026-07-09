from flask import Blueprint, request, jsonify
from services.auth_service import AuthService

auth_bp = Blueprint('auth', __name__, url_prefix='/api')

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
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

@auth_bp.route('/usuarios', methods=['GET'])
def get_usuarios():
    usuarios = AuthService.obtener_usuarios()
    return jsonify([u.to_dict() for u in usuarios])

@auth_bp.route('/crear_usuario', methods=['POST'])
def crear_usuario():
    data = request.json
    if AuthService.registrar_usuario(
        data['username'], 
        data['password'], 
        data['rol'], 
        data.get('nombre_completo')
    ):
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Error al crear"}), 500

@auth_bp.route('/eliminar_usuario/<int:id_usuario>', methods=['DELETE'])
def eliminar_usuario(id_usuario):
    if AuthService.eliminar_usuario(id_usuario):
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Error al eliminar"}), 500