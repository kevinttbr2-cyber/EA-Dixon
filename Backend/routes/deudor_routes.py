# Backend/routes/deudor_routes.py
from flask import Blueprint, request, jsonify
from database import get_connection, get_cursor
from utils.seguridad import sanitizar_input, sanitizar_patente, sanitizar_numero
from utils.fecha_utils import now_santiago
import logging

logger = logging.getLogger(__name__)
deudor_bp = Blueprint('deudor', __name__, url_prefix='/api')

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

@deudor_bp.route('/deudores/<cliente_nombre>', methods=['GET'])
def obtener_deudor(cliente_nombre):
    try:
        conn, cur = get_cursor()
        cur.execute("""
            SELECT id, cliente_nombre, patente, telefono, 
                   monto_deuda, monto_original, estado, 
                   fecha_deuda, fecha_actualizacion, ultimo_pago,
                   observaciones, frecuencia_deudas, id_registro
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
        
        if not cliente_nombre or monto_deuda <= 0:
            return jsonify({"error": "Cliente y monto son obligatorios"}), 400
        
        conn = get_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT COUNT(*) as total_deudas
            FROM historial_deudas 
            WHERE cliente_nombre ILIKE %s AND tipo = 'deuda'
        """, (cliente_nombre,))
        frecuencia = cur.fetchone()[0] or 0
        nueva_frecuencia = frecuencia + 1
        
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
            
            cur.execute("""
                UPDATE deudores 
                SET monto_deuda = %s,
                    monto_original = monto_original + %s,
                    estado = %s,
                    fecha_actualizacion = NOW() AT TIME ZONE 'America/Santiago',
                    observaciones = %s,
                    frecuencia_deudas = %s,
                    id_registro = COALESCE(id_registro, %s)
                WHERE id = %s
            """, (nuevo_monto, monto_original, nuevo_estado, descripcion, nueva_frecuencia, id_registro, deudor_id))
            
            cur.execute("""
                INSERT INTO historial_deudas 
                (deudor_id, cliente_nombre, patente, monto_deuda, 
                 monto_abonado, saldo_restante, tipo, descripcion, id_registro)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                deudor_id, cliente_nombre, patente, monto_deuda,
                0, nuevo_monto, 'deuda', descripcion, id_registro
            ))
            
            mensaje = f"✅ Deuda actualizada: ${nuevo_monto:,.0f} (Frecuencia: {nueva_frecuencia})"
        else:
            estado = 'amarillo'
            
            cur.execute("""
                INSERT INTO deudores 
                (cliente_nombre, patente, telefono, monto_deuda, 
                 monto_original, estado, observaciones, frecuencia_deudas, id_registro)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (cliente_nombre, patente, telefono, monto_deuda, 
                  monto_original, estado, descripcion, 1, id_registro))
            
            deudor_id = cur.fetchone()[0]
            
            cur.execute("""
                INSERT INTO historial_deudas 
                (deudor_id, cliente_nombre, patente, monto_deuda, 
                 monto_abonado, saldo_restante, tipo, descripcion, id_registro)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                deudor_id, cliente_nombre, patente, monto_deuda,
                0, monto_deuda, 'deuda', descripcion, id_registro
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
        
        cur.execute("""
            SELECT id, monto_deuda, estado, frecuencia_deudas, patente, id_registro 
            FROM deudores 
            WHERE cliente_nombre ILIKE %s
            ORDER BY fecha_actualizacion DESC
            LIMIT 1
        """, (cliente_nombre,))
        deudor = cur.fetchone()
        
        if not deudor:
            return jsonify({"error": "Cliente sin deuda registrada"}), 404
        
        deudor_id, monto_deuda, estado_actual, frecuencia, patente, id_registro_original = deudor
        monto_deuda = float(monto_deuda) if monto_deuda else 0
        nuevo_monto = max(0, monto_deuda - monto_abonado)
        
        if nuevo_monto == 0:
            nuevo_estado = 'verde'
        else:
            nuevo_estado = 'amarillo'
        
        ahora = now_santiago()
        hora_ahora = ahora.strftime('%H:%M:%S')
        
        id_pago = None
        monto_actual_pagos = 0
        
        if id_registro_original and id_registro_original > 0:
            cur.execute("SELECT id, monto FROM pagos WHERE id = %s", (id_registro_original,))
            registro = cur.fetchone()
            if registro:
                id_pago = registro[0]
                monto_actual_pagos = float(registro[1]) if registro[1] else 0
        
        if not id_pago:
            cur.execute("""
                SELECT id, monto FROM pagos 
                WHERE nombre ILIKE %s 
                ORDER BY fecha DESC, id DESC
                LIMIT 1
            """, (cliente_nombre,))
            registro = cur.fetchone()
            if registro:
                id_pago = registro[0]
                monto_actual_pagos = float(registro[1]) if registro[1] else 0
        
        if id_pago:
            nuevo_monto_pagos = monto_actual_pagos + monto_abonado
            cur.execute("""
                UPDATE pagos 
                SET monto = %s,
                    observaciones_pago = COALESCE(observaciones_pago || ' | ', '') || %s,
                    hora = %s,
                    forma_pago = %s,
                    updated_at = NOW() AT TIME ZONE 'America/Santiago'
                WHERE id = %s
            """, (
                nuevo_monto_pagos,
                f"💰 Pago de deuda: {descripcion} | Deuda restante: ${nuevo_monto:,.0f}",
                hora_ahora,
                forma_pago,
                id_pago
            ))
        else:
            fecha_hoy = ahora.strftime('%Y-%m-%d')
            cur.execute("""
                INSERT INTO pagos 
                (nombre, patente, monto, fecha, hora, estado, tipo_venta, 
                 observaciones_pago, atendido_por, forma_pago, diagnostico, reparacion)
                VALUES (%s, %s, %s, %s, %s, 'pagado', 'deuda', %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                cliente_nombre,
                patente or '',
                monto_abonado,
                fecha_hoy,
                hora_ahora,
                f"💰 Pago de deuda: {descripcion} | Deuda restante: ${nuevo_monto:,.0f}",
                'Sistema',
                forma_pago,
                'Pago de deuda',
                'Pago de deuda'
            ))
            id_pago = cur.fetchone()[0]
            nuevo_monto_pagos = monto_abonado
        
        cur.execute("""
            UPDATE deudores 
            SET monto_deuda = %s,
                estado = %s,
                ultimo_pago = NOW() AT TIME ZONE 'America/Santiago',
                fecha_actualizacion = NOW() AT TIME ZONE 'America/Santiago',
                id_registro = %s
            WHERE id = %s
        """, (nuevo_monto, nuevo_estado, id_pago, deudor_id))
        
        cur.execute("""
            INSERT INTO historial_deudas 
            (deudor_id, cliente_nombre, patente, monto_deuda, monto_abonado, 
             saldo_restante, tipo, descripcion, id_registro)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            deudor_id, cliente_nombre, patente or '', monto_deuda, monto_abonado,
            nuevo_monto, 'abono', f"Pago de deuda: {descripcion}", id_pago
        ))
        
        conn.commit()
        cur.close()
        conn.close()
        
        mensaje = f"✅ Pago de deuda registrado correctamente\n\n"
        mensaje += f"💰 Monto pagado: ${monto_abonado:,.0f}\n"
        mensaje += f"📌 Saldo restante: ${nuevo_monto:,.0f}\n"
        if nuevo_monto == 0:
            mensaje += f"🟢 ¡DEUDA LIQUIDADA!"
        else:
            mensaje += f"🟡 Cliente sigue debiendo: ${nuevo_monto:,.0f}"
        
        return jsonify({
            "success": True,
            "mensaje": mensaje,
            "saldo_restante": nuevo_monto,
            "estado": nuevo_estado,
            "id_pago": id_pago,
            "monto_total": nuevo_monto_pagos
        })
    except Exception as e:
        logger.error(f"Error en pagar_deuda: {e}")
        return jsonify({"error": str(e)}), 500

@deudor_bp.route('/deuda/<int:id_deuda>', methods=['GET'])
def obtener_deuda(id_deuda):
    try:
        conn, cur = get_cursor()
        cur.execute("""
            SELECT id, cliente_nombre, patente, telefono, 
                   monto_deuda, monto_original, estado, 
                   fecha_deuda, fecha_actualizacion, ultimo_pago,
                   observaciones, frecuencia_deudas, id_registro
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
