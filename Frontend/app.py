from flask import Flask, render_template, request, session, redirect, url_for, jsonify
import os
import requests
import secrets
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get("37b2354ab919f0a5515e81a6d4586147ecc9487cdfd33078d110a1361fd6bb86", "37b2354ab919f0a5515e81a6d4586147ecc9487cdfd33078d110a1361fd6bb86")

# URL del backend en Railway
BACKEND_URL = os.environ.get("BACKEND_URL", "https://tu-backend.railway.app")

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("usuario"):
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated

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
    resp = requests.get(f"{BACKEND_URL}/api/registro/{id_reg}")
    registro = resp.json() if resp.status_code == 200 else {}
    url_pdf = f"{BACKEND_URL}/api/pdf/{id_reg}"
    return render_template("pago_exitoso.html", registro=registro, url_pdf=url_pdf)

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
