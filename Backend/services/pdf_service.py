# Backend/services/pdf_service.py
import io
import hmac
import hashlib
import os
from datetime import datetime
from config import Config
from reportlab.lib.pagesizes import letter
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph,
    Spacer, Image
)
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import logging

logger = logging.getLogger(__name__)

class PDFService:

    @staticmethod
    def generar_firma(id_reg):
        return hmac.new(
            Config.PDF_SECRET_KEY.encode(),
            str(id_reg).encode(),
            hashlib.sha256
        ).hexdigest()[:16]

    @staticmethod
    def verificar_firma(id_reg, firma):
        return firma == PDFService.generar_firma(id_reg)

    @staticmethod
    def generar_pdf_formal(registro):
        buffer = io.BytesIO()

        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=60,
            leftMargin=60,
            topMargin=45,
            bottomMargin=45
        )

        styles = getSampleStyleSheet()

        # Paleta corporativa
        verde_oscuro = colors.HexColor('#1a4d2e')
        verde_medio = colors.HexColor('#2a6d44')
        gris = colors.HexColor('#666666')
        gris_claro = colors.HexColor('#f5f5f5')
        gris_oscuro = colors.HexColor('#333333')
        negro = colors.black
        rojo = colors.HexColor('#cc0000')
        naranja = colors.HexColor('#e67e22')

        # Estilos
        normal_style = ParagraphStyle(
            'Normal',
            parent=styles['Normal'],
            fontSize=9,
            textColor=negro,
            fontName='Helvetica'
        )

        bold_style = ParagraphStyle(
            'Bold',
            parent=styles['Normal'],
            fontSize=9,
            textColor=negro,
            fontName='Helvetica-Bold'
        )

        label_style = ParagraphStyle(
            'Label',
            parent=styles['Normal'],
            fontSize=8,
            textColor=gris_oscuro,
            fontName='Helvetica-Bold'
        )

        campo_style = ParagraphStyle(
            'Campo',
            parent=styles['Normal'],
            fontSize=9,
            textColor=negro,
            fontName='Helvetica'
        )

        titulo_seccion = ParagraphStyle(
            'TituloSeccion',
            parent=styles['Normal'],
            fontSize=11,
            textColor=verde_oscuro,
            fontName='Helvetica-Bold',
            spaceBefore=10,
            spaceAfter=6
        )

        pie_style = ParagraphStyle(
            'Pie',
            parent=styles['Normal'],
            fontSize=7,
            textColor=gris,
            alignment=1,
            spaceBefore=12,
            fontName='Helvetica'
        )

        titulo_dixon_centrado = ParagraphStyle(
            'TituloDixonCentrado',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=verde_oscuro,
            alignment=1,
            spaceAfter=0,
            fontName='Helvetica-Bold'
        )

        titulo_electricidad_centrado = ParagraphStyle(
            'TituloElectricidadCentrado',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=verde_medio,
            alignment=1,
            spaceAfter=4,
            fontName='Helvetica'
        )

        subtitulo_centrado = ParagraphStyle(
            'SubtituloCentrado',
            parent=styles['Heading2'],
            fontSize=13,
            textColor=verde_medio,
            alignment=1,
            spaceAfter=4,
            fontName='Helvetica-Bold'
        )

        elementos = []

        # Barra superior corporativa
        barra_superior = Table([['']], colWidths=[7 * inch], rowHeights=[0.25 * inch])
        barra_superior.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), verde_oscuro),
        ]))
        elementos.append(barra_superior)
        elementos.append(Spacer(1, 0.1 * inch))

        # Logo + datos del taller
        logo_path = os.path.join('static', 'images', 'dixon-logo.png')
        logo = None
        if os.path.exists(logo_path):
            try:
                logo = Image(logo_path, width=1.2 * inch, height=0.55 * inch)
            except:
                logo = None

        header_data = [
            [
                logo if logo else "",
                Paragraph(
                    "<b>DIXON Electricidad Automotriz</b><br/>"
                    "📱 +569 9855 0331<br/>"
                    "📍 Neptuno 163, Lo Prado, RM",
                    normal_style
                )
            ]
        ]

        header = Table(header_data, colWidths=[1.4 * inch, 5.6 * inch])
        header.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ]))

        elementos.append(header)
        elementos.append(Spacer(1, 0.15 * inch))

        # Títulos principales
        elementos.append(Paragraph("ORDEN DE TRABAJO", subtitulo_centrado))
        elementos.append(Spacer(1, 0.1 * inch))

        # Datos principales
        fecha_str = ''
        if registro.get('fecha'):
            if hasattr(registro['fecha'], 'strftime'):
                fecha_str = registro['fecha'].strftime('%d/%m/%Y')
            else:
                fecha_str = str(registro['fecha'])[:10]

        datos_data = [
            ['N° OT', str(registro.get('id', '')), 'Fecha', fecha_str],
            ['Cliente', registro.get('nombre', '') or '', 'Teléfono', registro.get('telefono', '') or ''],
            ['Patente', registro.get('patente', '') or '', 'Marca/Modelo',
             f"{registro.get('marca', '') or ''} {registro.get('modelo', '') or ''}"],
            ['Año', registro.get('anio', '') or '', 'Kilometraje',
             f"{registro.get('kilometraje', 0) or 0} km"],
        ]

        table_data = []
        for row in datos_data:
            table_data.append([
                Paragraph(f"<b>{row[0]}</b>", label_style),
                Paragraph(str(row[1] or ''), campo_style),
                Paragraph(f"<b>{row[2]}</b>", label_style),
                Paragraph(str(row[3] or ''), campo_style),
            ])

        tabla_datos = Table(table_data, colWidths=[0.8 * inch, 1.6 * inch, 1.0 * inch, 1.8 * inch])
        tabla_datos.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('GRID', (0, 0), (-1, -1), 0.3, colors.grey),
            ('BACKGROUND', (0, 0), (0, -1), gris_claro),
            ('BACKGROUND', (2, 0), (2, -1), gris_claro),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))

        elementos.append(tabla_datos)
        elementos.append(Spacer(1, 0.15 * inch))

        # Función para crear secciones tipo "card"
        def crear_card(titulo, contenido):
            elementos.append(Paragraph(titulo, titulo_seccion))
            card = Table([[Paragraph(contenido, normal_style)]], colWidths=[6.5 * inch])
            card.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#fafafa')),
                ('BOX', (0, 0), (-1, -1), 0.6, gris),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            elementos.append(card)
            elementos.append(Spacer(1, 0.12 * inch))

        # Observaciones, diagnóstico, reparación
        if registro.get('observaciones_cliente'):
            crear_card("Observaciones del ingreso", registro['observaciones_cliente'])

        if registro.get('diagnostico'):
            crear_card("Diagnóstico realizado", registro['diagnostico'])

        if registro.get('reparacion'):
            crear_card("Reparación realizada", registro['reparacion'])

        # Resultado destacado
        resultado = registro.get('resultado', 'pendiente')
        resultado_map = {
            'reparado': ('🟢 Reparado', verde_oscuro),
            'pendiente': ('🟡 Pendiente', naranja),
            'derivado': ('🔴 Derivado', rojo)
        }
        resultado_texto, resultado_color = resultado_map.get(resultado, ('🟡 Pendiente', naranja))

        resultado_style = ParagraphStyle(
            'ResultadoStyle',
            parent=normal_style,
            textColor=resultado_color,
            fontName='Helvetica-Bold',
            fontSize=11
        )

        resultado_table = Table(
            [[Paragraph(f"<b>Resultado:</b> {resultado_texto}", resultado_style)]],
            colWidths=[6.5 * inch]
        )
        resultado_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#eef7ee')),
            ('BOX', (0, 0), (-1, -1), 0.8, resultado_color),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))

        elementos.append(resultado_table)
        elementos.append(Spacer(1, 0.15 * inch))

        # Control interno
        elementos.append(Paragraph("CONTROL INTERNO", titulo_seccion))

        tecnico = registro.get('atendido_por', 'No registrado')
        tiempo = registro.get('tiempo_estimado', '') or '00:00:00'
        total_cobrado = registro.get('monto', 0) or 0

        if isinstance(tiempo, (int, float)) and tiempo > 0:
            horas = int(tiempo // 3600)
            minutos = int((tiempo % 3600) // 60)
            segundos = int(tiempo % 60)
            tiempo_formateado = f"{horas:02d}:{minutos:02d}:{segundos:02d}"
        else:
            tiempo_formateado = str(tiempo)

        control_data = [
            [
                Paragraph(f"<b>Técnico:</b> {tecnico}", normal_style),
                Paragraph(f"<b>Tiempo:</b> {tiempo_formateado}", normal_style),
                Paragraph(f"<b>Total cobrado:</b> ${total_cobrado:,.0f}", bold_style),
            ]
        ]

        tabla_control = Table(control_data, colWidths=[2 * inch, 2 * inch, 2.5 * inch])
        tabla_control.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), gris_claro),
            ('BOX', (0, 0), (-1, -1), 0.6, gris),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ]))

        elementos.append(tabla_control)
        elementos.append(Spacer(1, 0.2 * inch))

        # Línea final
        linea_final = Table([['']], colWidths=[7 * inch])
        linea_final.setStyle(TableStyle([
            ('LINEABOVE', (0, 0), (-1, -1), 1, verde_oscuro),
        ]))
        elementos.append(linea_final)
        elementos.append(Spacer(1, 0.1 * inch))

        # Pie de página
        pie_text = f"""
        <b>Dixon Electricidad Automotriz</b><br/>
        📱 +569 9855 0331 · 📍 Neptuno 163, Local C, Lo Prado, RM <br/>
        <font size='7' color='#999999'>Reporte generado el {datetime.now().strftime('%d/%m/%Y %H:%M')} · OT N° {registro.get('id', '')}</font>
        """
        pie = Paragraph(pie_text, pie_style)
        elementos.append(pie)

        try:
            doc.build(elementos)
            buffer.seek(0)
            return buffer
        except Exception as e:
            logger.error(f"Error generando PDF: {e}")
            return None
