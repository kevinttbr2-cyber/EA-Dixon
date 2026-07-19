# Backend/services/pdf_service.py
import io
import hmac
import hashlib
import os
from datetime import datetime
from config import Config
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
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
        """Genera un PDF con el formato formal de Dixon Electricidad Automotriz"""
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
        
        verde_oscuro = colors.HexColor('#1a4d2e')
        verde_medio = colors.HexColor('#2a6d44')
        gris = colors.HexColor('#666666')
        gris_claro = colors.HexColor('#f5f5f5')
        gris_oscuro = colors.HexColor('#333333')
        negro = colors.black
        rojo = colors.HexColor('#cc0000')
        naranja = colors.HexColor('#e67e22')
        
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
            fontSize=10,
            textColor=verde_oscuro,
            fontName='Helvetica-Bold',
            spaceBefore=6,
            spaceAfter=3
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
            fontSize=22,
            textColor=verde_oscuro,
            alignment=1,
            spaceAfter=0,
            fontName='Helvetica-Bold'
        )
        
        titulo_electricidad_centrado = ParagraphStyle(
            'TituloElectricidadCentrado',
            parent=styles['Heading2'],
            fontSize=13,
            textColor=verde_medio,
            alignment=1,
            spaceAfter=4,
            fontName='Helvetica'
        )
        
        subtitulo_centrado = ParagraphStyle(
            'SubtituloCentrado',
            parent=styles['Heading2'],
            fontSize=12,
            textColor=verde_medio,
            alignment=1,
            spaceAfter=4,
            fontName='Helvetica-Bold'
        )
        
        elementos = []
        
        logo_path = os.path.join('static', 'images', 'dixon-logo.png')
        if os.path.exists(logo_path):
            try:
                logo = Image(logo_path, width=0.9*inch, height=0.4*inch)
                logo_table = Table([[logo]], colWidths=[7*inch])
                logo_table.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ]))
                elementos.append(logo_table)
                elementos.append(Spacer(1, 0.02 * inch))
            except:
                pass
        
        elementos.append(Paragraph("DIXON", titulo_dixon_centrado))
        elementos.append(Paragraph("Electricidad Automotriz", titulo_electricidad_centrado))
        elementos.append(Spacer(1, 0.02 * inch))
        
        linea = Table([['']], colWidths=[7*inch])
        linea.setStyle(TableStyle([
            ('LINEABOVE', (0, 0), (-1, -1), 1.5, verde_oscuro),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ]))
        elementos.append(linea)
        elementos.append(Spacer(1, 0.02 * inch))
        
        elementos.append(Paragraph("ORDEN DE TRABAJO", subtitulo_centrado))
        elementos.append(Spacer(1, 0.04 * inch))
        
        fecha_str = ''
        if registro.get('fecha'):
            if hasattr(registro['fecha'], 'strftime'):
                fecha_str = registro['fecha'].strftime('%d/%m/%Y')
            else:
                fecha_str = str(registro['fecha'])[:10]
        
        datos_data = [
            ['N° OT', str(registro.get('id', '')), 'Fecha', fecha_str],
            ['Cliente', registro.get('nombre', '') or '', 'Teléfono', registro.get('telefono', '') or ''],
            ['Patente', registro.get('patente', '') or '', 'Marca/Modelo', f"{registro.get('marca', '') or ''} {registro.get('modelo', '') or ''}"],
            ['Año', registro.get('anio', '') or '', 'Kilometraje', f"{registro.get('kilometraje', 0) or 0} km"],
        ]
        
        table_data = []
        for row in datos_data:
            table_data.append([
                Paragraph(f"<b>{row[0]}</b>", label_style),
                Paragraph(str(row[1] or ''), campo_style),
                Paragraph(f"<b>{row[2]}</b>", label_style),
                Paragraph(str(row[3] or ''), campo_style),
            ])
        
        tabla_datos = Table(table_data, colWidths=[0.6*inch, 1.4*inch, 0.9*inch, 1.5*inch])
        tabla_datos.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('GRID', (0, 0), (-1, -1), 0.3, colors.grey),
            ('BACKGROUND', (0, 0), (0, -1), gris_claro),
            ('BACKGROUND', (2, 0), (2, -1), gris_claro),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elementos.append(tabla_datos)
        elementos.append(Spacer(1, 0.06 * inch))
        
        obs_cliente = registro.get('observaciones_cliente', '')
        if obs_cliente:
            elementos.append(Paragraph("Observaciones del ingreso", titulo_seccion))
            obs_table = Table([[Paragraph(obs_cliente, normal_style)]], colWidths=[6.5*inch])
            obs_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#fafafa')),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('GRID', (0, 0), (-1, -1), 0.3, colors.grey),
            ]))
            elementos.append(obs_table)
            elementos.append(Spacer(1, 0.04 * inch))
        
        diagnostico = registro.get('diagnostico', '')
        if diagnostico:
            elementos.append(Paragraph("Diagnóstico realizado", titulo_seccion))
            diag_table = Table([[Paragraph(diagnostico, normal_style)]], colWidths=[6.5*inch])
            diag_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#fafafa')),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('GRID', (0, 0), (-1, -1), 0.3, colors.grey),
            ]))
            elementos.append(diag_table)
            elementos.append(Spacer(1, 0.04 * inch))
        
        reparacion = registro.get('reparacion', '')
        if reparacion:
            elementos.append(Paragraph("Reparación realizada", titulo_seccion))
            rep_table = Table([[Paragraph(reparacion, normal_style)]], colWidths=[6.5*inch])
            rep_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#fafafa')),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('GRID', (0, 0), (-1, -1), 0.3, colors.grey),
            ]))
            elementos.append(rep_table)
            elementos.append(Spacer(1, 0.04 * inch))
        
        resultado = registro.get('resultado', 'pendiente')
        resultado_map = {
            'reparado': ('✅ Reparado', verde_oscuro),
            'pendiente': ('⏳ Pendiente', naranja),
            'derivado': ('↗️ Derivado', rojo)
        }
        resultado_texto, resultado_color = resultado_map.get(resultado, ('⏳ Pendiente', naranja))
        
        resultado_style = ParagraphStyle(
            'ResultadoStyle',
            parent=normal_style,
            textColor=resultado_color,
            fontName='Helvetica-Bold',
            fontSize=10
        )
        
        resultado_table = Table(
            [[Paragraph(f"<b>Resultado:</b> {resultado_texto}", resultado_style)]],
            colWidths=[6.5*inch]
        )
        resultado_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f0f7f0')),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('GRID', (0, 0), (-1, -1), 0.3, colors.grey),
        ]))
        elementos.append(resultado_table)
        elementos.append(Spacer(1, 0.04 * inch))
        
        obs_pago = registro.get('observaciones_pago', '')
        if obs_pago:
            elementos.append(Paragraph("Observaciones", titulo_seccion))
            obs_pago_table = Table([[Paragraph(obs_pago, normal_style)]], colWidths=[6.5*inch])
            obs_pago_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#fafafa')),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('GRID', (0, 0), (-1, -1), 0.3, colors.grey),
            ]))
            elementos.append(obs_pago_table)
            elementos.append(Spacer(1, 0.04 * inch))
        
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
        
        tabla_control = Table(control_data, colWidths=[2*inch, 2*inch, 2.5*inch])
        tabla_control.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('GRID', (0, 0), (-1, -1), 0.3, colors.grey),
            ('BACKGROUND', (0, 0), (-1, -1), gris_claro),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elementos.append(tabla_control)
        elementos.append(Spacer(1, 0.06 * inch))
        
        linea_final = Table([['']], colWidths=[7*inch])
        linea_final.setStyle(TableStyle([
            ('LINEABOVE', (0, 0), (-1, -1), 1, verde_oscuro),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ]))
        elementos.append(linea_final)
        elementos.append(Spacer(1, 0.05 * inch))
        
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
