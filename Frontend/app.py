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
import sys
import re
import json

# ============================
# CONFIGURACIÓN DE LA APP
# ============================
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "clave_frontend_segura")
PDF_SECRET_KEY = os.environ.get("PDF_SECRET_KEY", "dixon_pdf_2025")

# ============================
# CONFIGURACIÓN DE LOGS PERSISTENTES
# ============================
IS_VERCEL = os.environ.get('VERCEL_ENV') == 'production' or os.environ.get('VERCEL')

if IS_VERCEL:
    LOG_DIR = '/tmp/logs'
else:
    LOG_DIR = 'logs'

if not os.path.exists(LOG_DIR):
    try:
        os.makedirs(LOG_DIR)
    except OSError:
        LOG_DIR = None

logger = logging.getLogger('dixon_app')
logger.setLevel(logging.DEBUG)

if logger.hasHandlers():
    logger.handlers.clear()

if LOG_DIR:
    try:
        file_handler = RotatingFileHandler(
            os.path.join(LOG_DIR, 'dixon_app.log'),
            maxBytes=10485760,
            backupCount=5
        )
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"⚠️ No se pudo crear archivo de logs: {e}")

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)

app.logger.handlers = logger.handlers
app.logger.setLevel(logger.level)

if IS_VERCEL:
    logger.info("🚀 Aplicación corriendo en Vercel - Logs en consola")
else:
    logger.info(f"📁 Logs guardados en: {LOG_DIR}")

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
BACKEND_URL = os.environ.get("BACKEND_URL", "https://ea-dixon-production.up.railway.app")

# ============================
# FUNCIÓN CENTRALIZADA PARA ENVIAR NOTIFICACIONES (NUEVO)
# ============================
def enviar_notificacion_push(titulo, mensaje, url="/estado", id_reg=None):
    """
    Envía una notificación push a través del backend.
    Si falla, guarda en log local y continúa.
    """
    try:
        backend_url = os.environ.get("BACKEND_URL", "https://ea-dixon-production.up.railway.app")
        url_notificacion = f"{backend_url}/api/enviar_notificacion"
        
        logger.info(f"📨 Enviando notificación a: {url_notificacion}")
        logger.info(f"📨 Título: {titulo}")
        
        resp = requests.post(
            url_notificacion,
            json={
                "titulo": titulo,
                "mensaje": mensaje,
                "url": url,
                "id": id_reg
            },
            timeout=5,
            headers={"Content-Type": "application/json"}
        )
        
        if resp.status_code == 200:
            logger.info(f"✅ Notificación enviada correctamente")
            return True
        else:
            logger.warning(f"⚠️ Notificación falló: {resp.status_code} - {resp.text[:100]}")
            return False
            
    except requests.exceptions.ConnectionError:
        logger.error(f"❌ No se pudo conectar al backend para notificación")
        return False
    except Exception as e:
        logger.error(f"❌ Error en notificación: {e}")
        return False

# ============================
# SANITIZACIÓN
# ============================
def sanitizar_input(texto):
    if not texto:
        return ''
    texto = re.sub(r'<[^>]+>', '', texto)
    texto = re.sub(r'[;(){}<>]', '', texto)
    return texto[:500]

def sanitizar_patente(patente):
    if not patente:
        return ''
    patente = re.sub(r'[^A-Za-z0-9]', '', patente)
    return patente.upper()[:10]

# ============================
# CONFIGURACIÓN DE SESIÓN
# ============================
app.permanent_session_lifetime = timedelta(hours=8)

# ============================
# DECORADORES
# ============================
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("usuario"):
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated

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
# ============================
# CONTEXT PROCESSOR
# ============================
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
    
    # ============================================
    # CONTADOR DE FLOTAS PENDIENTES
    # ============================================
    flotas_pendientes_count = 0
    try:
        resp = requests.get(f"{BACKEND_URL}/api/flotas_pendientes_count", timeout=3)
        if resp.status_code == 200:
            flotas_pendientes_count = resp.json().get('count', 0)
    except Exception as e:
        print(f"⚠️ Error al obtener flotas pendientes: {e}")
        flotas_pendientes_count = 0
    
    # ============================================
    # ✅ CONTADOR DE DEUDORES (DEFINIDO ANTES DE USARLO)
    # ============================================
    deudores_count = 0
    try:
        resp_deudores = requests.get(f"{BACKEND_URL}/api/deudores/todos", timeout=3)
        if resp_deudores.status_code == 200:
            deudores = resp_deudores.json()
            deudores_count = len([d for d in deudores if d.get('monto_deuda', 0) > 0])
    except Exception as e:
        print(f"⚠️ Error al obtener deudores: {e}")
        deudores_count = 0
    
    vapid_public_key = os.environ.get("VAPID_PUBLIC_KEY", "")
    
    return dict(
        backend_url=BACKEND_URL,
        fecha_espanol=fecha_espanol,
        fecha_corta_espanol=fecha_corta_espanol,
        flotas_pendientes_count=flotas_pendientes_count,
        deudores_count=deudores_count,  # ✅ AHORA SÍ ESTÁ DEFINIDO
        vapid_public_key=vapid_public_key
    )


# ============================
# RUTAS PRINCIPALES
# ============================
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
        username = sanitizar_input(request.form.get('username', '').strip())
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
                session.permanent = True
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

@app.route('/verificar_sesion')
@login_required
def verificar_sesion():
    return jsonify({
        "activa": True,
        "usuario": session.get('usuario'),
        "rol": session.get('rol')
    })

# ============================
# PROXY PARA GUARDAR SUSCRIPCIÓN (SOLO REENVÍA AL BACKEND)
# ============================
@app.route('/api/guardar_suscripcion', methods=['POST'])
def guardar_suscripcion_route():
    """Reenvía la suscripción al backend (NO guarda directamente)"""
    try:
        data = request.json
        backend_url = os.environ.get("BACKEND_URL", "https://ea-dixon-production.up.railway.app")
        
        resp = requests.post(
            f"{backend_url}/api/guardar_suscripcion",
            json=data,
            timeout=10,
            headers={'Content-Type': 'application/json'}
        )
        
        if resp.status_code == 200:
            logger.info("✅ Suscripción guardada en el backend")
            return jsonify(resp.json()), resp.status_code
        else:
            logger.error(f"❌ Error guardando suscripción en backend: {resp.text}")
            return jsonify({"success": False}), 500
            
    except Exception as e:
        logger.error(f"Error al guardar suscripción: {e}")
        return jsonify({"success": False}), 500

# ============================
# ESTADO
# ============================
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
# AGREGAR CLIENTE (PÁGINA CON CATÁLOGO COMPLETO)
# ============================
@app.route('/agregar_cliente')
@login_required
def agregar_cliente():
    try:
        # Obtener flotas disponibles
        resp_flotas = requests.get(f"{BACKEND_URL}/api/flotas_disponibles", timeout=5)
        flotas = resp_flotas.json() if resp_flotas.status_code == 200 else []
        
        # Obtener marcas desde el backend
        resp_marcas = requests.get(f"{BACKEND_URL}/api/marcas", timeout=5)
        marcas = resp_marcas.json() if resp_marcas.status_code == 200 else []
        
        # Obtener modelos (se cargarán dinámicamente con JS)
        modelos = []
        
    except Exception as e:
        logger.error(f"⚠️ Error al cargar datos para agregar_cliente: {e}")
        flotas = []
        marcas = []
        modelos = []
    
    return render_template("agregar_cliente.html", 
                          flotas=flotas, 
                          marcas=marcas, 
                          modelos=modelos)
# ============================
# AGREGAR CLIENTE (PROCESAR)
# ============================
@app.route('/agregar', methods=['POST'])
@login_required
def agregar():
    usuario = session.get('usuario')
    nombre = sanitizar_input(request.form.get('nombre', '').strip())
    patente = sanitizar_patente(request.form.get('patente', '').strip())

    logger.info(f"📝 Usuario '{usuario}' agregando cliente: '{nombre}', patente: '{patente}'")
    
    flota = request.form.get('flota', '').strip()
    if flota == '__nueva__':
        flota = request.form.get('flota_nueva', '').strip()
    
    try:
        resp_verificar = requests.get(
            f"{BACKEND_URL}/api/verificar_duplicado",
            params={"nombre": nombre, "patente": patente},
            timeout=5
        )
        if resp_verificar.status_code == 200 and resp_verificar.json().get('duplicado', False):
            logger.warning(f"⚠️ Intento de duplicado: usuario '{usuario}' intentó agregar '{nombre}' - '{patente}'")
            flash('⚠️ Ya existe un registro con estos datos en los últimos 5 minutos.', 'warning')
            return redirect("/agregar_cliente")
    except Exception as e:
        logger.warning(f"⚠️ Error al verificar duplicado para '{nombre}': {str(e)}")
    
    data = {
        'nombre': nombre,
        'patente': patente,
        'marca': sanitizar_input(request.form.get('marca', '').strip()),
        'modelo': sanitizar_input(request.form.get('modelo', '').strip()),
        'telefono': sanitizar_input(request.form.get('telefono', '').strip()),
        'observaciones': sanitizar_input(request.form.get('observaciones', '').strip()),
        'kilometraje': int(request.form.get('kilometraje', 0) or 0),
        'anio': int(request.form.get('anio', 0) or 0),
        'flota': flota if flota else None,
        'usuario': usuario
    }
    
    try:
        resp = requests.post(f"{BACKEND_URL}/api/agregar", json=data, timeout=10)
        if resp.status_code != 200:
            logger.error(f"❌ Error al agregar cliente: {resp.text}")
            flash('❌ Error al registrar el cliente.', 'error')
            return redirect("/agregar_cliente")
        
        logger.info(f"✅ Cliente agregado exitosamente por '{usuario}': '{nombre}', patente: '{patente}'")
        
        # ✅ ENVIAR NOTIFICACIÓN - AHORA USA LA FUNCIÓN CENTRALIZADA
        enviar_notificacion_push(
            titulo="📋 Nuevo Cliente",
            mensaje=f"{nombre}\nPatente: {patente}\nRegistrado por: {usuario}",
            url="/estado"
        )
        
        flash('✅ Cliente registrado correctamente', 'success')
    except Exception as e:
        logger.error(f"⚠️ Error en /agregar: {str(e)}")
        flash('⚠️ Error de conexión.', 'error')
        return redirect("/agregar_cliente")
    
    return redirect("/estado")

# ============================
# PAGAR
# ============================
@app.route('/pagar/<int:id_reg>', methods=['GET', 'POST'])
@login_required
def pagar(id_reg):
    usuario = session.get('usuario')
    logger.info(f"💰 Usuario '{usuario}' iniciando pago para ID {id_reg}")
    
    try:
        resp = requests.get(f"{BACKEND_URL}/api/registro/{id_reg}", timeout=10)
        if resp.status_code != 200:
            logger.error(f"❌ Registro ID {id_reg} no encontrado")
            return f"Registro {id_reg} no encontrado", 404
        registro = resp.json()
    except Exception as e:
        logger.error(f"⚠️ Error al obtener registro ID {id_reg}: {str(e)}")
        return "Error de conexión", 500
    
    if request.method == 'POST':
        monto = float(request.form.get('monto', 0))
        forma_pago = sanitizar_input(request.form.get('forma_pago', 'efectivo').strip())
        observaciones_pago = sanitizar_input(request.form.get('observaciones_pago', '').strip())
        diagnostico = sanitizar_input(request.form.get('diagnostico', '').strip())
        reparacion = sanitizar_input(request.form.get('reparacion', 'Reparación realizada').strip())
        resultado = sanitizar_input(request.form.get('resultado', 'reparado').strip())
        tiempo_estimado = sanitizar_input(request.form.get('tiempo_estimado', '00:00:00').strip())
        
        if monto <= 0:
            logger.warning(f"⚠️ Intento de pago con monto 0 o negativo ID {id_reg}")
            flash('⚠️ El monto debe ser mayor a 0', 'error')
            return render_template("pagar.html", id=id_reg, registro=registro)
        
        logger.info(f"💳 Usuario '{usuario}' procesando pago ID {id_reg}: monto ${monto}, forma: {forma_pago}")
        
        data = {
            'monto': monto,
            'observaciones_pago': observaciones_pago,
            'diagnostico': diagnostico,
            'reparacion': reparacion,
            'resultado': resultado,
            'tiempo_estimado': tiempo_estimado,
            'atendido_por': session.get('nombre_completo', session.get('usuario')),
            'forma_pago': forma_pago
        }
        
        try:
            resp = requests.post(f"{BACKEND_URL}/api/pagar/{id_reg}", json=data, timeout=10)
            if resp.status_code == 200:
                logger.info(f"✅ Pago ID {id_reg} completado por '{usuario}' - monto: ${monto}")
                return redirect(f"/pago_exitoso/{id_reg}")
            logger.error(f"❌ Error en pago ID {id_reg}: {resp.text}")
            flash('❌ Error al procesar el pago', 'error')
            return render_template("pagar.html", id=id_reg, registro=registro)
        except Exception as e:
            logger.error(f"⚠️ Error en pago ID {id_reg}: {str(e)}")
            flash('⚠️ Error de conexión', 'error')
            return render_template("pagar.html", id=id_reg, registro=registro)
    
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
        
        # ✅ ENVIAR NOTIFICACIÓN - AHORA USA LA FUNCIÓN CENTRALIZADA
        nombre_cliente = registro.get('nombre', 'Cliente')
        monto = registro.get('monto', 0)
        forma_pago = registro.get('forma_pago', 'efectivo')
        
        enviar_notificacion_push(
            titulo="💰 Pago Confirmado",
            mensaje=f"Cliente: {nombre_cliente}\nMonto: ${float(monto):,.0f}\nForma: {forma_pago}",
            url=f"/pago_exitoso/{id_reg}",
            id_reg=id_reg
        )
            
    except Exception as e:
        logger.error(f"❌ Error en /pago_exitoso: {str(e)}")
        registro = {}
        url_pdf = ""
    
    return render_template("pago_exitoso.html", registro=registro, url_pdf=url_pdf)

# ============================
# CAMBIAR PASSWORD
# ============================
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
                data = {'username': usuario, 'password_actual': password_actual, 'password_nueva': password_nueva}
                resp = requests.post(f"{BACKEND_URL}/api/cambiar_password", json=data, timeout=10)
                if resp.status_code == 200:
                    success = "✅ Contraseña actualizada correctamente"
                    logger.info(f"🔑 Usuario '{usuario}' cambió su contraseña")
                else:
                    error = resp.json().get('error', '❌ Error al cambiar contraseña')
            except Exception as e:
                logger.error(f"⚠️ Error en /cambiar_password: {str(e)}")
                error = "⚠️ Error de conexión"
    
    return render_template("cambiar_password.html", error=error, success=success)

# ============================
# VALIDACIÓN DE PAGOS
# ============================
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
        else:
            pendientes, validados, total_pagado = [], [], 0
    except Exception as e:
        logger.error(f"❌ Error en /pendientes_validacion: {str(e)}")
        pendientes, validados, total_pagado = [], [], 0
    
    return render_template("pendientes_validacion.html", pendientes=pendientes, validados=validados, total_pagado=total_pagado)

@app.route('/validar_pago/<int:id_reg>', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'operador'])
def validar_pago(id_reg):
    usuario = session.get('usuario')
    logger.info(f"📊 Usuario '{usuario}' iniciando validación para ID {id_reg}")
    
    if session.get('rol') not in ['admin']:
        logger.warning(f"⚠️ Usuario '{usuario}' sin permisos para validar ID {id_reg}")
        return "No tienes permisos para validar pagos", 403
    
    try:
        resp = requests.get(f"{BACKEND_URL}/api/registro/{id_reg}", timeout=10)
        if resp.status_code != 200:
            logger.error(f"❌ Registro ID {id_reg} no encontrado")
            return "Registro no encontrado", 404
        registro = resp.json()
    except Exception as e:
        logger.error(f"⚠️ Error al obtener registro ID {id_reg}: {str(e)}")
        return "Error de conexión", 500
    
    if registro.get('tipo_venta') == 'directa':
        logger.info(f"ℹ️ Venta directa ID {id_reg} no requiere validación")
        flash('⚠️ Las ventas directas no requieren validación de costos.', 'warning')
        return redirect("/estado")
    
    if registro.get('estado') != 'pagado':
        logger.warning(f"⚠️ Intento de validar registro ID {id_reg} no pagado")
        return "Este pago no está pagado", 400
    
    try:
        resp_usuarios = requests.get(f"{BACKEND_URL}/api/usuarios", timeout=10)
        usuarios = resp_usuarios.json() if resp_usuarios.status_code == 200 else []
    except:
        usuarios = []
    
    error = None
    
    if request.method == 'POST':
        logger.info(f"📝 Usuario '{usuario}' enviando validación para ID {id_reg}")
        
        validado_por = sanitizar_input(request.form.get('validado_por', '').strip())
        if not validado_por:
            validado_por = session.get('nombre_completo', session.get('usuario'))
        
        nombres_repuestos = request.form.getlist('repuesto_nombre[]')
        nombres_repuestos = [sanitizar_input(n) for n in nombres_repuestos]
        costos_repuestos = request.form.getlist('repuesto_costo[]')
        
        detalles_repuestos = []
        for i in range(len(nombres_repuestos)):
            if nombres_repuestos[i].strip():
                try:
                    costo = float(costos_repuestos[i]) if costos_repuestos[i] else 0
                except ValueError:
                    costo = 0
                detalles_repuestos.append({
                    'nombre': nombres_repuestos[i].strip(),
                    'costo': costo
                })
        
        observaciones_pago = sanitizar_input(request.form.get('observaciones_costos', '').strip())
        diagnostico = sanitizar_input(request.form.get('diagnostico', '').strip())
        reparacion = sanitizar_input(request.form.get('reparacion', 'Reparación realizada').strip())
        resultado = sanitizar_input(request.form.get('resultado', 'reparado').strip())
        tiempo_estimado = sanitizar_input(request.form.get('tiempo_estimado', '00:00:00').strip())
        estado_ot = sanitizar_input(request.form.get('estado_ot', 'Pendiente').strip())
        
        if not detalles_repuestos:
            flash('⚠️ Debes agregar al menos un repuesto para validar.', 'warning')
            return render_template("validar_pago.html", id=id_reg, registro=registro, usuarios=usuarios, error=None)
        
        costo_repuestos_total = float(request.form.get('costo_repuestos', 0))
        if costo_repuestos_total <= 0 and not detalles_repuestos:
            flash('⚠️ El costo de repuestos debe ser mayor a 0.', 'warning')
            return render_template("validar_pago.html", id=id_reg, registro=registro, usuarios=usuarios, error=None)
        
        data = {
            'costo_repuestos': costo_repuestos_total,
            'costo_mano_obra_real': float(request.form.get('costo_mano_obra', 0)),
            'costo_diagnostico_real': float(request.form.get('costo_diagnostico', 0)),
            'ganancia_neta': float(request.form.get('ganancia_neta', 0)),
            'observaciones_pago': observaciones_pago,
            'validado_por': validado_por,
            'diagnostico': diagnostico,
            'reparacion': reparacion,
            'resultado': resultado,
            'tiempo_estimado': tiempo_estimado,
            'detalles_repuestos': detalles_repuestos,
            'estado_ot': estado_ot
        }
        
        try:
            resp = requests.post(f"{BACKEND_URL}/api/validar_pago/{id_reg}", json=data, timeout=10)
            if resp.status_code == 200:
                logger.info(f"✅ Validación completada para ID {id_reg} por '{usuario}'")
                return redirect(f"/pago_validado/{id_reg}")
            error = resp.json().get('error', 'Error al validar')
            logger.error(f"❌ Error en validación ID {id_reg}: {error}")
        except Exception as e:
            logger.error(f"⚠️ Error en /validar_pago POST: {str(e)}")
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
        logger.error(f"Error en /pago_validado: {e}")
        registro = {}
    return render_template("pago_validado.html", registro=registro)

# ============================
# REGISTROS
# ============================
@app.route('/registros')
@login_required
@role_required(['admin'])
def registros():
    filtro = request.args.get('filtro', 'todos')
    
    try:
        # Enviar el filtro al backend
        resp = requests.get(f"{BACKEND_URL}/api/registros?filtro={filtro}", timeout=10)
        registros = resp.json() if resp.status_code == 200 else []
    except Exception as e:
        logger.error(f"Error en /registros: {e}")
        registros = []
    
    hoy = datetime.now().date()
    hoy_str = hoy.strftime('%Y-%m-%d')
    fecha_7d = (hoy - timedelta(days=7)).strftime('%Y-%m-%d')
    fecha_mes = (hoy - timedelta(days=30)).strftime('%Y-%m-%d')
    
    # Estos son para mostrar en los filtros (siempre el total sin filtrar)
    try:
        resp_all = requests.get(f"{BACKEND_URL}/api/registros?filtro=todos", timeout=10)
        registros_all = resp_all.json() if resp_all.status_code == 200 else []
    except:
        registros_all = []
    
    registros_hoy = [r for r in registros_all if r.get('fecha', '') == hoy_str]
    registros_7d = [r for r in registros_all if r.get('fecha', '') >= fecha_7d]
    registros_mes = [r for r in registros_all if r.get('fecha', '') >= fecha_mes]
    total_general = sum(r.get('monto', 0) for r in registros_all)
    
    return render_template(
        "registros.html",
        registros=registros,           # Ya filtrados por el backend
        registros_hoy=registros_hoy,   # Para mostrar el contador
        registros_7d=registros_7d,     # Para mostrar el contador
        registros_mes=registros_mes,   # Para mostrar el contador
        total_general=total_general,
        filtro=filtro
    )

@app.route('/balance')
@login_required
@role_required(['admin'])
def balance():
    filtro = request.args.get('filtro', 'hoy')
    hoy = datetime.now().date()
    
    # ============================================
    # 1. OBTENER VENTAS
    # ============================================
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
            registros, total_pagado, total_repuestos, total_mano_obra, total_diagnostico, ganancia_neta = [], 0, 0, 0, 0, 0
    except Exception as e:
        logger.error(f"Error en /balance (ventas): {e}")
        registros, total_pagado, total_repuestos, total_mano_obra, total_diagnostico, ganancia_neta = [], 0, 0, 0, 0, 0
    
    # ============================================
    # 2. OBTENER GASTOS POR SEPARADO
    # ============================================
    gastos_operativos = []
    total_gastos = 0
    
    try:
        # ✅ CORREGIDO: Definir fechas correctamente según el filtro
        if filtro == 'hoy':
            # 🔧 CORRECCIÓN: Usar el día de HOY
            fecha_inicio = hoy.strftime('%Y-%m-%d')
            fecha_fin = hoy.strftime('%Y-%m-%d')
        elif filtro == '7d':
            fecha_inicio = (hoy - timedelta(days=7)).strftime('%Y-%m-%d')
            fecha_fin = hoy.strftime('%Y-%m-%d')
        elif filtro == 'mes':
            fecha_inicio = (hoy - timedelta(days=30)).strftime('%Y-%m-%d')
            fecha_fin = hoy.strftime('%Y-%m-%d')
        elif filtro == 'todos':
            fecha_inicio = '2020-01-01'
            fecha_fin = hoy.strftime('%Y-%m-%d')
        else:
            fecha_inicio = hoy.strftime('%Y-%m-%d')
            fecha_fin = hoy.strftime('%Y-%m-%d')
        
        logger.info(f"📊 Balance - Buscando gastos entre {fecha_inicio} y {fecha_fin}")
        
        resp_gastos = requests.get(
            f"{BACKEND_URL}/api/gastos_balance?fecha_inicio={fecha_inicio}&fecha_fin={fecha_fin}",
            timeout=10
        )
        
        if resp_gastos.status_code == 200:
            gastos_operativos = resp_gastos.json()
            for g in gastos_operativos:
                g['monto'] = float(g['monto']) if g.get('monto') else 0
            total_gastos = sum(g.get('monto', 0) for g in gastos_operativos)
            logger.info(f"✅ Gastos encontrados: {len(gastos_operativos)} - Total: ${total_gastos}")
        else:
            logger.error(f"❌ Error al obtener gastos: {resp_gastos.status_code}")
            
    except Exception as e:
        logger.error(f"❌ Error al obtener gastos para balance: {e}")
        gastos_operativos = []
        total_gastos = 0
    
    # ======================================@app.route('/balance')
@login_required
@role_required(['admin'])
def balance():
    filtro = request.args.get('filtro', 'hoy')
    hoy = datetime.now().date()
    
    # ============================================
    # 1. OBTENER VENTAS
    # ============================================
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
            registros, total_pagado, total_repuestos, total_mano_obra, total_diagnostico, ganancia_neta = [], 0, 0, 0, 0, 0
    except Exception as e:
        logger.error(f"Error en /balance (ventas): {e}")
        registros, total_pagado, total_repuestos, total_mano_obra, total_diagnostico, ganancia_neta = [], 0, 0, 0, 0, 0
    
    # ============================================
    # 2. OBTENER GASTOS POR SEPARADO
    # ============================================
    gastos_operativos = []
    total_gastos = 0
    
    try:
        primer_dia_mes = hoy.replace(day=1).strftime('%Y-%m-%d')
        ultimo_dia_mes = hoy.strftime('%Y-%m-%d')
        
        logger.info(f"📊 Balance - Buscando gastos del mes: {primer_dia_mes} a {ultimo_dia_mes}")
        
        resp_gastos = requests.get(
            f"{BACKEND_URL}/api/gastos_balance?fecha_inicio={primer_dia_mes}&fecha_fin={ultimo_dia_mes}",
            timeout=10
        )
        
        if resp_gastos.status_code == 200:
            gastos_operativos = resp_gastos.json()
            # ✅ CONVERTIR monto a float
            for g in gastos_operativos:
                g['monto'] = float(g['monto']) if g.get('monto') else 0
            total_gastos = sum(g.get('monto', 0) for g in gastos_operativos)
            logger.info(f"✅ Gastos encontrados: {len(gastos_operativos)} - Total: ${total_gastos}")
        else:
            logger.error(f"❌ Error al obtener gastos: {resp_gastos.status_code}")
            
    except Exception as e:
        logger.error(f"❌ Error al obtener gastos para balance: {e}")
        gastos_operativos = []
        total_gastos = 0
    
    # ============================================
    # 3. CALCULAR GANANCIA REAL
    # ============================================
    ganancia_real = total_pagado - total_repuestos - total_mano_obra - total_gastos
    
    logger.info(f"📊 Balance final:")
    logger.info(f"   Ingresos: ${total_pagado}")
    logger.info(f"   Repuestos: ${total_repuestos}")
    logger.info(f"   Mano de Obra: ${total_mano_obra}")
    logger.info(f"   Gastos: ${total_gastos}")
    logger.info(f"   Ganancia Real: ${ganancia_real}")
    
    # ============================================
    # 4. FILTROS PARA LA VISTA
    # ============================================
    hoy_list = [r for r in registros if r.get('fecha') == hoy.strftime('%Y-%m-%d')]
    semana_list = [r for r in registros if r.get('fecha', '') >= (hoy - timedelta(days=7)).strftime('%Y-%m-%d')]
    mes_list = [r for r in registros if r.get('fecha', '') >= (hoy - timedelta(days=30)).strftime('%Y-%m-%d')]
    todos_list = registros
    
    logger.info(f"📊 ENVIANDO AL TEMPLATE: gastos_operativos={len(gastos_operativos)}, total_gastos={total_gastos}")
    
    return render_template(
        "balance.html",
        registros=registros,
        total_pagado=total_pagado,
        total_repuestos=total_repuestos,
        total_mano_obra=total_mano_obra,
        total_diagnostico=total_diagnostico,
        ganancia_neta=ganancia_neta,
        ganancia_real=ganancia_real,
        total_gastos=total_gastos,
        gastos_operativos=gastos_operativos,
        filtro=filtro,
        hoy=hoy_list,
        semana=semana_list,
        mes=mes_list,
        todos=todos_list
    )
# ============================
# MODELOS
# ============================
@app.route('/modelos/<marca>')
@login_required
def modelos(marca):
    try:
        resp = requests.get(f"{BACKEND_URL}/api/modelos/{marca}", timeout=10)
        return jsonify(resp.json() if resp.status_code == 200 else [])
    except:
        return jsonify([])

# ============================
# EDITAR COMPLETO
# ============================
@app.route('/editar_completo/<int:id_reg>', methods=['POST'])
@login_required
@role_required(['admin'])
def editar_completo(id_reg):
    data = request.json
    
    campos_texto = [
        'nombre', 'telefono', 'patente', 'marca', 'modelo', 'flota', 
        'observaciones_cliente', 'diagnostico', 'reparacion', 'resultado',
        'observaciones_pago', 'validado_por', 'atendido_por'
    ]
    
    for campo in campos_texto:
        if campo in data and data[campo] is not None:
            data[campo] = sanitizar_input(str(data[campo]))
    
    if 'patente' in data and data['patente']:
        data['patente'] = sanitizar_patente(data['patente'])
    
    campos_numericos = [
        'monto', 'anio', 'costo_repuestos_real', 'costo_mano_obra_real',
        'costo_diagnostico_real', 'ganancia_neta', 'kilometraje'
    ]
    
    for campo in campos_numericos:
        if campo in data and data[campo] is not None:
            try:
                data[campo] = float(data[campo])
            except (ValueError, TypeError):
                data[campo] = 0
    
    if 'validado' in data:
        data['validado'] = bool(data['validado'])
    
    if 'fecha' in data and data['fecha']:
        import re
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', data['fecha']):
            data['fecha'] = None
    
    if 'hora' in data and data['hora']:
        import re
        if not re.match(r'^\d{2}:\d{2}:\d{2}$', data['hora']):
            data['hora'] = '00:00:00'
    
    if not data.get('nombre') or not data.get('nombre').strip():
        return jsonify({"success": False, "error": "El nombre es obligatorio"}), 400
    
    try:
        resp = requests.post(f"{BACKEND_URL}/api/editar_completo/{id_reg}", json=data, timeout=10)
        if resp.status_code == 200:
            logger.info(f"✅ Registro ID {id_reg} editado correctamente por '{session.get('usuario')}'")
            return jsonify({"success": True})
        
        logger.error(f"❌ Error al editar registro ID {id_reg}: {resp.text}")
        return jsonify({"success": False, "error": resp.text}), 500
    except Exception as e:
        logger.error(f"⚠️ Error en /editar_completo ID {id_reg}: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

# ============================
# FLOTAS
# ============================
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

@app.route('/flotas_pendientes')
@login_required
@role_required(['admin'])
def flotas_pendientes():
    try:
        resp = requests.get(f"{BACKEND_URL}/api/flotas_pendientes_agrupadas", timeout=10)
        flotas_agrupadas = resp.json() if resp.status_code == 200 else []
        total_general = sum(float(f.get('total_pendiente', 0)) for f in flotas_agrupadas)
    except Exception as e:
        logger.error(f"Error en /flotas_pendientes: {e}")
        flotas_agrupadas, total_general = [], 0
    
    today = datetime.now().strftime('%Y-%m-%d')
    return render_template("flotas_pendientes.html", 
                          flotas_agrupadas=flotas_agrupadas, 
                          total_general=total_general, 
                          today=today)

# ============================
# USUARIOS
# ============================
@app.route('/register', methods=['GET', 'POST'])
@login_required
def register():
    if session.get('rol') != 'admin':
        return "No tienes permisos", 403
    
    error = None
    success = None
    
    if request.method == 'POST':
        username = sanitizar_input(request.form.get('username', '').strip())
        password = request.form.get('password')
        rol = sanitizar_input(request.form.get('rol', 'basico').strip())
        nombre_completo = sanitizar_input(request.form.get('nombre_completo', '').strip())
        
        if not username:
            error = "⚠️ El nombre de usuario no puede estar vacío o contener caracteres inválidos"
        elif not password:
            error = "⚠️ La contraseña es obligatoria"
        elif len(password) < 6:
            error = "⚠️ La contraseña debe tener al menos 6 caracteres"
        elif rol not in ['admin', 'operador', 'basico']:
            error = "⚠️ Rol inválido"
        elif nombre_completo and len(nombre_completo) < 2:
            error = "⚠️ El nombre completo debe tener al menos 2 caracteres"
        else:
            try:
                data = {
                    'username': username,
                    'password': password,
                    'rol': rol,
                    'nombre_completo': nombre_completo
                }
                logger.info(f"📝 Creando usuario: {username}, rol: {rol}")
                resp = requests.post(f"{BACKEND_URL}/api/crear_usuario", json=data, timeout=10)
                
                if resp.status_code == 200:
                    success = f"✅ Usuario {username} creado correctamente"
                    logger.info(f"👤 Usuario '{username}' creado por '{session.get('usuario')}'")
                else:
                    error = resp.json().get('error', '❌ Error al crear usuario')
                    logger.error(f"❌ Error al crear usuario {username}: {error}")
            except Exception as e:
                logger.error(f"⚠️ Error en /register: {e}")
                error = "⚠️ Error de conexión con el servidor"
    
    return render_template("register.html", error=error, success=success)

@app.route('/usuarios')
@login_required
@role_required(['admin'])
def usuarios():
    try:
        resp = requests.get(f"{BACKEND_URL}/api/usuarios", timeout=10)
        usuarios = resp.json() if resp.status_code == 200 else []
    except Exception as e:
        logger.error(f"Error en /usuarios: {e}")
        usuarios = []
    return render_template("usuarios.html", usuarios=usuarios)

@app.route('/eliminar_usuario/<int:id_usuario>')
@login_required
@role_required(['admin'])
def eliminar_usuario(id_usuario):
    try:
        resp = requests.delete(f"{BACKEND_URL}/api/eliminar_usuario/{id_usuario}", timeout=10)
        if resp.status_code == 200:
            logger.info(f"🗑️ Usuario ID {id_usuario} eliminado por '{session.get('usuario')}'")
    except Exception as e:
        logger.error(f"Error en /eliminar_usuario: {e}")
    return redirect("/usuarios")

# ============================
# AUDITORÍA
# ============================
@app.route('/auditoria_descargas')
@login_required
@role_required(['admin'])
def auditoria_descargas():
    try:
        resp = requests.get(f"{BACKEND_URL}/api/auditoria", timeout=10)
        historial = resp.json() if resp.status_code == 200 else []
    except Exception as e:
        logger.error(f"Error en /auditoria_descargas: {e}")
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
        backend_url = os.environ.get("BACKEND_URL", "https://ea-dixon-production.up.railway.app")
        url = f"{backend_url}/api/exportar_flota_pdf/{flota}"
        resp = requests.post(url, json={"fecha_desde": fecha_desde, "fecha_hasta": fecha_hasta}, timeout=60)
        
        if resp.status_code == 200:
            # ✅ ENVIAR NOTIFICACIÓN - AHORA USA LA FUNCIÓN CENTRALIZADA
            enviar_notificacion_push(
                titulo="📄 Reporte Generado",
                mensaje=f"Flota: {flota}\nFechas: {fecha_desde} - {fecha_hasta}\nGenerado por: {session.get('usuario')}",
                url="/flotas"
            )
            
            return send_file(
                io.BytesIO(resp.content),
                mimetype='application/pdf',
                as_attachment=True,
                download_name=f'reporte_flota_{flota}.pdf'
            )
        return f"❌ Error: {resp.text}", resp.status_code
    except Exception as e:
        logger.error(f"Error en /exportar_flota_pdf: {e}")
        return f"❌ Error: {str(e)}", 500

# ============================
# DASHBOARD
# ============================
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
        data = resp.json() if resp.status_code == 200 else {}
    except Exception as e:
        logger.error(f"Error en /dashboard: {e}")
        data = {}
    
    default_data = {
        "total_facturado": 0, "total_repuestos": 0, "total_mano_obra": 0,
        "total_diagnostico": 0, "total_servicios": 0, "ganancia_total": 0,
        "promedio_diario": 0, "labels": [], "ventas": [],
        "ganancia_acumulada": [], "proyeccion_labels": [], "proyeccion": [],
        "clientes_labels": [], "clientes_data": [], "meses_disponibles": [],
        "filtro_actual": filtro, "mes_actual": mes, "anio_actual": anio
    }
    
    for key, value in default_data.items():
        if key not in data:
            data[key] = value
    
    return render_template("dashboard_v2.html", **data)

# ============================
# REPUESTOS
# ============================
@app.route('/repuestos')
@login_required
@role_required(['admin', 'operador'])
def repuestos():
    try:
        resp = requests.get(f"{BACKEND_URL}/api/repuestos", timeout=10)
        repuestos = resp.json() if resp.status_code == 200 else []
    except Exception as e:
        logger.error(f"Error en /repuestos: {e}")
        repuestos = []
    return render_template("repuestos.html", repuestos=repuestos)
# ============================================
# API: OBTENER REPUESTOS (CON CATEGORÍA)
# ============================================
@app.route('/api/repuestos', methods=['GET'])
@login_required
@role_required(['admin', 'operador'])
def api_repuestos():
    """Obtiene todos los repuestos con sus categorías para la tabla"""
    try:
        # Reenviar la solicitud al backend
        resp = requests.get(f"{BACKEND_URL}/api/repuestos", timeout=10)
        if resp.status_code == 200:
            return jsonify(resp.json())
        else:
            logger.error(f"❌ Error al obtener repuestos del backend: {resp.status_code}")
            return jsonify([])
    except Exception as e:
        logger.error(f"❌ Error en api_repuestos: {e}")
        return jsonify([])
# ============================
# DEUDORES
# ============================
@app.route('/deudores')
@login_required
@role_required(['admin', 'operador'])
def deudores():
    """Lista todos los clientes con deudas pendientes"""
    try:
        resp = requests.get(f"{BACKEND_URL}/api/deudores/todos", timeout=10)
        if resp.status_code == 200:
            deudores = resp.json()
            # ✅ CONVERTIR monto_deuda A NÚMERO
            for d in deudores:
                if 'monto_deuda' in d:
                    d['monto_deuda'] = float(d['monto_deuda']) if d['monto_deuda'] else 0
        else:
            deudores = []
    except Exception as e:
        logger.error(f"Error en /deudores: {e}")
        deudores = []
    
    # ✅ CALCULAR TOTAL (ahora con números)
    total_deudas = sum(d.get('monto_deuda', 0) for d in deudores)
    deudores_count = len([d for d in deudores if d.get('monto_deuda', 0) > 0])
    
    return render_template("deudores.html", 
                          deudores=deudores, 
                          total_deudas=total_deudas,
                          deudores_count=deudores_count)
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
        logger.error(f"Error en /balance_ventas: {e}")
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
    if not fecha:
        return ''
    if isinstance(fecha, str):
        try:
            fecha = datetime.strptime(fecha, '%Y-%m-%d')
        except:
            return fecha
    
    dias = {0: 'Lunes', 1: 'Martes', 2: 'Miércoles', 3: 'Jueves', 4: 'Viernes', 5: 'Sábado', 6: 'Domingo'}
    meses = {1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril', 5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto', 9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'}
    
    dia_nombre = dias.get(fecha.weekday(), '')
    dia = fecha.day
    mes = meses.get(fecha.month, '')
    año = fecha.year
    
    return f"{dia_nombre} {dia} de {mes} {año}"

app.jinja_env.filters['fecha_espanol'] = formato_fecha_espanol

# ============================
# VER LOGS
# ============================
@app.route('/ver_logs')
@login_required
@role_required(['admin'])
def ver_logs():
    try:
        log_file = os.path.join(LOG_DIR, 'dixon_app.log')
        
        if request.args.get('limpiar') == 'si':
            if os.path.exists(log_file):
                with open(log_file, 'w') as f:
                    f.write('')
                logger.info(f"🗑️ Logs limpiados por '{session.get('usuario')}'")
                flash('✅ Logs limpiados correctamente', 'success')
                return redirect('/ver_logs')
        
        if not os.path.exists(log_file):
            logs = "No hay logs disponibles"
        else:
            with open(log_file, 'r') as f:
                lines = f.readlines()
                ultimas = lines[-200:] if len(lines) > 200 else lines
                logs = ''.join(ultimas)
        
        return render_template("ver_logs.html", logs=logs)
    except Exception as e:
        logger.error(f"Error al leer logs: {str(e)}")
        return render_template("ver_logs.html", logs=f"Error al leer logs: {str(e)}")
@app.route('/gastos')
@login_required
@role_required(['admin', 'operador'])
def gastos():
    hoy = datetime.now().strftime('%Y-%m-%d')
    mes_actual = datetime.now().month
    anio_actual = datetime.now().year
    
    try:
        resp = requests.get(f"{BACKEND_URL}/api/gastos?fecha={hoy}", timeout=10)
        if resp.status_code == 200:
            gastos = resp.json()
            # ✅ CONVERTIR monto a float
            for g in gastos:
                g['monto'] = float(g['monto']) if g.get('monto') else 0
        else:
            gastos = []
    except Exception as e:
        logger.error(f"Error en /gastos: {e}")
        gastos = []
    
    total_gastos = sum(g.get('monto', 0) for g in gastos)
    gastos_efectivo = sum(g.get('monto', 0) for g in gastos if g.get('metodo_pago') == 'efectivo')
    gastos_transferencia = sum(g.get('monto', 0) for g in gastos if g.get('metodo_pago') == 'transferencia')
    gastos_sueldos = sum(g.get('monto', 0) for g in gastos if g.get('categoria') == 'Sueldos')
    gastos_efectivo_count = len([g for g in gastos if g.get('metodo_pago') == 'efectivo'])
    gastos_transferencia_count = len([g for g in gastos if g.get('metodo_pago') == 'transferencia'])
    gastos_sueldos_count = len([g for g in gastos if g.get('categoria') == 'Sueldos'])
    
    return render_template("gastos.html",
                          gastos=gastos,
                          total_gastos=total_gastos,
                          gastos_efectivo=gastos_efectivo,
                          gastos_transferencia=gastos_transferencia,
                          gastos_sueldos=gastos_sueldos,
                          gastos_efectivo_count=gastos_efectivo_count,
                          gastos_transferencia_count=gastos_transferencia_count,
                          gastos_sueldos_count=gastos_sueldos_count,
                          mes_actual=mes_actual,
                          anio_actual=anio_actual)

# ============================
# CIERRE DE CAJA
# ============================
@app.route('/cierre_caja')
@login_required
@role_required(['admin'])
def cierre_caja():
    hoy = datetime.now().strftime('%Y-%m-%d')
    efectivo_inicial = 50000  # Fondo de caja por defecto
    ventas_efectivo = 0
    gastos_efectivo = 0
    efectivo_esperado = 50000
    historial_cierres = []
    
    try:
        # Obtener cierre de hoy
        resp = requests.get(f"{BACKEND_URL}/api/cierre_caja/{hoy}", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            efectivo_inicial = data.get('cierre', {}).get('efectivo_inicial', 50000)
            ventas_efectivo = data.get('ventas_efectivo', 0)
            gastos_efectivo = data.get('gastos_efectivo', 0)
            efectivo_esperado = data.get('efectivo_esperado', 50000)
        else:
            # Crear cierre automáticamente
            requests.post(f"{BACKEND_URL}/api/cierre_caja", 
                         json={"fecha": hoy, "efectivo_inicial": 50000})
    except:
        pass
    
    # Historial
    try:
        resp = requests.get(f"{BACKEND_URL}/api/historial_cierres", timeout=10)
        historial_cierres = resp.json() if resp.status_code == 200 else []
    except:
        pass
    
    return render_template("cierre_caja.html",
                          hoy=hoy,
                          efectivo_inicial=efectivo_inicial,
                          ventas_efectivo=ventas_efectivo,
                          gastos_efectivo=gastos_efectivo,
                          efectivo_esperado=efectivo_esperado,
                          historial_cierres=historial_cierres)
# ============================
# PAGAR DEUDA
# ============================
@app.route('/pagar_deuda/<int:id_deuda>')
@login_required
@role_required(['admin', 'operador'])
def pagar_deuda(id_deuda):
    """Página para pagar una deuda específica"""
    try:
        resp = requests.get(f"{BACKEND_URL}/api/deuda/{id_deuda}", timeout=10)
        if resp.status_code == 200:
            deuda = resp.json()
            # ✅ Convertir a float por si acaso
            deuda['monto_deuda'] = float(deuda['monto_deuda']) if deuda.get('monto_deuda') else 0
            deuda['monto_original'] = float(deuda['monto_original']) if deuda.get('monto_original') else 0
        else:
            flash('❌ Deuda no encontrada o ya fue pagada', 'error')
            return redirect("/deudores")
    except Exception as e:
        logger.error(f"Error en /pagar_deuda: {e}")
        flash('❌ Error al cargar la deuda', 'error')
        return redirect("/deudores")
    
    return render_template("pagar_deuda.html", deuda=deuda)
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
# INICIO
# ============================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
