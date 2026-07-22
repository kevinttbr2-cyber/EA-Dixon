// ============================================
// LECTOR USB DE CÓDIGO DE BARRAS (SOPORTA PDF417)
// ============================================

class LectorUSB {
    constructor() {
        this.port = null;
        this.reader = null;
        this.connected = false;
        this.buffer = '';
        this.timeout = null;
        this.TIMEOUT_MS = 150; // Aumentado para PDF417 que tiene más datos
        this.onBarcode = null;
        this.onPDF417 = null;  // Nuevo evento específico para PDF417
        this.onConnect = null;
        this.onDisconnect = null;
        this.callbacks = [];
        this.ultimoCodigo = '';
        this.ultimoPDF417 = null;
        this.tiempoUltimo = 0;
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

            // Algunos lectores PDF417 usan 115200 baudios
            await this.port.open({
                baudRate: 9600,  // Probar con 9600 primero
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

            console.log('✅ Lector USB conectado (soporta PDF417)');
            return true;

        } catch (error) {
            console.error('❌ Error conectando lector USB:', error);
            if (error.message.includes('No port selected')) {
                alert('No seleccionaste ningún puerto');
            } else if (error.message.includes('baud')) {
                // Intentar con otra velocidad
                alert('⚠️ Error de velocidad. Intentando reconectar a 115200...');
                try {
                    await this.port.open({
                        baudRate: 115200,
                        dataBits: 8,
                        stopBits: 1,
                        parity: 'none'
                    });
                    this.connected = true;
                    const textDecoder = new TextDecoder();
                    this.reader = this.port.readable.getReader();
                    this.readLoop(textDecoder);
                    if (this.onConnect) this.onConnect(this.port);
                    console.log('✅ Reconectado a 115200 baudios');
                    return true;
                } catch (e2) {
                    alert('Error al conectar: ' + e2.message);
                    return false;
                }
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
    // PROCESAR DATOS RECIBIDOS (CON DETECCIÓN PDF417)
    // ============================================
    processData(data) {
        for (const char of data) {
            if (char === '\r' || char === '\n') {
                if (this.buffer.length > 0) {
                    const codigo = this.buffer.trim();
                    this.buffer = '';
                    
                    // DETECTAR PDF417 DEL SII
                    const esPDF417 = this._detectarPDF417(codigo);
                    
                    if (esPDF417) {
                        console.log('📄 PDF417 del SII detectado');
                        const datosSII = this._parsearPDF417(codigo);
                        if (datosSII) {
                            this.ultimoPDF417 = datosSII;
                            if (this.onPDF417) {
                                this.onPDF417(datosSII);
                            }
                            this._notifyCallbacks('pdf417', datosSII);
                        }
                    }
                    
                    // Siempre notificar el código
                    if (this.onBarcode) {
                        this.onBarcode(codigo);
                    }
                    this._notifyCallbacks('barcode', { 
                        barcode: codigo,
                        esPDF417: esPDF417,
                        datosSII: this.ultimoPDF417
                    });
                }
            } else {
                this.buffer += char;
            }
        }

        clearTimeout(this.timeout);
        this.timeout = setTimeout(() => {
            if (this.buffer.length > 0) {
                const codigo = this.buffer.trim();
                this.buffer = '';
                
                const esPDF417 = this._detectarPDF417(codigo);
                if (esPDF417) {
                    const datosSII = this._parsearPDF417(codigo);
                    if (datosSII) {
                        this.ultimoPDF417 = datosSII;
                        if (this.onPDF417) {
                            this.onPDF417(datosSII);
                        }
                        this._notifyCallbacks('pdf417', datosSII);
                    }
                }
                
                if (this.onBarcode) {
                    this.onBarcode(codigo);
                }
                this._notifyCallbacks('barcode', { 
                    barcode: codigo,
                    esPDF417: esPDF417,
                    datosSII: this.ultimoPDF417
                });
            }
        }, this.TIMEOUT_MS);
    }

    // ============================================
    // DETECTAR PDF417 DEL SII
    // ============================================
    _detectarPDF417(texto) {
        // Características del PDF417 del SII:
        // - Contiene RUT (formato XX.XXX.XXX-X)
        // - Contiene palabras clave
        const tieneRUT = texto.match(/\d{1,2}\.\d{3}\.\d{3}-[\dkK]/);
        const tieneFolio = texto.match(/[Ff]olio[:]\s*(\d+)/);
        const tieneFecha = texto.match(/\d{4}-\d{2}-\d{2}/);
        const tieneMonto = texto.match(/[Tt]otal[:]\s*[\$]?\s*([\d.,]+)/);
        const tieneSII = texto.match(/S\.I\.I\.|Servicio de Impuestos Internos|Timbre Electrónico/i);
        const tieneFormato = texto.split('|').length >= 3;
        const tieneCodigoAut = texto.match(/[Cc]ódigo(?: de)? [Aa]utorización[:]\s*([A-Za-z0-9]+)/);
        
        let puntaje = 0;
        if (tieneRUT) puntaje += 3;
        if (tieneFolio) puntaje += 2;
        if (tieneFecha) puntaje += 1;
        if (tieneMonto) puntaje += 2;
        if (tieneSII) puntaje += 4;
        if (tieneFormato) puntaje += 2;
        if (tieneCodigoAut) puntaje += 3;
        
        return puntaje >= 4;
    }

    // ============================================
    // PARSEAR PDF417 DEL SII
    // ============================================
    _parsearPDF417(texto) {
        try {
            const data = {
                raw: texto,
                rut_emisor: '',
                rut_receptor: '',
                folio: '',
                fecha: '',
                monto: 0,
                tipo_documento: '',
                codigo_autorizacion: '',
                razon_social_emisor: '',
                razon_social_receptor: '',
                es_valido: false
            };

            // Método 1: Formato pipe (|)
            const partes = texto.split('|');
            if (partes.length >= 3) {
                data.rut_emisor = partes[0]?.trim() || '';
                data.rut_receptor = partes[1]?.trim() || '';
                data.folio = partes[2]?.trim() || '';
                data.fecha = partes[3]?.trim() || '';
                if (partes[4]) {
                    data.monto = parseFloat(partes[4].replace(/[.,]/g, m => m === '.' ? '' : '.')) || 0;
                }
                data.tipo_documento = partes[5]?.trim() || 'Factura Electrónica';
                if (partes.length > 6) {
                    data.codigo_autorizacion = partes[6]?.trim() || '';
                }
                data.es_valido = true;
                return data;
            }

            // Método 2: Búsqueda por patrones
            const rutMatch = texto.match(/(\d{1,2}\.\d{3}\.\d{3}-[\dkK])/);
            if (rutMatch) {
                const ruts = texto.match(/(\d{1,2}\.\d{3}\.\d{3}-[\dkK])/g);
                if (ruts) {
                    data.rut_emisor = ruts[0] || '';
                    data.rut_receptor = ruts[1] || '';
                }
            }

            const folioMatch = texto.match(/[Ff]olio[:]\s*(\d+)/);
            if (folioMatch) data.folio = folioMatch[1];

            const fechaMatch = texto.match(/(\d{4}-\d{2}-\d{2})/);
            if (fechaMatch) data.fecha = fechaMatch[1];

            const montoMatch = texto.match(/[Tt]otal[:]\s*[\$]?\s*([\d.,]+)/);
            if (montoMatch) {
                data.monto = parseFloat(montoMatch[1].replace(/[.,]/g, m => m === '.' ? '' : '.')) || 0;
            }

            const tipoMatch = texto.match(/[Tt]ipo(?: de)? [Dd]ocumento[:]\s*([^\n]+)/);
            if (tipoMatch) data.tipo_documento = tipoMatch[1].trim();

            const codAutMatch = texto.match(/[Cc]ódigo(?: de)? [Aa]utorización[:]\s*([A-Za-z0-9]+)/);
            if (codAutMatch) data.codigo_autorizacion = codAutMatch[1];

            const razonEmisorMatch = texto.match(/[Ee]misor[:]\s*([^\n]+)/);
            if (razonEmisorMatch) data.razon_social_emisor = razonEmisorMatch[1].trim();

            const razonReceptorMatch = texto.match(/[Rr]eceptor[:]\s*([^\n]+)/);
            if (razonReceptorMatch) data.razon_social_receptor = razonReceptorMatch[1].trim();

            // Verificar si tenemos suficientes datos
            data.es_valido = data.rut_emisor || data.folio || data.monto > 0;
            
            return data;
        } catch (error) {
            console.error('❌ Error parseando PDF417:', error);
            return {
                raw: texto,
                es_valido: false,
                error: error.message
            };
        }
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
