// Script para manejar el formulario de búsqueda y los filtros
        document.addEventListener('DOMContentLoaded', function() {
            const formBusquedaTermas = document.getElementById('formBusquedaTermas');
            const buscarTermasBtn = document.getElementById('buscarTermas');
            const limpiarFiltrosBtn = document.getElementById('limpiarFiltros');
            const regionSelect = document.getElementById('region');
            const comunaSelect = document.getElementById('comuna');

            // Función para obtener los parámetros de búsqueda del formulario
            function obtenerParametrosBusqueda() {
                const formData = new FormData(formBusquedaTermas);
                const params = new URLSearchParams();
                for (const [key, value] of formData.entries()) {
                    if (value) {
                        params.append(key, value);
                    }
                }
                return params;
            }

            // Evento para el botón de búsqueda
            buscarTermasBtn.addEventListener('click', function(event) {
                event.preventDefault();
                const params = obtenerParametrosBusqueda();
                window.location.href = '{% url "termas:buscar" %}?' + params.toString();
            });

            // Evento para el botón de limpiar filtros
            limpiarFiltrosBtn.addEventListener('click', function() {
                regionSelect.value = '';
                comunaSelect.value = '';
                formBusquedaTermas.submit();
            });

            // Filtrado de comunas por región
            regionSelect.addEventListener('change', function() {
                const regionId = this.value;
                for (const option of comunaSelect.options) {
                    option.style.display = option.dataset.region === regionId || regionId === '' ? 'block' : 'none';
                }
                comunaSelect.value = '';
            });
        });