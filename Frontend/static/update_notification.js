// Frontend/static/js/update_notification.js

const API_URL = 'https://ea-dixon-production.up.railway.app';

// ============================================
// VERIFICAR ACTUALIZACIONES CADA 5 MINUTOS
// ============================================
let updateChecked = false;

function verificarActualizacion() {
    console.log('🔍 Verificando actualizaciones...');
    
    fetch(`${API_URL}/api/update/check`, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' }
    })
    .then(response => response.json())
    .then(data => {
        console.log('📊 Datos de actualización:', data);
        
        if (data.update_available) {
            mostrarBanner(data);
        }
    })
    .catch(error => {
        console.log('⚠️ Error verificando actualización:', error);
    });
}

// ============================================
// MOSTRAR BANNER DE ACTUALIZACIÓN
// ============================================
function mostrarBanner(data) {
    const banner = document.getElementById('updateBanner');
    const message = document.getElementById('updateMessage');
    const notes = document.getElementById('updateNotes');
    const btn = document.getElementById('btnUpdate');
    
    if (!banner) return;
    
    // Actualizar mensajes
    if (message) {
        message.textContent = `Versión actual: v${data.current_version || '1.0.0'} → Nueva: v${data.latest_version || '1.1.0'}`;
    }
    
    if (notes) {
        notes.textContent = data.release_notes || '📌 Corrección de errores y mejoras';
    }
    
    // Mostrar banner
    banner.style.display = 'block';
    
    // Animación de entrada
    banner.style.animation = 'slideUp 0.5s ease-out';
}

// ============================================
// EJECUTAR ACTUALIZACIÓN
// ============================================
function ejecutarActualizacion() {
    // Mostrar modal
    const modal = document.getElementById('updateModal');
    if (modal) modal.style.display = 'flex';
    
    // Actualizar progreso
    const progressBar = document.getElementById('progressBar');
    const updateLog = document.getElementById('updateLog');
    const btn = document.getElementById('btnUpdate');
    const closeBtn = document.getElementById('btnCloseUpdate');
    
    if (btn) {
        btn.disabled = true;
        btn.textContent = '⏳ Actualizando...';
    }
    
    if (closeBtn) closeBtn.style.display = 'none';
    if (updateLog) updateLog.innerHTML = '🔄 Iniciando actualización...\n';
    if (progressBar) progressBar.style.width = '10%';
    
    // Obtener usuario actual
    const user = localStorage.getItem('username') || 'Usuario';
    
    fetch(`${API_URL}/api/update/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user: user })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            if (updateLog) {
                updateLog.innerHTML += '✅ Actualización completada exitosamente!\n';
                updateLog.innerHTML += '📌 Recargando la página...\n';
            }
            if (progressBar) progressBar.style.width = '100%';
            
            setTimeout(() => {
                // Recargar la página después de 2 segundos
                location.reload();
            }, 2000);
        } else {
            if (updateLog) {
                updateLog.innerHTML += `❌ Error: ${data.error || 'Desconocido'}\n`;
            }
            if (btn) {
                btn.disabled = false;
                btn.textContent = '🔄 Reintentar';
            }
            if (closeBtn) closeBtn.style.display = 'inline-block';
        }
    })
    .catch(error => {
        console.error('❌ Error:', error);
        if (updateLog) {
            updateLog.innerHTML += `❌ Error de conexión: ${error.message}\n`;
        }
        if (btn) {
            btn.disabled = false;
            btn.textContent = '🔄 Reintentar';
        }
        if (closeBtn) closeBtn.style.display = 'inline-block';
    });
}

// ============================================
// CERRAR BANNER
// ============================================
function cerrarBanner() {
    const banner = document.getElementById('updateBanner');
    if (banner) {
        banner.style.display = 'none';
        // Guardar preferencia
        localStorage.setItem('updateBannerDismissed', 'true');
        // Volver a verificar en 1 hora
        setTimeout(() => {
            localStorage.removeItem('updateBannerDismissed');
            verificarActualizacion();
        }, 3600000);
    }
}

// ============================================
// CERRAR MODAL
// ============================================
function cerrarModalActualizacion() {
    const modal = document.getElementById('updateModal');
    if (modal) modal.style.display = 'none';
}

// ============================================
// INICIALIZAR
// ============================================
document.addEventListener('DOMContentLoaded', function() {
    // Verificar si el banner fue cerrado recientemente
    const dismissed = localStorage.getItem('updateBannerDismissed');
    
    if (!dismissed) {
        // Esperar 3 segundos después de cargar la página
        setTimeout(() => {
            verificarActualizacion();
        }, 3000);
    }
    
    // Verificar cada 5 minutos
    setInterval(() => {
        verificarActualizacion();
    }, 300000); // 5 minutos
});

// ============================================
// ESTILOS CSS PARA EL BANNER
// ============================================
const style = document.createElement('style');
style.textContent = `
    @keyframes slideUp {
        from {
            transform: translateY(100%);
            opacity: 0;
        }
        to {
            transform: translateY(0);
            opacity: 1;
        }
    }
    
    #updateBanner {
        animation: slideUp 0.5s ease-out;
    }
`;
document.head.appendChild(style);
