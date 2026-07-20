# Backend/routes/reporte_routes.py
from flask import Blueprint, request, jsonify, send_file
from database import get_connection, get_cursor
from utils.seguridad import sanitizar_input, sanitizar_numero, validar_filtro
from utils.fecha_utils import get_fecha_chile, now_santiago
from services.pago_service import PagoService
import io
import logging
from datetime import datetime, timedelta
import pytz
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

logger = logging.getLogger(__name__)
reporte_bp = Blueprint('reporte', __name__, url_prefix='/api')

# ============================================
# REPORTE DE STOCK BAJO
# ============================================

@reporte_bp.route('/reporte_stock_bajo', methods=['POST'])
def generar_reporte_stock_bajo():
    """Genera un PDF con el reporte de stock bajo"""
    try:
        data = request.json
        proveedor_filtro = data.get('proveedor', 'todos')
        stock_minimo = int(data.get('stock_minimo', 5))
        
        chile_tz = pytz.timezone('America/Santiago')
        ahora = datetime.now(chile_tz)
        
        # Obtener productos con stock bajo
        productos = PagoService.obtener_repuestos_con_stock(stock_minimo, proveedor_filtro)
        proveedores = PagoService.obtener_proveedores_repuestos()
        
        if not productos:
            return jsonify({
                "error": f"No hay productos con stock menor o igual a {stock_minimo}",
                "proveedores": proveedores
            }), 404
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(letter),
            rightMargin=40,
            leftMargin=40,
            topMargin=40,
            bottomMargin=40
        )
        
        styles = getSampleStyleSheet()
        elementos = []
        
        titulo_style = ParagraphStyle(
            'Titulo',
            parent=styles['Heading1'],
            fontSize=22,
            textColor=colors.HexColor('#1a4d2e'),
            alignment=1,
            spaceAfter=6,
            fontName='Helvetica-Bold'
        )
        
        subtitulo_style = ParagraphStyle(
            'Subtitulo',
            parent=styles['Normal'],
            fontSize=12,
            textColor=colors.HexColor('#666666'),
            alignment=1,
            spaceAfter=20,
            fontName='Helvetica'
        )
        
        titulo = Paragraph("DIXON ELECTRICIDAD AUTOMOTRIZ", titulo_style)
        elementos.append(titulo)
        
        subtitulo = Paragraph("Reporte de Stock Bajo", subtitulo_style)
        elementos.append(subtitulo)
        
        info_style = ParagraphStyle(
            'Info',
            parent=styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#333333'),
            alignment=0,
            spaceAfter=8,
            fontName='Helvetica'
        )
        
        fecha_str = ahora.strftime('%d/%m/%Y %H:%M')
        info_text = f"""
        <b>Fecha de emisión:</b> {fecha_str}<br/>
        <b>Stock mínimo:</b> {stock_minimo} unidades<br/>
        <b>Proveedor filtrado:</b> {proveedor_filtro if proveedor_filtro != 'todos' else 'Todos'}<br/>
        <b>Total de productos con stock bajo:</b> {len(productos)}
        """
        info = Paragraph(info_text, info_style)
        elementos.append(info)
        elementos.append(Spacer(1, 0.15 * inch))
        
        table_data = [
            ['ID', 'Producto', 'Stock', 'Costo Proveedor ($)', 'Margen (%)', 'Precio Venta ($)', 'Proveedor', 'Categoría']
        ]
        
        for p in productos:
            table_data.append([
                str(p['id']),
                p['nombre'][:30] + '...' if len(p['nombre']) > 30 else p['nombre'],
                str(p['stock'] or 0),
                f"{p['costo_proveedor']:,.0f}" if p['costo_proveedor'] else 'Pendiente',
                f"{p['margen_ganancia']:.1f}%" if p['margen_ganancia'] else '0%',
                f"{p['costo_venta_final']:,.0f}" if p['costo_venta_final'] else 'N/A',
                p['proveedor'] or 'Sin proveedor',
                p['categoria_nombre'] or 'Sin categoría'
            ])
        
        col_widths = [0.5*inch, 2.5*inch, 0.7*inch, 1.0*inch, 0.8*inch, 1.0*inch, 1.2*inch, 1.2*inch]
        tabla = Table(table_data, colWidths=col_widths, repeatRows=1)
        tabla.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a4d2e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ('TOPPADDING', (0, 0), (-1, 0), 6),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ALIGN', (2, 1), (2, -1), 'CENTER'),
            ('ALIGN', (3, 1), (5, -1), 'RIGHT'),
            ('VALIGN', (0, 1), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#2e3138')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')]),
        ]))
        
        elementos.append(tabla)
        elementos.append(Spacer(1, 0.2 * inch))
        
        total_productos = len(productos)
        stock_total = sum(p.get('stock', 0) for p in productos)
        
        resumen_style = ParagraphStyle(
            'Resumen',
            parent=styles['Normal'],
            fontSize=12,
            textColor=colors.HexColor('#1a4d2e'),
            alignment=2,
            spaceBefore=10,
            fontName='Helvetica-Bold'
        )
        
        resumen_text = f"""
        <b>Resumen del Reporte</b><br/>
        Total de productos con stock bajo: {total_productos}<br/>
        Stock total de estos productos: {stock_total} unidades
        """
        resumen = Paragraph(resumen_text, resumen_style)
        elementos.append(resumen)
        
        pie_style = ParagraphStyle(
            'Pie',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#666666'),
            alignment=1,
            spaceBefore=30,
            fontName='Helvetica'
        )
        
        pie_text = f"""
        <b>Dixon Electricidad Automotriz</b><br/>
        Neptuno 163, Local C, Lo Prado, RM, Chile<br/>
        +569 9855 0331<br/>
        Reporte generado automáticamente el {ahora.strftime('%d/%m/%Y %H:%M')}
        """
        pie = Paragraph(pie_text, pie_style)
        elementos.append(pie)
        
        doc.build(elementos)
        buffer.seek(0)
        
        nombre_archivo = f'reporte_stock_bajo_{ahora.strftime("%Y%m%d_%H%M")}.pdf'
        
        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=nombre_archivo
        )
        
    except Exception as e:
        logger.error(f"Error en generar_reporte_stock_bajo: {e}")
        return jsonify({"error": str(e)}), 500

# ============================================
# GANANCIA REAL
# ============================================

@reporte_bp.route('/ganancia_real', methods=['GET'])
def get_ganancia_real():
    """Obtiene la ganancia real (ventas - costos - gastos)"""
    try:
        filtro = request.args.get('filtro', 'hoy')
        fecha_inicio = request.args.get('fecha_inicio')
        fecha_fin = request.args.get('fecha_fin')
        
        if not validar_filtro(filtro):
            return jsonify({"error": "Filtro inválido"}), 400
        
        hoy = get_fecha_chile()
        conn, cur = get_cursor()
        
        # Construir query de ventas
        query_ventas = """
            SELECT 
                COALESCE(SUM(monto), 0) as total_ventas,
                COALESCE(SUM(costo_repuestos_real), 0) as total_costos_repuestos,
                COALESCE(SUM(costo_mano_obra_real), 0) as total_mano_obra,
                COALESCE(SUM(costo_diagnostico_real), 0) as total_diagnostico,
                COALESCE(SUM(ganancia_neta), 0) as ganancia_neta
            FROM pagos 
            WHERE estado = 'pagado' AND estado_pago = 'pagado'
        """
        params_ventas = []
        
        if fecha_inicio and fecha_fin:
            query_ventas += " AND fecha BETWEEN %s AND %s"
            params_ventas.extend([fecha_inicio, fecha_fin])
        elif filtro == 'hoy':
            query_ventas += " AND fecha = %s"
            params_ventas.append(hoy.strftime('%Y-%m-%d'))
        elif filtro == '7d':
            query_ventas += " AND fecha >= %s"
            params_ventas.append((hoy - timedelta(days=7)).strftime('%Y-%m-%d'))
        elif filtro == 'mes':
            query_ventas += " AND fecha >= %s"
            params_ventas.append((hoy - timedelta(days=30)).strftime('%Y-%m-%d'))
        elif filtro == 'anio':
            query_ventas += " AND fecha >= %s"
            params_ventas.append((hoy - timedelta(days=365)).strftime('%Y-%m-%d'))
        
        cur.execute(query_ventas, params_ventas)
        ventas_data = cur.fetchone()
        
        # Construir query de gastos
        query_gastos = """
            SELECT 
                COALESCE(SUM(CASE WHEN metodo_pago = 'efectivo' THEN monto ELSE 0 END), 0) as gastos_efectivo,
                COALESCE(SUM(CASE WHEN metodo_pago = 'transferencia' THEN monto ELSE 0 END), 0) as gastos_transferencia,
                COALESCE(SUM(monto), 0) as total_gastos,
                COALESCE(SUM(CASE WHEN categoria = 'Sueldos' THEN monto ELSE 0 END), 0) as gastos_sueldos,
                COALESCE(SUM(CASE WHEN categoria = 'Arriendo' THEN monto ELSE 0 END), 0) as gastos_arriendo,
                COALESCE(SUM(CASE WHEN categoria = 'Servicios Públicos' THEN monto ELSE 0 END), 0) as gastos_servicios,
                COALESCE(SUM(CASE WHEN categoria = 'Alimentación' THEN monto ELSE 0 END), 0) as gastos_alimentacion,
                COALESCE(SUM(CASE WHEN categoria = 'Herramientas' THEN monto ELSE 0 END), 0) as gastos_herramientas,
                COALESCE(SUM(CASE WHEN categoria = 'Impuestos' THEN monto ELSE 0 END), 0) as gastos_impuestos,
                COALESCE(SUM(CASE WHEN categoria = 'Otros' THEN monto ELSE 0 END), 0) as gastos_otros
            FROM gastos
        """
        params_gastos = []
        
        if fecha_inicio and fecha_fin:
            query_gastos += " WHERE fecha BETWEEN %s AND %s"
            params_gastos.extend([fecha_inicio, fecha_fin])
        elif filtro == 'hoy':
            query_gastos += " WHERE fecha = %s"
            params_gastos.append(hoy.strftime('%Y-%m-%d'))
        elif filtro == '7d':
            query_gastos += " WHERE fecha >= %s"
            params_gastos.append((hoy - timedelta(days=7)).strftime('%Y-%m-%d'))
        elif filtro == 'mes':
            query_gastos += " WHERE fecha >= %s"
            params_gastos.append((hoy - timedelta(days=30)).strftime('%Y-%m-%d'))
        elif filtro == 'anio':
            query_gastos += " WHERE fecha >= %s"
            params_gastos.append((hoy - timedelta(days=365)).strftime('%Y-%m-%d'))
        
        cur.execute(query_gastos, params_gastos)
        gastos_data = cur.fetchone()
        
        cur.close()
        conn.close()
        
        ventas = {
            'total_ventas': float(ventas_data[0] or 0),
            'total_costos_repuestos': float(ventas_data[1] or 0),
            'total_mano_obra': float(ventas_data[2] or 0),
            'total_diagnostico': float(ventas_data[3] or 0),
            'ganancia_neta': float(ventas_data[4] or 0)
        }
        
        gastos = {
            'gastos_efectivo': float(gastos_data[0] or 0),
            'gastos_transferencia': float(gastos_data[1] or 0),
            'total_gastos': float(gastos_data[2] or 0),
            'gastos_sueldos': float(gastos_data[3] or 0),
            'gastos_arriendo': float(gastos_data[4] or 0),
            'gastos_servicios': float(gastos_data[5] or 0),
            'gastos_alimentacion': float(gastos_data[6] or 0),
            'gastos_herramientas': float(gastos_data[7] or 0),
            'gastos_impuestos': float(gastos_data[8] or 0),
            'gastos_otros': float(gastos_data[9] or 0)
        }
        
        ganancia_real = ventas['total_ventas'] - ventas['total_costos_repuestos'] - gastos['total_gastos']
        
        return jsonify({
            'ventas': ventas,
            'gastos': gastos,
            'ganancia_real': round(ganancia_real, 2),
            'filtro': filtro,
            'fecha_inicio': fecha_inicio,
            'fecha_fin': fecha_fin
        })
        
    except Exception as e:
        logger.error(f"Error en get_ganancia_real: {e}")
        return jsonify({"error": str(e)}), 500
