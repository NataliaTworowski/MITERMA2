// Admin General JavaScript - Clean Version
let solicitudParaRechazar = null;

function mostrarDetalles(solicitudId) {
    const url = `/termas/detalles_solicitud/${solicitudId}/`;
    
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
                            <h4 class="font-semibold text-gray-700 mb-2">Información de la Empresa</h4>
                            <p><span class="font-medium">RUT Empresa:</span> ${solicitud.rut_empresa || 'No especificado'}</p>
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
    const modal = document.getElementById('modal-detalles');
    modal.classList.add('hidden');
}

function aprobarSolicitud(solicitudId) {
    if (confirm('¿Estás seguro de que deseas aprobar esta solicitud?')) {
        const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;
        const url = `/termas/aprobar_solicitud/${solicitudId}/`;
        
        fetch(url, {
            method: 'POST',
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json',
                'X-CSRFToken': csrftoken
            },
            credentials: 'same-origin',
            body: JSON.stringify({})
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
    const modal = document.getElementById('modal-rechazo');
    
    if (!modal) {
        const motivo = prompt('Por favor, ingrese el motivo del rechazo:');
        if (motivo !== null && motivo.trim()) {
            enviarRechazo(solicitudId, motivo.trim());
        }
        return;
    }
    
    solicitudParaRechazar = solicitudId;
    
    const textarea = document.getElementById('motivo-rechazo-textarea');
    const errorDiv = document.getElementById('error-motivo');
    
    if (textarea) {
        textarea.value = '';
    }
    if (errorDiv) {
        errorDiv.classList.add('hidden');
    }
    
    modal.classList.remove('hidden');
    
    setTimeout(() => {
        if (textarea) {
            textarea.focus();
        }
    }, 100);
}

function enviarRechazo(solicitudId, motivo) {
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
    const modal = document.getElementById('modal-rechazo');
    if (modal) {
        modal.classList.add('hidden');
    }
    
    solicitudParaRechazar = null;
    
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
    
    if (!motivo) {
        errorDiv.classList.remove('hidden');
        document.getElementById('motivo-rechazo-textarea').focus();
        return;
    }
    
    errorDiv.classList.add('hidden');
    
    if (solicitudParaRechazar) {
        const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;
        const url = `/termas/rechazar_solicitud/${solicitudParaRechazar}/`;
        
        const botonConfirmar = document.querySelector('#modal-rechazo button[onclick="confirmarRechazo()"]');
        if (botonConfirmar) {
            const textoOriginal = botonConfirmar.innerHTML;
            botonConfirmar.disabled = true;
            botonConfirmar.innerHTML = 'Procesando...';
            
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
                    cerrarModalRechazo();
                    window.location.reload();
                } else {
                    alert('Error al rechazar la solicitud: ' + data.message);
                    botonConfirmar.disabled = false;
                    botonConfirmar.innerHTML = textoOriginal;
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Error al procesar la solicitud: ' + error.message);
                botonConfirmar.disabled = false;
                botonConfirmar.innerHTML = textoOriginal;
            });
        }
    }
}

// Hacer funciones disponibles globalmente
window.mostrarDetalles = mostrarDetalles;
window.cerrarModal = cerrarModal;
window.aprobarSolicitud = aprobarSolicitud;
window.rechazarSolicitud = rechazarSolicitud;
window.cerrarModalRechazo = cerrarModalRechazo;
window.confirmarRechazo = confirmarRechazo;

// Eventos cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', function() {
    const modalRechazo = document.getElementById('modal-rechazo');
    const modalDetalles = document.getElementById('modal-detalles');
    const textarea = document.getElementById('motivo-rechazo-textarea');
    
    // Cerrar modales con Escape
    document.addEventListener('keydown', function(event) {
        if (event.key === 'Escape') {
            if (modalRechazo && !modalRechazo.classList.contains('hidden')) {
                cerrarModalRechazo();
            } else if (modalDetalles && !modalDetalles.classList.contains('hidden')) {
                cerrarModal();
            }
        }
    });
    
    // Ctrl+Enter en textarea para enviar
    if (textarea) {
        textarea.addEventListener('keydown', function(event) {
            if (event.key === 'Enter' && event.ctrlKey) {
                event.preventDefault();
                confirmarRechazo();
            }
        });
    }
});