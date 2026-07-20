# Backend/routes/update_routes.py
from flask import Blueprint, request, jsonify, current_app
import subprocess
import os
import json
import logging
from datetime import datetime
import requests

logger = logging.getLogger(__name__)
update_bp = Blueprint('update', __name__, url_prefix='/api/update')

# Archivo para guardar la versión actual
VERSION_FILE = '/tmp/ea_dixon_version.json'

# ============================================
# 1. OBTENER VERSIÓN ACTUAL
# ============================================
def get_current_version():
    """Obtiene la versión actual de la aplicación"""
    try:
        # Intentar leer desde archivo
        if os.path.exists(VERSION_FILE):
            with open(VERSION_FILE, 'r') as f:
                data = json.load(f)
                return data.get('version', '1.0.0')
        
        # Si no existe, obtener desde git
        result = subprocess.run(
            ['git', 'rev-parse', '--short', 'HEAD'],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        return result.stdout.strip()[:8]
    except Exception as e:
        logger.error(f"Error obteniendo versión: {e}")
        return '1.0.0'

# ============================================
# 2. OBTENER ÚLTIMA VERSIÓN DISPONIBLE
# ============================================
def get_latest_version():
    """Obtiene la última versión disponible en el repositorio"""
    try:
        # Opción 1: Desde GitHub API (si usas GitHub)
        repo_url = os.environ.get('GITHUB_REPO', 'EA-DIXON/EA-DIXON')
        response = requests.get(
            f'https://api.github.com/repos/{repo_url}/commits/main',
            timeout=5
        )
        if response.status_code == 200:
            return response.json().get('sha', '')[:8]
        
        # Opción 2: Desde Git local
        result = subprocess.run(
            ['git', 'ls-remote', 'origin', 'main'],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        if result.stdout:
            return result.stdout.split()[0][:8]
        
        return None
    except Exception as e:
        logger.error(f"Error obteniendo última versión: {e}")
        return None

# ============================================
# 3. VERIFICAR SI HAY ACTUALIZACIÓN
# ============================================
@update_bp.route('/check', methods=['GET'])
def check_update():
    """Verifica si hay una nueva versión disponible"""
    try:
        current = get_current_version()
        latest = get_latest_version()
        
        if not latest:
            return jsonify({
                'update_available': False,
                'message': 'No se pudo verificar actualizaciones',
                'current_version': current
            })
        
        # Comparar versiones
        update_available = current != latest
        
        return jsonify({
            'update_available': update_available,
            'current_version': current,
            'latest_version': latest,
            'message': 'Hay una nueva versión disponible' if update_available else 'Estás en la última versión',
            'release_notes': get_release_notes() if update_available else None
        })
    except Exception as e:
        logger.error(f"Error verificando actualización: {e}")
        return jsonify({
            'update_available': False,
            'error': str(e)
        }), 500

# ============================================
# 4. OBTENER NOTAS DE LA VERSIÓN
# ============================================
def get_release_notes():
    """Obtiene las notas de la última versión"""
    try:
        # Leer desde archivo CHANGELOG.md o similar
        changelog_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            '../../CHANGELOG.md'
        )
        if os.path.exists(changelog_path):
            with open(changelog_path, 'r') as f:
                content = f.read()
                # Tomar solo las últimas notas
                lines = content.split('\n')
                notes = []
                for line in lines[:20]:  # Primeras 20 líneas
                    if line.strip() and not line.startswith('#'):
                        notes.append(line.strip())
                return '\n'.join(notes[:10])
        return "📌 Corrección de errores y mejoras de rendimiento"
    except Exception as e:
        logger.error(f"Error obteniendo notas: {e}")
        return "📌 Actualización disponible"

# ============================================
# 5. EJECUTAR ACTUALIZACIÓN
# ============================================
@update_bp.route('/execute', methods=['POST'])
def execute_update():
    """Ejecuta la actualización de la aplicación"""
    try:
        data = request.json
        user = data.get('user', 'Sistema')
        
        logger.info(f"🚀 Usuario {user} iniciando actualización...")
        
        # Ejecutar script de actualización
        script_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            '../../update_version.sh'
        )
        
        if os.path.exists(script_path):
            result = subprocess.run(
                ['bash', script_path],
                capture_output=True,
                text=True,
                cwd=os.path.dirname(os.path.abspath(__file__))
            )
            
            if result.returncode == 0:
                # Guardar nueva versión
                new_version = get_latest_version()
                with open(VERSION_FILE, 'w') as f:
                    json.dump({
                        'version': new_version,
                        'updated_at': datetime.now().isoformat(),
                        'updated_by': user
                    }, f)
                
                return jsonify({
                    'success': True,
                    'message': '✅ Actualización completada exitosamente',
                    'new_version': new_version,
                    'output': result.stdout
                })
            else:
                return jsonify({
                    'success': False,
                    'error': result.stderr,
                    'message': '❌ Error durante la actualización'
                }), 500
        else:
            # Si no hay script, solo reiniciar
            return jsonify({
                'success': True,
                'message': '✅ Actualización completada (sin script)',
                'note': 'Reinicia los servicios manualmente si es necesario'
            })
            
    except Exception as e:
        logger.error(f"Error ejecutando actualización: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
