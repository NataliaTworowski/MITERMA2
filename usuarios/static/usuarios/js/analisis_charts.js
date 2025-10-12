/**
 * Gráfico de análisis de ventas para administradores de termas
 */

function crearGraficoVentas(fechas, ventasPorDia, nombreTerma) {
    const ctx = document.getElementById('ventasChart').getContext('2d');
    
    const ventasChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: fechas,
            datasets: [{
                label: 'Ventas por Día',
                data: ventasPorDia,
                backgroundColor: 'rgba(59, 130, 246, 0.6)',
                borderColor: 'rgba(59, 130, 246, 1)',
                borderWidth: 2,
                borderRadius: 6,
                borderSkipped: false,
                hoverBackgroundColor: 'rgba(59, 130, 246, 0.8)',
                hoverBorderColor: 'rgba(37, 99, 235, 1)',
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
                    text: `Ventas Diarias - ${nombreTerma}`,
                    color: '#1f2937',
                    font: {
                        size: 16,
                        weight: 'bold'
                    },
                    padding: 20
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1,
                        color: '#6b7280',
                        font: {
                            size: 11
                        }
                    },
                    title: {
                        display: true,
                        text: 'Número de Ventas',
                        color: '#374151',
                        font: {
                            size: 12,
                            weight: 'bold'
                        }
                    },
                    grid: {
                        color: 'rgba(107, 114, 128, 0.1)'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Fecha',
                        color: '#374151',
                        font: {
                            size: 12,
                            weight: 'bold'
                        }
                    },
                    ticks: {
                        color: '#6b7280',
                        font: {
                            size: 11
                        }
                    },
                    grid: {
                        display: false
                    }
                }
            },
            animation: {
                duration: 1200,
                easing: 'easeInOutQuart'
            },
            interaction: {
                intersect: false,
                mode: 'index'
            }
        }
    });

    return ventasChart;
}

// Función para animar las estadísticas
function animarEstadisticas() {
    const estadisticas = document.querySelectorAll('.estadistica-numero');
    
    estadisticas.forEach((elemento, index) => {
        const valorFinal = parseInt(elemento.textContent) || parseFloat(elemento.textContent) || 0;
        let valorActual = 0;
        const incremento = valorFinal / 50; // 50 pasos de animación
        
        const intervalo = setInterval(() => {
            valorActual += incremento;
            if (valorActual >= valorFinal) {
                elemento.textContent = valorFinal;
                clearInterval(intervalo);
            } else {
                elemento.textContent = Math.floor(valorActual);
            }
        }, 30);
        
        // Retrasar cada animación
        setTimeout(() => {
            clearInterval(intervalo);
            const newIntervalo = setInterval(() => {
                valorActual += incremento;
                if (valorActual >= valorFinal) {
                    elemento.textContent = valorFinal;
                    clearInterval(newIntervalo);
                } else {
                    elemento.textContent = Math.floor(valorActual);
                }
            }, 30);
        }, index * 200);
    });
}

// Función para crear gráfico de líneas (opcional)
function crearGraficoLineas(fechas, ventasPorDia, nombreTerma) {
    const ctx = document.getElementById('ventasChart').getContext('2d');
    
    return new Chart(ctx, {
        type: 'line',
        data: {
            labels: fechas,
            datasets: [{
                label: 'Tendencia de Ventas',
                data: ventasPorDia,
                borderColor: 'rgba(34, 197, 94, 1)',
                backgroundColor: 'rgba(34, 197, 94, 0.1)',
                borderWidth: 3,
                fill: true,
                tension: 0.4,
                pointBackgroundColor: 'rgba(34, 197, 94, 1)',
                pointBorderColor: '#ffffff',
                pointBorderWidth: 2,
                pointRadius: 6,
                pointHoverRadius: 8,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: `Tendencia de Ventas - ${nombreTerma}`,
                    color: '#1f2937',
                    font: {
                        size: 16,
                        weight: 'bold'
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1
                    }
                }
            },
            animation: {
                duration: 1500,
                easing: 'easeInOutCubic'
            }
        }
    });
}