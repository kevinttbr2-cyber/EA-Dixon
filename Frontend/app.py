from flask import Flask, render_template, request, session, redirect, url_for, jsonify, send_file, flash
import os
import requests
import secrets
from functools import wraps
import hmac
import hashlib
from datetime import datetime, timedelta
import io
import time
import locale
import logging
from logging.handlers import RotatingFileHandler

# ============================
# CONFIGURACIÓN DE LOGS PERSISTENTES
# ============================
# Crear carpeta logs si no existe
LOG_DIR = 'logs'
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# Configurar logger principal
logger = logging.getLogger('dixon_app')
logger.setLevel(logging.DEBUG)

# Limpiar handlers existentes para evitar duplicados
if logger.hasHandlers():
    logger.handlers.clear()

# Handler para archivo (con rotación)
file_handler = RotatingFileHandler(
    os.path.join(LOG_DIR, 'dixon_app.log'),
    maxBytes=10485760,  # 10 MB
    backupCount=5       # Mantener 5 archivos de backup
)
file_handler.setLevel(logging.DEBUG)

# Handler para consola (para desarrollo)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

# Formato de los logs
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# Agregar handlers al logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# ============================
# CONFIGURACIÓN DE LA APP
# ============================
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "clave_frontend_segura")
PDF_SECRET_KEY = os.environ.get("PDF_SECRET_KEY", "dixon_pdf_2025")

# Configurar logger de Flask con los mismos handlers
app.logger.handlers = logger.handlers
app.logger.setLevel(logger.level)

# ============================
# CONFIGURAR IDIOMA A ESPAÑOL
# ============================
try:
    locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_TIME, 'spanish')
    except:
        print("⚠️ No se pudo configurar el idioma español, usando inglés por defecto")

os.environ['TZ'] = 'America/Santiago'
time.tzset()

app.jinja_env.filters['strftime'] = lambda date, fmt: date.strftime(fmt) if date else ''
# URL del backend en Railway
BACKEND_URL = os.environ.get("BACKEND_URL", "https://ea-dixon-production.up.railway.app")

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("usuario"):
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated

# Agrega este decorador para roles específicos
def role_required(allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not session.get("usuario"):
                return redirect("/login")
            if session.get("rol") not in allowed_roles:
                return "No tienes permisos para acceder a esta sección", 403
            return f(*args, **kwargs)
        return decorated
    return decorator

def generar_firma_pdf(id_reg):
    return hmac.new(
        PDF_SECRET_KEY.encode(),
        str(id_reg).encode(),
        hashlib.sha256
    ).hexdigest()[:16]
    
@app.context_processor
def inject_globals():
    def fecha_espanol(fecha):
        if not fecha:
            return ''
        if isinstance(fecha, str):
            try:
                fecha = datetime.strptime(fecha, '%Y-%m-%d')
            except:
                return fecha
        dias = {0: 'Lunes', 1: 'Martes', 2: 'Miércoles', 3: 'Jueves', 4: 'Viernes', 5: 'Sábado', 6: 'Domingo'}
        meses = {1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril', 5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto', 9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'}
        return f"{dias.get(fecha.weekday(), '')} {fecha.day} de {meses.get(fecha.month, '')} {fecha.year}"
    
    def fecha_corta_espanol(fecha):
        if not fecha:
            return ''
        if isinstance(fecha, str):
            try:
                fecha = datetime.strptime(fecha, '%Y-%m-%d')
            except:
                return fecha
        dias_cortos = {0: 'Lun', 1: 'Mar', 2: 'Mié', 3: 'Jue', 4: 'Vie', 5: 'Sáb', 6: 'Dom'}
        meses_cortos = {1: 'Ene', 2: 'Feb', 3: 'Mar', 4: 'Abr', 5: 'May', 6: 'Jun', 7: 'Jul', 8: 'Ago', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dic'}
        return f"{dias_cortos.get(fecha.weekday(), '')} {fecha.day} {meses_cortos.get(fecha.month, '')}"
    
    # OBTENER CONTEO DE FLOTAS PENDIENTES
    flotas_pendientes_count = 0
    try:
        import requests
        resp = requests.get(f"{BACKEND_URL}/api/flotas_pendientes_count", timeout=3)
        if resp.status_code == 200:
            flotas_pendientes_count = resp.json().get('count', 0)
    except Exception as e:
        print(f"⚠️ Error al obtener flotas pendientes: {e}")
        flotas_pendientes_count = 0
    
    return dict(
        backend_url=BACKEND_URL,
        fecha_espanol=fecha_espanol,
        fecha_corta_espanol=fecha_corta_espanol,
        flotas_pendientes_count=flotas_pendientes_count
    )

@app.route('/')
def index():
    if session.get("usuario"):
        return redirect("/estado")
    return redirect("/login")

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_hex(32)
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        ip = request.remote_addr
        
        logger.info(f"🔐 Intento de login: usuario '{username}' desde IP {ip}")
        
        try:
            resp = requests.post(f"{BACKEND_URL}/api/login", json={"username": username, "password": password}, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                session["usuario"] = data['user']['username']
                session["rol"] = data['user']['rol']
                session["nombre_completo"] = data['user'].get('nombre_completo', username)
                logger.info(f"✅ Login exitoso: '{username}' desde IP {ip}, rol: {session['rol']}")
                return redirect("/estado")
            else:
                logger.warning(f"❌ Login fallido: usuario '{username}' desde IP {ip} - Contraseña incorrecta")
                error = "❌ Usuario o contraseña incorrectos"
        except Exception as e:
            logger.error(f"⚠️ Error en login: usuario '{username}' desde IP {ip} - {str(e)}")
            error = "⚠️ Error de conexión con el servidor"
    
    return render_template("login.html", csrf_token=session['csrf_token'], error=error)

@app.route('/logout')
def logout():
    usuario = session.get('usuario')
    logger.info(f"🚪 Usuario '{usuario}' cerró sesión")
    session.clear()
    return redirect("/login")

@app.route('/estado')
@login_required
def estado():
    usuario = session.get('usuario')
    logger.info(f"📋 Usuario '{usuario}' accedió a /estado")
    
    try:
        resp = requests.get(f"{BACKEND_URL}/api/estado", timeout=10)
        data = resp.json() if resp.status_code == 200 else {"pendientes": [], "pagados_hoy": []}
        logger.debug(f"📊 /estado: {len(data.get('pendientes', []))} pendientes, {len(data.get('pagados_hoy', []))} pagados hoy")
    except Exception as e:
        logger.error(f"❌ Error en /estado para usuario '{usuario}': {str(e)}")
        data = {"pendientes": [], "pagados_hoy": []}
    
    return render_template("estado.html", 
                          registros=data.get('pendientes', []) + data.get('pagados_hoy', []),
                          pendientes_mes=len(data.get('pendientes', [])),
                          pagados_mes=len(data.get('pagados_hoy', [])),
                          estado="todos")

# ============================
# AGREGAR CLIENTE (CON FLOTAS)
# ============================
@app.route('/agregar_cliente')
@login_required
def agregar_cliente():
    try:
        resp_marcas = requests.get(f"{BACKEND_URL}/api/marcas", timeout=10)
        marcas = resp_marcas.json() if resp_marcas.status_code == 200 else []
        
        # CARGAR FLOTAS DISPONIBLES
        resp_flotas = requests.get(f"{BACKEND_URL}/api/flotas_disponibles", timeout=10)
        flotas = resp_flotas.json() if resp_flotas.status_code == 200 else []
    except Exception as e:
        print(f"Error en /agregar_cliente: {e}")
        marcas = []
        flotas = []
    
    hoy = datetime.now().strftime('%Y-%m-%d')
    return render_template("agregar_cliente.html", marcas=marcas, flotas=flotas, hoy=hoy)
    
@app.route('/agregar', methods=['POST'])
@login_required
def agregar():
    usuario = session.get('usuario')
    nombre = request.form.get('nombre', '').strip()
    patente = request.form.get('patente', '').strip().upper()

    logger.info(f"📝 Usuario '{usuario}' agregando cliente: '{nombre}', patente: '{patente}'")
    
    # Obtener flota
    flota = request.form.get('flota', '').strip()
    if flota == '__nueva__':
        flota = request.form.get('flota_nueva', '').strip()
    
    # VALIDACIÓN: Verificar si ya existe un registro en los últimos 5 minutos
    try:
        resp_verificar = requests.get(
            f"{BACKEND_URL}/api/verificar_duplicado",
            params={"nombre": nombre, "patente": patente},
            timeout=5
        )
        
        if resp_verificar.status_code == 200 and resp_verificar.json().get('duplicado', False):
            logger.warning(f"⚠️ Intento de duplicado: usuario '{usuario}' intentó agregar '{nombre}' - '{patente}'")
            flash('⚠️ Ya existe un registro con estos datos en los últimos 5 minutos. Si es un error, intenta de nuevo.', 'warning')
            return redirect("/agregar_cliente")
    except Exception as e:
        logger.warning(f"⚠️ Error al verificar duplicado para '{nombre}': {str(e)}")
    
    # Construir data
    data = {
        'nombre': nombre,
        'patente': patente,
        'marca': request.form.get('marca', '').strip(),
        'modelo': request.form.get('modelo', '').strip(),
        'telefono': request.form.get('telefono', '').strip(),
        'observaciones': request.form.get('observaciones', '').strip(),
        'kilometraje': int(request.form.get('kilometraje', 0) or 0),
        'anio': int(request.form.get('anio', 0) or 0),
        'flota': flota if flota else None,
        'usuario': usuario
    }
    
    try:
        resp = requests.post(f"{BACKEND_URL}/api/agregar", json=data, timeout=10)
        if resp.status_code != 200:
            logger.error(f"❌ Error al agregar cliente para usuario '{usuario}': {resp.text}")
            flash('❌ Error al registrar el cliente. Intenta de nuevo.', 'error')
            return redirect("/agregar_cliente")
        else:
            logger.info(f"✅ Cliente agregado exitosamente por '{usuario}': '{nombre}', patente: '{patente}'")
    except Exception as e:
        logger.error(f"⚠️ Error en /agregar para usuario '{usuario}': {str(e)}")
        flash('⚠️ Error de conexión. Intenta de nuevo.', 'error')
        return redirect("/agregar_cliente")
    
    flash('✅ Cliente registrado correctamente', 'success')
    return redirect("/estado")

@app.route('/pagar/<int:id_reg>', methods=['GET', 'POST'])
@login_required
def pagar(id_reg):
    usuario = session.get('usuario')
    logger.info(f"💰 Usuario '{usuario}' iniciando pago para registro ID {id_reg}")
    
    try:
        resp = requests.get(f"{BACKEND_URL}/api/registro/{id_reg}", timeout=10)
        if resp.status_code != 200:
            logger.error(f"❌ Registro ID {id_reg} no encontrado para usuario '{usuario}'")
            return f"Registro {id_reg} no encontrado en backend", 404
        registro = resp.json()
    except Exception as e:
        logger.error(f"⚠️ Error al obtener registro ID {id_reg} para '{usuario}': {str(e)}")
        return "Error de conexión", 500
    
    if request.method == 'POST':
        monto = float(request.form.get('monto', 0))
        forma_pago = request.form.get('forma_pago', 'efectivo')
        
        logger.info(f"💳 Usuario '{usuario}' procesando pago ID {id_reg}: monto ${monto}, forma: {forma_pago}")
        
        data = {
            'monto': monto,
            'observaciones_pago': request.form.get('observaciones_pago', ''),
            'diagnostico': request.form.get('diagnostico', ''),
            'reparacion': request.form.get('reparacion', 'Reparación realizada'),
            'resultado': request.form.get('resultado', 'reparado'),
            'tiempo_estimado': request.form.get('tiempo_estimado', '00:00:00'),
            'atendido_por': session.get('nombre_completo', session.get('usuario')),
            'forma_pago': forma_pago
        }
        
        try:
            resp = requests.post(f"{BACKEND_URL}/api/pagar/{id_reg}", json=data, timeout=10)
            if resp.status_code == 200:
                logger.info(f"✅ Pago ID {id_reg} completado por '{usuario}' - monto: ${monto}")
                return redirect(f"/pago_exitoso/{id_reg}")
            else:
                logger.error(f"❌ Error en pago ID {id_reg} por '{usuario}': {resp.text}")
                return f"Error al procesar el pago: {resp.text}", 500
        except Exception as e:
            logger.error(f"⚠️ Error en pago ID {id_reg} por '{usuario}': {str(e)}")
            return "Error de conexión al procesar el pago", 500
    
    return render_template("pagar.html", id=id_reg, registro=registro)

@app.route('/pago_exitoso/<int:id_reg>')
@login_required
def pago_exitoso(id_reg):
    usuario = session.get('usuario')
    logger.info(f"📄 Usuario '{usuario}' viendo pago exitoso ID {id_reg}")
    
    try:
        resp = requests.get(f"{BACKEND_URL}/api/registro/{id_reg}", timeout=10)
        registro = resp.json() if resp.status_code == 200 else {}
        firma = generar_firma_pdf(id_reg)
        registro['firma'] = firma
        url_pdf = f"{BACKEND_URL}/api/pdf/{id_reg}/{firma}"
    except Exception as e:
        logger.error(f"❌ Error en /pago_exitoso ID {id_reg} para '{usuario}': {str(e)}")
        registro = {}
        url_pdf = ""
    return render_template("pago_exitoso.html", registro=registro, url_pdf=url_pdf)

@app.route('/cambiar_password', methods=['GET', 'POST'])
@login_required
def cambiar_password():
    usuario = session.get('usuario')
    error = None
    success = None
    
    if request.method == 'POST':
        password_actual = request.form.get('password_actual')
        password_nueva = request.form.get('password_nueva')
        password_confirmar = request.form.get('password_confirmar')
        
        if not password_actual or not password_nueva or not password_confirmar:
            error = "⚠️ Todos los campos son obligatorios"
        elif password_nueva != password_confirmar:
            error = "⚠️ Las contraseñas nuevas no coinciden"
        elif len(password_nueva) < 6:
            error = "⚠️ La contraseña debe tener al menos 6 caracteres"
        else:
            try:
                data = {
                    'username': usuario,
                    'password_actual': password_actual,
                    'password_nueva': password_nueva
                }
                resp = requests.post(f"{BACKEND_URL}/api/cambiar_password", json=data, timeout=10)
                if resp.status_code == 200:
                    success = "✅ Contraseña actualizada correctamente"
                    logger.info(f"🔑 Usuario '{usuario}' cambió su contraseña")
                else:
                    error = resp.json().get('error', '❌ Error al cambiar contraseña')
            except Exception as e:
                logger.error(f"⚠️ Error en /cambiar_password para '{usuario}': {str(e)}")
                error = "⚠️ Error de conexión con el servidor"
    
    return render_template("cambiar_password.html", error=error, success=success)

@app.route('/pendientes_validacion')
@login_required
@role_required(['admin'])
def pendientes_validacion():
    usuario = session.get('usuario')
    logger.info(f"📊 Usuario '{usuario}' accedió a /pendientes_validacion")
    
    try:
        resp = requests.get(f"{BACKEND_URL}/api/pendientes_validacion", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            pendientes = [p for p in data.get('pendientes', []) if p.get('tipo_venta') != 'directa']
            validados = [v for v in data.get('validados', []) if v.get('tipo_venta') != 'directa']
            total_pagado = data.get('total_pagado', 0)
            logger.debug(f"📊 Pendientes: {len(pendientes)}, Validados: {len(validados)}")
        else:
            pendientes = []
            validados = []
            total_pagado = 0
    except Exception as e:
        logger.error(f"❌ Error en /pendientes_validacion para '{usuario}': {str(e)}")
        pendientes = []
        validados = []
        total_pagado = 0
    
    return render_template("pendientes_validacion.html", pendientes=pendientes, validados=validados, total_pagado=total_pagado)

@app.route('/validar_pago/<int:id_reg>', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'operador'])
def validar_pago(id_reg):
    usuario = session.get('usuario')
    logger.info(f"📊 Usuario '{usuario}' iniciando validación para registro ID {id_reg}")
    
    if session.get('rol') not in ['admin']:
        logger.warning(f"⚠️ Usuario '{usuario}' sin permisos para validar ID {id_reg}")
        return "No tienes permisos para validar pagos", 403
    
    try:
        resp = requests.get(f"{BACKEND_URL}/api/registro/{id_reg}", timeout=10)
        if resp.status_code != 200:
            logger.error(f"❌ Registro ID {id_reg} no encontrado para validación")
            return "Registro no encontrado", 404
        registro = resp.json()
    except Exception as e:
        logger.error(f"⚠️ Error al obtener registro ID {id_reg} para '{usuario}': {str(e)}")
        return "Error de conexión", 500
    
    # VALIDACIÓN: Venta directa no necesita validación
    if registro.get('tipo_venta') == 'directa':
        logger.info(f"ℹ️ Venta directa ID {id_reg} no requiere validación")
        flash('⚠️ Las ventas directas no requieren validación de costos.', 'warning')
        return redirect("/estado")
    
    if registro.get('estado') != 'pagado':
        logger.warning(f"⚠️ Intento de validar registro ID {id_reg} que no está pagado")
        return "Este pago no está pagado", 400
    
    try:
        resp_usuarios = requests.get(f"{BACKEND_URL}/api/usuarios", timeout=10)
        usuarios = resp_usuarios.json() if resp_usuarios.status_code == 200 else []
    except:
        usuarios = []
    
    error = None
    
    if request.method == 'POST':
        logger.info(f"📝 Usuario '{usuario}' enviando validación para ID {id_reg}")
        
        validado_por = request.form.get('validado_por', '').strip()
        if not validado_por:
            validado_por = session.get('nombre_completo', session.get('usuario'))
        
        nombres_repuestos = request.form.getlist('repuesto_nombre[]')
        costos_repuestos = request.form.getlist('repuesto_costo[]')
        
        detalles_repuestos = []
        for i in range(len(nombres_repuestos)):
            if nombres_repuestos[i].strip():
                detalles_repuestos.append({
                    'nombre': nombres_repuestos[i].strip(),
                    'costo': float(costos_repuestos[i]) if costos_repuestos[i] else 0
                })
        
        data = {
            'costo_repuestos': float(request.form.get('costo_repuestos', 0)),
            'costo_mano_obra_real': float(request.form.get('costo_mano_obra', 0)),
            'costo_diagnostico_real': float(request.form.get('costo_diagnostico', 0)),
            'ganancia_neta': float(request.form.get('ganancia_neta', 0)),
            'observaciones_pago': request.form.get('observaciones_costos', ''),
            'validado_por': validado_por,
            'diagnostico': request.form.get('diagnostico', ''),
            'reparacion': request.form.get('reparacion', 'Reparación realizada'),
            'resultado': request.form.get('resultado', 'reparado'),
            'tiempo_estimado': request.form.get('tiempo_estimado', '00:00:00'),
            'detalles_repuestos': detalles_repuestos,
            'estado_ot': request.form.get('estado_ot', 'Pendiente')
        }
        
        try:
            resp = requests.post(f"{BACKEND_URL}/api/validar_pago/{id_reg}", json=data, timeout=10)
            if resp.status_code == 200:
                logger.info(f"✅ Validación completada para ID {id_reg} por '{usuario}'")
                return redirect(f"/pago_validado/{id_reg}")
            else:
                error = resp.json().get('error', 'Error al validar')
                logger.error(f"❌ Error en validación ID {id_reg} por '{usuario}': {error}")
        except Exception as e:
            logger.error(f"⚠️ Error en /validar_pago POST ID {id_reg} por '{usuario}': {str(e)}")
            error = "Error de conexión"
        
        return render_template("validar_pago.html", id=id_reg, registro=registro, usuarios=usuarios, error=error)
    
    return render_template("validar_pago.html", id=id_reg, registro=registro, usuarios=usuarios, error=None)

@app.route('/pago_validado/<int:id_reg>')
@login_required
@role_required(['admin', 'operador'])
def pago_validado(id_reg):
    try:
        resp = requests.get(f"{BACKEND_URL}/api/registro/{id_reg}", timeout=10)
        registro = resp.json() if resp.status_code == 200 else {}
    except Exception as e:
        print(f"Error en /pago_validado: {e}")
        registro = {}
    return render_template("pago_validado.html", registro=registro)

# ============================
# REGISTROS CON FILTROS
# ============================
@app.route('/registros')
@login_required
@role_required(['admin'])
def registros():
    try:
        resp = requests.get(f"{BACKEND_URL}/api/registros", timeout=10)
        registros = resp.json() if resp.status_code == 200 else []
    except Exception as e:
        print(f"Error en /registros: {e}")
        registros = []
    
    hoy = datetime.now().date()
    hoy_str = hoy.strftime('%Y-%m-%d')
    fecha_7d = (hoy - timedelta(days=7)).strftime('%Y-%m-%d')
    fecha_mes = (hoy - timedelta(days=30)).strftime('%Y-%m-%d')
    
    registros_hoy = [r for r in registros if r.get('fecha', '') == hoy_str]
    registros_7d = [r for r in registros if r.get('fecha', '') >= fecha_7d]
    registros_mes = [r for r in registros if r.get('fecha', '') >= fecha_mes]
    total_general = sum(r.get('monto', 0) for r in registros)
    
    return render_template(
        "registros.html",
        registros=registros,
        registros_hoy=registros_hoy,
        registros_7d=registros_7d,
        registros_mes=registros_mes,
        total_general=total_general,
        filtro=request.args.get('filtro', 'todos')
    )

# ============================
# BALANCE DE GANANCIA
# ============================
@app.route('/balance')
@login_required
@role_required(['admin'])
def balance():
    filtro = request.args.get('filtro', 'hoy')
    try:
        resp = requests.get(f"{BACKEND_URL}/api/balance?filtro={filtro}", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            registros = data.get('registros', [])
            total_pagado = data.get('total_pagado', 0)
            total_repuestos = data.get('total_repuestos', 0)
            total_mano_obra = data.get('total_mano_obra', 0)
            total_diagnostico = data.get('total_diagnostico', 0)
            ganancia_neta = data.get('ganancia_neta', 0)
        else:
            registros = []
            total_pagado = total_repuestos = total_mano_obra = total_diagnostico = ganancia_neta = 0
    except Exception as e:
        print(f"Error en /balance: {e}")
        registros = []
        total_pagado = total_repuestos = total_mano_obra = total_diagnostico = ganancia_neta = 0
    
    hoy = [r for r in registros if r.get('fecha') == datetime.now().strftime('%Y-%m-%d')]
    semana = [r for r in registros if r.get('fecha', '') >= (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')]
    mes = [r for r in registros if r.get('fecha', '') >= (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')]
    todos = registros
    
    return render_template(
        "balance.html",
        registros=registros,
        total_pagado=total_pagado,
        total_repuestos=total_repuestos,
        total_mano_obra=total_mano_obra,
        total_diagnostico=total_diagnostico,
        ganancia_neta=ganancia_neta,
        filtro=filtro,
        hoy=hoy,
        semana=semana,
        mes=mes,
        todos=todos
    )

@app.route('/modelos/<marca>')
@login_required
def modelos(marca):
    try:
        resp = requests.get(f"{BACKEND_URL}/api/modelos/{marca}", timeout=10)
        return jsonify(resp.json() if resp.status_code == 200 else [])
    except:
        return jsonify([])
@app.route('/editar_completo/<int:id_reg>', methods=['POST'])
@login_required
@role_required(['admin'])
def editar_completo(id_reg):
    """Edición completa de un registro (todos los campos)"""
    data = request.json
    
    try:
        resp = requests.post(f"{BACKEND_URL}/api/editar_completo/{id_reg}", json=data, timeout=10)
        if resp.status_code == 200:
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "error": resp.text}), 500
    except Exception as e:
        print(f"Error en /editar_completo: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/flotas')
@login_required
@role_required(['admin'])
def flotas():
    try:
        resp = requests.get(f"{BACKEND_URL}/api/flotas", timeout=10)
        clientes = resp.json() if resp.status_code == 200 else []
    except:
        clientes = []
    return render_template("flotas.html", clientes=clientes)

@app.route('/register', methods=['GET', 'POST'])
@login_required
def register():
    if session.get('rol') != 'admin':
        return "No tienes permisos", 403
    
    error = None
    success = None
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        rol = request.form.get('rol', 'basico')
        nombre_completo = request.form.get('nombre_completo', '')
        
        print(f"📝 POST recibido: username={username}, rol={rol}")  # ← LOG
        
        if not username or not password:
            error = "⚠️ Usuario y contraseña son obligatorios"
        elif len(password) < 6:
            error = "⚠️ La contraseña debe tener al menos 6 caracteres"
        else:
            try:
                data = {
                    'username': username,
                    'password': password,
                    'rol': rol,
                    'nombre_completo': nombre_completo
                }
                print(f"📤 Enviando a backend: {data}")  # ← LOG
                resp = requests.post(f"{BACKEND_URL}/api/crear_usuario", json=data, timeout=10)
                print(f"📥 Respuesta: {resp.status_code} - {resp.text}")  # ← LOG
                if resp.status_code == 200:
                    success = f"✅ Usuario {username} creado correctamente"
                else:
                    error = resp.json().get('error', '❌ Error al crear usuario')
            except Exception as e:
                print(f"Error en /register POST: {e}")
                error = "⚠️ Error de conexión con el servidor"
    
    return render_template("register.html", error=error, success=success)
# ============================
# FLOTAS PENDIENTES
# ============================
@app.route('/flotas_pendientes')
@login_required
@role_required(['admin'])
def flotas_pendientes():
    try:
        resp = requests.get(f"{BACKEND_URL}/api/flotas_pendientes_agrupadas", timeout=10)
        flotas_agrupadas = resp.json() if resp.status_code == 200 else []
        
        total_general = sum(float(f.get('total_pendiente', 0)) for f in flotas_agrupadas)
        
    except Exception as e:
        print(f"Error en /flotas_pendientes: {e}")
        flotas_agrupadas = []
        total_general = 0
    
    today = datetime.now().strftime('%Y-%m-%d')
    return render_template("flotas_pendientes.html", 
                          flotas_agrupadas=flotas_agrupadas, 
                          total_general=total_general, 
                          today=today)
    
@app.route('/usuarios')
@login_required
@role_required(['admin'])
def usuarios():
    try:
        resp = requests.get(f"{BACKEND_URL}/api/usuarios", timeout=10)
        usuarios = resp.json() if resp.status_code == 200 else []
    except Exception as e:
        print(f"Error en /usuarios: {e}")
        usuarios = []
    return render_template("usuarios.html", usuarios=usuarios)

@app.route('/auditoria_descargas')
@login_required
@role_required(['admin'])
def auditoria_descargas():
    try:
        resp = requests.get(f"{BACKEND_URL}/api/auditoria", timeout=10)
        historial = resp.json() if resp.status_code == 200 else []
    except Exception as e:
        print(f"Error en /auditoria_descargas: {e}")
        historial = []
    return render_template("auditoria_descargas.html", historial=historial)

@app.route("/exportar_flota_pdf/<flota>", methods=["GET", "POST"])
@login_required
@role_required(['admin'])
def exportar_flota_pdf(flota):
    if request.method == "GET":
        return render_template("exportar_flota.html", flota=flota)
    
    fecha_desde = request.form.get("fecha_desde")
    fecha_hasta = request.form.get("fecha_hasta")
    
    if not fecha_desde or not fecha_hasta:
        return "Debes seleccionar ambas fechas", 400
    
    try:
        # 🔥 Usar la URL correcta del backend
        backend_url = os.environ.get("BACKEND_URL", "https://ea-dixon-production.up.railway.app")
        url = f"{backend_url}/api/exportar_flota_pdf/{flota}"
        
        print(f"📤 Enviando a: {url}")
        print(f"📅 Fechas: {fecha_desde} - {fecha_hasta}")
        
        resp = requests.post(
            url,
            json={"fecha_desde": fecha_desde, "fecha_hasta": fecha_hasta},
            timeout=60
        )
        
        print(f"📥 Respuesta: {resp.status_code}")
        
        if resp.status_code == 200:
            return send_file(
                io.BytesIO(resp.content),
                mimetype='application/pdf',
                as_attachment=True,
                download_name=f'reporte_flota_{flota}.pdf'
            )
        else:
            return f"❌ Error: {resp.text}", resp.status_code
            
    except requests.exceptions.ConnectionError as e:
        print(f"❌ Error de conexión: {e}")
        return "❌ No se pudo conectar al servidor. Verifica que Railway esté funcionando.", 500
    except Exception as e:
        print(f"❌ Error: {e}")
        return f"❌ Error: {str(e)}", 500
        
@app.route('/eliminar_usuario/<int:id_usuario>')
@login_required
@role_required(['admin'])
def eliminar_usuario(id_usuario):
    """Elimina un usuario (solo admin)"""
    try:
        resp = requests.delete(f"{BACKEND_URL}/api/eliminar_usuario/{id_usuario}", timeout=10)
        if resp.status_code == 200:
            # Redirige sin mensaje
            pass
    except Exception as e:
        print(f"Error en /eliminar_usuario: {e}")
    
    return redirect("/usuarios")

@app.route('/dashboard')
@login_required
@role_required(['admin'])
def dashboard():
    filtro = request.args.get('filtro', '7d')
    mes = request.args.get('mes')
    anio = request.args.get('anio')
    
    try:
        url = f"{BACKEND_URL}/api/dashboard?filtro={filtro}"
        if mes and anio:
            url += f"&mes={mes}&anio={anio}"
        
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
        else:
            data = {}
    except Exception as e:
        print(f"Error en /dashboard: {e}")
        data = {}
    
    # Valores por defecto
    default_data = {
        "total_facturado": 0,
        "total_repuestos": 0,
        "total_mano_obra": 0,
        "total_diagnostico": 0,
        "total_servicios": 0,
        "ganancia_total": 0,
        "promedio_diario": 0,
        "labels": [],
        "ventas": [],
        "ganancia_acumulada": [],
        "proyeccion_labels": [],
        "proyeccion": [],
        "clientes_labels": [],
        "clientes_data": [],
        "meses_disponibles": [],
        "filtro_actual": filtro,
        "mes_actual": mes,
        "anio_actual": anio
    }
    
    for key, value in default_data.items():
        if key not in data:
            data[key] = value
    
    # ✅ LOG PARA VERIFICAR DATOS
    print(f"📊 Datos para dashboard: labels={len(data.get('labels', []))}, ventas={len(data.get('ventas', []))}")
    
    return render_template("dashboard_v2.html", **data)
    
@app.route('/repuestos')
@login_required
@role_required(['admin', 'operador'])
def repuestos():
    try:
        resp = requests.get(f"{BACKEND_URL}/api/repuestos", timeout=10)
        repuestos = resp.json() if resp.status_code == 200 else []
    except Exception as e:
        print(f"Error en /repuestos: {e}")
        repuestos = []
    return render_template("repuestos.html", repuestos=repuestos)
        
# ============================
# RUTAS ESTÁTICAS
# ============================
@app.route('/static/<path:path>')
def static_files(path):
    return app.send_static_file(path)

@app.route('/manifest.json')
def manifest():
    return app.send_static_file('manifest.json')

@app.route('/service-worker.js')
def service_worker():
    return app.send_static_file('service-worker.js')
# ============================
# VENTA RÁPIDA
# ============================
@app.route('/venta_rapida')
@login_required
@role_required(['admin', 'operador'])
def venta_rapida():
    return render_template("venta_rapida.html")


# ============================
# BALANCE DE VENTAS
# ============================
@app.route('/balance_ventas')
@login_required
@role_required(['admin'])
def balance_ventas():
    filtro = request.args.get('filtro', 'hoy')
    try:
        resp = requests.get(f"{BACKEND_URL}/api/balance_ventas?filtro={filtro}", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            registros = data.get('registros', [])
            total_ventas = data.get('total_ventas', 0)
            total_trabajo = data.get('total_trabajo', 0)
            total_directa = data.get('total_directa', 0)
            ganancia_trabajo = data.get('ganancia_trabajo', 0)
            ganancia_directa = data.get('ganancia_directa', 0)
            ganancia_neta = data.get('ganancia_neta', 0)
            total_repuestos_trabajo = data.get('total_repuestos_trabajo', 0)
            total_repuestos_directa = data.get('total_repuestos_directa', 0)
            trabajo_margen = data.get('trabajo_margen', 0)
            directa_margen = data.get('directa_margen', 0)
        else:
            registros = []
            total_ventas = 0
            total_trabajo = 0
            total_directa = 0
            ganancia_trabajo = 0
            ganancia_directa = 0
            ganancia_neta = 0
            total_repuestos_trabajo = 0
            total_repuestos_directa = 0
            trabajo_margen = 0
            directa_margen = 0
    except Exception as e:
        print(f"Error en /balance_ventas: {e}")
        registros = []
        total_ventas = 0
        total_trabajo = 0
        total_directa = 0
        ganancia_trabajo = 0
        ganancia_directa = 0
        ganancia_neta = 0
        total_repuestos_trabajo = 0
        total_repuestos_directa = 0
        trabajo_margen = 0
        directa_margen = 0
    
    hoy = datetime.now().strftime('%Y-%m-%d')
    hoy_count = sum(1 for r in registros if r.get('fecha', '') == hoy)
    registros_7d = [r for r in registros if r.get('fecha', '') >= (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')]
    registros_mes = [r for r in registros if r.get('fecha', '') >= (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')]
    
    return render_template(
        "balance_ventas.html",
        registros=registros,
        registros_7d=registros_7d,
        registros_mes=registros_mes,
        hoy_count=hoy_count,
        hoy_str=hoy,
        total_ventas=total_ventas,
        total_trabajo=total_trabajo,
        total_directa=total_directa,
        ganancia_trabajo=ganancia_trabajo,
        ganancia_directa=ganancia_directa,
        ganancia_neta=ganancia_neta,
        total_repuestos_trabajo=total_repuestos_trabajo,
        total_repuestos_directa=total_repuestos_directa,
        trabajo_margen=trabajo_margen,
        directa_margen=directa_margen,
        filtro=filtro
    )
# ============================
# FILTRO PARA FORMATO DE FECHA EN ESPAÑOL
# ============================
def formato_fecha_espanol(fecha):
    """Formatea una fecha en español (ej: Lunes 13 de Julio 2026)"""
    if not fecha:
        return ''
    
    if isinstance(fecha, str):
        try:
            fecha = datetime.strptime(fecha, '%Y-%m-%d')
        except:
            return fecha
    
    dias = {
        0: 'Lunes', 1: 'Martes', 2: 'Miércoles', 3: 'Jueves',
        4: 'Viernes', 5: 'Sábado', 6: 'Domingo'
    }
    meses = {
        1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
        5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
        9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
    }
    
    dia_nombre = dias.get(fecha.weekday(), '')
    dia = fecha.day
    mes = meses.get(fecha.month, '')
    año = fecha.year
    
    return f"{dia_nombre} {dia} de {mes} {año}"

# Agregar el filtro a Jinja2
app.jinja_env.filters['fecha_espanol'] = formato_fecha_espanol

# ============================
# INICIO
# ============================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
