// Datos del gráfico desde Django
        const fechasData = JSON.parse('{{ fechas_json|escapejs }}');
        const ventasData = JSON.parse('{{ ventas_por_dia_json|escapejs }}'); // Transacciones
        const ingresosData = JSON.parse('{{ ingresos_por_dia_json|escapejs }}'); // Ingresos en dinero
        const entradasData = JSON.parse('{{ entradas_vendidas_por_dia_json|escapejs }}'); // Entradas vendidas
        const nombreTerma = "{{ terma.nombre_terma|escapejs }}";
        
        // Variables para el gráfico
        let chartVentas = null;
        let tipoVistaActual = 'ingresos'; // Por defecto mostrar ingresos
        
        // Función para formatear precios en formato chileno
        function formatearPrecioChileno(numero) {
            return new Intl.NumberFormat('es-CL', {
                style: 'currency',
                currency: 'CLP',
                minimumFractionDigits: 0,
                maximumFractionDigits: 0
            }).format(numero);
        }
        
        // Función para cambiar tipo de vista del gráfico
        function cambiarTipoVista(tipo) {
            tipoVistaActual = tipo;
            
            // Actualizar botones
            const btnIngresos = document.getElementById('btnIngresos');
            const btnEntradas = document.getElementById('btnEntradas');
            
            // Resetear todos los botones
            btnIngresos.className = 'px-3 py-1 rounded text-xs font-semibold border bg-white text-gray-500 border-gray-200 hover:bg-gray-50';
            btnEntradas.className = 'px-3 py-1 rounded text-xs font-semibold border bg-white text-gray-500 border-gray-200 hover:bg-gray-50';
            
            // Activar el botón seleccionado
            if (tipo === 'ingresos') {
                btnIngresos.className = 'px-3 py-1 rounded text-xs font-semibold border bg-green-100 text-green-700 border-green-200';
            } else if (tipo === 'entradas') {
                btnEntradas.className = 'px-3 py-1 rounded text-xs font-semibold border bg-blue-100 text-blue-700 border-blue-200';
            }
            
            // Recrear el gráfico
            crearGraficoVentasActualizado();
        }
        
        // Función para crear el gráfico de ventas con múltiples opciones
        function crearGraficoVentasActualizado() {
            const ctx = document.getElementById('ventasChart').getContext('2d');
            
            // Destruir gráfico anterior si existe
            if (chartVentas) {
                chartVentas.destroy();
            }
            
            let datos, etiqueta, color, colorBorde;
            
            switch(tipoVistaActual) {
                case 'ingresos':
                    datos = ingresosData;
                    etiqueta = 'Ingresos por Día';
                    color = 'rgba(34, 197, 94, 0.6)';
                    colorBorde = 'rgba(34, 197, 94, 1)';
                    break;
                case 'entradas':
                    datos = entradasData;
                    etiqueta = 'Entradas Vendidas por Día';
                    color = 'rgba(59, 130, 246, 0.6)';
                    colorBorde = 'rgba(59, 130, 246, 1)';
                    break;
                default:
                    datos = ingresosData;
                    etiqueta = 'Ingresos por Día';
                    color = 'rgba(34, 197, 94, 0.6)';
                    colorBorde = 'rgba(34, 197, 94, 1)';
            }
            
            chartVentas = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: fechasData,
                    datasets: [{
                        label: etiqueta,
                        data: datos,
                        backgroundColor: color,
                        borderColor: colorBorde,
                        borderWidth: 2,
                        borderRadius: 6,
                        borderSkipped: false,
                        hoverBackgroundColor: color.replace('0.6', '0.8'),
                        hoverBorderColor: colorBorde,
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: true,
                            position: 'top',
                            labels: {
                                color: '#374151',
                                font: {
                                    size: 12,
                                    weight: 'bold'
                                }
                            }
                        },
                        title: {
                            display: true,
                            text: `${etiqueta} - ${nombreTerma}`,
                            color: '#1f2937',
                            font: {
                                size: 16,
                                weight: 'bold'
                            },
                            padding: 20
                        },
                        tooltip: {
                            backgroundColor: 'rgba(0,0,0,0.8)',
                            titleColor: 'white',
                            bodyColor: 'white',
                            callbacks: {
                                label: function(context) {
                                    const valor = context.parsed.y;
                                    if (tipoVistaActual === 'ingresos') {
                                        return `Ingresos: ${formatearPrecioChileno(valor)}`;
                                    } else {
                                        return `Entradas: ${valor} tickets`;
                                    }
                                }
                            }
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: {
                                color: '#6B7280',
                                callback: function(value) {
                                    if (tipoVistaActual === 'ingresos') {
                                        return formatearPrecioChileno(value);
                                    } else {
                                        return value;
                                    }
                                }
                            },
                            grid: {
                                color: '#E5E7EB'
                            }
                        },
                        x: {
                            ticks: {
                                color: '#6B7280',
                                maxRotation: 45
                            },
                            grid: {
                                display: false
                            }
                        }
                    },
                    animation: {
                        duration: 1000,
                        easing: 'easeOutQuart'
                    }
                }
            });
        }
        // Datos para el gráfico de tipos de entradas
        const tiposLabels = JSON.parse('{{ tipos_labels_json|escapejs }}');
        const tiposValues = JSON.parse('{{ tipos_values_json|escapejs }}');
        // Datos para el gráfico de servicios populares
        const serviciosLabels = JSON.parse('{{ servicios_labels_json|escapejs }}');
        const serviciosValues = JSON.parse('{{ servicios_values_json|escapejs }}');
        // Datos para el gráfico de días de la semana
        const diasSemanaLabels = JSON.parse('{{ dias_semana_json|escapejs }}');
        const ventasDiaSemanaValues = JSON.parse('{{ ventas_dia_semana_json|escapejs }}');
        // Datos para el gráfico de entradas más vendidas
        const entradasLabels = JSON.parse('{{ tipos_labels_json|escapejs }}');
        const entradasValues = JSON.parse('{{ tipos_values_json|escapejs }}');

        document.addEventListener('DOMContentLoaded', function() {
            // Crear el gráfico de ventas con la nueva funcionalidad
            crearGraficoVentasActualizado();

            // Crear el gráfico de servicios populares (torta)
            const ctxServicios = document.getElementById('serviciosTortaChart').getContext('2d');
            new Chart(ctxServicios, {
                type: 'pie',
                data: {
                    labels: serviciosLabels,
                    datasets: [{
                        label: 'Servicios Populares',
                        data: serviciosValues,
                        backgroundColor: [
                            '#4caf50',
                            '#2196f3',
                            '#ff9800',
                            '#f44336',
                            '#9c27b0',
                            '#00bcd4',
                            '#8bc34a',
                            '#ffc107',
                            '#e91e63',
                            '#673ab7'
                        ],
                        borderColor: '#fff',
                        borderWidth: 2
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: {
                            position: 'top',
                        },
                        tooltip: {
                            callbacks: {
                                label: function(tooltipItem) {
                                    const label = tooltipItem.label || '';
                                    const value = tooltipItem.raw || 0;
                                    return `${label}: ${value}`;
                                }
                            }
                        }
                    }
                }
            });

            // Crear el gráfico de tendencias por día de la semana
            const ctxDiaSemana = document.getElementById('diaSemanaChart').getContext('2d');
            new Chart(ctxDiaSemana, {
                type: 'bar',
                data: {
                    labels: diasSemanaLabels,
                    datasets: [{
                        label: 'Ventas por Día',
                        data: ventasDiaSemanaValues,
                        backgroundColor: [
                            '#FF6B6B', // Lunes - Rojo suave
                            '#4ECDC4', // Martes - Turquesa
                            '#45B7D1', // Miércoles - Azul
                            '#96CEB4', // Jueves - Verde suave
                            '#FFEAA7', // Viernes - Amarillo
                            '#DDA0DD', // Sábado - Lila
                            '#FF9FF3'  // Domingo - Rosa
                        ],
                        borderColor: [
                            '#FF5252',
                            '#26A69A',
                            '#2196F3',
                            '#66BB6A',
                            '#FFCA28',
                            '#BA68C8',
                            '#E91E63'
                        ],
                        borderWidth: 2,
                        borderRadius: 8,
                        borderSkipped: false,
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: false
                        },
                        tooltip: {
                            backgroundColor: 'rgba(0,0,0,0.8)',
                            titleColor: 'white',
                            bodyColor: 'white',
                            callbacks: {
                                label: function(context) {
                                    return `Ventas: ${context.parsed.y}`;
                                }
                            }
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: {
                                stepSize: 1,
                                color: '#6B7280'
                            },
                            grid: {
                                color: '#E5E7EB'
                            }
                        },
                        x: {
                            ticks: {
                                color: '#6B7280',
                                maxRotation: 45
                            },
                            grid: {
                                display: false
                            }
                        }
                    },
                    animation: {
                        duration: 1000,
                        easing: 'easeOutQuart'
                    }
                }
            });

            // Crear el gráfico de entradas más vendidas
            const ctxEntradas = document.getElementById('entradasChart').getContext('2d');
            new Chart(ctxEntradas, {
                type: 'doughnut',
                data: {
                    labels: entradasLabels,
                    datasets: [{
                        label: 'Entradas Vendidas',
                        data: entradasValues,
                        backgroundColor: [
                            '#3B82F6', // Azul
                            '#10B981', // Verde esmeralda
                            '#F59E0B', // Ámbar
                            '#EF4444', // Rojo
                            '#8B5CF6', // Violeta
                            '#06B6D4', // Cian
                            '#84CC16', // Lima
                            '#F97316', // Naranja
                            '#EC4899', // Rosa
                            '#6366F1'  // Índigo
                        ],
                        borderColor: '#ffffff',
                        borderWidth: 3,
                        hoverOffset: 10
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: {
                                padding: 20,
                                usePointStyle: true,
                                font: {
                                    size: 12
                                }
                            }
                        },
                        tooltip: {
                            backgroundColor: 'rgba(0,0,0,0.8)',
                            titleColor: 'white',
                            bodyColor: 'white',
                            callbacks: {
                                label: function(context) {
                                    const label = context.label || '';
                                    const value = context.parsed || 0;
                                    const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                    const percentage = ((value / total) * 100).toFixed(1);
                                    return `${label}: ${value} (${percentage}%)`;
                                }
                            }
                        }
                    },
                    animation: {
                        animateRotate: true,
                        duration: 1000
                    }
                }
            });

            // Llenar los detalles de entradas
            function llenarDetallesEntradas() {
                const contenedor = document.getElementById('entradas-detalles');
                if (!contenedor) return;
                
                let html = '';
                const total = entradasValues.reduce((a, b) => a + b, 0);
                
                for (let i = 0; i < entradasLabels.length; i++) {
                    const porcentaje = total > 0 ? ((entradasValues[i] / total) * 100).toFixed(1) : 0;
                    html += `
                        <div class="flex justify-between items-center text-sm py-1">
                            <div class="flex items-center">
                                <div class="w-3 h-3 rounded-full mr-2" style="background-color: ${getColorForIndex(i)}"></div>
                                <span class="text-gray-700">${entradasLabels[i]}</span>
                            </div>
                            <div class="text-right">
                                <span class="font-medium text-gray-900">${entradasValues[i]}</span>
                                <span class="text-gray-500 ml-1">(${porcentaje}%)</span>
                            </div>
                        </div>
                    `;
                }
                
                contenedor.innerHTML = html;
            }
            
            function getColorForIndex(index) {
                const colors = [
                    '#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6',
                    '#06B6D4', '#84CC16', '#F97316', '#EC4899', '#6366F1'
                ];
                return colors[index % colors.length];
            }
            
            // Llenar detalles después de crear el gráfico
            llenarDetallesEntradas();

            // Animar las estadísticas
            setTimeout(() => {
                animarEstadisticas();
            }, 500);
        });