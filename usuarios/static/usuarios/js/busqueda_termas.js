document.addEventListener('DOMContentLoaded', function() {
    const regionSelect = document.getElementById('region');
    const comunaSelect = document.getElementById('comuna');
    
    // Verificar que los elementos existen antes de proceder
    if (!regionSelect || !comunaSelect) {
        console.log('No se encontraron los selectores necesarios');
        return;
    }
    
    // Guardar todas las opciones originales de comunas
    const originalComunas = Array.from(comunaSelect.options);
    
    // Función para filtrar comunas según región seleccionada
    function filtrarComunas() {
        const regionSeleccionada = regionSelect.value;
        
        // Limpiar opciones actuales (excepto la primera)
        comunaSelect.innerHTML = '<option value="">Todas las comunas</option>';
        
        if (!regionSeleccionada) {
            // Si no hay región seleccionada, mostrar todas las comunas
            originalComunas.forEach(option => {
                if (option.value !== '') {  // Excluir la opción "Todas las comunas"
                    comunaSelect.appendChild(option.cloneNode(true));
                }
            });
        } else {
            // Filtrar y agregar solo las comunas de la región seleccionada
            originalComunas.forEach(option => {
                if (option.value !== '' && option.dataset.region === regionSeleccionada) {
                    comunaSelect.appendChild(option.cloneNode(true));
                }
            });
        }
        
        // Actualizar el texto de la primera opción
        comunaSelect.options[0].text = regionSeleccionada 
            ? 'Todas las comunas de esta región' 
            : 'Todas las comunas';
    }
    
    // Event listener para cambio de región
    regionSelect.addEventListener('change', function() {
        filtrarComunas();
        // Reset comuna seleccionada cuando cambia la región
        comunaSelect.value = '';
    });
    
    // Filtrar comunas al cargar la página si hay región seleccionada
    if (regionSelect.value) {
        filtrarComunas();
    }
    
    // Agregar botón de limpiar filtros
    const form = document.querySelector('form');
    if (form) {
        const clearButton = document.createElement('button');
        clearButton.type = 'button';
        clearButton.className = 'bg-gray-500 hover:bg-gray-600 text-white font-bold py-3 px-6 rounded-lg text-lg transition-colors duration-200 ml-4';
        clearButton.innerHTML = 'Limpiar filtros';
        
        clearButton.addEventListener('click', function() {
            // Limpiar el formulario
            form.reset();
            
            // Restaurar todas las comunas
            comunaSelect.innerHTML = '<option value="">Todas las comunas</option>';
            originalComunas.forEach(option => {
                if (option.value !== '') {
                    comunaSelect.appendChild(option.cloneNode(true));
                }
            });
        });
        
        // Insertar botón de limpiar al lado del botón de búsqueda
        const submitButton = form.querySelector('button[type="submit"]').parentNode;
        if (submitButton) {
            submitButton.appendChild(clearButton);
        }
    }
});