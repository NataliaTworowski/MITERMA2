// Script para el comportamiento del navbar
document.addEventListener('DOMContentLoaded', function() {
    const navbar = document.getElementById('navbar');
    let lastScrollY = window.scrollY;
    let isNavbarVisible = true;
    
    function updateNavbar() {
        const currentScrollY = window.scrollY;
        
        // Si estamos en la parte superior de la página, siempre mostrar el navbar
        if (currentScrollY === 0) {
            navbar.style.transform = 'translateY(0)';
            isNavbarVisible = true;
            return;
        }
        
        // Si el scroll hacia abajo es mayor que 10px, ocultar navbar
        if (currentScrollY > lastScrollY && currentScrollY > 10) {
            // Scrolling hacia abajo - ocultar navbar
            if (isNavbarVisible) {
                navbar.style.transform = 'translateY(-100%)';
                isNavbarVisible = false;
            }
        } else if (currentScrollY < lastScrollY) {
            // Scrolling hacia arriba - mostrar navbar
            if (!isNavbarVisible) {
                navbar.style.transform = 'translateY(0)';
                isNavbarVisible = true;
            }
        }
        
        lastScrollY = currentScrollY;
    }
    
    // Throttle function para optimizar performance
    let ticking = false;
    function requestTick() {
        if (!ticking) {
            requestAnimationFrame(updateNavbar);
            ticking = true;
            setTimeout(() => { ticking = false; }, 10);
        }
    }
    
    // Event listener para el scroll
    window.addEventListener('scroll', requestTick, { passive: true });
});

// Funciones para el modal de login
function openLoginModal() {
    const modal = document.getElementById('loginModal');
    const modalContent = document.getElementById('loginModalContent');
    
    modal.classList.remove('hidden');
    
    // Animación de entrada
    setTimeout(() => {
        modalContent.classList.remove('scale-95', 'opacity-0');
        modalContent.classList.add('scale-100', 'opacity-100');
    }, 10);
    
    // Prevenir scroll del body
    document.body.style.overflow = 'hidden';
}

function closeLoginModal() {
    const modal = document.getElementById('loginModal');
    const modalContent = document.getElementById('loginModalContent');
    
    // Animación de salida
    modalContent.classList.remove('scale-100', 'opacity-100');
    modalContent.classList.add('scale-95', 'opacity-0');
    
    setTimeout(() => {
        modal.classList.add('hidden');
        document.body.style.overflow = 'auto';
    }, 300);
}

function togglePassword() {
    const passwordInput = document.getElementById('password');
    const eyeIcon = document.getElementById('eyeIcon');
    
    if (passwordInput.type === 'password') {
        passwordInput.type = 'text';
        eyeIcon.innerHTML = `
            <path d="M3.707 2.293a1 1 0 00-1.414 1.414l14 14a1 1 0 001.414-1.414l-1.473-1.473A10.014 10.014 0 0019.542 10C18.268 5.943 14.478 3 10 3a9.958 9.958 0 00-4.512 1.074l-1.78-1.781zm4.261 4.26l1.514 1.515a2.003 2.003 0 012.45 2.45l1.514 1.514a4 4 0 00-5.478-5.478z"></path>
            <path d="M12.454 16.697L9.75 13.992a4 4 0 01-3.742-3.741L2.335 6.578A9.98 9.98 0 00.458 10c1.274 4.057 5.065 7 9.542 7 .847 0 1.669-.105 2.454-.303z"></path>
        `;
    } else {
        passwordInput.type = 'password';
        eyeIcon.innerHTML = `
            <path d="M10 12a2 2 0 100-4 2 2 0 000 4z"></path>
            <path fill-rule="evenodd" d="M.458 10C1.732 5.943 5.522 3 10 3s8.268 2.943 9.542 7c-1.274 4.057-5.064 7-9.542 7S1.732 14.057.458 10zM14 10a4 4 0 11-8 0 4 4 0 018 0z" clip-rule="evenodd"></path>
        `;
    }
}

// Funciones para el modal de registro
function openRegisterModal() {
    const modal = document.getElementById('registerModal');
    const modalContent = document.getElementById('registerModalContent');
    
    modal.classList.remove('hidden');
    
    // Animación de entrada
    setTimeout(() => {
        modalContent.classList.remove('scale-95', 'opacity-0');
        modalContent.classList.add('scale-100', 'opacity-100');
    }, 10);
    
    // Prevenir scroll del body
    document.body.style.overflow = 'hidden';
}

function closeRegisterModal() {
    const modal = document.getElementById('registerModal');
    const modalContent = document.getElementById('registerModalContent');
    
    // Animación de salida
    modalContent.classList.remove('scale-100', 'opacity-100');
    modalContent.classList.add('scale-95', 'opacity-0');
    
    setTimeout(() => {
        modal.classList.add('hidden');
        document.body.style.overflow = 'auto';
    }, 300);
}

function toggleRegisterPassword() {
    const passwordInput = document.getElementById('register_password');
    const eyeIcon = document.getElementById('registerEyeIcon');
    
    if (passwordInput.type === 'password') {
        passwordInput.type = 'text';
        eyeIcon.innerHTML = `
            <path d="M3.707 2.293a1 1 0 00-1.414 1.414l14 14a1 1 0 001.414-1.414l-1.473-1.473A10.014 10.014 0 0019.542 10C18.268 5.943 14.478 3 10 3a9.958 9.958 0 00-4.512 1.074l-1.78-1.781zm4.261 4.26l1.514 1.515a2.003 2.003 0 012.45 2.45l1.514 1.514a4 4 0 00-5.478-5.478z"></path>
            <path d="M12.454 16.697L9.75 13.992a4 4 0 01-3.742-3.741L2.335 6.578A9.98 9.98 0 00.458 10c1.274 4.057 5.065 7 9.542 7 .847 0 1.669-.105 2.454-.303z"></path>
        `;
    } else {
        passwordInput.type = 'password';
        eyeIcon.innerHTML = `
            <path d="M10 12a2 2 0 100-4 2 2 0 000 4z"></path>
            <path fill-rule="evenodd" d="M.458 10C1.732 5.943 5.522 3 10 3s8.268 2.943 9.542 7c-1.274 4.057-5.064 7-9.542 7S1.732 14.057.458 10zM14 10a4 4 0 11-8 0 4 4 0 018 0z" clip-rule="evenodd"></path>
        `;
    }
}

// Validación de contraseñas coincidentes
document.addEventListener('DOMContentLoaded', function() {
    const passwordInput = document.getElementById('register_password');
    const confirmPasswordInput = document.getElementById('register_password_confirm');
    
    function validatePasswords() {
        if (confirmPasswordInput && passwordInput) {
            if (confirmPasswordInput.value && passwordInput.value !== confirmPasswordInput.value) {
                confirmPasswordInput.setCustomValidity('Las contraseñas no coinciden');
            } else {
                confirmPasswordInput.setCustomValidity('');
            }
        }
    }
    
    if (passwordInput && confirmPasswordInput) {
        passwordInput.addEventListener('input', validatePasswords);
        confirmPasswordInput.addEventListener('input', validatePasswords);
    }
});

// Cerrar modales al hacer clic fuera
document.addEventListener('click', function(e) {
    const loginModal = document.getElementById('loginModal');
    const registerModal = document.getElementById('registerModal');
    
    if (e.target === loginModal) {
        closeLoginModal();
    }
    if (e.target === registerModal) {
        closeRegisterModal();
    }
});

// Cerrar modales con tecla Escape
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        closeLoginModal();
        closeRegisterModal();
    }
});

// Funciones utilitarias globales
function showAlert(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    const container = document.querySelector('main .container');
    if (container) {
        container.insertBefore(alertDiv, container.firstChild);
    }
}

// Función para confirmar acciones
function confirmAction(message, callback) {
    if (confirm(message)) {
        callback();
    }
}

// Auto-cerrar mensajes después de 5 segundos
document.addEventListener('DOMContentLoaded', function() {
    const messages = document.querySelectorAll('.alert');
    messages.forEach(function(message) {
        setTimeout(function() {
            if (message && message.parentElement) {
                message.style.opacity = '0';
                message.style.transform = 'translateX(100%)';
                setTimeout(function() {
                    if (message.parentElement) {
                        message.remove();
                    }
                }, 300);
            }
        }, 5000); // 5 segundos
    });
});