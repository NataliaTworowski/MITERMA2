// Funciones para el modal de solicitud de terma
function openSolicitudModal() {
    document.getElementById('solicitudModal').classList.remove('hidden');
}

function closeSolicitudModal() {
    document.getElementById('solicitudModal').classList.add('hidden');
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