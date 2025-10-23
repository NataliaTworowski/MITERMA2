document.addEventListener('DOMContentLoaded', function() {
    var toggleBtn = document.getElementById('toggleServicioForm');
    var servicioForm = document.getElementById('servicioForm');
    var cancelBtn = document.getElementById('cancelServicioForm');

    if (toggleBtn && servicioForm) {
        toggleBtn.addEventListener('click', function() {
            servicioForm.classList.toggle('hidden');
        });
    }
    if (cancelBtn && servicioForm) {
        cancelBtn.addEventListener('click', function() {
            servicioForm.classList.add('hidden');
        });
    }
});