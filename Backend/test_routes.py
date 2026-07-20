# Backend/test_routes.py
import requests
import json
import sys
from datetime import datetime, timedelta

# ============================================
# CONFIGURACIÓN
# ============================================
BASE_URL = "https://ea-dixon-production.up.railway.app"  # Cambia según tu entorno
# BASE_URL = "http://localhost:5000"  # Para pruebas locales

# Colores para la consola
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_test(name, status, details=""):
    """Imprime el resultado de una prueba"""
    icon = "✅" if status else "❌"
    color = GREEN if status else RED
    print(f"{color}{icon} {name}{RESET}")
    if details:
        print(f"   {details}")

def print_section(title):
    """Imprime una sección de pruebas"""
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}📋 {title}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")

# ============================================
# PRUEBAS DE AUTENTICACIÓN
# ============================================

def test_health():
    """Prueba el endpoint de health check"""
    print_section("HEALTH CHECK")
    
    try:
        response = requests.get(f"{BASE_URL}/api/health", timeout=5)
        status = response.status_code == 200
        print_test("Health Check", status, f"Status: {response.status_code}")
        if status:
            print(f"   Response: {json.dumps(response.json(), indent=2)}")
        return status
    except Exception as e:
        print_test("Health Check", False, f"Error: {e}")
        return False

def test_login():
    """Prueba el login"""
    print_section("AUTENTICACIÓN - LOGIN")
    
    # Prueba con admin
    try:
        response = requests.post(
            f"{BASE_URL}/api/login",
            json={"username": "admin", "password": "ad12345"},
            timeout=5
        )
        status = response.status_code == 200
        print_test("Login Admin", status, f"Status: {response.status_code}")
        if status:
            data = response.json()
            print(f"   Usuario: {data.get('user', {}).get('username')}")
            print(f"   Rol: {data.get('user', {}).get('rol')}")
    except Exception as e:
        print_test("Login Admin", False, f"Error: {e}")
    
    # Prueba con credenciales incorrectas
    try:
        response = requests.post(
            f"{BASE_URL}/api/login",
            json={"username": "admin", "password": "incorrecto"},
            timeout=5
        )
        status = response.status_code == 401
        print_test("Login Fallido", status, f"Status: {response.status_code} (esperado 401)")
    except Exception as e:
        print_test("Login Fallido", False, f"Error: {e}")

# ============================================
# PRUEBAS DE PAGOS
# ============================================

def test_estado():
    """Prueba el endpoint de estado"""
    print_section("PAGOS - ESTADO")
    
    try:
        response = requests.get(f"{BASE_URL}/api/estado", timeout=5)
        status = response.status_code == 200
        print_test("Obtener Estado", status, f"Status: {response.status_code}")
        if status:
            data = response.json()
            print(f"   Pendientes: {data.get('total_pendientes', 0)}")
            print(f"   Pagados hoy: {data.get('total_pagados_hoy', 0)}")
        return status
    except Exception as e:
        print_test("Obtener Estado", False, f"Error: {e}")
        return False

def test_registros():
    """Prueba los endpoints de registros"""
    print_section("PAGOS - REGISTROS")
    
    # Obtener todos los registros
    try:
        response = requests.get(f"{BASE_URL}/api/registros", timeout=5)
        status = response.status_code == 200
        print_test("Obtener Registros (todos)", status, f"Status: {response.status_code}")
        if status:
            data = response.json()
            print(f"   Total registros: {len(data)}")
    except Exception as e:
        print_test("Obtener Registros (todos)", False, f"Error: {e}")
    
    # Obtener registros con filtro
    for filtro in ['hoy', '7d', 'mes']:
        try:
            response = requests.get(f"{BASE_URL}/api/registros?filtro={filtro}", timeout=5)
            status = response.status_code == 200
            print_test(f"Obtener Registros ({filtro})", status, f"Status: {response.status_code}")
        except Exception as e:
            print_test(f"Obtener Registros ({filtro})", False, f"Error: {e}")

def test_flotas_disponibles():
    """Prueba el endpoint de flotas disponibles"""
    print_section("PAGOS - FLOTAS DISPONIBLES")
    
    try:
        response = requests.get(f"{BASE_URL}/api/flotas_disponibles", timeout=5)
        status = response.status_code == 200
        print_test("Obtener Flotas Disponibles", status, f"Status: {response.status_code}")
        if status:
            data = response.json()
            print(f"   Flotas encontradas: {len(data)}")
            if data:
                print(f"   Primeras 3: {data[:3]}")
    except Exception as e:
        print_test("Obtener Flotas Disponibles", False, f"Error: {e}")

def test_flotas_pendientes():
    """Prueba los endpoints de flotas pendientes"""
    print_section("PAGOS - FLOTAS PENDIENTES")
    
    # Listar flotas pendientes
    try:
        response = requests.get(f"{BASE_URL}/api/flotas_pendientes", timeout=5)
        status = response.status_code == 200
        print_test("Listar Flotas Pendientes", status, f"Status: {response.status_code}")
        if status:
            data = response.json()
            print(f"   Total: {len(data)}")
    except Exception as e:
        print_test("Listar Flotas Pendientes", False, f"Error: {e}")
    
    # Contador de flotas pendientes
    try:
        response = requests.get(f"{BASE_URL}/api/flotas_pendientes_count", timeout=5)
        status = response.status_code == 200
        print_test("Contador Flotas Pendientes", status, f"Status: {response.status_code}")
        if status:
            data = response.json()
            print(f"   Count: {data.get('count', 0)}")
    except Exception as e:
        print_test("Contador Flotas Pendientes", False, f"Error: {e}")
    
    # Flotas pendientes agrupadas
    try:
        response = requests.get(f"{BASE_URL}/api/flotas_pendientes_agrupadas", timeout=5)
        status = response.status_code == 200
        print_test("Flotas Pendientes Agrupadas", status, f"Status: {response.status_code}")
        if status:
            data = response.json()
            print(f"   Grupos: {len(data)}")
    except Exception as e:
        print_test("Flotas Pendientes Agrupadas", False, f"Error: {e}")

def test_balance():
    """Prueba el endpoint de balance"""
    print_section("PAGOS - BALANCE")
    
    for filtro in ['hoy', '7d', 'mes']:
        try:
            response = requests.get(f"{BASE_URL}/api/balance?filtro={filtro}", timeout=5)
            status = response.status_code == 200
            print_test(f"Balance ({filtro})", status, f"Status: {response.status_code}")
            if status:
                data = response.json()
                print(f"   Total pagado: ${data.get('total_pagado', 0):,.0f}")
                print(f"   Ganancia neta: ${data.get('ganancia_neta', 0):,.0f}")
        except Exception as e:
            print_test(f"Balance ({filtro})", False, f"Error: {e}")

def test_balance_ventas():
    """Prueba el endpoint de balance de ventas"""
    print_section("PAGOS - BALANCE DE VENTAS")
    
    for filtro in ['hoy', '7d', 'mes']:
        try:
            response = requests.get(f"{BASE_URL}/api/balance_ventas?filtro={filtro}", timeout=5)
            status = response.status_code == 200
            print_test(f"Balance Ventas ({filtro})", status, f"Status: {response.status_code}")
            if status:
                data = response.json()
                print(f"   Total ventas: ${data.get('total_ventas', 0):,.0f}")
                print(f"   Ganancia neta: ${data.get('ganancia_neta', 0):,.0f}")
        except Exception as e:
            print_test(f"Balance Ventas ({filtro})", False, f"Error: {e}")

def test_dashboard():
    """Prueba el endpoint de dashboard"""
    print_section("PAGOS - DASHBOARD")
    
    for filtro in ['7d', '30d', '90d']:
        try:
            response = requests.get(f"{BASE_URL}/api/dashboard?filtro={filtro}", timeout=5)
            status = response.status_code == 200
            print_test(f"Dashboard ({filtro})", status, f"Status: {response.status_code}")
            if status:
                data = response.json()
                print(f"   Total facturado: ${data.get('total_facturado', 0):,.0f}")
                print(f"   Total servicios: {data.get('total_servicios', 0)}")
                print(f"   Ganancia total: ${data.get('ganancia_total', 0):,.0f}")
        except Exception as e:
            print_test(f"Dashboard ({filtro})", False, f"Error: {e}")

def test_pendientes_validacion():
    """Prueba el endpoint de pendientes de validación"""
    print_section("PAGOS - PENDIENTES DE VALIDACIÓN")
    
    try:
        response = requests.get(f"{BASE_URL}/api/pendientes_validacion", timeout=5)
        status = response.status_code == 200
        print_test("Pendientes Validación", status, f"Status: {response.status_code}")
        if status:
            data = response.json()
            print(f"   Pendientes: {len(data.get('pendientes', []))}")
            print(f"   Validados: {len(data.get('validados', []))}")
            print(f"   Total pagado: ${data.get('total_pagado', 0):,.0f}")
    except Exception as e:
        print_test("Pendientes Validación", False, f"Error: {e}")

def test_verificar_duplicado():
    """Prueba el endpoint de verificar duplicado"""
    print_section("PAGOS - VERIFICAR DUPLICADO")
    
    # Prueba con datos que no existen
    try:
        response = requests.get(
            f"{BASE_URL}/api/verificar_duplicado",
            params={"nombre": "Cliente Test", "patente": "XX-00-XX"},
            timeout=5
        )
        status = response.status_code == 200
        print_test("Verificar Duplicado (no existe)", status, f"Status: {response.status_code}")
        if status:
            data = response.json()
            print(f"   Duplicado: {data.get('duplicado', False)}")
    except Exception as e:
        print_test("Verificar Duplicado (no existe)", False, f"Error: {e}")

# ============================================
# PRUEBAS DE REPUESTOS
# ============================================

def test_repuestos():
    """Prueba los endpoints de repuestos"""
    print_section("REPUESTOS")
    
    # Obtener todos los repuestos
    try:
        response = requests.get(f"{BASE_URL}/api/repuestos", timeout=5)
        status = response.status_code == 200
        print_test("Obtener Repuestos", status, f"Status: {response.status_code}")
        if status:
            data = response.json()
            print(f"   Total: {len(data)}")
    except Exception as e:
        print_test("Obtener Repuestos", False, f"Error: {e}")
    
    # Buscar repuestos
    for query in ['filtro', 'aceite', 'bateria']:
        try:
            response = requests.get(
                f"{BASE_URL}/api/repuestos/buscar",
                params={"q": query},
                timeout=5
            )
            status = response.status_code == 200
            print_test(f"Buscar Repuestos ('{query}')", status, f"Status: {response.status_code}")
        except Exception as e:
            print_test(f"Buscar Repuestos ('{query}')", False, f"Error: {e}")

# ============================================
# PRUEBAS DE CATEGORÍAS
# ============================================

def test_categorias():
    """Prueba los endpoints de categorías"""
    print_section("CATEGORÍAS")
    
    # Obtener categorías
    try:
        response = requests.get(f"{BASE_URL}/api/categorias_repuestos", timeout=5)
        status = response.status_code == 200
        print_test("Obtener Categorías", status, f"Status: {response.status_code}")
        if status:
            data = response.json()
            print(f"   Total: {len(data)}")
    except Exception as e:
        print_test("Obtener Categorías", False, f"Error: {e}")
    
    # Obtener subcategorías de una categoría
    try:
        response = requests.get(f"{BASE_URL}/api/subcategorias_repuestos", timeout=5)
        status = response.status_code == 200
        print_test("Obtener Subcategorías", status, f"Status: {response.status_code}")
        if status:
            data = response.json()
            print(f"   Total: {len(data)}")
    except Exception as e:
        print_test("Obtener Subcategorías", False, f"Error: {e}")

# ============================================
# PRUEBAS DE GASTOS
# ============================================

def test_gastos():
    """Prueba los endpoints de gastos"""
    print_section("GASTOS")
    
    hoy = datetime.now().strftime('%Y-%m-%d')
    
    # Obtener gastos del día
    try:
        response = requests.get(f"{BASE_URL}/api/gastos?fecha={hoy}", timeout=5)
        status = response.status_code == 200
        print_test("Obtener Gastos (hoy)", status, f"Status: {response.status_code}")
        if status:
            data = response.json()
            print(f"   Total: {len(data)}")
    except Exception as e:
        print_test("Obtener Gastos (hoy)", False, f"Error: {e}")

# ============================================
# PRUEBAS DE CIERRE DE CAJA
# ============================================

def test_cierre_caja():
    """Prueba los endpoints de cierre de caja"""
    print_section("CIERRE DE CAJA")
    
    hoy = datetime.now().strftime('%Y-%m-%d')
    
    # Obtener historial de cierres
    try:
        response = requests.get(f"{BASE_URL}/api/historial_cierres", timeout=5)
        status = response.status_code == 200
        print_test("Historial Cierres", status, f"Status: {response.status_code}")
        if status:
            data = response.json()
            print(f"   Total: {len(data)}")
    except Exception as e:
        print_test("Historial Cierres", False, f"Error: {e}")

# ============================================
# PRUEBAS DE DEUDORES
# ============================================

def test_deudores():
    """Prueba los endpoints de deudores"""
    print_section("DEUDORES")
    
    # Obtener todos los deudores
    try:
        response = requests.get(f"{BASE_URL}/api/deudores/todos", timeout=5)
        status = response.status_code == 200
        print_test("Obtener Deudores", status, f"Status: {response.status_code}")
        if status:
            data = response.json()
            print(f"   Total: {len(data)}")
            if data:
                total = sum(d.get('monto_deuda', 0) for d in data)
                print(f"   Total deudas: ${total:,.0f}")
    except Exception as e:
        print_test("Obtener Deudores", False, f"Error: {e}")

# ============================================
# PRUEBAS DE NOTIFICACIONES
# ============================================

def test_notificaciones():
    """Prueba los endpoints de notificaciones"""
    print_section("NOTIFICACIONES")
    
    # Test de notificaciones
    try:
        response = requests.get(f"{BASE_URL}/api/test_notificacion", timeout=5)
        status = response.status_code == 200
        print_test("Test Notificación", status, f"Status: {response.status_code}")
        if status:
            data = response.json()
            print(f"   Mensaje: {data.get('mensaje', 'N/A')}")
    except Exception as e:
        print_test("Test Notificación", False, f"Error: {e}")

# ============================================
# PRUEBAS DE EXPORTACIÓN
# ============================================

def test_exportacion():
    """Prueba los endpoints de exportación"""
    print_section("EXPORTACIÓN")
    
    # Exportar datos
    try:
        response = requests.get(f"{BASE_URL}/exportar_datos", timeout=10)
        status = response.status_code == 200
        print_test("Exportar Datos", status, f"Status: {response.status_code}")
        if status:
            print(f"   Tamaño: {len(response.content):,} bytes")
            print(f"   Content-Type: {response.headers.get('Content-Type')}")
    except Exception as e:
        print_test("Exportar Datos", False, f"Error: {e}")

# ============================================
# PRUEBAS DE CATÁLOGO
# ============================================

def test_catalogo():
    """Prueba los endpoints de catálogo"""
    print_section("CATÁLOGO")
    
    # Obtener marcas
    try:
        response = requests.get(f"{BASE_URL}/api/marcas", timeout=5)
        status = response.status_code == 200
        print_test("Obtener Marcas", status, f"Status: {response.status_code}")
        if status:
            data = response.json()
            print(f"   Total: {len(data)}")
            if data:
                print(f"   Primeras 3: {data[:3]}")
    except Exception as e:
        print_test("Obtener Marcas", False, f"Error: {e}")

# ============================================
# EJECUTAR TODAS LAS PRUEBAS
# ============================================

def run_all_tests():
    """Ejecuta todas las pruebas"""
    print(f"\n{GREEN}{'='*60}{RESET}")
    print(f"{GREEN}🚀 INICIANDO PRUEBAS DE RUTAS{RESET}")
    print(f"{GREEN}{'='*60}{RESET}")
    print(f"📡 Base URL: {BASE_URL}")
    
    resultados = []
    
    # Ejecutar pruebas
    tests = [
        ('Health Check', test_health),
        ('Login', test_login),
        ('Estado', test_estado),
        ('Registros', test_registros),
        ('Flotas Disponibles', test_flotas_disponibles),
        ('Flotas Pendientes', test_flotas_pendientes),
        ('Balance', test_balance),
        ('Balance Ventas', test_balance_ventas),
        ('Dashboard', test_dashboard),
        ('Pendientes Validación', test_pendientes_validacion),
        ('Verificar Duplicado', test_verificar_duplicado),
        ('Repuestos', test_repuestos),
        ('Categorías', test_categorias),
        ('Gastos', test_gastos),
        ('Cierre de Caja', test_cierre_caja),
        ('Deudores', test_deudores),
        ('Notificaciones', test_notificaciones),
        ('Exportación', test_exportacion),
        ('Catálogo', test_catalogo),
    ]
    
    for name, test_func in tests:
        try:
            result = test_func()
            resultados.append((name, result))
        except Exception as e:
            print_test(name, False, f"Error: {e}")
            resultados.append((name, False))
    
    # Resumen final
    print(f"\n{YELLOW}{'='*60}{RESET}")
    print(f"{YELLOW}📊 RESUMEN DE PRUEBAS{RESET}")
    print(f"{YELLOW}{'='*60}{RESET}")
    
    total = len(resultados)
    pasaron = sum(1 for _, r in resultados if r)
    fallaron = total - pasaron
    
    print(f"✅ Pasaron: {pasaron}/{total}")
    if fallaron > 0:
        print(f"❌ Fallaron: {fallaron}/{total}")
        print(f"\n{RED}Pruebas fallidas:{RESET}")
        for name, result in resultados:
            if not result:
                print(f"  ❌ {name}")
    
    if pasaron == total:
        print(f"\n{GREEN}🎉 TODAS LAS PRUEBAS PASARON EXITOSAMENTE{RESET}")
    else:
        print(f"\n{YELLOW}⚠️ Algunas pruebas fallaron. Revisa los detalles arriba.{RESET}")

if __name__ == "__main__":
    # Verificar si se pasó una URL personalizada
    if len(sys.argv) > 1:
        BASE_URL = sys.argv[1]
        print(f"📡 Usando URL personalizada: {BASE_URL}")
    
    run_all_tests()
