
document.addEventListener('DOMContentLoaded', function() {
    const mobileMenuBtn = document.getElementById('mobile-menu-btn');
    const mobileMenu = document.getElementById('mobile-menu');
    const menuLines = mobileMenuBtn.querySelectorAll('span');
    const navbar = document.getElementById('navbar') || document.querySelector('nav');
    
    // Variables para el scroll
    let lastScrollTop = 0;
    let isScrolling = false;

    // Función para manejar el scroll del navbar
    function handleNavbarScroll() {
        const currentScroll = window.pageYOffset || document.documentElement.scrollTop;
        
        // Si estamos en la parte superior de la página, siempre mostrar el navbar
        if (currentScroll <= 50) {
            navbar.classList.remove('navbar-hidden');
            navbar.classList.add('navbar-visible');
            return;
        }
        
        // Si scrolleamos hacia abajo más de 50px, ocultar navbar
        if (currentScroll > lastScrollTop && currentScroll > 100) {
            navbar.classList.add('navbar-hidden');
            navbar.classList.remove('navbar-visible');
            // Cerrar menú móvil si está abierto
            if (!mobileMenu.classList.contains('hidden')) {
                mobileMenu.classList.add('hidden');
                resetMenuIcon();
            }
        } 
        // Si scrolleamos hacia arriba, mostrar navbar
        else if (currentScroll < lastScrollTop) {
            navbar.classList.remove('navbar-hidden');
            navbar.classList.add('navbar-visible');
        }
        
        lastScrollTop = currentScroll <= 0 ? 0 : currentScroll;
    }

    // Función para resetear el ícono del menú
    function resetMenuIcon() {
        menuLines[0].style.transform = 'rotate(0) translate(0, 0)';
        menuLines[1].style.opacity = '1';
        menuLines[2].style.transform = 'rotate(0) translate(0, 0)';
    }

    // Event listener para el scroll con throttling
    window.addEventListener('scroll', function() {
        if (!isScrolling) {
            window.requestAnimationFrame(function() {
                handleNavbarScroll();
                isScrolling = false;
            });
            isScrolling = true;
        }
    });

    mobileMenuBtn.addEventListener('click', function() {
        mobileMenu.classList.toggle('hidden');
        
        // Animación del botón hamburguesa
        if (!mobileMenu.classList.contains('hidden')) {
            menuLines[0].style.transform = 'rotate(45deg) translate(5px, 5px)';
            menuLines[1].style.opacity = '0';
            menuLines[2].style.transform = 'rotate(-45deg) translate(7px, -6px)';
        } else {
            resetMenuIcon();
        }
    });

    // Cerrar menú al hacer clic en un enlace
    const mobileLinks = mobileMenu.querySelectorAll('a');
    mobileLinks.forEach(link => {
        link.addEventListener('click', function() {
            mobileMenu.classList.add('hidden');
            resetMenuIcon();
        });
    });

    // Cerrar menú móvil al hacer clic fuera de él
    document.addEventListener('click', function(event) {
        const isClickInsideMenu = mobileMenu.contains(event.target);
        const isClickOnButton = mobileMenuBtn.contains(event.target);
        
        if (!isClickInsideMenu && !isClickOnButton && !mobileMenu.classList.contains('hidden')) {
            mobileMenu.classList.add('hidden');
            resetMenuIcon();
        }
    });
});