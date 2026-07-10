from flask import Flask, render_template, request, session, redirect, url_for, jsonify
import os
import requests
import secrets
from functools import wraps
import hmac
import hashlib

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "clave_frontend_segura")
PDF_SECRET_KEY = os.environ.get("PDF_SECRET_KEY", "clave_pdf_2025")

# URL del backend en Railway
BACKEND_URL = os.environ.get("BACKEND_URL", "https://ea-dixon-production.up.railway.app")

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("usuario"):
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated
def generar_firma_pdf(id_reg):
    return hmac.new(
        PDF_SECRET_KEY.encode(),
        str(id_reg).encode(),
        hashlib.sha256
    ).hexdigest()[:16]

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
        resp = requests.post(f"{BACKEND_URL}/api/login", json={"username": username, "password": password})
        if resp.status_code == 200:
            data = resp.json()
            session["usuario"] = data['user']['username']
            session["rol"] = data['user']['rol']
            session["nombre_completo"] = data['user'].get('nombre_completo', username)
            return redirect("/estado")
        else:
            error = "❌ Usuario o contraseña incorrectos"
    return render_template("login.html", csrf_token=session['csrf_token'], error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect("/login")

@app.route('/estado')
@login_required
def estado():
    resp = requests.get(f"{BACKEND_URL}/api/estado")
    data = resp.json() if resp.status_code == 200 else {"pendientes": [], "pagados_hoy": []}
    return render_template("estado.html", 
                          registros=data.get('pendientes', []) + data.get('pagados_hoy', []),
                          pendientes_mes=len(data.get('pendientes', [])),
                          pagados_mes=len(data.get('pagados_hoy', [])),
                          estado="todos")

@app.route('/agregar_cliente')
@login_required
def agregar_cliente():
    resp = requests.get(f"{BACKEND_URL}/api/marcas")
    marcas = resp.json() if resp.status_code == 200 else []
    return render_template("agregar_cliente.html", marcas=marcas, flotas=[])

@app.route('/agregar', methods=['POST'])
@login_required
def agregar():
    data = {
        'nombre': request.form.get('nombre'),
        'patente': request.form.get('patente'),
        'marca': request.form.get('marca'),
        'modelo': request.form.get('modelo'),
        'telefono': request.form.get('telefono', ''),
        'observaciones': request.form.get('observaciones', ''),
        'kilometraje': request.form.get('kilometraje', 0),
        'flota': request.form.get('flota'),
        'usuario': session.get('usuario')
    }
    resp = requests.post(f"{BACKEND_URL}/api/agregar", json=data)
    return redirect("/estado")

@app.route('/pagar/<int:id_reg>', methods=['GET', 'POST'])
@login_required
def pagar(id_reg):
    resp = requests.get(f"{BACKEND_URL}/api/registro/{id_reg}")
    if resp.status_code != 200:
        return "Registro no encontrado", 404
    registro = resp.json()
    if request.method == 'POST':
        data = {
            'monto': float(request.form.get('monto', 0)),
            'observaciones_pago': request.form.get('observaciones_pago', ''),
            'diagnostico': request.form.get('diagnostico', ''),
            'reparacion': request.form.get('reparacion', 'Reparación realizada'),
            'resultado': request.form.get('resultado', 'reparado'),
            'tiempo_estimado': request.form.get('tiempo_estimado', '00:00:00'),
            'atendido_por': session.get('nombre_completo', session.get('usuario'))
        }
        resp = requests.post(f"{BACKEND_URL}/api/pagar/{id_reg}", json=data)
        if resp.status_code == 200:
            return redirect(f"/pago_exitoso/{id_reg}")
    return render_template("pagar.html", id=id_reg, registro=registro)

@app.route('/pago_exitoso/<int:id_reg>')
@login_required
def pago_exitoso(id_reg):
    try:
        resp = requests.get(f"{BACKEND_URL}/api/registro/{id_reg}", timeout=10)
        registro = resp.json() if resp.status_code == 200 else {}
        
        # Calcular firma en el frontend
        firma = generar_firma_pdf(id_reg)
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
        
        # Validaciones
        if not password_actual or not password_nueva or not password_confirmar:
            error = "⚠️ Todos los campos son obligatorios"
        elif password_nueva != password_confirmar:
            error = "⚠️ Las contraseñas nuevas no coinciden"
        elif len(password_nueva) < 6:
            error = "⚠️ La contraseña debe tener al menos 6 caracteres"
        else:
            # Enviar al backend
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
    
    return render_template(
        "pendientes_validacion.html", 
        pendientes=pendientes,
        validados=validados,
        total_pagado=total_pagado
    )

@app.route('/validar_pago/<int:id_reg>', methods=['GET', 'POST'])
@login_required
def validar_pago(id_reg):
    """Paso 2: Validación de costos y ganancia neta"""
    
    if session.get('rol') not in ['admin', 'operador']:
        return "No tienes permisos para validar pagos", 403
    
    try:
        # Obtener registro
        resp = requests.get(f"{BACKEND_URL}/api/registro/{id_reg}", timeout=10)
        if resp.status_code != 200:
            return "Registro no encontrado", 404
        registro = resp.json()
    except Exception as e:
        print(f"Error en /validar_pago: {e}")
        return "Error de conexión", 500
    
    if registro.get('estado') != 'pagado':
        return "Este pago no está pagado", 400
    
    # Obtener lista de usuarios para el dropdown
    try:
        resp_usuarios = requests.get(f"{BACKEND_URL}/api/usuarios", timeout=10)
        usuarios = resp_usuarios.json() if resp_usuarios.status_code == 200 else []
    except:
        usuarios = []
    
    if request.method == 'POST':
        # Obtener datos del formulario
        validado_por = request.form.get('validado_por', '').strip()
        if not validado_por:
            validado_por = session.get('nombre_completo', session.get('usuario'))
        
        # Obtener lista de repuestos
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
            'costo_repuestos_real': float(request.form.get('costo_repuestos', 0)),
            'costo_mano_obra_real': float(request.form.get('costo_mano_obra', 0)),
            'costo_diagnostico_real': float(request.form.get('costo_diagnostico', 0)),
            'ganancia_neta': float(request.form.get('ganancia_neta', 0)),
            'observaciones_pago': request.form.get('observaciones_costos', ''),
            'validado_por': validado_por,
            'diagnostico': request.form.get('diagnostico', ''),
            'reparacion': request.form.get('reparacion', 'Reparación realizada'),
            'resultado': request.form.get('resultado', 'reparado'),
            'tiempo_estimado': request.form.get('tiempo_estimado', '00:00:00'),
            'detalles_repuestos': detalles_repuestos
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
def pago_validado(id_reg):
    """Página de confirmación de validación"""
    try:
        resp = requests.get(f"{BACKEND_URL}/api/registro/{id_reg}", timeout=10)
        registro = resp.json() if resp.status_code == 200 else {}
    except Exception as e:
        print(f"Error en /pago_validado: {e}")
        registro = {}
    
    return render_template("pago_validado.html", registro=registro)
@app.route('/registros')
@login_required
def registros():
    try:
        # ✅ Usa BACKEND_URL
        resp = requests.get(f"{BACKEND_URL}/api/registros", timeout=10)
        registros = resp.json() if resp.status_code == 200 else []
    except Exception as e:
        print(f"Error en /registros: {e}")
        registros = []
    
    return render_template("registros.html", registros=registros)
@app.route('/modelos/<marca>')
@login_required
def modelos(marca):
    resp = requests.get(f"{BACKEND_URL}/api/modelos/{marca}")
    return jsonify(resp.json() if resp.status_code == 200 else [])

@app.route('/flotas')
@login_required
def flotas():
    resp = requests.get(f"{BACKEND_URL}/api/flotas")
    clientes = resp.json() if resp.status_code == 200 else []
    return render_template("flotas.html", clientes=clientes)
@app.route('/register')
@login_required
def register():
    return render_template("register.html")

@app.route('/usuarios')
@login_required
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
def auditoria_descargas():
    """Página de auditoría de descargas de informes"""
    try:
        resp = requests.get(f"{BACKEND_URL}/api/auditoria", timeout=10)
        historial = resp.json() if resp.status_code == 200 else []
    except Exception as e:
        print(f"Error en /auditoria_descargas: {e}")
        historial = []
    
    return render_template("auditoria_descargas.html", historial=historial)

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
