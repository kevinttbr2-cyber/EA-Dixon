// ============================================
// IMPRESORA TÉRMICA - XP-58IIH
// Controlador principal
// ============================================

class ThermalPrinter {
    constructor() {
        this.device = null;
        this.interface = null;
        this.endpointIn = null;
        this.endpointOut = null;
        this.connected = false;
        
        // IDs de XP-58IIH (ajusta según tu impresora)
        this.VENDOR_ID = 0x6868;  // o 0x0483
        this.PRODUCT_ID = 0x0200; // o 0x5740
    }

    // ============================================
    // CONECTAR A LA IMPRESORA
    // ============================================
    async connect() {
        try {
            // Verificar si WebUSB está disponible
            if (!navigator.usb) {
                throw new Error('WebUSB no está disponible. Usa Chrome/Edge/Opera.');
            }

            // Solicitar permisos al usuario
            this.device = await navigator.usb.requestDevice({
                filters: [
                    { vendorId: this.VENDOR_ID, productId: this.PRODUCT_ID },
                    { vendorId: 0x6868 }, // fallback
                    { vendorId: 0x0483 }, // fallback
                    { vendorId: 0x1A86, productId: 0x7584 } // otro común
                ]
            });

            await this.device.open();

            // Configurar la interfaz
            if (this.device.configuration === null) {
                await this.device.selectConfiguration(1);
            }

            await this.device.claimInterface(0);

            // Encontrar endpoints
            const interfaces = this.device.configuration.interfaces;
            for (const iface of interfaces) {
                if (iface.alternate.endpoints.length > 0) {
                    for (const endpoint of iface.alternate.endpoints) {
                        if (endpoint.direction === 'out') {
                            this.endpointOut = endpoint.endpointNumber;
                        }
                        if (endpoint.direction === 'in') {
                            this.endpointIn = endpoint.endpointNumber;
                        }
                    }
                }
            }

            this.connected = true;
            console.log('✅ Impresora conectada');
            return true;

        } catch (error) {
            console.error('❌ Error conectando impresora:', error);
            if (error.message.includes('No device selected')) {
                alert('No seleccionaste ninguna impresora');
            } else if (error.message.includes('No WebUSB')) {
                alert('Este navegador no soporta WebUSB. Usa Chrome, Edge u Opera.');
            } else {
                alert('Error al conectar: ' + error.message);
            }
            return false;
        }
    }

    // ============================================
    // ENVIAR DATOS A LA IMPRESORA
    // ============================================
    async sendData(data) {
        if (!this.connected || !this.device) {
            throw new Error('Impresora no conectada');
        }

        try {
            await this.device.transferOut(this.endpointOut, data);
        } catch (error) {
            console.error('❌ Error enviando datos:', error);
            throw error;
        }
    }

    // ============================================
    // COMANDOS ESC/POS
    // ============================================

    // Inicializar impresora
    async init() {
        const buffer = new Uint8Array([0x1B, 0x40]);
        await this.sendData(buffer);
    }

    // Texto normal
    async text(text, options = {}) {
        const bytes = [];
        
        // Alineación
        if (options.align === 'center') {
            bytes.push(0x1B, 0x61, 0x01);
        } else if (options.align === 'right') {
            bytes.push(0x1B, 0x61, 0x02);
        } else {
            bytes.push(0x1B, 0x61, 0x00);
        }

        // Negrita
        if (options.bold) {
            bytes.push(0x1B, 0x45, 0x01);
        }

        // Tamaño de fuente (double)
        if (options.size === 'double') {
            bytes.push(0x1D, 0x21, 0x11); // Doble alto y ancho
        } else if (options.size === 'large') {
            bytes.push(0x1D, 0x21, 0x22); // Triple alto y ancho
        } else {
            bytes.push(0x1D, 0x21, 0x00); // Normal
        }

        // Texto
        const textBytes = new TextEncoder().encode(text + '\n');
        bytes.push(...textBytes);

        // Resetear estilo
        if (options.bold) {
            bytes.push(0x1B, 0x45, 0x00);
        }

        await this.sendData(new Uint8Array(bytes));
    }

    // Texto con 2 columnas (producto + precio)
    async text2Col(left, right, options = {}) {
        const leftLength = left.length;
        const maxLeft = 20;
        const paddedLeft = left.padEnd(maxLeft, ' ');
        const rightPadded = right.padStart(12, ' ');
        
        await this.text(paddedLeft + rightPadded, options);
    }

    // Línea de separación
    async dashLine() {
        const line = '-'.repeat(32);
        await this.text(line);
    }

    // Línea de separación doble
    async doubleLine() {
        const line = '='.repeat(32);
        await this.text(line);
    }

    // Salto de línea
    async newLine(count = 1) {
        const bytes = new Uint8Array(count * 2);
        bytes.fill(0x0A);
        await this.sendData(bytes);
    }

    // Cortar papel
    async cut() {
        const buffer = new Uint8Array([0x1D, 0x56, 0x42, 0x00]);
        await this.sendData(buffer);
    }

    // ============================================
    // CÓDIGO DE BARRAS
    // ============================================
    async barcode(data, options = {}) {
        const format = options.format || 'CODE128';
        const width = options.width || 2;
        const height = options.height || 50;
        const displayValue = options.displayValue !== false;

        const bytes = [];

        // Configurar altura del código de barras
        bytes.push(0x1D, 0x68, height);

        // Configurar ancho del código de barras
        bytes.push(0x1D, 0x77, width);

        // Configurar alineación
        if (options.align === 'center') {
            bytes.push(0x1B, 0x61, 0x01);
        } else if (options.align === 'right') {
            bytes.push(0x1B, 0x61, 0x02);
        } else {
            bytes.push(0x1B, 0x61, 0x00);
        }

        // Mostrar valor debajo del código
        if (displayValue) {
            bytes.push(0x1D, 0x48, 0x02);
        } else {
            bytes.push(0x1D, 0x48, 0x00);
        }

        // Seleccionar formato de código de barras
        const formatMap = {
            'CODE128': 0x49,
            'CODE39': 0x00,
            'EAN13': 0x43,
            'EAN8': 0x44,
            'UPC': 0x41,
            'ITF14': 0x46,
            'CODABAR': 0x47
        };

        const formatCode = formatMap[format] || 0x49;
        bytes.push(0x1D, 0x6B, formatCode);

        // Longitud del dato
        const dataLength = data.length;
        bytes.push(dataLength);

        // Datos del código de barras
        const dataBytes = new TextEncoder().encode(data);
        bytes.push(...dataBytes);

        // Comando para imprimir
        bytes.push(0x0A);

        await this.sendData(new Uint8Array(bytes));
    }

    // ============================================
    // CÓDIGO QR
    // ============================================
    async qr(data, options = {}) {
        const size = options.size || 4;
        const errorCorrection = options.errorCorrection || 'M';

        const bytes = [];

        // Configurar tamaño del QR
        bytes.push(0x1D, 0x28, 0x6B, 0x03, 0x00, 0x31, 0x43, size);

        // Configurar nivel de corrección de errores
        const ecMap = { 'L': 0x31, 'M': 0x32, 'Q': 0x33, 'H': 0x34 };
        const ecCode = ecMap[errorCorrection] || 0x32;
        bytes.push(0x1D, 0x28, 0x6B, 0x03, 0x00, 0x31, 0x45, ecCode);

        // Almacenar datos del QR
        const dataBytes = new TextEncoder().encode(data);
        const dataLength = dataBytes.length;
        const lengthLow = dataLength & 0xFF;
        const lengthHigh = (dataLength >> 8) & 0xFF;

        bytes.push(0x1D, 0x28, 0x6B, lengthLow, lengthHigh, 0x31, 0x50, 0x30);
        bytes.push(...dataBytes);

        // Imprimir QR
        bytes.push(0x1D, 0x28, 0x6B, 0x03, 0x00, 0x31, 0x51, 0x30);
        bytes.push(0x0A);

        await this.sendData(new Uint8Array(bytes));
    }

    // ============================================
    // GENERAR TICKET COMPLETO
    // ============================================
    async printTicket(data) {
        try {
            await this.connect();

            if (!this.connected) {
                alert('No se pudo conectar a la impresora');
                return false;
            }

            await this.init();
            await this.newLine(2);

            // ========== ENCABEZADO ==========
            await this.text('TIENDA DIXON', { 
                align: 'center', 
                bold: true, 
                size: 'double' 
            });
            await this.text('ELECTRICIDAD AUTOMOTRIZ', { 
                align: 'center', 
                bold: true 
            });
            await this.text('RUT: 76.123.456-7', { align: 'center' });
            await this.text('Dirección: Calle Principal #123', { align: 'center' });
            await this.dashLine();

            // ========== DATOS DEL TICKET ==========
            await this.text2Col('Folio:', data.folio || '#001');
            await this.text2Col('Fecha:', data.fecha || new Date().toLocaleDateString('es-CL'));
            await this.text2Col('Hora:', data.hora || new Date().toLocaleTimeString('es-CL'));
            await this.text2Col('Cliente:', data.cliente || 'Consumidor Final');
            await this.dashLine();

            // ========== PRODUCTOS ==========
            await this.text('DETALLE:', { bold: true });
            if (data.productos && data.productos.length > 0) {
                for (const item of data.productos) {
                    const label = item.nombre || item.producto || 'Producto';
                    const price = item.precio || item.costo || 0;
                    const qty = item.cantidad || 1;
                    const total = price * qty;
                    await this.text2Col(
                        `${label} x${qty}`,
                        `$${total.toFixed(0)}`
                    );
                }
            }
            await this.dashLine();

            // ========== TOTAL ==========
            const total = data.total || data.productos?.reduce((sum, p) => sum + (p.precio * p.cantidad), 0) || 0;
            await this.text2Col('TOTAL', `$${total.toFixed(0)}`, { bold: true });
            await this.doubleLine();

            // ========== FORMA DE PAGO ==========
            if (data.forma_pago) {
                await this.text2Col('Forma de Pago:', data.forma_pago);
            }
            if (data.vuelto) {
                await this.text2Col('Vuelto:', `$${data.vuelto.toFixed(0)}`);
            }
            await this.newLine();

            // ========== CÓDIGO DE BARRAS ==========
            if (data.barcode) {
                await this.barcode(data.barcode, { 
                    format: 'CODE128',
                    height: 50,
                    align: 'center'
                });
            }

            // ========== CÓDIGO QR ==========
            if (data.qr) {
                await this.qr(data.qr, { size: 4 });
            }

            // ========== PIE DE PÁGINA ==========
            await this.text('¡Gracias por su compra!', { align: 'center' });
            await this.text('www.dixon.cl', { align: 'center' });
            await this.newLine(3);

            // ========== CORTAR PAPEL ==========
            await this.cut();

            console.log('✅ Ticket impreso correctamente');
            return true;

        } catch (error) {
            console.error('❌ Error imprimiendo ticket:', error);
            alert('Error al imprimir: ' + error.message);
            return false;
        }
    }

    // ============================================
    // DESCONECTAR
    // ============================================
    async disconnect() {
        if (this.device) {
            try {
                await this.device.close();
            } catch (e) {}
            this.connected = false;
            this.device = null;
            console.log('🔌 Impresora desconectada');
        }
    }
}

// ============================================
// EXPORTAR PARA USO EN OTROS ARCHIVOS
// ============================================
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ThermalPrinter;
}
