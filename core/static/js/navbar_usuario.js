document.addEventListener('DOMContentLoaded', function() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebar-overlay');
    const closeBtn = document.getElementById('close-sidebar');

    function closeSidebar() {
        sidebar.classList.add('-translate-x-full');
        overlay.classList.add('hidden');
    }

    function openSidebar() {
        sidebar.classList.remove('-translate-x-full');
        overlay.classList.remove('hidden');
    }

    // Cerrar sidebar al hacer click en el botón
    if (closeBtn) {
        closeBtn.addEventListener('click', closeSidebar);
    }

    // Cerrar sidebar al hacer click en el overlay
    if (overlay) {
        overlay.addEventListener('click', closeSidebar);
    }

    // Opcional: abrir sidebar desde algún botón/menu hamburguesa
    // Ejemplo:
    // document.getElementById('open-sidebar').addEventListener('click', openSidebar);
});