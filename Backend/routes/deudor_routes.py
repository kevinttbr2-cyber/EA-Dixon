# Backend/routes/deudor_routes.py
from flask import Blueprint, request, jsonify
from database import get_connection, get_cursor
from utils.seguridad import sanitizar_input, sanitizar_patente, sanitizar_numero
from utils.fecha_utils import now_santiago
import logging

logger = logging.getLogger(__name__)
deudor_bp = Blueprint('deudor', __name__, url_prefix='/api')

# ============================================
# 1. OBTENER TODOS LOS DEUDORES
# ============================================
@deudor_bp.route('/deudores/todos', methods=['GET'])
def obtener_todos_deudores():
    try:
        conn, cur = get_cursor()
        cur.execute("""
            SELECT d.* FROM deudores d
            WHERE d.monto_deuda > 0
            ORDER BY d.monto_deuda DESC
        """)
        deudores = []
        for row in cur.fetchall():
            d = dict(row)
            d['monto_deuda'] = float(d['monto_deuda']) if d['monto_deuda'] else 0
            d['monto_original'] = float(d['monto_original']) if d['monto_original'] else 0
            deudores.append(d)
        cur.close()
        conn.close()
        return jsonify(deudores)
    except Exception as e:
        logger.error(f"Error en obtener_todos_deudores: {e}")
        return jsonify([])

# ============================================
# 2. OBTENER DEUDOR POR NOMBRE
# ============================================
@deudor_bp.route('/deudores/<cliente_nombre>', methods=['GET'])
def obtener_deudor(cliente_nombre):
    try:
        conn, cur = get_cursor()
        cur.execute("""
            SELECT id, cliente_nombre, patente, telefono, 
                   monto_deuda, monto_original, estado, 
                   fecha_deuda, fecha_actualizacion, ultimo_pago,
                   observaciones, frecuencia_deudas, id_registro,
                   marca, modelo, anio
            FROM deudores 
            WHERE cliente_nombre ILIKE %s
            ORDER BY fecha_actualizacion DESC
            LIMIT 1
        """, (cliente_nombre,))
        deudor = cur.fetchone()
        cur.close()
        conn.close()
        if deudor:
            d = dict(deudor)
            d['monto_deuda'] = float(d['monto_deuda']) if d['monto_deuda'] else 0
            d['monto_original'] = float(d['monto_original']) if d['monto_original'] else 0
            return jsonify(d)
        return jsonify({"success": False, "mensaje": "Cliente sin deudas"}), 404
    except Exception as e:
        logger.error(f"Error en obtener_deudor: {e}")
        return jsonify({"error": str(e)}), 500

# ============================================
# 3. REGISTRAR NUEVA DEUDA
# ============================================
@deudor_bp.route('/deudores', methods=['POST'])
def registrar_deuda():
    try:
        data = request.json
        cliente_nombre = sanitizar_input(data.get('cliente_nombre', '').strip())
        patente = sanitizar_patente(data.get('patente', '').strip())
        telefono = sanitizar_input(data.get('telefono', '').strip())
        monto_deuda = sanitizar_numero(data.get('monto_deuda', 0), min_val=0)
        monto_original = sanitizar_numero(data.get('monto_original', monto_deuda), min_val=0)
        id_registro = data.get('id_registro')
        descripcion = sanitizar_input(data.get('descripcion', ''))
        marca = sanitizar_input(data.get('marca', '').strip())
        modelo = sanitizar_input(data.get('modelo', '').strip())
        anio = sanitizar_numero(data.get('anio', 0), min_val=0)
        
        if not cliente_nombre or monto_deuda <= 0:
            return jsonify({"error": "Cliente y monto son obligatorios"}), 400
        
        conn = get_connection()
        cur = conn.cursor()
        
        # Contar frecuencia de deudas
        cur.execute("""
            SELECT COUNT(*) as total_deudas
            FROM historial_deudas 
            WHERE cliente_nombre ILIKE %s AND tipo = 'deuda'
        """, (cliente_nombre,))
        frecuencia = cur.fetchone()[0] or 0
        nueva_frecuencia = frecuencia + 1
        
        # Buscar si el cliente ya tiene deuda
        cur.execute("""
            SELECT id, monto_deuda, estado FROM deudores 
            WHERE cliente_nombre ILIKE %s
            ORDER BY fecha_actualizacion DESC
            LIMIT 1
        """, (cliente_nombre,))
        existente = cur.fetchone()
        
        if existente:
            deudor_id, monto_actual, estado_actual = existente
            nuevo_monto = float(monto_actual) + monto_deuda
            
            if nueva_frecuencia == 1:
                nuevo_estado = 'amarillo'
            elif estado_actual == 'negro':
                nuevo_estado = 'negro'
            elif nuevo_monto > 100000:
                nuevo_estado = 'rojo'
            elif nuevo_monto > 30000:
                nuevo_estado = 'rojo'
            elif nuevo_monto > 0:
                nuevo_estado = 'amarillo'
            else:
                nuevo_estado = 'verde'
            
            # Actualizar deudor existente
            cur.execute("""
                UPDATE deudores 
                SET monto_deuda = %s,
                    monto_original = monto_original + %s,
                    estado = %s,
                    fecha_actualizacion = NOW() AT TIME ZONE 'America/Santiago',
                    observaciones = %s,
                    frecuencia_deudas = %s,
                    id_registro = COALESCE(id_registro, %s),
                    marca = COALESCE(%s, marca),
                    modelo = COALESCE(%s, modelo),
                    anio = COALESCE(%s, anio)
                WHERE id = %s
            """, (
                nuevo_monto, 
                monto_original, 
                nuevo_estado, 
                descripcion, 
                nueva_frecuencia, 
                id_registro,
                marca,
                modelo,
                anio,
                deudor_id
            ))
            
            # Registrar en historial
            cur.execute("""
                INSERT INTO historial_deudas 
                (deudor_id, cliente_nombre, patente, monto_deuda, 
                 monto_abonado, saldo_restante, tipo, descripcion, id_registro)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                deudor_id, 
                cliente_nombre, 
                patente, 
                monto_deuda,
                0, 
                nuevo_monto, 
                'deuda', 
                descripcion, 
                id_registro
            ))
            
            mensaje = f"✅ Deuda actualizada: ${nuevo_monto:,.0f} (Frecuencia: {nueva_frecuencia})"
        else:
            # Nuevo deudor
            estado = 'amarillo'
            
            cur.execute("""
                INSERT INTO deudores 
                (cliente_nombre, patente, telefono, monto_deuda, 
                 monto_original, estado, observaciones, frecuencia_deudas, 
                 id_registro, marca, modelo, anio)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                cliente_nombre, 
                patente, 
                telefono, 
                monto_deuda, 
                monto_original, 
                estado, 
                descripcion, 
                1, 
                id_registro,
                marca,
                modelo,
                anio
            ))
            
            deudor_id = cur.fetchone()[0]
            
            cur.execute("""
                INSERT INTO historial_deudas 
                (deudor_id, cliente_nombre, patente, monto_deuda, 
                 monto_abonado, saldo_restante, tipo, descripcion, id_registro)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                deudor_id, 
                cliente_nombre, 
                patente, 
                monto_deuda,
                0, 
                monto_deuda, 
                'deuda', 
                descripcion, 
                id_registro
            ))
            
            mensaje = f"✅ Nueva deuda registrada: ${monto_deuda:,.0f} (Primera vez → AMARILLO)"
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "mensaje": mensaje,
            "deudor": {
                "cliente": cliente_nombre,
                "monto_deuda": monto_deuda,
                "estado": estado if not existente else nuevo_estado,
                "frecuencia": nueva_frecuencia
            }
        })
    except Exception as e:
        logger.error(f"Error en registrar_deuda: {e}")
        return jsonify({"error": str(e)}), 500

# ============================================
# 4. PAGAR DEUDA (CORREGIDO)
# ============================================
@deudor_bp.route('/deudores/pagar', methods=['POST'])
def pagar_deuda():
    try:
        data = request.json
        cliente_nombre = sanitizar_input(data.get('cliente_nombre', '').strip())
        monto_abonado = sanitizar_numero(data.get('monto_abonado', 0), min_val=0)
        descripcion = sanitizar_input(data.get('descripcion', 'Pago de deuda'))
        forma_pago = sanitizar_input(data.get('forma_pago', 'efectivo'))
        
        if not cliente_nombre or monto_abonado <= 0:
            return jsonify({"error": "Cliente y monto son obligatorios"}), 400
        
        conn = get_connection()
        cur = conn.cursor()
        
        # Obtener datos del deudor (incluyendo marca, modelo, patente, telefono)
        cur.execute("""
            SELECT id, monto_deuda, estado, frecuencia_deudas, patente, 
                   id_registro, marca, modelo, anio, telefono
            FROM deudores 
            WHERE cliente_nombre ILIKE %s
            ORDER BY fecha_actualizacion DESC
            LIMIT 1
        """, (cliente_nombre,))
        deudor = cur.fetchone()
        
        if not deudor:
            return jsonify({"error": "Cliente sin deuda registrada"}), 404
        
        deudor_id, monto_deuda, estado_actual, frecuencia, patente, \
        id_registro_original, marca, modelo, anio, telefono = deudor
        
        monto_deuda = float(monto_deuda) if monto_deuda else 0
        nuevo_monto = max(0, monto_deuda - monto_abonado)
        
        if nuevo_monto == 0:
            nuevo_estado = 'verde'
        else:
            nuevo_estado = 'amarillo'
        
        ahora = now_santiago()
        hora_ahora = ahora.strftime('%H:%M:%S')
        fecha_hoy = ahora.strftime('%Y-%m-%d')
        
        # ============================================
        # 1. BUSCAR DATOS DEL REGISTRO ORIGINAL EN pagos
        # ============================================
        id_pago_original = None
        monto_deuda_original = monto_deuda  # El monto total de la deuda
        marca_final = marca or ''
        modelo_final = modelo or ''
        patente_final = patente or ''
        telefono_final = telefono or ''
        
        if id_registro_original and id_registro_original > 0:
            cur.execute("""
                SELECT id, monto, marca, modelo, patente, telefono, nombre
                FROM pagos WHERE id = %s
            """, (id_registro_original,))
            registro = cur.fetchone()
            if registro:
                id_pago_original = registro[0]
                monto_deuda_original = float(registro[1]) if registro[1] else monto_deuda
                if not marca_final:
                    marca_final = registro[2] or ''
                if not modelo_final:
                    modelo_final = registro[3] or ''
                if not patente_final:
                    patente_final = registro[4] or ''
                if not telefono_final:
                    telefono_final = registro[5] or ''
        
        # Si no se encontró por id_registro, buscar por nombre
        if not id_pago_original:
            cur.execute("""
                SELECT id, monto, marca, modelo, patente, telefono FROM pagos 
                WHERE nombre ILIKE %s 
                ORDER BY fecha DESC, id DESC
                LIMIT 1
            """, (cliente_nombre,))
            registro = cur.fetchone()
            if registro:
                id_pago_original = registro[0]
                monto_deuda_original = float(registro[1]) if registro[1] else monto_deuda
                if not marca_final:
                    marca_final = registro[2] or ''
                if not modelo_final:
                    modelo_final = registro[3] or ''
                if not patente_final:
                    patente_final = registro[4] or ''
                if not telefono_final:
                    telefono_final = registro[5] or ''
        
        # ============================================
        # 2. CREAR NUEVO REGISTRO DE PAGO (ABONO)
        # ============================================
        # Cada abono es un registro independiente en pagos
        cur.execute("""
            INSERT INTO pagos 
            (nombre, patente, marca, modelo, anio, telefono,
             monto, fecha, hora, estado, tipo_venta, 
             observaciones_pago, atendido_por, forma_pago, 
             diagnostico, reparacion, estado_pago,
             created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s,
                    %s, %s, %s, 'pagado', 'deuda', 
                    %s, %s, %s, 
                    %s, %s, 'pagado',
                    NOW() AT TIME ZONE 'America/Santiago',
                    NOW() AT TIME ZONE 'America/Santiago')
            RETURNING id
        """, (
            cliente_nombre,
            patente_final,
            marca_final,
            modelo_final,
            anio or 0,
            telefono_final,
            monto_abonado,  # ✅ El abono (lo que paga hoy)
            fecha_hoy,
            hora_ahora,
            f"💰 Pago de deuda: {descripcion} | Saldo restante: ${nuevo_monto:,.0f} | Deuda original: ${monto_deuda:,.0f}",
            'Sistema',
            forma_pago,
            f"Pago de deuda #{deudor_id} - Abono de ${monto_abonado:,.0f}",
            f"Deuda original: ${monto_deuda:,.0f}"
        ))
        id_abono = cur.fetchone()[0]
        
        # ============================================
        # 3. ACTUALIZAR LA DEUDA EN deudores
        # ============================================
        cur.execute("""
            UPDATE deudores 
            SET monto_deuda = %s,
                estado = %s,
                ultimo_pago = NOW() AT TIME ZONE 'America/Santiago',
                fecha_actualizacion = NOW() AT TIME ZONE 'America/Santiago',
                id_registro = %s
            WHERE id = %s
        """, (
            nuevo_monto, 
            nuevo_estado, 
            id_abono,  # ✅ Guardar el ID del abono
            deudor_id
        ))
        
        # ============================================
        # 4. GUARDAR EN HISTORIAL DE DEUDAS
        # ============================================
        cur.execute("""
            INSERT INTO historial_deudas 
            (deudor_id, cliente_nombre, patente, monto_deuda, monto_abonado, 
             saldo_restante, tipo, descripcion, id_registro)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            deudor_id, 
            cliente_nombre, 
            patente_final, 
            monto_deuda, 
            monto_abonado,
            nuevo_monto, 
            'abono', 
            f"Pago de deuda: {descripcion} | Abono: ${monto_abonado:,.0f} | Saldo: ${nuevo_monto:,.0f}", 
            id_abono
        ))
        
        conn.commit()
        cur.close()
        conn.close()
        
        # ============================================
        # 5. MENSAJE DE CONFIRMACIÓN
        # ============================================
        mensaje = f"✅ Pago de deuda registrado correctamente\n\n"
        mensaje += f"💰 Abono registrado: ${monto_abonado:,.0f}\n"
        mensaje += f"📌 Saldo restante: ${nuevo_monto:,.0f}\n"
        mensaje += f"📋 Registro de abono ID: {id_abono}\n"
        if id_pago_original:
            mensaje += f"📋 Deuda original ID: {id_pago_original}\n"
        if nuevo_monto == 0:
            mensaje += f"🟢 ¡DEUDA LIQUIDADA!"
        else:
            mensaje += f"🟡 Cliente sigue debiendo: ${nuevo_monto:,.0f}"
        
        return jsonify({
            "success": True,
            "mensaje": mensaje,
            "saldo_restante": nuevo_monto,
            "estado": nuevo_estado,
            "id_abono": id_abono,
            "id_deuda_original": id_pago_original,
            "monto_abonado": monto_abonado,
            "monto_total_original": monto_deuda
        })
    except Exception as e:
        logger.error(f"Error en pagar_deuda: {e}")
        return jsonify({"error": str(e)}), 500

# ============================================
# 5. OBTENER DEUDA POR ID
# ============================================
@deudor_bp.route('/deuda/<int:id_deuda>', methods=['GET'])
def obtener_deuda(id_deuda):
    try:
        conn, cur = get_cursor()
        cur.execute("""
            SELECT id, cliente_nombre, patente, telefono, 
                   monto_deuda, monto_original, estado, 
                   fecha_deuda, fecha_actualizacion, ultimo_pago,
                   observaciones, frecuencia_deudas, id_registro,
                   marca, modelo, anio
            FROM deudores 
            WHERE id = %s AND monto_deuda > 0
        """, (id_deuda,))
        deuda = cur.fetchone()
        cur.close()
        conn.close()
        if deuda:
            deuda_dict = dict(deuda)
            deuda_dict['monto_deuda'] = float(deuda_dict['monto_deuda']) if deuda_dict['monto_deuda'] else 0
            deuda_dict['monto_original'] = float(deuda_dict['monto_original']) if deuda_dict['monto_original'] else 0
            return jsonify(deuda_dict)
        return jsonify({"error": "Deuda no encontrada o ya pagada"}), 404
    except Exception as e:
        logger.error(f"Error en obtener_deuda: {e}")
        return jsonify({"error": str(e)}), 500

# ============================================
# 6. OBTENER HISTORIAL DE DEUDAS DE UN CLIENTE
# ============================================
@deudor_bp.route('/deudores/historial/<cliente_nombre>', methods=['GET'])
def obtener_historial_deuda(cliente_nombre):
    try:
        conn, cur = get_cursor()
        cur.execute("""
            SELECT h.*, d.marca, d.modelo, d.patente
            FROM historial_deudas h
            LEFT JOIN deudores d ON h.deudor_id = d.id
            WHERE h.cliente_nombre ILIKE %s
            ORDER BY h.created_at DESC
        """, (cliente_nombre,))
        historial = []
        for row in cur.fetchall():
            item = dict(row)
            item['monto_deuda'] = float(item['monto_deuda']) if item['monto_deuda'] else 0
            item['monto_abonado'] = float(item['monto_abonado']) if item['monto_abonado'] else 0
            item['saldo_restante'] = float(item['saldo_restante']) if item['saldo_restante'] else 0
            historial.append(item)
        cur.close()
        conn.close()
        return jsonify(historial)
    except Exception as e:
        logger.error(f"Error en obtener_historial_deuda: {e}")
        return jsonify([])

# ============================================
# 7. ELIMINAR DEUDA (SOLO ADMIN)
# ============================================
@deudor_bp.route('/deudores/<int:id_deuda>', methods=['DELETE'])
def eliminar_deuda(id_deuda):
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        cur.execute("SELECT id FROM deudores WHERE id = %s AND monto_deuda > 0", (id_deuda,))
        if cur.fetchone() is None:
            cur.close()
            conn.close()
            return jsonify({"error": "Deuda no encontrada o ya pagada"}), 404
        
        cur.execute("DELETE FROM deudores WHERE id = %s", (id_deuda,))
        cur.execute("DELETE FROM historial_deudas WHERE deudor_id = %s", (id_deuda,))
        
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info(f"✅ Deuda eliminada: ID {id_deuda}")
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Error en eliminar_deuda: {e}")
        return jsonify({"error": str(e)}), 500
