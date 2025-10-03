
document.addEventListener('DOMContentLoaded', function() {
    const mobileMenuBtn = document.getElementById('mobile-menu-btn');
    const mobileMenu = document.getElementById('mobile-menu');
    const menuLines = mobileMenuBtn.querySelectorAll('span');

    mobileMenuBtn.addEventListener('click', function() {
        mobileMenu.classList.toggle('hidden');
        
        // Animación del botón hamburguesa
        if (!mobileMenu.classList.contains('hidden')) {
            menuLines[0].style.transform = 'rotate(45deg) translate(5px, 5px)';
            menuLines[1].style.opacity = '0';
            menuLines[2].style.transform = 'rotate(-45deg) translate(7px, -6px)';
        } else {
            menuLines[0].style.transform = 'rotate(0) translate(0, 0)';
            menuLines[1].style.opacity = '1';
            menuLines[2].style.transform = 'rotate(0) translate(0, 0)';
        }
    });

    // Cerrar menú al hacer clic en un enlace
    const mobileLinks = mobileMenu.querySelectorAll('a');
    mobileLinks.forEach(link => {
        link.addEventListener('click', function() {
            mobileMenu.classList.add('hidden');
            menuLines[0].style.transform = 'rotate(0) translate(0, 0)';
            menuLines[1].style.opacity = '1';
            menuLines[2].style.transform = 'rotate(0) translate(0, 0)';
        });
    });
});