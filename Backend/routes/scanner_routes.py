# Backend/routes/scanner_routes.py
from flask import Blueprint, request, jsonify
from database import get_connection
from utils.seguridad import sanitizar_input, sanitizar_numero
import json
import re
import math
import logging

logger = logging.getLogger(__name__)
scanner_bp = Blueprint('scanner', __name__, url_prefix='/api')

# ============================================
# PROCESAR PRODUCTO DESDE ESCÁNER
# ============================================

@scanner_bp.route('/repuestos/from_scan', methods=['POST'])
def procesar_producto_escaner():
    """
    Procesa un producto escaneado desde un código de barras o QR
    El texto puede ser JSON o texto plano con formato específico
    """
    try:
        data = request.json
        texto_escaneado = data.get('texto', '')
        
        if not texto_escaneado:
            return jsonify({"error": "No se recibió texto del escáner"}), 400
        
        # Intentar parsear como JSON
        try:
            producto_data = json.loads(texto_escaneado) if isinstance(texto_escaneado, str) else texto_escaneado
        except:
            producto_data = {'nombre': 'Producto escaneado', 'precio': 0}
        
        nombre = sanitizar_input(producto_data.get('nombre', 'Producto escaneado'))
        precio = sanitizar_numero(producto_data.get('precio', 0), min_val=0)
        proveedor = sanitizar_input(producto_data.get('proveedor', 'Escáner'))
        cantidad = int(sanitizar_numero(producto_data.get('cantidad', 1), min_val=1))
        codigo = sanitizar_input(producto_data.get('codigo', ''))
        
        # Si no se pudo extraer nombre o precio, intentar parsear el texto
        if not nombre or precio == 0:
            lineas = texto_escaneado.split('\n')
            for linea in lineas:
                if linea.strip() and not linea.startswith('http'):
                    nombre = sanitizar_input(linea.strip())
                    break
            
            # Buscar números al final del texto
            match = re.search(r'([\d.,]+)\s*$', texto_escaneado)
            if match:
                precio = float(match.group(1).replace('.', '').replace(',', '.'))
        
        if not nombre or precio == 0:
            return jsonify({"error": "No se pudo extraer información del producto"}), 400
        
        conn = get_connection()
        cur = conn.cursor()
        
        # Buscar si el producto ya existe
        cur.execute("SELECT id, costo_venta_final, stock FROM repuestos WHERE nombre ILIKE %s", (nombre,))
        existente = cur.fetchone()
        
        if existente:
            # Actualizar existente
            id_existente, costo_venta, stock_actual = existente
            nuevo_stock = (stock_actual or 0) + cantidad
            
            cur.execute("""
                UPDATE repuestos 
                SET stock = %s,
                    costo_proveedor = %s,
                    proveedor = %s,
                    updated_at = NOW() AT TIME ZONE 'America/Santiago'
                WHERE id = %s
                RETURNING id
            """, (nuevo_stock, precio, proveedor, id_existente))
            
            id_repuesto = cur.fetchone()[0]
            mensaje = f"✅ Producto actualizado: {nombre}\n📦 Nuevo stock: {nuevo_stock}\n💰 Costo proveedor: ${precio:,.0f}"
            
        else:
            # Crear nuevo repuesto
            margen = 30
            iva = 1.19
            costo_con_iva = precio * iva
            precio_venta = costo_con_iva * (1 + (margen / 100))
            
            cur.execute("""
                INSERT INTO repuestos 
                (nombre, costo_proveedor, margen_ganancia, costo_venta_final, proveedor, stock, 
                 codigo_barras, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s,
                        NOW() AT TIME ZONE 'America/Santiago', 
                        NOW() AT TIME ZONE 'America/Santiago')
                RETURNING id
            """, (
                nombre,
                precio,
                margen,
                math.floor(precio_venta),
                proveedor,
                cantidad,
                codigo
            ))
            
            id_repuesto = cur.fetchone()[0]
            mensaje = f"✅ Nuevo repuesto agregado: {nombre}\n💰 Costo: ${precio:,.0f}\n💰 Precio venta: ${math.floor(precio_venta):,.0f}\n📦 Stock inicial: {cantidad}"
        
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info(f"📦 Producto procesado desde escáner: {nombre}")
        
        return jsonify({
            "success": True, 
            "mensaje": mensaje,
            "producto": {
                'id': id_repuesto,
                'nombre': nombre,
                'costo_proveedor': precio,
                'stock': cantidad,
                'codigo': codigo
            }
        })
        
    except Exception as e:
        logger.error(f"Error en procesar_producto_escaner: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# ============================================
# IMPORTAR PRODUCTOS DESDE EXCEL/CSV
# ============================================

@scanner_bp.route('/repuestos/importar', methods=['POST', 'OPTIONS'])
def importar_repuestos():
    """
    Importa productos desde Excel con categorías, subcategorías y stock
    """
    if request.method == 'OPTIONS':
        response = jsonify({"success": True})
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        return response
    
    try:
        data = request.json
        productos = data.get('productos', [])
        
        logger.info(f"📦 Importando {len(productos)} productos...")
        
        if not productos:
            return jsonify({"error": "No hay productos para importar"}), 400
        
        conn = get_connection()
        cur = conn.cursor()
        
        importados = 0
        actualizados = 0
        errores = []
        exitosos = []
        
        # Cargar categorías en memoria
        cur.execute("SELECT id, nombre FROM categorias_repuestos")
        categorias_db = cur.fetchall()
        
        categorias_map = {}
        for row in categorias_db:
            categorias_map[row[1].lower()] = row[0]
        
        for idx, item in enumerate(productos):
            try:
                if idx % 10 == 0:
                    logger.info(f"📦 Progreso: {idx+1}/{len(productos)}")
                
                nombre = sanitizar_input(item.get('nombre', '').strip())
                costo_proveedor = sanitizar_numero(item.get('costo', 0), min_val=0)
                precio_venta = sanitizar_numero(item.get('precio_venta', 0), min_val=0)
                proveedor = sanitizar_input(item.get('proveedor', 'Importado').strip())
                categoria_nombre = sanitizar_input(item.get('categoria', '').strip())
                subcategoria_nombre = sanitizar_input(item.get('subcategoria', '').strip())
                stock = int(sanitizar_numero(item.get('stock', 0), min_val=0))
                codigo = sanitizar_input(item.get('codigo', '').strip())
                
                if not nombre or costo_proveedor <= 0 or precio_venta <= 0:
                    errores.append({"nombre": nombre or 'Sin nombre', "error": "Faltan datos obligatorios"})
                    continue
                
                # Buscar o crear categoría
                categoria_id = None
                categoria_nombre_final = None
                
                if categoria_nombre:
                    key = categoria_nombre.lower()
                    if key in categorias_map:
                        categoria_id = categorias_map[key]
                        categoria_nombre_final = categoria_nombre
                    else:
                        cur.execute("""
                            INSERT INTO categorias_repuestos (nombre, descripcion, created_at, updated_at)
                            VALUES (%s, %s, NOW() AT TIME ZONE 'America/Santiago', NOW() AT TIME ZONE 'America/Santiago')
                            RETURNING id
                        """, (categoria_nombre, f'Categoría importada: {categoria_nombre}'))
                        categoria_id = cur.fetchone()[0]
                        categoria_nombre_final = categoria_nombre
                        categorias_map[key] = categoria_id
                
                # Buscar o crear subcategoría
                subcategoria_id = None
                if subcategoria_nombre and categoria_id:
                    cur.execute("""
                        SELECT id FROM subcategorias_repuestos 
                        WHERE LOWER(nombre) = LOWER(%s) AND categoria_id = %s
                    """, (subcategoria_nombre, categoria_id))
                    result = cur.fetchone()
                    if result:
                        subcategoria_id = result[0]
                    else:
                        cur.execute("""
                            INSERT INTO subcategorias_repuestos (categoria_id, nombre, created_at, updated_at)
                            VALUES (%s, %s, NOW() AT TIME ZONE 'America/Santiago', NOW() AT TIME ZONE 'America/Santiago')
                            RETURNING id
                        """, (categoria_id, subcategoria_nombre))
                        subcategoria_id = cur.fetchone()[0]
                
                # Calcular margen
                margen = 30
                if costo_proveedor > 0 and precio_venta > 0:
                    iva = 1.19
                    costo_con_iva = costo_proveedor * iva
                    margen = round(((precio_venta / costo_con_iva) - 1) * 100, 1)
                
                # Buscar si el producto ya existe
                cur.execute("SELECT id, stock FROM repuestos WHERE LOWER(nombre) = LOWER(%s)", (nombre,))
                existente = cur.fetchone()
                
                if existente:
                    nuevo_stock = (existente[1] or 0) + stock
                    cur.execute("""
                        UPDATE repuestos 
                        SET costo_proveedor = %s,
                            costo_venta_final = %s,
                            margen_ganancia = %s,
                            proveedor = %s,
                            stock = %s,
                            subcategoria_id = %s,
                            categoria_nombre = %s,
                            codigo_barras = %s,
                            updated_at = NOW() AT TIME ZONE 'America/Santiago'
                        WHERE id = %s
                    """, (
                        costo_proveedor,
                        precio_venta,
                        margen,
                        proveedor,
                        nuevo_stock,
                        subcategoria_id,
                        categoria_nombre_final,
                        codigo,
                        existente[0]
                    ))
                    actualizados += 1
                    exitosos.append(f"{nombre} (stock: {nuevo_stock}, categoría: {categoria_nombre_final})")
                else:
                    cur.execute("""
                        INSERT INTO repuestos 
                        (nombre, costo_proveedor, costo_venta_final, margen_ganancia, proveedor, 
                         subcategoria_id, categoria_nombre, stock, codigo_barras,
                         created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s,
                                NOW() AT TIME ZONE 'America/Santiago',
                                NOW() AT TIME ZONE 'America/Santiago')
                    """, (
                        nombre,
                        costo_proveedor,
                        precio_venta,
                        margen,
                        proveedor,
                        subcategoria_id,
                        categoria_nombre_final,
                        stock,
                        codigo
                    ))
                    importados += 1
                    exitosos.append(f"{nombre} (nuevo, categoría: {categoria_nombre_final})")
                
                conn.commit()
                
                if idx % 20 == 0:
                    conn.commit()
                
            except Exception as e:
                logger.error(f"Error en producto: {e}")
                errores.append({
                    "nombre": item.get('nombre', 'desconocido'),
                    "error": str(e)
                })
                conn.rollback()
                continue
        
        cur.close()
        conn.close()
        
        logger.info(f"✅ Importación completada: {importados} nuevos, {actualizados} actualizados")
        
        return jsonify({
            "success": True,
            "importados": importados,
            "actualizados": actualizados,
            "exitosos": exitosos[:10],  # Solo los primeros 10 para no sobrecargar
            "errores": errores[:10],
            "total_exitosos": len(exitosos),
            "total_errores": len(errores)
        })
        
    except Exception as e:
        logger.error(f"Error en importar_repuestos: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
