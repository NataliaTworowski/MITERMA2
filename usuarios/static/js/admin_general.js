// Variable global para almacenar el ID de la solicitud que se va a rechazar
let solicitudParaRechazar = null;

function mostrarDetalles(solicitudId) {
    // Usar la URL directamente
    const url = `/termas/detalles_solicitud/${solicitudId}/`;
    
    // Obtener detalles de la solicitud
    fetch(url)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const solicitud = data.data;
                const modalContent = document.getElementById('modal-content');
                
                modalContent.innerHTML = `
                    <div class="space-y-4">
                        <h3 class="text-2xl font-bold text-gray-800">${solicitud.nombre_terma}</h3>
                        
                        <div class="bg-gray-50 p-4 rounded-lg">
                            <h4 class="font-semibold text-gray-700 mb-2">Información de Contacto</h4>
                            <p><span class="font-medium">Email:</span> ${solicitud.correo_institucional}</p>
                            <p><span class="font-medium">Teléfono:</span> ${solicitud.telefono_contacto || 'No especificado'}</p>
                        </div>
                        
                        <div class="bg-gray-50 p-4 rounded-lg">
                            <h4 class="font-semibold text-gray-700 mb-2">Ubicación</h4>
                            <p><span class="font-medium">Región:</span> ${solicitud.region}</p>
                            <p><span class="font-medium">Comuna:</span> ${solicitud.comuna}</p>
                            <p><span class="font-medium">Dirección:</span> ${solicitud.direccion}</p>
                        </div>
                        
                        ${solicitud.solicitante ? `
                            <div class="bg-gray-50 p-4 rounded-lg">
                                <h4 class="font-semibold text-gray-700 mb-2">Solicitante</h4>
                                <p><span class="font-medium">Nombre:</span> ${solicitud.solicitante.nombre}</p>
                                <p><span class="font-medium">Email:</span> ${solicitud.solicitante.email}</p>
                            </div>
                        ` : ''}
                        
                        <div class="bg-gray-50 p-4 rounded-lg">
                            <h4 class="font-semibold text-gray-700 mb-2">Descripción</h4>
                            <p>${solicitud.descripcion || 'Sin descripción'}</p>
                        </div>
                        
                        <div class="bg-gray-50 p-4 rounded-lg">
                            <h4 class="font-semibold text-gray-700 mb-2">Detalles de la Solicitud</h4>
                            <p><span class="font-medium">Estado:</span> ${solicitud.estado}</p>
                            <p><span class="font-medium">Fecha de solicitud:</span> ${solicitud.fecha_solicitud}</p>
                        </div>
                    </div>
                `;
                
                // Mostrar el modal
                const modal = document.getElementById('modal-detalles');
                modal.classList.remove('hidden');
            } else {
                alert('Error al obtener los detalles: ' + data.message);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Error al obtener los detalles de la solicitud');
        });
}

function cerrarModal() {
    // Ocultar modal
    const modal = document.getElementById('modal-detalles');
    modal.classList.add('hidden');
}

function aprobarSolicitud(solicitudId) {
    if (confirm('¿Estás seguro de que deseas aprobar esta solicitud?')) {
        // Obtener el token CSRF
        const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;
        
        // Usar la URL directamente
        const url = `/termas/aprobar_solicitud/${solicitudId}/`;
        
        // Aquí se enviará la petición al backend
        fetch(url, {
            method: 'POST',
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json',
                'X-CSRFToken': csrftoken
            },
            credentials: 'same-origin',
            body: JSON.stringify({}) // Cuerpo vacío pero necesario para POST
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Error de red o servidor');
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                window.location.reload();
            } else {
                alert('Error al aprobar la solicitud: ' + data.message);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Error al procesar la solicitud: ' + error.message);
        });
    }
}

function rechazarSolicitud(solicitudId) {
    console.log('[DEBUG] rechazarSolicitud llamada con ID:', solicitudId);
    
    // Verificar si existe el modal
    const modal = document.getElementById('modal-rechazo');
    console.log('[DEBUG] Modal encontrado:', modal);
    
    if (!modal) {
        console.error('[ERROR] Modal de rechazo no encontrado en el DOM');
        alert('Error: Modal no encontrado. Usando método alternativo.');
        // Fallback al prompt original
        const motivo = prompt('Por favor, ingrese el motivo del rechazo:');
        if (motivo !== null && motivo.trim()) {
            enviarRechazo(solicitudId, motivo.trim());
        }
        return;
    }
    
    // Guardar el ID de la solicitud y mostrar el modal
    solicitudParaRechazar = solicitudId;
    console.log('[DEBUG] solicitudParaRechazar establecida:', solicitudParaRechazar);
    
    // Verificar y limpiar elementos
    const textarea = document.getElementById('motivo-rechazo-textarea');
    const errorDiv = document.getElementById('error-motivo');
    
    console.log('[DEBUG] Textarea encontrado:', textarea);
    console.log('[DEBUG] Error div encontrado:', errorDiv);
    
    if (textarea) {
        textarea.value = '';
    }
    if (errorDiv) {
        errorDiv.classList.add('hidden');
    }
    
    // Mostrar el modal - usar múltiples métodos para asegurar visibilidad
    console.log('[DEBUG] Mostrando modal...');
    modal.classList.remove('hidden');
    modal.style.display = 'block'; // Fallback CSS
    modal.style.zIndex = '9999';   // Asegurar que esté al frente
    console.log('[DEBUG] Modal classes after show:', modal.className);
    console.log('[DEBUG] Modal style display:', modal.style.display);
    
    // Verificar si el modal es visible
    const isVisible = modal.offsetWidth > 0 && modal.offsetHeight > 0;
    console.log('[DEBUG] Modal visible?', isVisible);
    
    if (!isVisible) {
        console.warn('[WARNING] Modal no parece estar visible, usando fallback');
        modal.style.display = 'block';
        modal.style.position = 'fixed';
        modal.style.top = '0';
        modal.style.left = '0';
        modal.style.width = '100%';
        modal.style.height = '100%';
        modal.style.backgroundColor = 'rgba(0,0,0,0.5)';
    }
    
    // Enfocar el textarea
    setTimeout(() => {
        if (textarea) {
            textarea.focus();
            console.log('[DEBUG] Textarea enfocado');
        }
    }, 100);
}

// Función auxiliar para enviar rechazo (usada como fallback)
function enviarRechazo(solicitudId, motivo) {
    console.log('[DEBUG] enviarRechazo llamada:', solicitudId, motivo);
    
    const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    const url = `/termas/rechazar_solicitud/${solicitudId}/`;
    
    fetch(url, {
        method: 'POST',
        headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken
        },
        credentials: 'same-origin',
        body: JSON.stringify({
            motivo_rechazo: motivo
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            window.location.reload();
        } else {
            alert('Error al rechazar la solicitud: ' + data.message);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Error al procesar la solicitud: ' + error.message);
    });
}

function cerrarModalRechazo() {
    console.log('[DEBUG] cerrarModalRechazo llamada');
    
    // Ocultar el modal y limpiar variables
    const modal = document.getElementById('modal-rechazo');
    if (modal) {
        modal.classList.add('hidden');
        modal.style.display = 'none'; // Fallback CSS
        console.log('[DEBUG] Modal oculto');
    }
    
    solicitudParaRechazar = null;
    console.log('[DEBUG] solicitudParaRechazar limpiada');
    
    // Limpiar el textarea
    const textarea = document.getElementById('motivo-rechazo-textarea');
    const errorDiv = document.getElementById('error-motivo');
    
    if (textarea) {
        textarea.value = '';
    }
    if (errorDiv) {
        errorDiv.classList.add('hidden');
    }
}

function confirmarRechazo() {
    const motivo = document.getElementById('motivo-rechazo-textarea').value.trim();
    const errorDiv = document.getElementById('error-motivo');
    
    // Validar que se haya ingresado un motivo
    if (!motivo) {
        errorDiv.classList.remove('hidden');
        document.getElementById('motivo-rechazo-textarea').focus();
        return;
    }
    
    // Ocultar error si está visible
    errorDiv.classList.add('hidden');
    
    if (solicitudParaRechazar) {
        // Obtener el token CSRF
        const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;
        
        // Usar la URL directamente
        const url = `/termas/rechazar_solicitud/${solicitudParaRechazar}/`;
        
        // Deshabilitar el botón mientras se procesa
        const botonConfirmar = document.querySelector('#modal-rechazo button[onclick="confirmarRechazo()"]');
        const textoOriginal = botonConfirmar.innerHTML;
        botonConfirmar.disabled = true;
        botonConfirmar.innerHTML = '<svg class="animate-spin -ml-1 mr-3 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>Procesando...';
        
        // Aquí se enviará la petición al backend
        fetch(url, {
            method: 'POST',
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json',
                'X-CSRFToken': csrftoken
            },
            credentials: 'same-origin',
            body: JSON.stringify({
                motivo_rechazo: motivo
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Cerrar el modal
                cerrarModalRechazo();
                // Recargar la página para mostrar los cambios
                window.location.reload();
            } else {
                alert('Error al rechazar la solicitud: ' + data.message);
                // Restaurar el botón
                botonConfirmar.disabled = false;
                botonConfirmar.innerHTML = textoOriginal;
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Error al procesar la solicitud: ' + error.message);
            // Restaurar el botón
            botonConfirmar.disabled = false;
            botonConfirmar.innerHTML = textoOriginal;
        });
    }
}

// Función para obtener el token CSRF de las cookies
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Asegurarse de que las funciones están disponibles globalmente
window.mostrarDetalles = mostrarDetalles;
window.cerrarModal = cerrarModal;
window.aprobarSolicitud = aprobarSolicitud;
window.rechazarSolicitud = rechazarSolicitud;
window.cerrarModalRechazo = cerrarModalRechazo;
window.confirmarRechazo = confirmarRechazo;

// Agregar eventos cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', function() {
    console.log('[DEBUG] DOMContentLoaded ejecutado');
    
    // Verificar que los elementos existan
    const modalRechazo = document.getElementById('modal-rechazo');
    const modalDetalles = document.getElementById('modal-detalles');
    const textarea = document.getElementById('motivo-rechazo-textarea');
    
    console.log('[DEBUG] Elementos encontrados:');
    console.log('- modal-rechazo:', modalRechazo);
    console.log('- modal-detalles:', modalDetalles);
    console.log('- motivo-rechazo-textarea:', textarea);
    
    // Cerrar modal de rechazo con Escape
    document.addEventListener('keydown', function(event) {
        if (event.key === 'Escape') {
            
            if (modalRechazo && !modalRechazo.classList.contains('hidden')) {
                console.log('[DEBUG] Cerrando modal rechazo con Escape');
                cerrarModalRechazo();
            } else if (modalDetalles && !modalDetalles.classList.contains('hidden')) {
                console.log('[DEBUG] Cerrando modal detalles con Escape');
                cerrarModal();
            }
        }
    });
    
    // Permitir envío del formulario con Enter en el textarea
    if (textarea) {
        textarea.addEventListener('keydown', function(event) {
            if (event.key === 'Enter' && event.ctrlKey) {
                event.preventDefault();
                console.log('[DEBUG] Ctrl+Enter detectado en textarea');
                confirmarRechazo();
            }
        });
    }
});