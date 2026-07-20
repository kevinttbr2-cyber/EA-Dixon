# Backend/routes/categoria_routes.py
from flask import Blueprint, request, jsonify
from database import get_connection, get_cursor
from utils.seguridad import sanitizar_input
import logging

logger = logging.getLogger(__name__)
categoria_bp = Blueprint('categoria', __name__, url_prefix='/api')

# ============================================
# CATEGORÍAS
# ============================================

@categoria_bp.route('/categorias_repuestos', methods=['GET'])
def obtener_categorias_repuestos():
    """Obtiene todas las categorías de repuestos con conteo de subcategorías"""
    try:
        conn, cur = get_cursor()
        cur.execute("""
            SELECT c.*, 
                   (SELECT COUNT(*) FROM subcategorias_repuestos WHERE categoria_id = c.id) as subcategorias_count
            FROM categorias_repuestos c 
            ORDER BY c.nombre
        """)
        categorias = [dict(row) for row in cur.fetchall()]
        cur.close()
        conn.close()
        return jsonify(categorias)
    except Exception as e:
        logger.error(f"Error en obtener_categorias_repuestos: {e}")
        return jsonify([])

@categoria_bp.route('/categorias_repuestos', methods=['POST'])
def crear_categoria_repuesto():
    """Crea una nueva categoría de repuesto"""
    try:
        data = request.json
        nombre = sanitizar_input(data.get('nombre', '').strip())
        descripcion = sanitizar_input(data.get('descripcion', '').strip())
        
        if not nombre:
            return jsonify({"error": "El nombre es obligatorio"}), 400
        
        conn = get_connection()
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO categorias_repuestos (nombre, descripcion, created_at, updated_at)
            VALUES (%s, %s, NOW() AT TIME ZONE 'America/Santiago', NOW() AT TIME ZONE 'America/Santiago')
            RETURNING id
        """, (nombre, descripcion))
        
        id_categoria = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info(f"✅ Categoría creada: {nombre} (ID: {id_categoria})")
        return jsonify({"success": True, "id": id_categoria})
        
    except Exception as e:
        logger.error(f"Error en crear_categoria_repuesto: {e}")
        return jsonify({"error": str(e)}), 500

@categoria_bp.route('/categorias_repuestos/<int:id_categoria>', methods=['PUT'])
def actualizar_categoria_repuesto(id_categoria):
    """Actualiza una categoría de repuesto"""
    try:
        data = request.json
        nombre = sanitizar_input(data.get('nombre', '').strip())
        descripcion = sanitizar_input(data.get('descripcion', '').strip())
        
        if not nombre:
            return jsonify({"error": "El nombre es obligatorio"}), 400
        
        conn = get_connection()
        cur = conn.cursor()
        
        cur.execute("""
            UPDATE categorias_repuestos 
            SET nombre = %s,
                descripcion = %s,
                updated_at = NOW() AT TIME ZONE 'America/Santiago'
            WHERE id = %s
            RETURNING id
        """, (nombre, descripcion, id_categoria))
        
        if cur.fetchone() is None:
            cur.close()
            conn.close()
            return jsonify({"error": "Categoría no encontrada"}), 404
        
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info(f"✅ Categoría actualizada: {nombre} (ID: {id_categoria})")
        return jsonify({"success": True})
        
    except Exception as e:
        logger.error(f"Error en actualizar_categoria_repuesto: {e}")
        return jsonify({"error": str(e)}), 500

@categoria_bp.route('/categorias_repuestos/<int:id_categoria>', methods=['DELETE'])
def eliminar_categoria_repuesto(id_categoria):
    """Elimina una categoría de repuesto (solo si no tiene subcategorías)"""
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        # Verificar si tiene subcategorías
        cur.execute("SELECT COUNT(*) FROM subcategorias_repuestos WHERE categoria_id = %s", (id_categoria,))
        count = cur.fetchone()[0]
        
        if count > 0:
            cur.close()
            conn.close()
            return jsonify({"error": f"No se puede eliminar: tiene {count} subcategorías asociadas"}), 400
        
        cur.execute("DELETE FROM categorias_repuestos WHERE id = %s RETURNING id", (id_categoria,))
        if cur.fetchone() is None:
            cur.close()
            conn.close()
            return jsonify({"error": "Categoría no encontrada"}), 404
        
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info(f"✅ Categoría eliminada: ID {id_categoria}")
        return jsonify({"success": True})
        
    except Exception as e:
        logger.error(f"Error en eliminar_categoria_repuesto: {e}")
        return jsonify({"error": str(e)}), 500

# ============================================
# SUBCATEGORÍAS
# ============================================

@categoria_bp.route('/subcategorias_repuestos/<int:categoria_id>', methods=['GET'])
def obtener_subcategorias_repuestos(categoria_id):
    """Obtiene todas las subcategorías de una categoría"""
    try:
        conn, cur = get_cursor()
        cur.execute("""
            SELECT * FROM subcategorias_repuestos 
            WHERE categoria_id = %s 
            ORDER BY nombre
        """, (categoria_id,))
        subcategorias = [dict(row) for row in cur.fetchall()]
        cur.close()
        conn.close()
        return jsonify(subcategorias)
    except Exception as e:
        logger.error(f"Error en obtener_subcategorias_repuestos: {e}")
        return jsonify([])

@categoria_bp.route('/subcategorias_repuestos', methods=['GET'])
def obtener_todas_subcategorias_repuestos():
    """Obtiene todas las subcategorías con su categoría padre"""
    try:
        conn, cur = get_cursor()
        cur.execute("""
            SELECT s.*, c.nombre as categoria_nombre 
            FROM subcategorias_repuestos s
            JOIN categorias_repuestos c ON c.id = s.categoria_id
            ORDER BY c.nombre, s.nombre
        """)
        subcategorias = [dict(row) for row in cur.fetchall()]
        cur.close()
        conn.close()
        return jsonify(subcategorias)
    except Exception as e:
        logger.error(f"Error en obtener_todas_subcategorias_repuestos: {e}")
        return jsonify([])

@categoria_bp.route('/subcategorias_repuestos', methods=['POST'])
def crear_subcategoria_repuesto():
    """Crea una nueva subcategoría de repuesto"""
    try:
        data = request.json
        categoria_id = data.get('categoria_id')
        nombre = sanitizar_input(data.get('nombre', '').strip())
        descripcion = sanitizar_input(data.get('descripcion', '').strip())
        
        if not categoria_id or not nombre:
            return jsonify({"error": "Categoría y nombre son obligatorios"}), 400
        
        conn = get_connection()
        cur = conn.cursor()
        
        # Verificar que la categoría existe
        cur.execute("SELECT id FROM categorias_repuestos WHERE id = %s", (categoria_id,))
        if cur.fetchone() is None:
            cur.close()
            conn.close()
            return jsonify({"error": "Categoría no encontrada"}), 404
        
        cur.execute("""
            INSERT INTO subcategorias_repuestos (categoria_id, nombre, descripcion, created_at, updated_at)
            VALUES (%s, %s, %s, NOW() AT TIME ZONE 'America/Santiago', NOW() AT TIME ZONE 'America/Santiago')
            RETURNING id
        """, (categoria_id, nombre, descripcion))
        
        id_subcategoria = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info(f"✅ Subcategoría creada: {nombre} (ID: {id_subcategoria})")
        return jsonify({"success": True, "id": id_subcategoria})
        
    except Exception as e:
        logger.error(f"Error en crear_subcategoria_repuesto: {e}")
        return jsonify({"error": str(e)}), 500

@categoria_bp.route('/subcategorias_repuestos/<int:id_subcategoria>', methods=['PUT'])
def actualizar_subcategoria_repuesto(id_subcategoria):
    """Actualiza una subcategoría de repuesto"""
    try:
        data = request.json
        nombre = sanitizar_input(data.get('nombre', '').strip())
        descripcion = sanitizar_input(data.get('descripcion', '').strip())
        
        if not nombre:
            return jsonify({"error": "El nombre es obligatorio"}), 400
        
        conn = get_connection()
        cur = conn.cursor()
        
        cur.execute("""
            UPDATE subcategorias_repuestos 
            SET nombre = %s,
                descripcion = %s,
                updated_at = NOW() AT TIME ZONE 'America/Santiago'
            WHERE id = %s
            RETURNING id
        """, (nombre, descripcion, id_subcategoria))
        
        if cur.fetchone() is None:
            cur.close()
            conn.close()
            return jsonify({"error": "Subcategoría no encontrada"}), 404
        
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info(f"✅ Subcategoría actualizada: {nombre} (ID: {id_subcategoria})")
        return jsonify({"success": True})
        
    except Exception as e:
        logger.error(f"Error en actualizar_subcategoria_repuesto: {e}")
        return jsonify({"error": str(e)}), 500

@categoria_bp.route('/subcategorias_repuestos/<int:id_subcategoria>', methods=['DELETE'])
def eliminar_subcategoria_repuesto(id_subcategoria):
    """Elimina una subcategoría de repuesto"""
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        # Verificar si tiene repuestos asociados
        cur.execute("SELECT COUNT(*) FROM repuestos WHERE subcategoria_id = %s", (id_subcategoria,))
        count = cur.fetchone()[0]
        
        if count > 0:
            cur.close()
            conn.close()
            return jsonify({"error": f"No se puede eliminar: tiene {count} repuestos asociados"}), 400
        
        cur.execute("DELETE FROM subcategorias_repuestos WHERE id = %s RETURNING id", (id_subcategoria,))
        if cur.fetchone() is None:
            cur.close()
            conn.close()
            return jsonify({"error": "Subcategoría no encontrada"}), 404
        
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info(f"✅ Subcategoría eliminada: ID {id_subcategoria}")
        return jsonify({"success": True})
        
    except Exception as e:
        logger.error(f"Error en eliminar_subcategoria_repuesto: {e}")
        return jsonify({"error": str(e)}), 500

# ============================================
# ASIGNAR CATEGORÍA A REPUESTO
# ============================================

@categoria_bp.route('/repuestos/<int:id_repuesto>/categoria', methods=['PUT'])
def asignar_categoria_repuesto(id_repuesto):
    """Asigna una categoría/subcategoría a un repuesto"""
    try:
        data = request.json
        subcategoria_id = data.get('subcategoria_id')
        
        conn = get_connection()
        cur = conn.cursor()
        
        if subcategoria_id:
            # Obtener el nombre de la categoría padre
            cur.execute("""
                SELECT c.nombre 
                FROM subcategorias_repuestos s
                JOIN categorias_repuestos c ON c.id = s.categoria_id
                WHERE s.id = %s
            """, (subcategoria_id,))
            result = cur.fetchone()
            
            if not result:
                cur.close()
                conn.close()
                return jsonify({"error": "Subcategoría no encontrada"}), 404
            
            categoria_nombre = result[0]
            
            cur.execute("""
                UPDATE repuestos 
                SET subcategoria_id = %s, 
                    categoria_nombre = %s,
                    updated_at = NOW() AT TIME ZONE 'America/Santiago'
                WHERE id = %s
                RETURNING id
            """, (subcategoria_id, categoria_nombre, id_repuesto))
            
            if cur.fetchone() is None:
                cur.close()
                conn.close()
                return jsonify({"error": "Repuesto no encontrado"}), 404
        else:
            # Quitar categoría
            cur.execute("""
                UPDATE repuestos 
                SET subcategoria_id = NULL, 
                    categoria_nombre = NULL,
                    updated_at = NOW() AT TIME ZONE 'America/Santiago'
                WHERE id = %s
                RETURNING id
            """, (id_repuesto,))
            
            if cur.fetchone() is None:
                cur.close()
                conn.close()
                return jsonify({"error": "Repuesto no encontrado"}), 404
        
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info(f"✅ Categoría asignada al repuesto ID {id_repuesto}")
        return jsonify({"success": True})
        
    except Exception as e:
        logger.error(f"Error en asignar_categoria_repuesto: {e}")
        return jsonify({"error": str(e)}), 500
