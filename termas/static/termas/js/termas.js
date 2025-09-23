// JavaScript específico para la app termas

document.addEventListener('DOMContentLoaded', function() {
    console.log('Termas app cargada');
    
    // Animación de las tarjetas de termas
    const termaCards = document.querySelectorAll('.terma-card');
    
    // Efecto hover mejorado
    termaCards.forEach((card, index) => {
        // Animación escalonada al cargar
        setTimeout(() => {
            card.style.opacity = '0';
            card.style.transform = 'translateY(20px)';
            card.style.transition = 'all 0.3s ease';
            
            setTimeout(() => {
                card.style.opacity = '1';
                card.style.transform = 'translateY(0)';
            }, 50);
        }, index * 100);
        
        // Efectos de hover
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-10px) scale(1.02)';
            this.style.boxShadow = '0 15px 35px rgba(0,0,0,0.2)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0) scale(1)';
            this.style.boxShadow = '0 2px 10px rgba(0,0,0,0.1)';
        });
    });
    
    // Funcionalidad de reserva rápida
    const botonesReserva = document.querySelectorAll('.btn-outline-success');
    botonesReserva.forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            mostrarModalReserva();
        });
    });
    
    // Función para mostrar modal de reserva (placeholder)
    function mostrarModalReserva() {
        alert('Funcionalidad de reserva - Próximamente disponible');
    }
    
    // Filtro de temperatura (si existe input)
    const temperaturaFilter = document.getElementById('temperatura-filter');
    if (temperaturaFilter) {
        temperaturaFilter.addEventListener('input', function() {
            filtrarPorTemperatura(this.value);
        });
    }
    
    // Función para filtrar termas por temperatura
    function filtrarPorTemperatura(temperatura) {
        termaCards.forEach(card => {
            const tempElement = card.querySelector('.fa-thermometer-half').nextElementSibling;
            const tempValue = parseInt(tempElement.textContent);
            
            if (temperatura === '' || Math.abs(tempValue - temperatura) <= 5) {
                card.style.display = 'block';
            } else {
                card.style.display = 'none';
            }
        });
    }
    
    // Tooltip para información adicional
    const tooltips = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    tooltips.forEach(tooltip => {
        new bootstrap.Tooltip(tooltip);
    });
});

// Función para validar formulario de terma
function validarFormularioTerma() {
    const nombre = document.getElementById('id_nombre');
    const precio = document.getElementById('id_precio_por_hora');
    const capacidad = document.getElementById('id_capacidad_personas');
    const temperatura = document.getElementById('id_temperatura_agua');
    
    let valido = true;
    
    if (nombre && nombre.value.trim() === '') {
        mostrarError(nombre, 'El nombre es obligatorio');
        valido = false;
    }
    
    if (precio && (precio.value <= 0 || precio.value > 1000000)) {
        mostrarError(precio, 'El precio debe estar entre 1 y 1,000,000');
        valido = false;
    }
    
    if (capacidad && (capacidad.value < 1 || capacidad.value > 20)) {
        mostrarError(capacidad, 'La capacidad debe estar entre 1 y 20 personas');
        valido = false;
    }
    
    if (temperatura && (temperatura.value < 20 || temperatura.value > 50)) {
        mostrarError(temperatura, 'La temperatura debe estar entre 20°C y 50°C');
        valido = false;
    }
    
    return valido;
}

// Función auxiliar para mostrar errores
function mostrarError(elemento, mensaje) {
    elemento.classList.add('is-invalid');
    
    let feedbackElement = elemento.nextElementSibling;
    if (!feedbackElement || !feedbackElement.classList.contains('invalid-feedback')) {
        feedbackElement = document.createElement('div');
        feedbackElement.classList.add('invalid-feedback');
        elemento.parentNode.insertBefore(feedbackElement, elemento.nextSibling);
    }
    
    feedbackElement.textContent = mensaje;
}