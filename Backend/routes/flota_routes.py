from flask import Blueprint, jsonify
from services.pago_service import PagoService

flota_bp = Blueprint('flota', __name__, url_prefix='/api')

@flota_bp.route('/flotas', methods=['GET'])
def get_flotas():
    flotas = PagoService.obtener_flotas()
    return jsonify(flotas)