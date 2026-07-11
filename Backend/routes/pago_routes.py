from flask import Blueprint, request, jsonify, send_file
from services.pago_service import PagoService
from database import get_connection, get_cursor
from datetime import datetime, timedelta
from services.pdf_service import PDFService
import json
import io
import os
import traceback
import psycopg2.extras
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

# ============================
# BLUEPRINT
# ============================
pago_bp = Blueprint('pago', __name__, url_prefix='/api')


# ============================
# 1. ESTADO (PENDIENTES + PAGADOS HOY)
# ============================
@pago_bp.route('/estado', methods=['GET'])
def get_estado():
    pendientes = PagoService.obtener_pendientes()
    pagados = PagoService.obtener_pagados_hoy()
    return jsonify({
        "pendientes": [p.to_dict() for p in pendientes],
        "pagados_hoy": [p.to_dict() for p in pagados],
        "total_pendientes": len(pendientes),
        "total_pagados_hoy": len(pagados)
    })

# ============================
# 2. OBTENER REGISTRO POR ID
# ============================
@pago_bp.route('/registro/<int:id_reg>', methods=['GET'])
def get_registro(id_reg):
    pago = PagoService.obtener_por_id(id_reg)
    if pago:
        return jsonify(pago.to_dict())
    return jsonify({"error": "No encontrado"}), 404


# ============================
# 3. REGISTROS CON FILTROS
# ============================
@pago_bp.route('/registros', methods=['GET'])
def get_registros_filtrados():
    filtro = request.args.get('filtro', 'todos')
    hoy = datetime.now().date()
    
    try:
        conn, cur = get_cursor()
        query = "SELECT * FROM pagos WHERE estado = 'pagado'"
        params = []
        
        if filtro == 'hoy':
            query += " AND fecha = %s"
            params.append(hoy.strftime('%Y-%m-%d'))
        elif filtro == '7d':
            query += " AND fecha >= %s"
            params.append((hoy - timedelta(days=7)).strftime('%Y-%m-%d'))
        elif filtro == 'mes':
            query += " AND fecha >= %s"
            params.append((hoy - timedelta(days=30)).strftime('%Y-%m-%d'))
        
        query += " ORDER BY fecha DESC, hora DESC"
        cur.execute(query, params)
        rows = cur.fetchall()
        registros = [dict(row) for row in rows]
        
        for r in registros:
            r['firma'] = PDFService.generar_firma(r['id'])
        
        cur.close()
        conn.close()
        return jsonify(registros)
    except Exception as e:
        print(f"Error en get_registros_filtrados: {e}")
        return jsonify({"error": str(e)}), 500


# ============================
# 4. EDITAR REGISTRO COMPLETO
# ============================
@pago_bp.route('/editar_completo/<int:id_reg>', methods=['POST'])
def editar_completo(id_reg):
    data = request.json
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            UPDATE pagos 
            SET nombre = %s,
                telefono = %s,
                patente = %s,
                marca = %s,
                modelo = %s,
                anio = %s,
                flota = %s,
                fecha = %s,
                hora = %s,
                observaciones_cliente = %s,
                diagnostico = %s,
                reparacion = %s,
                resultado = %s,
                tiempo_estimado = %s,
                costo_repuestos_real = %s,
                costo_mano_obra_real = %s,
                costo_diagnostico_real = %s,
                ganancia_neta = %s,
                observaciones_pago = %s,
                validado_por = %s,
                atendido_por = %s,
                validado = %s
            WHERE id = %s
        """, (
            data.get('nombre'),
            data.get('telefono'),
            data.get('patente'),
            data.get('marca'),
            data.get('modelo'),
            data.get('anio', 0),
            data.get('flota'),
            data.get('fecha'),
            data.get('hora'),
            data.get('observaciones_cliente'),
            data.get('diagnostico'),
            data.get('reparacion', 'Reparación realizada'),
            data.get('resultado', 'reparado'),
            data.get('tiempo_estimado', '00:00:00'),
            data.get('costo_repuestos_real', 0),
            data.get('costo_mano_obra_real', 0),
            data.get('costo_diagnostico_real', 0),
            data.get('ganancia_neta', 0),
            data.get('observaciones_pago'),
            data.get('validado_por'),
            data.get('atendido_por'),
            data.get('validado', False),
            id_reg
        ))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        print(f"Error en editar_completo: {e}")
        return jsonify({"error": str(e)}), 500


# ============================
# 5. ELIMINAR REGISTRO
# ============================
@pago_bp.route('/eliminar_registro/<int:id_reg>', methods=['DELETE'])
def eliminar_registro(id_reg):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM pagos WHERE id = %s", (id_reg,))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        print(f"Error en eliminar_registro: {e}")
        return jsonify({"error": str(e)}), 500


# ============================
# 6. BALANCE DE GANANCIA
# ============================
@pago_bp.route('/balance', methods=['GET'])
def get_balance():
    filtro = request.args.get('filtro', 'hoy')
    hoy = datetime.now().date()
    
    try:
        conn, cur = get_cursor()
        
        query = """
            SELECT * FROM pagos 
            WHERE estado = 'pagado'
        """
        params = []
        
        if filtro == 'hoy':
            query += " AND fecha = %s"
            params.append(hoy.strftime('%Y-%m-%d'))
        elif filtro == '7d':
            query += " AND fecha >= %s"
            params.append((hoy - timedelta(days=7)).strftime('%Y-%m-%d'))
        elif filtro == 'mes':
            query += " AND fecha >= %s"
            params.append((hoy - timedelta(days=30)).strftime('%Y-%m-%d'))
        
        query += " ORDER BY fecha DESC, hora DESC"
        cur.execute(query, params)
        rows = cur.fetchall()
        registros = [dict(row) for row in rows]
        
        total_pagado = float(sum(r.get('monto', 0) or 0 for r in registros))
        total_repuestos = float(sum(r.get('costo_repuestos_real', 0) or 0 for r in registros))
        total_mano_obra = float(sum(r.get('costo_mano_obra_real', 0) or 0 for r in registros))
        total_diagnostico = float(sum(r.get('costo_diagnostico_real', 0) or 0 for r in registros))
        ganancia_neta = total_pagado - (total_repuestos + total_mano_obra + total_diagnostico)
        
        cur.close()
        conn.close()
        
        return jsonify({
            "registros": registros,
            "total_pagado": total_pagado,
            "total_repuestos": total_repuestos,
            "total_mano_obra": total_mano_obra,
            "total_diagnostico": total_diagnostico,
            "ganancia_neta": ganancia_neta
        })
    except Exception as e:
        print(f"Error en get_balance: {e}")
        return jsonify({"error": str(e)}), 500


# ============================
# 7. AGREGAR CLIENTE (CON FLOTA)
# ============================
@pago_bp.route('/agregar', methods=['POST'])
def agregar_pago():
    data = request.json
    if data.get('flota') == '__nueva__':
        data['flota'] = data.get('flota_nueva', '').strip()
    if not data.get('flota'):
        data['flota'] = None
    id_reg = PagoService.crear_pago(data)
    if id_reg:
        return jsonify({"success": True, "id": id_reg})
    return jsonify({"success": False, "error": "Error al guardar"}), 500


# ============================
# 8. PROCESAR PAGO (PASO 1 - PAGO EXPRESS)
# ============================
@pago_bp.route('/pagar/<int:id_reg>', methods=['POST'])
def pagar(id_reg):
    data = request.json
    # 🔥 AGREGAR estado_ot
    data['estado_ot'] = data.get('estado_ot', 'Pendiente')
    pago = PagoService.procesar_pago(id_reg, data)
    if pago:
        return jsonify({"success": True, "pago": pago.to_dict()})
    return jsonify({"success": False, "error": "Error al procesar"}), 500


# ============================
# 9. PENDIENTES DE VALIDACIÓN
# ============================
@pago_bp.route('/pendientes_validacion', methods=['GET'])
def get_pendientes_validacion():
    """Obtiene pagos pendientes de validación"""
    try:
        conn, cur = get_cursor()
        
        cur.execute("""
            SELECT * FROM pagos 
            WHERE estado = 'pagado' AND (validado IS NULL OR validado = FALSE)
            ORDER BY fecha DESC, hora DESC
        """)
        pendientes = [dict(row) for row in cur.fetchall()]
        
        cur.execute("""
            SELECT * FROM pagos 
            WHERE estado = 'pagado' AND validado = TRUE
            ORDER BY fecha DESC, hora DESC
        """)
        validados = [dict(row) for row in cur.fetchall()]
        
        cur.execute("""
            SELECT SUM(monto) as total FROM pagos 
            WHERE estado = 'pagado' AND validado = TRUE
        """)
        total_pagado = cur.fetchone()[0] or 0
        
        cur.close()
        conn.close()
        
        return jsonify({
            "pendientes": pendientes,
            "validados": validados,
            "total_pagado": total_pagado
        })
    except Exception as e:
        print(f"Error en get_pendientes_validacion: {e}")
        return jsonify({"error": str(e)}), 500


# ============================
# 10. VALIDAR PAGO (PASO 2 - VALIDACIÓN DE COSTOS)
# ============================
@pago_bp.route('/validar_pago/<int:id_reg>', methods=['POST'])
def validar_pago(id_reg):
    data = request.json
    print(f"📥 Datos recibidos: {data}")
    
    # 🔥 Asegurar que costo_repuestos se guarde
    costo_repuestos = float(data.get('costo_repuestos', 0) or 0)
    detalles_repuestos = data.get('detalles_repuestos', [])
    
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        # Guardar repuestos en tabla separada
        for item in detalles_repuestos:
            nombre = item.get('nombre', '').strip()
            costo = float(item.get('costo', 0) or 0)
            if nombre:
                cur.execute("SELECT id FROM repuestos WHERE nombre = %s", (nombre,))
                if cur.fetchone():
                    cur.execute("UPDATE repuestos SET costo = %s, updated_at = CURRENT_TIMESTAMP WHERE nombre = %s", (costo, nombre))
                else:
                    cur.execute("INSERT INTO repuestos (nombre, costo, created_at, updated_at) VALUES (%s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)", (nombre, costo))
        
        detalles_json = json.dumps(detalles_repuestos)
        
        cur.execute("""
            UPDATE pagos 
            SET costo_repuestos_real = %s,
                costo_mano_obra_real = %s,
                costo_diagnostico_real = %s,
                ganancia_neta = %s,
                observaciones_pago = %s,
                validado = TRUE,
                validado_por = %s,
                fecha_validacion = CURRENT_TIMESTAMP,
                diagnostico = %s,
                reparacion = %s,
                resultado = %s,
                tiempo_estimado = %s,
                detalles_repuestos = %s::jsonb,
                estado_ot = %s
            WHERE id = %s
        """, (
            costo_repuestos,  # ← ESTE ES EL CAMPO QUE DEBE GUARDARSE
            data.get('costo_mano_obra_real', 0),
            data.get('costo_diagnostico_real', 0),
            data.get('ganancia_neta', 0),
            data.get('observaciones_pago', ''),
            data.get('validado_por', 'Sistema'),
            data.get('diagnostico', ''),
            data.get('reparacion', 'Reparación realizada'),
            data.get('resultado', 'reparado'),
            data.get('tiempo_estimado', '00:00:00'),
            detalles_json,
            data.get('estado_ot', 'Pendiente'),
            id_reg
        ))
        
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        print(f"Error en validar_pago: {e}")
        return jsonify({"error": str(e)}), 500
        
        # ============================
        # 2. ACTUALIZAR EL PAGO
        # ============================
        detalles_json = json.dumps(detalles_repuestos)
        
        cur.execute("""
            UPDATE pagos 
            SET costo_repuestos_real = %s,
                costo_mano_obra_real = %s,
                costo_diagnostico_real = %s,
                ganancia_neta = %s,
                observaciones_pago = %s,
                validado = TRUE,
                validado_por = %s,
                fecha_validacion = CURRENT_TIMESTAMP,
                diagnostico = %s,
                reparacion = %s,
                resultado = %s,
                tiempo_estimado = %s,
                detalles_repuestos = %s::jsonb,
                estado_ot = %s
            WHERE id = %s
        """, (
            costo_repuestos,
            data.get('costo_mano_obra_real', 0),
            data.get('costo_diagnostico_real', 0),
            data.get('ganancia_neta', 0),
            data.get('observaciones_pago', ''),
            data.get('validado_por', 'Sistema'),
            data.get('diagnostico', ''),
            data.get('reparacion', 'Reparación realizada'),
            data.get('resultado', 'reparado'),
            data.get('tiempo_estimado', '00:00:00'),
            detalles_json,
            data.get('estado_ot', 'Pendiente'),
            id_reg
        ))
        
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        print(f"Error en validar_pago: {e}")
        return jsonify({"error": str(e)}), 500

@pago_bp.route('/repuestos', methods=['GET'])
def get_repuestos():
    """Obtiene lista de repuestos para autocompletar"""
    try:
        search = request.args.get('q', '')
        conn, cur = get_cursor()
        if search:
            cur.execute("""
                SELECT id, nombre, costo 
                FROM repuestos 
                WHERE nombre ILIKE %s 
                ORDER BY nombre 
                LIMIT 10
            """, (f'%{search}%',))
        else:
            cur.execute("""
                SELECT id, nombre, costo 
                FROM repuestos 
                ORDER BY nombre 
                LIMIT 20
            """)
        repuestos = [dict(row) for row in cur.fetchall()]
        cur.close()
        conn.close()
        return jsonify(repuestos)
    except Exception as e:
        print(f"Error en get_repuestos: {e}")
        return jsonify([])


# ============================
# 11. FLOTAS DISPONIBLES
# ============================
@pago_bp.route('/flotas_disponibles', methods=['GET'])
def get_flotas_disponibles():
    """Obtiene todas las flotas registradas (nombres únicos)"""
    try:
        conn, cur = get_cursor()
        cur.execute("""
            SELECT DISTINCT flota FROM pagos 
            WHERE flota IS NOT NULL AND flota != '' 
            ORDER BY flota
        """)
        flotas = [row[0] for row in cur.fetchall()]
        cur.close()
        conn.close()
        return jsonify(flotas)
    except Exception as e:
        print(f"Error en get_flotas_disponibles: {e}")
        return jsonify([])
# ============================
# REPUESTOS - CRUD COMPLETO
# ============================

@pago_bp.route('/repuestos', methods=['GET'])
def get_repuestos_lista():
    """Obtiene todos los repuestos"""
    try:
        conn, cur = get_cursor()
        cur.execute("SELECT id, nombre, costo, proveedor FROM repuestos ORDER BY nombre")
        repuestos = [dict(row) for row in cur.fetchall()]
        cur.close()
        conn.close()
        return jsonify(repuestos)
    except Exception as e:
        print(f"Error en get_repuestos_lista: {e}")
        return jsonify([])

@pago_bp.route('/repuestos', methods=['POST'])
def crear_repuesto():
    """Crea un nuevo repuesto"""
    try:
        data = request.json
        nombre = data.get('nombre', '').strip()
        costo = float(data.get('costo', 0))
        proveedor = data.get('proveedor', '').strip()
        
        if not nombre:
            return jsonify({"error": "El nombre es obligatorio"}), 400
        
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO repuestos (nombre, costo, proveedor, created_at, updated_at)
            VALUES (%s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            RETURNING id
        """, (nombre, costo, proveedor))
        id_repuesto = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({"success": True, "id": id_repuesto})
    except Exception as e:
        print(f"Error en crear_repuesto: {e}")
        return jsonify({"error": str(e)}), 500

@pago_bp.route('/repuestos/<int:id_repuesto>', methods=['PUT'])
def actualizar_repuesto(id_repuesto):
    """Actualiza un repuesto existente"""
    try:
        data = request.json
        nombre = data.get('nombre', '').strip()
        costo = float(data.get('costo', 0))
        proveedor = data.get('proveedor', '').strip()
        
        if not nombre:
            return jsonify({"error": "El nombre es obligatorio"}), 400
        
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            UPDATE repuestos 
            SET nombre = %s, costo = %s, proveedor = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (nombre, costo, proveedor, id_repuesto))
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({"success": True})
    except Exception as e:
        print(f"Error en actualizar_repuesto: {e}")
        return jsonify({"error": str(e)}), 500

@pago_bp.route('/repuestos/<int:id_repuesto>', methods=['DELETE'])
def eliminar_repuesto(id_repuesto):
    """Elimina un repuesto por ID"""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM repuestos WHERE id = %s", (id_repuesto,))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        print(f"Error en eliminar_repuesto: {e}")
        return jsonify({"error": str(e)}), 500

@pago_bp.route('/repuestos/buscar', methods=['GET'])
def buscar_repuestos():
    """Busca repuestos por nombre (autocompletado)"""
    try:
        query = request.args.get('q', '').strip()
        if len(query) < 2:
            return jsonify([])
        
        conn, cur = get_cursor()
        cur.execute("""
            SELECT id, nombre, costo 
            FROM repuestos 
            WHERE nombre ILIKE %s 
            ORDER BY nombre 
            LIMIT 10
        """, (f'%{query}%',))
        repuestos = [dict(row) for row in cur.fetchall()]
        cur.close()
        conn.close()
        return jsonify(repuestos)
    except Exception as e:
        print(f"Error en buscar_repuestos: {e}")
        return jsonify([])


# ============================
# 12. EXPORTAR FLOTA A PDF
# ============================
@pago_bp.route('/exportar_flota_pdf/<flota>', methods=['POST'])
def exportar_flota_pdf(flota):
    """Genera un PDF con los servicios de una flota en un rango de fechas"""
    try:
        data = request.json
        fecha_desde = data.get('fecha_desde')
        fecha_hasta = data.get('fecha_hasta')
        
        if not fecha_desde or not fecha_hasta:
            return jsonify({"error": "Debes seleccionar ambas fechas"}), 400
        
        conn = get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        cursor.execute("""
            SELECT 
                patente,
                marca,
                modelo,
                nombre as trabajador,
                fecha,
                monto,
                observaciones_pago,
                hora_pago
            FROM pagos
            WHERE flota = %s
            AND estado = 'pagado'
            AND fecha BETWEEN %s AND %s
            ORDER BY fecha DESC
        """, (flota, fecha_desde, fecha_hasta))
        
        datos = cursor.fetchall()
        
        cursor.execute("""
            SELECT SUM(monto) as total
            FROM pagos
            WHERE flota = %s
            AND estado = 'pagado'
            AND fecha BETWEEN %s AND %s
        """, (flota, fecha_desde, fecha_hasta))
        
        total = cursor.fetchone()['total'] or 0
        conn.close()
        
        if not datos:
            return jsonify({"error": "No hay datos en el rango seleccionado"}), 400
        
        buffer = io.BytesIO()
        
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=120,
            bottomMargin=100
        )
        
        styles = getSampleStyleSheet()
        
        negro = colors.black
        verde_muy_oscuro = colors.HexColor('#1a4d2e')
        verde_oscuro = colors.HexColor('#2a6d44')
        gris = colors.HexColor('#666666')
        gris_claro = colors.HexColor('#f5f5f5')
        
        titulo_style = ParagraphStyle(
            'Titulo',
            parent=styles['Heading1'],
            fontSize=22,
            textColor=negro,
            alignment=1,
            spaceAfter=6,
            fontName='Helvetica-Bold'
        )
        
        subtitulo_style = ParagraphStyle(
            'Subtitulo',
            parent=styles['Normal'],
            fontSize=12,
            textColor=gris,
            alignment=1,
            spaceAfter=20,
            fontName='Helvetica'
        )
        
        intro_style = ParagraphStyle(
            'Introduccion',
            parent=styles['Normal'],
            fontSize=11,
            textColor=negro,
            alignment=0,
            spaceAfter=16,
            fontName='Helvetica'
        )
        
        total_style = ParagraphStyle(
            'Total',
            parent=styles['Normal'],
            fontSize=16,
            textColor=negro,
            alignment=2,
            spaceBefore=12,
            spaceAfter=10,
            fontName='Helvetica-Bold'
        )
        
        pie_style = ParagraphStyle(
            'Pie',
            parent=styles['Normal'],
            fontSize=9,
            textColor=gris,
            alignment=1,
            spaceBefore=30,
            fontName='Helvetica'
        )
        
        elementos = []
        
        logo_path = os.path.join('static', 'images', 'dixon-logo.png')
        if os.path.exists(logo_path):
            try:
                logo = Image(logo_path, width=0.8*inch, height=0.8*inch)
                logo_table = Table([[logo]], colWidths=[7*inch])
                logo_table.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ]))
                elementos.append(logo_table)
                elementos.append(Spacer(1, 0.05 * inch))
            except Exception as e:
                print(f"⚠️ Error al cargar logo: {e}")
                elementos.append(Paragraph("DIXON ELECTRICIDAD AUTOMOTRIZ", 
                    ParagraphStyle('LogoTexto', parent=styles['Normal'], fontSize=12, textColor=verde_muy_oscuro, fontName='Helvetica-Bold')))
                elementos.append(Spacer(1, 0.1 * inch))
        else:
            elementos.append(Paragraph("DIXON ELECTRICIDAD AUTOMOTRIZ", 
                ParagraphStyle('LogoTexto', parent=styles['Normal'], fontSize=12, textColor=verde_muy_oscuro, fontName='Helvetica-Bold')))
            elementos.append(Spacer(1, 0.1 * inch))
        
        titulo = Paragraph(f"REPORTE DE FLOTA: {flota.upper()}", titulo_style)
        elementos.append(titulo)
        
        linea = Table([['']], colWidths=[4*inch])
        linea.setStyle(TableStyle([
            ('LINEABOVE', (0, 0), (-1, -1), 1.5, verde_muy_oscuro),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ]))
        elementos.append(linea)
        elementos.append(Spacer(1, 0.05 * inch))
        
        fecha_desde_obj = datetime.strptime(fecha_desde, "%Y-%m-%d")
        fecha_hasta_obj = datetime.strptime(fecha_hasta, "%Y-%m-%d")
        fecha_desde_str = fecha_desde_obj.strftime('%d/%m/%Y')
        fecha_hasta_str = fecha_hasta_obj.strftime('%d/%m/%Y')
        subtitulo = Paragraph(f"Período: {fecha_desde_str} - {fecha_hasta_str}", subtitulo_style)
        elementos.append(subtitulo)
        elementos.append(Spacer(1, 0.1 * inch))
        
        intro_text = f"""
        El presente documento detalla los servicios realizados para la flota <b>"{flota}"</b> 
        durante el período comprendido entre el <b>{fecha_desde_str}</b> y el <b>{fecha_hasta_str}</b>.<br/><br/>
        Se han registrado un total de <b>{len(datos)} servicios</b> para los siguientes vehículos:
        """
        introduccion = Paragraph(intro_text, intro_style)
        elementos.append(introduccion)
        elementos.append(Spacer(1, 0.15 * inch))
        
        table_data = [
            ['Patente', 'Marca', 'Modelo', 'Trabajador', 'Fecha', 'Monto ($)']
        ]
        
        for row in datos:
            fecha_str = row['fecha'].strftime('%d/%m/%Y') if row['fecha'] else ''
            table_data.append([
                row['patente'] or '',
                row['marca'] or '',
                row['modelo'] or '',
                row['trabajador'] or '',
                fecha_str,
                f"{row['monto']:,.0f}"
            ])
        
        tabla = Table(table_data, colWidths=[1.0*inch, 0.9*inch, 0.9*inch, 1.2*inch, 0.8*inch, 1.0*inch])
        tabla.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), verde_oscuro),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ('TOPPADDING', (0, 0), (-1, 0), 6),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ALIGN', (5, 1), (5, -1), 'RIGHT'),
            ('VALIGN', (0, 1), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, verde_muy_oscuro),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, gris_claro]),
        ]))
        elementos.append(tabla)
        elementos.append(Spacer(1, 0.2 * inch))
        
        total_text = f"MONTO TOTAL: ${total:,.0f}"
        total_paragraph = Paragraph(total_text, total_style)
        elementos.append(total_paragraph)
        
        linea_final = Table([['']], colWidths=[4*inch])
        linea_final.setStyle(TableStyle([
            ('LINEABOVE', (0, 0), (-1, -1), 1, verde_muy_oscuro),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ]))
        elementos.append(Spacer(1, 0.1 * inch))
        elementos.append(linea_final)
        elementos.append(Spacer(1, 0.15 * inch))
        
        pie_text = f"""
        <b>Dixon Electricidad Automotriz</b><br/>
        +569 9855 0331 · Neptuno 163, Local C, Lo Prado, RM, Chile<br/>
        Reporte generado automáticamente el {datetime.now().strftime('%d/%m/%Y %H:%M')}
        """
        pie = Paragraph(pie_text, pie_style)
        elementos.append(pie)
        
        elementos.append(Spacer(1, 0.1 * inch))
        num_pagina = Paragraph("Página 1", 
            ParagraphStyle('NumPagina', parent=styles['Normal'], fontSize=8, textColor=gris, alignment=1))
        elementos.append(num_pagina)
        
        doc.build(elementos)
        
        buffer.seek(0)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        nombre_archivo = f'reporte_flota_{flota}_{timestamp}.pdf'
        
        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=nombre_archivo
        )
        
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"❌ Error en exportar_flota_pdf: {error_trace}")
        return jsonify({"error": str(e)}), 500
        
@pago_bp.route('/dashboard', methods=['GET'])
def get_dashboard():
    """Devuelve datos agregados para el dashboard con filtros"""
    try:
        filtro = request.args.get('filtro', '7d')
        mes = request.args.get('mes')
        anio = request.args.get('anio')
        
        from datetime import timedelta
        hoy = datetime.now().date()
        
        # ============================
        # 1. DETERMINAR RANGO DE FECHAS
        # ============================
        fecha_desde = None
        
        if filtro == '7d':
            fecha_desde = hoy - timedelta(days=7)
        elif filtro == '30d':
            fecha_desde = hoy - timedelta(days=30)
        elif filtro == '90d':
            fecha_desde = hoy - timedelta(days=90)
        elif filtro == 'mes' and mes and anio:
            try:
                fecha_desde = datetime(int(anio), int(mes), 1).date()
            except:
                fecha_desde = hoy - timedelta(days=30)
        else:
            fecha_desde = hoy - timedelta(days=7)
        
        # ============================
        # 2. CONEXIÓN Y CONSULTAS
        # ============================
        conn, cur = get_cursor()  # ← CORRECTO: desempacar tupla
        
        # Totales generales
        cur.execute("""
            SELECT 
                COALESCE(SUM(monto), 0) as total_facturado,
                COALESCE(SUM(costo_repuestos_real), 0) as total_repuestos,
                COALESCE(SUM(costo_mano_obra_real), 0) as total_mano_obra,
                COALESCE(SUM(costo_diagnostico_real), 0) as total_diagnostico,
                COUNT(*) as total_servicios
            FROM pagos 
            WHERE estado = 'pagado' 
            AND fecha >= %s
        """, (fecha_desde,))
        totales = cur.fetchone()
        
        # Ventas diarias
        cur.execute("""
            SELECT 
                fecha,
                COALESCE(SUM(monto), 0) as total
            FROM pagos 
            WHERE estado = 'pagado' 
            AND fecha >= %s
            GROUP BY fecha
            ORDER BY fecha ASC
        """, (fecha_desde,))
        ventas = cur.fetchall()
        
        # Ganancia acumulada
        cur.execute("""
            SELECT 
                fecha,
                COALESCE(SUM(monto - COALESCE(costo_repuestos_real, 0) - COALESCE(costo_mano_obra_real, 0) - COALESCE(costo_diagnostico_real, 0)), 0) as ganancia
            FROM pagos 
            WHERE estado = 'pagado' 
            AND fecha >= %s
            GROUP BY fecha
            ORDER BY fecha ASC
        """, (fecha_desde,))
        ganancias = cur.fetchall()
        
        # Top 5 clientes
        cur.execute("""
            SELECT 
                nombre,
                COALESCE(SUM(monto), 0) as total_gastado
            FROM pagos 
            WHERE estado = 'pagado' 
            AND nombre IS NOT NULL
            AND fecha >= %s
            GROUP BY nombre
            ORDER BY total_gastado DESC
            LIMIT 5
        """, (fecha_desde,))
        clientes = cur.fetchall()
        
        # Promedio diario
        cur.execute("""
            SELECT 
                COALESCE(AVG(monto), 0) as promedio_diario
            FROM pagos 
            WHERE estado = 'pagado' 
            AND fecha >= %s
        """, (fecha_desde,))
        promedio = cur.fetchone()
        promedio_diario = float(promedio[0]) if promedio and promedio[0] else 0
        
        cur.close()
        conn.close()
        
        # ============================
        # 3. FORMATO DE RESPUESTA
        # ============================
        labels = []
        ventas_data = []
        
        for row in ventas:
            if row[0]:
                labels.append(row[0].strftime('%d/%m'))
                ventas_data.append(float(row[1]))
        
        ganancia_data = []
        acumulado = 0
        for row in ganancias:
            acumulado += float(row[1])
            ganancia_data.append(acumulado)
        
        # Proyección a 7 días
        proyeccion = []
        proyeccion_labels = []
        for i in range(1, 8):
            fecha_futura = hoy + timedelta(days=i)
            proyeccion_labels.append(fecha_futura.strftime('%d/%m'))
            proyeccion.append(round(promedio_diario * 0.85, 0))
        
        # Obtener meses disponibles (con una nueva conexión)
        conn2, cur2 = get_cursor()
        cur2.execute("""
            SELECT DISTINCT 
                EXTRACT(YEAR FROM fecha) as anio,
                EXTRACT(MONTH FROM fecha) as mes
            FROM pagos 
            WHERE estado = 'pagado' 
            AND fecha IS NOT NULL
            ORDER BY anio DESC, mes DESC
        """)
        meses_disponibles = []
        for row in cur2.fetchall():
            meses_disponibles.append({
                'anio': int(row[0]),
                'mes': int(row[1])
            })
        cur2.close()
        conn2.close()
        
        return jsonify({
            "total_facturado": float(totales[0]),
            "total_repuestos": float(totales[1]),
            "total_mano_obra": float(totales[2]),
            "total_diagnostico": float(totales[3]),
            "total_servicios": totales[4],
            "ganancia_total": float(totales[0]) - float(totales[1]) - float(totales[2]) - float(totales[3]),
            "promedio_diario": promedio_diario,
            "labels": labels,
            "ventas": ventas_data,
            "ganancia_acumulada": ganancia_data,
            "proyeccion_labels": proyeccion_labels,
            "proyeccion": proyeccion,
            "clientes_labels": [row[0] for row in clientes],
            "clientes_data": [float(row[1]) for row in clientes],
            "meses_disponibles": meses_disponibles,
            "filtro_actual": filtro,
            "mes_actual": mes,
            "anio_actual": anio
        })
    except Exception as e:
        print(f"Error en get_dashboard: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
