// Mostrar pop-up de login al intentar pagar si el usuario no está logueado
document.addEventListener('DOMContentLoaded', function() {
    var btnPagar = document.getElementById('btn-pagar');
    var popupLogin = document.getElementById('popup-login');
    var cerrarPopup = document.getElementById('cerrar-popup-login');
    if (btnPagar && popupLogin && cerrarPopup) {
        btnPagar.addEventListener('click', function(e) {
            e.preventDefault();
            popupLogin.classList.remove('hidden');
        });
        cerrarPopup.addEventListener('click', function() {
            popupLogin.classList.add('hidden');
        });
    }
});
// Mostrar opiniones debajo

document.addEventListener('DOMContentLoaded', function() {
    const btnVer = document.getElementById('btn-ver-opiniones');
    const lista = document.getElementById('opiniones-lista');
    if (btnVer && lista) {
        btnVer.addEventListener('click', function(e) {
            e.preventDefault();
            lista.classList.toggle('hidden');
            btnVer.textContent = lista.classList.contains('hidden') ? 'Ver todas las opiniones' : 'Ocultar opiniones';
        });
    }

    // Carrusel simple
    const imgs = document.querySelectorAll('#carrusel-terma .carrusel-img');
    let idx = 0;
    function showImg(i) {
        imgs.forEach((img, j) => {
            if (j === i) {
                img.classList.remove('opacity-0', 'pointer-events-none');
            } else {
                img.classList.add('opacity-0', 'pointer-events-none');
            }
        });
    }
    const prevBtn = document.getElementById('carrusel-prev');
    const nextBtn = document.getElementById('carrusel-next');
    if (prevBtn && nextBtn) {
        prevBtn.onclick = () => {
            idx = (idx - 1 + imgs.length) % imgs.length;
            showImg(idx);
        };
        nextBtn.onclick = () => {
            idx = (idx + 1) % imgs.length;
            showImg(idx);
        };
    }

    // Interactividad para seleccionar experiencia y actualizar resumen
    const cards = document.querySelectorAll('.experiencia-card');
    const inputExperiencia = document.getElementById('experiencia');
    const inputEntradaId = document.getElementById('entrada_id');
    const resumenExperiencia = document.getElementById('resumen-experiencia');
    const resumenPrecio = document.getElementById('resumen-precio');
    const resumenTotal = document.getElementById('resumen-total');
    const inputCantidad = document.getElementById('cantidad');
    let precioSeleccionado = 0;

    function renderServiciosIncluidos(servicios) {
        const cont = document.getElementById('servicios-incluidos');
        if (!cont) return;
        cont.innerHTML = '';
        if (servicios.length === 0) {
            cont.innerHTML = '<div class="col-span-3 text-gray-400">No hay servicios incluidos para esta experiencia.</div>';
            return;
        }
        servicios.forEach(servicio => {
            cont.innerHTML += `<div class="w-full max-w-4xl mx-auto flex flex-row items-center gap-10 bg-gradient-to-br from-blue-50 via-orange-50 to-blue-100 rounded-2xl shadow-xl border border-gray-100 px-16 py-8">
                <div class="flex-shrink-0 mr-8">
                    <svg class="w-16 h-16 text-blue-400" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2" fill="#e3eafc"/></svg>
                </div>
                <div class="flex flex-col gap-2 flex-1">
                    <span class="text-3xl font-bold text-blue-900 mb-2 font-serif">${servicio.servicio}</span>
                    <span class="text-lg text-blue-800 font-medium">${servicio.descripcion || ''}</span>
                </div>
            </div>`;
        });
    }

    function seleccionarExperiencia(card) {
        cards.forEach(c => c.classList.remove('border-[#234176]', 'bg-[#f5f7fa]'));
        card.classList.add('border-[#234176]', 'bg-[#f5f7fa]');
        const nombre = card.getAttribute('data-nombre');
        const precio = card.getAttribute('data-precio');
        const id = card.getAttribute('data-id');
        inputExperiencia.value = nombre;
        inputEntradaId.value = id;
        resumenExperiencia.textContent = nombre;
        resumenPrecio.textContent = `$${parseInt(precio).toLocaleString('es-CL')} CLP`;
        precioSeleccionado = parseInt(precio);
        const serviciosPorEntrada = JSON.parse(document.getElementById('servicios-por-entrada-json').textContent);
        const data = serviciosPorEntrada[id];
        renderServiciosIncluidos(data.incluidos);
        document.querySelectorAll('.servicio-extra-checkbox').forEach(cb => {
            cb.addEventListener('change', actualizarTotal);
        });
        actualizarTotal();
    }

    cards.forEach(card => {
        card.addEventListener('click', () => seleccionarExperiencia(card));
        const btn = card.querySelector('.select-experiencia');
        if (btn) {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                seleccionarExperiencia(card);
            });
        }
    });

    const entradaInicial = document.querySelector('.experiencia-card.border-blue-400') || document.querySelector('.experiencia-card');
    if (entradaInicial) seleccionarExperiencia(entradaInicial);

    function actualizarTotal() {
        const cantidad = parseInt(inputCantidad.value) || 1;
        let totalExtras = 0;
        let extrasNombres = [];
        document.querySelectorAll('.servicio-extra-checkbox:checked').forEach(cb => {
            let precio = parseInt(cb.getAttribute('data-precio')) || 0;
            totalExtras += precio * cantidad;
            extrasNombres.push(cb.getAttribute('data-nombre'));
        });
        const totalCLP = precioSeleccionado * cantidad + totalExtras;
        let resumenIncluidos = document.getElementById('resumen-incluidos');
        let serviciosIncluidos = [];
        let incluidosDivs = document.querySelectorAll('#servicios-incluidos > div .text-lg');
        if (incluidosDivs) {
            incluidosDivs.forEach(el => {
                serviciosIncluidos.push(el.textContent);
            });
        }
        if (resumenIncluidos) {
            resumenIncluidos.textContent = serviciosIncluidos.length > 0 ? serviciosIncluidos.join(', ') : '-';
        }
        let resumenExtras = document.getElementById('resumen-extras');
        if (resumenExtras) {
            if (extrasNombres.length > 0) {
                resumenExtras.textContent = extrasNombres.join(', ');
            } else {
                resumenExtras.textContent = '-';
            }
        }
        let resumenTotal = document.getElementById('resumen-total');
        if (resumenTotal) {
            resumenTotal.textContent = `$${totalCLP.toLocaleString('es-CL')} CLP`;
        }
    }

    document.querySelectorAll('.servicio-extra-checkbox').forEach(cb => {
        cb.addEventListener('change', actualizarTotal);
    });

    document.getElementById('menos').addEventListener('click', () => {
        let val = parseInt(inputCantidad.value) || 1;
        if (val > 1) inputCantidad.value = val - 1;
        actualizarTotal();
    });
    document.getElementById('mas').addEventListener('click', () => {
        let val = parseInt(inputCantidad.value) || 1;
        inputCantidad.value = val + 1;
        actualizarTotal();
    });
    inputCantidad.addEventListener('input', actualizarTotal);
});
