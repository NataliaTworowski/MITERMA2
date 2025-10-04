document.addEventListener('DOMContentLoaded', function() {
    const regionSelect = document.getElementById('region');
    const comunaSelect = document.getElementById('comuna');
    const searchInput = document.getElementById('searchInput');
    const limpiarFiltrosBtn = document.getElementById('limpiarFiltros');
    
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
    
    // Función para limpiar todos los filtros
    function limpiarFiltros() {
        // Limpiar región
        regionSelect.value = '';
        
        // Limpiar y restaurar comunas
        comunaSelect.innerHTML = '<option value="">Todas las comunas</option>';
        originalComunas.forEach(option => {
            if (option.value !== '') {
                comunaSelect.appendChild(option.cloneNode(true));
            }
        });
        
        // Limpiar búsqueda
        if (searchInput) {
            searchInput.value = '';
        }
    }
    
    // Event listener para cambio de región
    regionSelect.addEventListener('change', function() {
        filtrarComunas();
        // Reset comuna seleccionada cuando cambia la región
        comunaSelect.value = '';
    });
    
    // Event listener para limpiar filtros
    if (limpiarFiltrosBtn) {
        limpiarFiltrosBtn.addEventListener('click', limpiarFiltros);
    }
    
    // Filtrar comunas al cargar la página si hay región seleccionada
    if (regionSelect.value) {
        filtrarComunas();
    }
});