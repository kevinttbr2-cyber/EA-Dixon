# Backend/services/pdf_service.py
import io
import hmac
import hashlib
import os
from datetime import datetime
from config import Config

# ReportLab base
from reportlab.lib.pagesizes import letter
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph,
    Spacer, Image, HRFlowable
)

# ReportLab extras del modelo profesional
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.textlabels import Label
from reportlab.pdfgen import canvas
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.lib.units import inch, cm

from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

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
            rightMargin=40,
            leftMargin=40,
            topMargin=30,
            bottomMargin=30
        )

        styles = getSampleStyleSheet()

        # PALETA VERDE INSTITUCIONAL
        VERDE_OSCURO = colors.HexColor('#1a4d2e')
        VERDE_MEDIO = colors.HexColor('#2a6d44')
        GRIS_CLARO = colors.HexColor('#f5f5f5')
        GRIS_MEDIO = colors.HexColor('#555555')
        GRIS_BORDE = colors.HexColor('#cccccc')
        GRIS_FONDO = colors.HexColor('#f8f9fa')
        GRIS_HEADER = colors.HexColor('#e9ecef')
        ROJO = colors.HexColor('#cc0000')

        # ESTILOS
        title_style = ParagraphStyle(
            'TitleCustom',
            parent=styles['Heading1'],
            fontSize=22,
            textColor=VERDE_OSCURO,
            spaceAfter=4,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )

        subtitle_style = ParagraphStyle(
            'SubtitleCustom',
            parent=styles['Normal'],
            fontSize=10,
            textColor=GRIS_MEDIO,
            alignment=TA_CENTER,
            spaceAfter=12,
            fontName='Helvetica'
        )

        section_style = ParagraphStyle(
            'SectionTitle',
            parent=styles['Heading3'],
            fontSize=11,
            textColor=colors.white,
            fontName='Helvetica-Bold',
            alignment=TA_LEFT,
            leading=14
        )

        label_style = ParagraphStyle(
            'LabelStyle',
            parent=styles['Normal'],
            fontSize=9,
            textColor=GRIS_MEDIO,
            fontName='Helvetica-Bold',
            leading=12
        )

        value_style = ParagraphStyle(
            'ValueStyle',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.black,
            fontName='Helvetica',
            leading=12
        )

        footer_style = ParagraphStyle(
            'FooterStyle',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#777777'),
            alignment=TA_CENTER,
            fontName='Helvetica'
        )

        elements = []

        # ============ ENCABEZADO ============
        header_data = [
            [
                Paragraph(
                    f"<b>{registro.get('empresa','DIXON')}</b>",
                    ParagraphStyle('Empresa', parent=styles['Normal'], fontSize=26,
                                   textColor=VERDE_OSCURO, fontName='Helvetica-Bold',
                                   alignment=TA_LEFT, leading=28)
                ),
                Paragraph(
                    "<b>ORDEN DE TRABAJO</b>",
                    ParagraphStyle('OTTitle', parent=styles['Normal'], fontSize=18,
                                   textColor=VERDE_OSCURO, fontName='Helvetica-Bold',
                                   alignment=TA_RIGHT, leading=20)
                )
            ],
            [
                Paragraph(
                    registro.get('empresa_sub','Electricidad Automotriz'),
                    ParagraphStyle('EmpresaSub', parent=styles['Normal'], fontSize=11,
                                   textColor=GRIS_MEDIO, fontName='Helvetica',
                                   alignment=TA_LEFT, leading=14)
                ),
                Paragraph(
                    f"N° <b>{registro.get('id','')}</b>",
                    ParagraphStyle('OTNum', parent=styles['Normal'], fontSize=14,
                                   textColor=ROJO, fontName='Helvetica-Bold',
                                   alignment=TA_RIGHT, leading=16)
                )
            ]
        ]

        header_table = Table(header_data, colWidths=[doc.width*0.55, doc.width*0.45])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 8))

        # Línea separadora verde
        elements.append(HRFlowable(width="100%", thickness=3, color=VERDE_OSCURO, spaceBefore=0, spaceAfter=12))

        # ============ DATOS GENERALES ============
        section_header = Table([[Paragraph("DATOS DEL VEHÍCULO Y CLIENTE", section_style)]], colWidths=[doc.width])
        section_header.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), VERDE_OSCURO),
            ('LEFTPADDING', (0,0), (-1,-1), 8),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ]))
        elements.append(section_header)

        info_data = [
            [Paragraph("<b>Cliente:</b>", label_style), Paragraph(registro.get('nombre',''), value_style),
             Paragraph("<b>Fecha:</b>", label_style), Paragraph(registro.get('fecha',''), value_style)],

            [Paragraph("<b>Patente:</b>", label_style), Paragraph(registro.get('patente',''), value_style),
             Paragraph("<b>Teléfono:</b>", label_style), Paragraph(registro.get('telefono','—'), value_style)],

            [Paragraph("<b>Marca/Modelo:</b>", label_style),
             Paragraph(f"{registro.get('marca','')} {registro.get('modelo','')}", value_style),
             Paragraph("<b>Año:</b>", label_style), Paragraph(registro.get('anio','—'), value_style)],

            [Paragraph("<b>Kilometraje:</b>", label_style),
             Paragraph(f"{registro.get('kilometraje','0')} km", value_style),
             Paragraph("", label_style), Paragraph("", value_style)],
        ]

        info_table = Table(info_data, colWidths=[doc.width*0.15, doc.width*0.35, doc.width*0.15, doc.width*0.35])
        info_table.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.5, GRIS_BORDE),
            ('BACKGROUND', (0,0), (-1,-1), GRIS_FONDO),
            ('LEFTPADDING', (0,0), (-1,-1), 8),
            ('RIGHTPADDING', (0,0), (-1,-1), 8),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('BACKGROUND', (0,0), (0,-1), GRIS_HEADER),
            ('BACKGROUND', (2,0), (2,-1), GRIS_HEADER),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 10))

        # ============ OBSERVACIONES ============
        section_header2 = Table([[Paragraph("OBSERVACIONES DEL INGRESO", section_style)]], colWidths=[doc.width])
        section_header2.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), VERDE_OSCURO),
            ('LEFTPADDING', (0,0), (-1,-1), 8),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ]))
        elements.append(section_header2)

        obs_data = [[Paragraph(registro.get('observaciones_cliente',''), value_style)]]
        obs_table = Table(obs_data, colWidths=[doc.width])
        obs_table.setStyle(TableStyle([
            ('BOX', (0,0), (-1,-1), 0.5, GRIS_BORDE),
            ('LEFTPADDING', (0,0), (-1,-1), 10),
            ('TOPPADDING', (0,0), (-1,-1), 10),
            ('BOTTOMPADDING', (0,0), (-1,-1), 10),
            ('BACKGROUND', (0,0), (-1,-1), GRIS_FONDO),
        ]))
        elements.append(obs_table)
        elements.append(Spacer(1, 10))

        # ============ DIAGNÓSTICO ============
        section_header3 = Table([[Paragraph("DIAGNÓSTICO REALIZADO", section_style)]], colWidths=[doc.width])
        section_header3.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), VERDE_OSCURO),
            ('LEFTPADDING', (0,0), (-1,-1), 8),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ]))
        elements.append(section_header3)

        diag_data = [[Paragraph(registro.get('diagnostico',''), value_style)]]
        diag_table = Table(diag_data, colWidths=[doc.width])
        diag_table.setStyle(TableStyle([
            ('BOX', (0,0), (-1,-1), 0.5, GRIS_BORDE),
            ('LEFTPADDING', (0,0), (-1,-1), 10),
            ('TOPPADDING', (0,0), (-1,-1), 10),
            ('BOTTOMPADDING', (0,0), (-1,-1), 10),
            ('BACKGROUND', (0,0), (-1,-1), GRIS_FONDO),
        ]))
        elements.append(diag_table)
        elements.append(Spacer(1, 10))

        # ============ REPARACIÓN ============
        section_header4 = Table([[Paragraph("REPARACIÓN REALIZADA", section_style)]], colWidths=[doc.width])
        section_header4.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), VERDE_OSCURO),
            ('LEFTPADDING', (0,0), (-1,-1), 8),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ]))
        elements.append(section_header4)

        rep_data = [[Paragraph(registro.get('reparacion',''), value_style)]]
        rep_table = Table(rep_data, colWidths=[doc.width])
        rep_table.setStyle(TableStyle([
            ('BOX', (0,0), (-1,-1), 0.5, GRIS_BORDE),
            ('LEFTPADDING', (0,0), (-1,-1), 10),
            ('TOPPADDING', (0,0), (-1,-1), 10),
            ('BOTTOMPADDING', (0,0), (-1,-1), 10),
            ('BACKGROUND', (0,0), (-1,-1), GRIS_FONDO),
        ]))
        elements.append(rep_table)
        elements.append(Spacer(1, 10))

        # ============ RESULTADO + CONTROL INTERNO ============
        res_section = Table([[Paragraph("RESULTADO", section_style)]], colWidths=[doc.width*0.48])
        res_section.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), VERDE_OSCURO),
            ('LEFTPADDING', (0,0), (-1,-1), 8),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ]))

        ci_section = Table([[Paragraph("CONTROL INTERNO", section_style)]], colWidths=[doc.width*0.48])
        ci_section.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), VERDE_OSCURO),
            ('LEFTPADDING', (0,0), (-1,-1), 8),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ]))

        header_two = Table([[res_section, '', ci_section]], colWidths=[doc.width*0.48, doc.width*0.04, doc.width*0.48])
        elements.append(header_two)

        resultado_texto = registro.get('resultado','Pendiente')
        resultado_color = VERDE_MEDIO if resultado_texto.lower() == 'reparado' else ROJO

        res_value = Table(
            [[Paragraph(f"<font color='{resultado_color}'><b>✓ {resultado_texto}</b></font>",
                        ParagraphStyle('ResOK', parent=styles['Normal'], fontSize=11,
                                       fontName='Helvetica', leading=14))]],
            colWidths=[doc.width*0.48]
        )
        res_value.setStyle(TableStyle([
            ('BOX', (0,0), (-1,-1), 0.5, GRIS_BORDE),
            ('LEFTPADDING', (0,0), (-1,-1), 10),
            ('TOPPADDING', (0,0), (-1,-1), 10),
            ('BOTTOMPADDING', (0,0), (-1,-1), 10),
            ('BACKGROUND', (0,0), (-1,-1), GRIS_FONDO),
        ]))

        ci_data = [
            [Paragraph("<b>Técnico:</b>", label_style), Paragraph(registro.get('atendido_por',''), value_style)],
            [Paragraph("<b>Tiempo:</b>", label_style), Paragraph(registro.get('tiempo_estimado',''), value_style)],
            [Paragraph("<b>Total:</b>", label_style),
             Paragraph(f"<b>${float(registro.get('monto',0)):,.0f}</b>",
                       ParagraphStyle('TotalStyle', parent=value_style,
                                      textColor=ROJO, fontName='Helvetica-Bold'))],
        ]

        ci_value = Table(ci_data, colWidths=[doc.width*0.18, doc.width*0.30])
        ci_value.setStyle(TableStyle([
            ('BOX', (0,0), (-1,-1), 0.5, GRIS_BORDE),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e0e0e0')),
            ('LEFTPADDING', (0,0), (-1,-1), 8),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('BACKGROUND', (0,0), (-1,-1), GRIS_FONDO),
            ('BACKGROUND', (0,0), (0,-1), GRIS_HEADER),
        ]))

        body_two = Table([[res_value, '', ci_value]], colWidths=[doc.width*0.48, doc.width*0.04, doc.width*0.48])
        elements.append(body_two)
        elements.append(Spacer(1, 14))

        # ============ FIRMAS ============
        sign_data = [
            ['', ''],
            ['_________________________', '_________________________'],
            [
                Paragraph("<b>Firma Cliente</b>", ParagraphStyle('Firma', parent=styles['Normal'], fontSize=9, alignment=TA_CENTER)),
                Paragraph("<b>Firma Técnico</b>", ParagraphStyle('Firma2', parent=styles['Normal'], fontSize=9, alignment=TA_CENTER))
            ],
        ]

        sign_table = Table(sign_data, colWidths=[doc.width*0.45, doc.width*0.45])
        sign_table.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'BOTTOM'),
            ('TOPPADDING', (0,0), (0,0), 30),
            ('TOPPADDING', (1,0), (1,0), 30),
        ]))
        elements.append(sign_table)
        elements.append(Spacer(1, 12))

        # ============ PIE DE PÁGINA ============
        elements.append(HRFlowable(width="100%", thickness=1, color=GRIS_BORDE, spaceBefore=0, spaceAfter=6))

        footer_text = f"Dixon Electricidad Automotriz · {registro.get('telefono','')} · {registro.get('direccion','')}"
        elements.append(Paragraph(footer_text, footer_style))

        fecha_gen = datetime.now().strftime('%d/%m/%Y %H:%M')
        elements.append(Paragraph(f"Reporte generado el {fecha_gen} · OT N° {registro.get('id','')}",
                                  ParagraphStyle('Footer2', parent=styles['Normal'], fontSize=8,
                                                 textColor=colors.HexColor('#777777'),
                                                 alignment=TA_CENTER, fontName='Helvetica')))

        # ============ CONSTRUIR PDF ============
        try:
            doc.build(elements)
            buffer.seek(0)
            return buffer
        except Exception as e:
            logger.error(f"Error generando PDF: {e}")
            return None
