// ============================================
// LECTOR USB DE CÓDIGO DE BARRAS
// ============================================

class LectorUSB {
    constructor() {
        this.port = null;
        this.reader = null;
        this.connected = false;
        this.buffer = '';
        this.timeout = null;
        this.TIMEOUT_MS = 100;
        this.onBarcode = null;
        this.onConnect = null;
        this.onDisconnect = null;
        this.callbacks = [];
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
            if (!this.isAvailable()) {
                throw new Error('Web Serial API no está disponible. Usa Chrome/Edge/Opera.');
            }

            this.port = await navigator.serial.requestPort();

            await this.port.open({
                baudRate: 9600,
                dataBits: 8,
                stopBits: 1,
                parity: 'none'
            });

            this.connected = true;

            const textDecoder = new TextDecoder();
            this.reader = this.port.readable.getReader();

            this.readLoop(textDecoder);

            if (this.onConnect) {
                this.onConnect(this.port);
            }

            this._notifyCallbacks('connected', { status: 'connected' });

            console.log('✅ Lector USB conectado');
            return true;

        } catch (error) {
            console.error('❌ Error conectando lector USB:', error);
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
                    this.connected = false;
                    if (this.onDisconnect) {
                        this.onDisconnect();
                    }
                    this._notifyCallbacks('disconnected', { status: 'disconnected' });
                    break;
                }

                if (value) {
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
            this._notifyCallbacks('disconnected', { status: 'disconnected' });
        }
    }

    // ============================================
    // PROCESAR DATOS RECIBIDOS
    // ============================================
    processData(data) {
        for (const char of data) {
            if (char === '\r' || char === '\n') {
                if (this.buffer.length > 0) {
                    const barcode = this.buffer.trim();
                    this.buffer = '';
                    
                    if (this.onBarcode) {
                        this.onBarcode(barcode);
                    }
                    this._notifyCallbacks('barcode', { barcode: barcode });
                }
            } else {
                this.buffer += char;
            }
        }

        clearTimeout(this.timeout);
        this.timeout = setTimeout(() => {
            if (this.buffer.length > 0) {
                const barcode = this.buffer.trim();
                this.buffer = '';
                
                if (this.onBarcode) {
                    this.onBarcode(barcode);
                }
                this._notifyCallbacks('barcode', { barcode: barcode });
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
            console.log('🔌 Lector USB desconectado');
            if (this.onDisconnect) {
                this.onDisconnect();
            }
            this._notifyCallbacks('disconnected', { status: 'disconnected' });
            return true;
        } catch (error) {
            console.error('❌ Error desconectando:', error);
            return false;
        }
    }

    // ============================================
    // REGISTRAR CALLBACKS
    // ============================================
    addEventListener(event, callback) {
        this.callbacks.push({ event, callback });
    }

    _notifyCallbacks(event, data) {
        this.callbacks.forEach(cb => {
            if (cb.event === event) {
                try { cb.callback(data); } catch(e) {}
            }
        });
    }

    // ============================================
    // OBTENER ESTADO
    // ============================================
    isConnected() {
        return this.connected;
    }
}

// Exportar para uso global
if (typeof window !== 'undefined') {
    window.LectorUSB = LectorUSB;
}
