import io
import hmac
import hashlib
from config import Config
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

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
    def generar_pdf(registro):
        """Genera un PDF formal de Orden de Trabajo"""
        try:
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=60, leftMargin=60, topMargin=45, bottomMargin=45)
            styles = getSampleStyleSheet()
            
            verde_oscuro = colors.HexColor('#1a4d2e')
            gris_claro = colors.HexColor('#f5f5f5')
            
            elementos = []
            
            # Título
            titulo_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=18, textColor=verde_oscuro, alignment=1)
            elementos.append(Paragraph("DIXON ELECTRICIDAD AUTOMOTRIZ", titulo_style))
            elementos.append(Paragraph("ORDEN DE TRABAJO", ParagraphStyle('Subtitle', parent=styles['Heading2'], fontSize=14, textColor=verde_oscuro, alignment=1)))
            elementos.append(Spacer(1, 0.1*inch))
            
            # Datos del cliente
            datos_data = [
                ['N° OT', str(registro.id), 'Fecha', registro.fecha.strftime('%d/%m/%Y') if registro.fecha else ''],
                ['Cliente', registro.nombre or '', 'Teléfono', registro.telefono or ''],
                ['Patente', registro.patente or '', 'Marca/Modelo', f"{registro.marca or ''} {registro.modelo or ''}"],
                ['Kilometraje', f"{registro.kilometraje or 0} km", 'Hora Ingreso', registro.hora or ''],
            ]
            
            table_data = []
            for row in datos_data:
                table_data.append([
                    Paragraph(f"<b>{row[0]}</b>", styles['Normal']),
                    Paragraph(str(row[1] or ''), styles['Normal']),
                    Paragraph(f"<b>{row[2]}</b>", styles['Normal']),
                    Paragraph(str(row[3] or ''), styles['Normal'])
                ])
            
            tabla = Table(table_data, colWidths=[0.7*inch, 1.4*inch, 0.7*inch, 1.4*inch])
            tabla.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('BACKGROUND', (0, 0), (0, -1), gris_claro),
                ('BACKGROUND', (2, 0), (2, -1), gris_claro),
            ]))
            elementos.append(tabla)
            elementos.append(Spacer(1, 0.1*inch))
            
            # Diagnóstico
            if registro.diagnostico:
                elementos.append(Paragraph("<b>Diagnóstico:</b>", styles['Normal']))
                elementos.append(Paragraph(registro.diagnostico, styles['Normal']))
                elementos.append(Spacer(1, 0.05*inch))
            
            # Reparación
            if registro.reparacion:
                elementos.append(Paragraph("<b>Reparación realizada:</b>", styles['Normal']))
                elementos.append(Paragraph(registro.reparacion, styles['Normal']))
                elementos.append(Spacer(1, 0.05*inch))
            
            # Resultado
            resultado_map = {
                'reparado': '✅ Reparado',
                'pendiente': '⏳ Pendiente',
                'derivado': '↗️ Derivado'
            }
            resultado_texto = resultado_map.get(registro.resultado, '⏳ Pendiente')
            elementos.append(Paragraph(f"<b>Resultado:</b> {resultado_texto}", styles['Normal']))
            elementos.append(Spacer(1, 0.05*inch))
            
            # Total
            elementos.append(Paragraph(f"<b>Total:</b> ${registro.monto:,.0f}", styles['Normal']))
            elementos.append(Spacer(1, 0.1*inch))
            
            # Pie de página
            from datetime import datetime
            pie_text = f"""
            <b>Dixon Electricidad Automotriz</b><br/>
            📱 +569 9855 0331 · 📍 Neptuno 163, Local C, Lo Prado, RM<br/>
            Reporte generado el {datetime.now().strftime('%d/%m/%Y %H:%M')}
            """
            pie_style = ParagraphStyle('Pie', parent=styles['Normal'], fontSize=8, textColor=colors.HexColor('#666666'), alignment=1)
            elementos.append(Paragraph(pie_text, pie_style))
            
            doc.build(elementos)
            buffer.seek(0)
            return buffer
            
        except Exception as e:
            print(f"Error generando PDF: {e}")
            return None