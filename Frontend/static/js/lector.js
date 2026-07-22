// ============================================
// LECTOR DE CÓDIGO DE BARRAS - Web Serial API
// ============================================

class LectorCodigoBarras {
    constructor() {
        this.port = null;
        this.reader = null;
        this.connected = false;
        this.onBarcode = null;
        this.onConnect = null;
        this.onDisconnect = null;
        this.buffer = '';
        this.timeout = null;
        
        // Configuración del lector
        this.BAUD_RATE = 9600;
        this.DATA_BITS = 8;
        this.STOP_BITS = 1;
        this.PARITY = 'none';
        this.TIMEOUT_MS = 100; // Tiempo entre caracteres para detectar fin de código
    }

    // ============================================
    // DETECTAR COMPATIBILIDAD
    // ============================================
    isAvailable() {
        return 'serial' in navigator;
    }

    // ============================================
    // CONECTAR LECTOR
    // ============================================
    async connect() {
        try {
            // Verificar compatibilidad
            if (!this.isAvailable()) {
                throw new Error('Web Serial API no está disponible. Usa Chrome/Edge/Opera.');
            }

            // Solicitar permisos al usuario
            this.port = await navigator.serial.requestPort();

            // Abrir puerto serie
            await this.port.open({
                baudRate: this.BAUD_RATE,
                dataBits: this.DATA_BITS,
                stopBits: this.STOP_BITS,
                parity: this.PARITY
            });

            this.connected = true;

            // Crear reader para leer datos
            const textDecoder = new TextDecoder();
            this.reader = this.port.readable.getReader();

            // Iniciar lectura
            this.readLoop(textDecoder);

            // Disparar evento de conexión
            if (this.onConnect) {
                this.onConnect(this.port);
            }

            console.log('✅ Lector conectado');
            return true;

        } catch (error) {
            console.error('❌ Error conectando lector:', error);
            if (error.message.includes('No port selected')) {
                alert('No seleccionaste ningún puerto');
            } else {
                alert('Error al conectar: ' + error.message);
            }
            return false;
        }
    }

    // ============================================
    // BUCLE DE LECTURA
    // ============================================
    async readLoop(textDecoder) {
        try {
            while (this.connected) {
                const { value, done } = await this.reader.read();
                
                if (done) {
                    // El puerto se cerró
                    this.connected = false;
                    if (this.onDisconnect) {
                        this.onDisconnect();
                    }
                    break;
                }

                if (value) {
                    // Decodificar los datos recibidos
                    const text = textDecoder.decode(value);
                    this.processData(text);
                }
            }
        } catch (error) {
            console.error('❌ Error en lectura:', error);
            this.connected = false;
            if (this.onDisconnect) {
                this.onDisconnect();
            }
        }
    }

    // ============================================
    // PROCESAR DATOS RECIBIDOS
    // ============================================
    processData(data) {
        // El lector puede enviar caracteres de control
        // CR (0x0D) o LF (0x0A) indican fin de código
        for (const char of data) {
            if (char === '\r' || char === '\n') {
                // Fin del código de barras
                if (this.buffer.length > 0) {
                    const barcode = this.buffer.trim();
                    this.buffer = '';
                    
                    // Disparar evento de código leído
                    if (this.onBarcode) {
                        this.onBarcode(barcode);
                    }
                }
            } else {
                // Acumular caracteres
                this.buffer += char;
            }
        }

        // Timeout para detectar fin de código (si no hay CR/LF)
        clearTimeout(this.timeout);
        this.timeout = setTimeout(() => {
            if (this.buffer.length > 0) {
                const barcode = this.buffer.trim();
                this.buffer = '';
                
                if (this.onBarcode) {
                    this.onBarcode(barcode);
                }
            }
        }, this.TIMEOUT_MS);
    }

    // ============================================
    // DESCONECTAR
    // ============================================
    async disconnect() {
        try {
            if (this.reader) {
                await this.reader.cancel();
                this.reader = null;
            }
            if (this.port) {
                await this.port.close();
                this.port = null;
            }
            this.connected = false;
            console.log('🔌 Lector desconectado');
            if (this.onDisconnect) {
                this.onDisconnect();
            }
            return true;
        } catch (error) {
            console.error('❌ Error desconectando:', error);
            return false;
        }
    }

    // ============================================
    // REGISTRAR EVENTOS
    // ============================================
    onConnected(callback) {
        this.onConnect = callback;
    }

    onDisconnected(callback) {
        this.onDisconnect = callback;
    }

    onBarcodeRead(callback) {
        this.onBarcode = callback;
    }
}

// ============================================
// EXPORTAR PARA USO EN OTROS ARCHIVOS
// ============================================
if (typeof module !== 'undefined' && module.exports) {
    module.exports = LectorCodigoBarras;
}
