// Frontend/static/js/update_notification.js

const API_URL = 'https://ea-dixon-production.up.railway.app';

// ============================================
// VERIFICAR ACTUALIZACIONES (CADA 6 HORAS)
// ============================================
let updateChecked = false;

function verificarActualizacion() {
    // ✅ NO verificar si la app está instalada como PWA
    if (window.matchMedia('(display-mode: standalone)').matches) {
        console.log('📱 App en modo standalone - Sistema de actualización desactivado');
        return;
    }
    
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
    
    if (message) {
        message.textContent = `Versión actual: v${data.current_version || '1.0.0'} → Nueva: v${data.latest_version || '1.1.0'}`;
    }
    
    if (notes) {
        notes.textContent = data.release_notes || '📌 Corrección de errores y mejoras';
    }
    
    banner.style.display = 'block';
    banner.style.animation = 'slideUp 0.5s ease-out';
}

// ============================================
// EJECUTAR ACTUALIZACIÓN
// ============================================
function ejecutarActualizacion() {
    const modal = document.getElementById('updateModal');
    if (modal) modal.style.display = 'flex';
    
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
        localStorage.setItem('updateBannerDismissed', 'true');
        // ✅ Volver a verificar en 24 horas
        setTimeout(() => {
            localStorage.removeItem('updateBannerDismissed');
            verificarActualizacion();
        }, 86400000); // 24 horas
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
    // ✅ NO verificar si la app está instalada como PWA
    if (window.matchMedia('(display-mode: standalone)').matches) {
        console.log('📱 App en modo standalone - Sistema de actualización desactivado');
        return;
    }
    
    const dismissed = localStorage.getItem('updateBannerDismissed');
    
    if (!dismissed) {
        // ✅ Esperar 10 segundos (no 3) para no interferir con la carga
        setTimeout(() => {
            verificarActualizacion();
        }, 10000);
    }
    
    // ✅ Verificar cada 6 horas (no 5 minutos)
    setInterval(() => {
        verificarActualizacion();
    }, 21600000); // 6 horas
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
