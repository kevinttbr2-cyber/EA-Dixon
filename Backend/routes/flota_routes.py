# Backend/routes/flota_routes.py
from flask import Blueprint, request, jsonify, send_file
from services.pago_service import PagoService
from database import get_connection
import psycopg2.extras
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import io
import os
import pytz
import logging

logger = logging.getLogger(__name__)
flota_bp = Blueprint('flota', __name__, url_prefix='/api')

@flota_bp.route('/flotas', methods=['GET'])
def get_flotas():
    try:
        flotas = PagoService.obtener_flotas()
        return jsonify(flotas)
    except Exception as e:
        logger.error(f"Error en get_flotas: {e}")
        return jsonify({"error": str(e)}), 500

@flota_bp.route('/exportar_flota_pdf/<flota>', methods=['POST'])
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
                logger.warning(f"Error al cargar logo: {e}")
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
        
        chile_tz = pytz.timezone('America/Santiago')
        ahora_chile = datetime.now(chile_tz)
        pie_text = f"""
        <b>Dixon Electricidad Automotriz</b><br/>
        +569 9855 0331 · Neptuno 163, Local C, Lo Prado, RM, Chile<br/>
        Reporte generado automáticamente el {ahora_chile.strftime('%d/%m/%Y %H:%M')}
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
        logger.error(f"Error en exportar_flota_pdf: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
