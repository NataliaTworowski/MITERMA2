// Funcionalidad para el filtro de búsqueda de termas
document.addEventListener('DOMContentLoaded', function() {
    const regionSelect = document.getElementById('region');
    const ciudadSelect = document.getElementById('ciudad');
    
    // Verificar que los elementos existen antes de proceder
    if (!regionSelect || !ciudadSelect) {
        return;
    }
    
    const originalCiudades = Array.from(ciudadSelect.options);
    
    // Función para filtrar ciudades según región seleccionada
    function filterCiudades() {
        const selectedRegion = regionSelect.value;
        
        // Limpiar opciones actuales (excepto la primera)
        ciudadSelect.innerHTML = '<option value="">Todas las ciudades</option>';
        
        // Agregar ciudades filtradas
        originalCiudades.slice(1).forEach(option => {
            if (!selectedRegion || option.dataset.region === selectedRegion) {
                ciudadSelect.appendChild(option.cloneNode(true));
            }
        });
        
        // Si se selecciona una región específica, cambiar el texto de la primera opción
        if (selectedRegion) {
            ciudadSelect.options[0].textContent = 'Todas las ciudades de esta región';
        }
    }
    
    // Event listener para cambio de región
    regionSelect.addEventListener('change', function() {
        filterCiudades();
        // Reset ciudad seleccionada cuando cambia la región
        ciudadSelect.value = '';
    });
    
    // Filtrar ciudades al cargar la página si hay región seleccionada
    if (regionSelect.value) {
        filterCiudades();
    }
    
    // Agregar botón de limpiar filtros
    const form = document.querySelector('form');
    if (form) {
        const clearButton = document.createElement('button');
        clearButton.type = 'button';
        clearButton.className = 'bg-gray-500 hover:bg-gray-600 text-white font-bold py-3 px-6 rounded-lg text-lg transition-colors duration-200 ml-4';
        clearButton.innerHTML = 'Limpiar filtros';
        
        clearButton.addEventListener('click', function() {
            form.reset();
            ciudadSelect.innerHTML = '<option value="">Todas las ciudades</option>';
            originalCiudades.slice(1).forEach(option => {
                ciudadSelect.appendChild(option.cloneNode(true));
            });
        });
        
        // Insertar botón de limpiar al lado del botón de búsqueda
        const submitButton = form.querySelector('button[type="submit"]');
        if (submitButton && submitButton.parentNode) {
            submitButton.parentNode.appendChild(clearButton);
        }
    }
});