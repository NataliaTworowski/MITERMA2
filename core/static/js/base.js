// Funciones para el modal de solicitud de terma
function openSolicitudModal(planId = null) {
    console.log('base.js - openSolicitudModal llamada con planId:', planId);
    const modal = document.getElementById('solicitudModal');
    console.log('Modal encontrado:', modal);
    
    if (modal) {
        // Mostrar el modal
        modal.style.display = 'flex';
        modal.classList.remove('hidden');
        console.log('Modal mostrado');
        
        // Si hay un plan seleccionado, preseleccionar en el formulario
        if (planId) {
            setTimeout(() => {
                const planSelect = document.querySelector('select[name="plan_seleccionado"]');
                console.log('base.js - Select de plan encontrado:', planSelect);
                if (planSelect) {
                    planSelect.value = planId;
                    console.log('base.js - Plan seleccionado establecido a:', planId);
                }
            }, 100);
        }
        
        // Prevent body scroll
        document.body.style.overflow = 'hidden';
    } else {
        console.error('Modal no encontrado!');
    }
}

function closeSolicitudModal() {
    console.log('base.js - closeSolicitudModal llamada');
    const modal = document.getElementById('solicitudModal');
    if (modal) {
        modal.style.display = 'none';
        modal.classList.add('hidden');
        
        // Restore body scroll
        document.body.style.overflow = 'auto';
        console.log('Modal cerrado');
    }
}

// Función para mostrar popup de éxito
function mostrarPopupExito() {
    console.log('Función mostrarPopupExito() llamada');
    const popup = document.getElementById('popupExito');
    console.log('Popup element:', popup);
    if (popup) {
        console.log('Popup encontrado, removiendo hidden y agregando flex');
        popup.classList.remove('hidden');
        popup.classList.add('flex');
        
        // Animación de entrada
        setTimeout(() => {
            console.log('Agregando animación fadeIn');
            popup.classList.add('animate-fadeIn');
        }, 10);
    } else {
        console.error('Elemento popupExito no encontrado en el DOM');
    }
}

// Función para cerrar popup de éxito
function cerrarPopupExito() {
    const popup = document.getElementById('popupExito');
    if (popup) {
        popup.classList.add('animate-fadeOut');
        
        // Ocultar después de la animación
        setTimeout(() => {
            popup.classList.add('hidden');
            popup.classList.remove('flex', 'animate-fadeIn', 'animate-fadeOut');
        }, 300);
    }
}

// Función para mostrar mensajes de error
function mostrarError(mensaje) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'p-4 mb-4 rounded-lg bg-red-100 text-red-700 border border-red-400';
    errorDiv.textContent = mensaje;
    
    const form = document.querySelector('form');
    form.insertBefore(errorDiv, form.firstChild);
    
    setTimeout(() => {
        errorDiv.remove();
    }, 5000);
}

// Función para cargar comunas según la región seleccionada
async function cargarComunas(regionId) {
    try {
        const response = await fetch(`/api/comunas/${regionId}/`);
        if (!response.ok) {
            throw new Error('Error al cargar las comunas');
        }
        
        const comunas = await response.json();
        const comunaSelect = document.getElementById('id_comuna');
        
        // Limpiar opciones actuales
        comunaSelect.innerHTML = '<option value="">Selecciona una comuna</option>';
        
        // Agregar nuevas opciones
        comunas.forEach(comuna => {
            const option = document.createElement('option');
            option.value = comuna.id;
            option.textContent = comuna.nombre;
            comunaSelect.appendChild(option);
        });
        
        // Habilitar el select de comuna
        comunaSelect.disabled = false;
    } catch (error) {
        console.error('Error al cargar las comunas:', error);
        mostrarError('Error al cargar las comunas. Por favor, intenta nuevamente.');
        
        const comunaSelect = document.getElementById('id_comuna');
        comunaSelect.innerHTML = '<option value="">Error al cargar comunas</option>';
        comunaSelect.disabled = true;
    }
}

// Inicializar eventos cuando el documento está listo
document.addEventListener('DOMContentLoaded', function() {
    // Modal events
    const modal = document.getElementById('solicitudModal');
    if (modal) {
        window.addEventListener('click', function(event) {
            if (event.target === modal) {
                closeSolicitudModal();
            }
        });
    }
    
    // Popup de éxito events
    const popupExito = document.getElementById('popupExito');
    if (popupExito) {
        window.addEventListener('click', function(event) {
            if (event.target === popupExito) {
                cerrarPopupExito();
            }
        });
    }
    
    // Region-Comuna filtering
    const regionSelect = document.getElementById('id_region');
    const comunaSelect = document.getElementById('id_comuna');
    
    if (regionSelect && comunaSelect) {
        // Deshabilitar comuna inicialmente
        comunaSelect.disabled = !regionSelect.value;
        
        // Evento cuando cambia la región
        regionSelect.addEventListener('change', function() {
            if (this.value) {
                cargarComunas(this.value);
            } else {
                comunaSelect.innerHTML = '<option value="">---------</option>';
                comunaSelect.disabled = true;
            }
        });
    }
});