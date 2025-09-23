
document.addEventListener('DOMContentLoaded', function() {
    console.log('Core app cargada');
    
    // Animaciones para las tarjetas
    const cards = document.querySelectorAll('.card');
    cards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.boxShadow = '0 8px 16px rgba(0,0,0,0.2)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.boxShadow = '0 2px 4px rgba(0,0,0,0.1)';
        });
    });
});