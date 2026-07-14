from flask import Flask, render_template, request, session, redirect, url_for, jsonify, send_file, flash
import os
import requests
import secrets
from functools import wraps
import hmac
import hashlib
from datetime import datetime, timedelta
import io

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "clave_frontend_segura")
PDF_SECRET_KEY = os.environ.get("PDF_SECRET_KEY", "dixon_pdf_2025")

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
    return dict(backend_url=BACKEND_URL)

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
        try:
            resp = requests.post(f"{BACKEND_URL}/api/login", json={"username": username, "password": password}, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                session["usuario"] = data['user']['username']
                session["rol"] = data['user']['rol']
                session["nombre_completo"] = data['user'].get('nombre_completo', username)
                return redirect("/estado")
            else:
                error = "❌ Usuario o contraseña incorrectos"
        except Exception as e:
            print(f"Error en /login: {e}")
            error = "⚠️ Error de conexión con el servidor"
    return render_template("login.html", csrf_token=session['csrf_token'], error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect("/login")

@app.route('/estado')
@login_required
def estado():
    try:
        resp = requests.get(f"{BACKEND_URL}/api/estado", timeout=10)
        data = resp.json() if resp.status_code == 200 else {"pendientes": [], "pagados_hoy": []}
    except:
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
        
        # 🔥 CARGAR FLOTAS DISPONIBLES
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
    # Obtener flota (si viene como "__nueva__" usar el valor manual)
    flota = request.form.get('flota', '').strip()
    if flota == '__nueva__':
        flota = request.form.get('flota_nueva', '').strip()
    
    data = {
        'nombre': request.form.get('nombre', '').strip(),
        'patente': request.form.get('patente', '').strip().upper(),
        'marca': request.form.get('marca', '').strip(),
        'modelo': request.form.get('modelo', '').strip(),
        'telefono': request.form.get('telefono', '').strip(),
        'observaciones': request.form.get('observaciones', '').strip(),
        'kilometraje': int(request.form.get('kilometraje', 0) or 0),
        'anio': int(request.form.get('anio', 0) or 0),
        'flota': flota if flota else None,
        'usuario': session.get('usuario')
    }
    
    try:
        resp = requests.post(f"{BACKEND_URL}/api/agregar", json=data, timeout=10)
        if resp.status_code != 200:
            print(f"Error al agregar: {resp.text}")
    except Exception as e:
        print(f"Error en /agregar: {e}")
    
    return redirect("/estado")

@app.route('/pagar/<int:id_reg>', methods=['GET', 'POST'])
@login_required
def pagar(id_reg):
    print(f"🔍 ID recibido: {id_reg}")
    try:
        resp = requests.get(f"{BACKEND_URL}/api/registro/{id_reg}", timeout=10)
        print(f"📡 Status: {resp.status_code}")
        if resp.status_code != 200:
            return f"Registro {id_reg} no encontrado en backend", 404
        registro = resp.json()
    except Exception as e:
        print(f"❌ Error: {e}")
        return "Error de conexión", 500
    
    if request.method == 'POST':
        data = {
            'monto': float(request.form.get('monto', 0)),
            'observaciones_pago': request.form.get('observaciones_pago', ''),
            'diagnostico': request.form.get('diagnostico', ''),
            'reparacion': request.form.get('reparacion', 'Reparación realizada'),
            'resultado': request.form.get('resultado', 'reparado'),
            'tiempo_estimado': request.form.get('tiempo_estimado', '00:00:00'),
            'atendido_por': session.get('nombre_completo', session.get('usuario')),
            'forma_pago': request.form.get('forma_pago', 'efectivo')
        }
        try:
            resp = requests.post(f"{BACKEND_URL}/api/pagar/{id_reg}", json=data, timeout=10)
            print(f"📥 Respuesta pago: {resp.status_code} - {resp.text}")
            if resp.status_code == 200:
                # 🔥 REDIRIGIR A PÁGINA DE ÉXITO
                return redirect(f"/pago_exitoso/{id_reg}")
            else:
                return f"Error al procesar el pago: {resp.text}", 500
        except Exception as e:
            print(f"❌ Error en POST pago: {e}")
            return "Error de conexión al procesar el pago", 500
    
    return render_template("pagar.html", id=id_reg, registro=registro)

@app.route('/pago_exitoso/<int:id_reg>')
@login_required
def pago_exitoso(id_reg):
    try:
        resp = requests.get(f"{BACKEND_URL}/api/registro/{id_reg}", timeout=10)
        registro = resp.json() if resp.status_code == 200 else {}
        firma = generar_firma_pdf(id_reg)
        registro['firma'] = firma  # ← AGREGAR LA FIRMA
        url_pdf = f"{BACKEND_URL}/api/pdf/{id_reg}/{firma}"
    except Exception as e:
        print(f"Error en /pago_exitoso: {e}")
        registro = {}
        url_pdf = ""
    return render_template("pago_exitoso.html", registro=registro, url_pdf=url_pdf)
    
@app.route('/cambiar_password', methods=['GET', 'POST'])
@login_required
def cambiar_password():
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
                    'username': session.get('usuario'),
                    'password_actual': password_actual,
                    'password_nueva': password_nueva
                }
                resp = requests.post(f"{BACKEND_URL}/api/cambiar_password", json=data, timeout=10)
                if resp.status_code == 200:
                    success = "✅ Contraseña actualizada correctamente"
                else:
                    error = resp.json().get('error', '❌ Error al cambiar contraseña')
            except Exception as e:
                print(f"Error en /cambiar_password: {e}")
                error = "⚠️ Error de conexión con el servidor"
    return render_template("cambiar_password.html", error=error, success=success)

@app.route('/pendientes_validacion')
@login_required
@role_required(['admin', 'operador'])
def pendientes_validacion():
    try:
        resp = requests.get(f"{BACKEND_URL}/api/pendientes_validacion", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            pendientes = data.get('pendientes', [])
            validados = data.get('validados', [])
            total_pagado = data.get('total_pagado', 0)
        else:
            pendientes = []
            validados = []
            total_pagado = 0
    except Exception as e:
        print(f"Error en /pendientes_validacion: {e}")
        pendientes = []
        validados = []
        total_pagado = 0
    return render_template("pendientes_validacion.html", pendientes=pendientes, validados=validados, total_pagado=total_pagado)

@app.route('/validar_pago/<int:id_reg>', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'operador'])
def validar_pago(id_reg):
    if session.get('rol') not in ['admin', 'operador']:
        return "No tienes permisos para validar pagos", 403
    
    try:
        resp = requests.get(f"{BACKEND_URL}/api/registro/{id_reg}", timeout=10)
        if resp.status_code != 200:
            return "Registro no encontrado", 404
        registro = resp.json()
    except Exception as e:
        print(f"Error en /validar_pago: {e}")
        return "Error de conexión", 500
    
    if registro.get('estado') != 'pagado':
        return "Este pago no está pagado", 400
    
    try:
        resp_usuarios = requests.get(f"{BACKEND_URL}/api/usuarios", timeout=10)
        usuarios = resp_usuarios.json() if resp_usuarios.status_code == 200 else []
    except:
        usuarios = []
    
    if request.method == 'POST':
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
        'costo_repuestos': float(request.form.get('costo_repuestos', 0)),  # ← NOMBRE CORRECTO
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
                return redirect(f"/pago_validado/{id_reg}")
            else:
                error = resp.json().get('error', 'Error al validar')
        except Exception as e:
            print(f"Error en /validar_pago POST: {e}")
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
@role_required(['admin', 'operador'])
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
@role_required(['admin', 'operador'])
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
@role_required(['admin', 'operador'])
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
@role_required(['admin', 'operador'])
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
    
@app.route('/usuarios')
@login_required
@role_required(['admin', 'operador'])
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
@role_required(['admin', 'operador'])
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
@role_required(['admin', 'operador'])
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
@role_required(['admin', 'operador'])
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
@role_required(['admin', 'operador'])
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
# INICIO
# ============================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
