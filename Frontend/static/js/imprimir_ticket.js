// ============================================
// FUNCIONES DE IMPRESIÓN DE TICKETS
// ============================================

// Importar la clase ThermalPrinter
// Si usas módulos ES6
// import ThermalPrinter from './imprimir.js';

// Si usas script tradicional
// const ThermalPrinter = require('./imprimir.js');

// ============================================
// FUNCIÓN PARA IMPRIMIR TICKET
// ============================================
export async function imprimirTicket(datos) {
    const printer = new ThermalPrinter();

    try {
        // Conectar
        const conectado = await printer.connect();
        if (!conectado) {
            return false;
        }

        // Datos del ticket
        const ticketData = {
            folio: datos.folio || '001',
            fecha: datos.fecha || new Date().toLocaleDateString('es-CL'),
            hora: datos.hora || new Date().toLocaleTimeString('es-CL'),
            cliente: datos.cliente || 'Consumidor Final',
            productos: datos.productos || [],
            total: datos.total || 0,
            forma_pago: datos.forma_pago || 'Efectivo',
            vuelto: datos.vuelto || 0,
            barcode: datos.barcode || datos.folio || '1234567890',
            qr: datos.qr || window.location.href
        };

        const resultado = await printer.printTicket(ticketData);
        await printer.disconnect();
        return resultado;

    } catch (error) {
        console.error('Error en imprimirTicket:', error);
        await printer.disconnect();
        return false;
    }
}

// ============================================
// FUNCIÓN PARA PRUEBA RÁPIDA
// ============================================
export async function imprimirPrueba() {
    const printer = new ThermalPrinter();

    try {
        const conectado = await printer.connect();
        if (!conectado) {
            alert('No se pudo conectar a la impresora');
            return;
        }

        await printer.init();
        await printer.text('PRUEBA DE IMPRESION', { align: 'center', bold: true, size: 'double' });
        await printer.dashLine();
        await printer.text('¡La impresora funciona correctamente!', { align: 'center' });
        await printer.newLine();
        await printer.barcode('1234567890', { format: 'CODE128', height: 50, align: 'center' });
        await printer.newLine(3);
        await printer.cut();

        console.log('✅ Prueba exitosa');
        await printer.disconnect();
        alert('✅ Prueba de impresión exitosa');

    } catch (error) {
        console.error('❌ Error en prueba:', error);
        alert('Error en prueba: ' + error.message);
        await printer.disconnect();
    }
}
