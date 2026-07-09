from flask import Blueprint, request, jsonify
from repositories.pago_repo import PagoRepository
import psycopg2
from database import get_connection

catalogo_bp = Blueprint('catalogo', __name__, url_prefix='/api')

@catalogo_bp.route('/marcas', methods=['GET'])
def get_marcas():
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT marca FROM catalogo ORDER BY marca")
        marcas = [row[0] for row in cur.fetchall()]
        cur.close()
        conn.close()
        return jsonify(marcas)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@catalogo_bp.route('/modelos/<marca>', methods=['GET'])
def get_modelos(marca):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT modelo FROM catalogo WHERE marca=%s ORDER BY modelo", (marca,))
        modelos = [row[0] for row in cur.fetchall()]
        cur.close()
        conn.close()
        return jsonify(modelos)
    except Exception as e:
        return jsonify({"error": str(e)}), 500