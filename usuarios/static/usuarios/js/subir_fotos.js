// Preview de imagen
function previewImage(input) {
    const preview = document.getElementById('imagePreview');
    const previewImg = document.getElementById('preview');
    
    if (input.files && input.files[0]) {
        const reader = new FileReader();
        
        reader.onload = function(e) {
            previewImg.src = e.target.result;
            preview.classList.remove('hidden');
        }
        
        reader.readAsDataURL(input.files[0]);
    }
}

// Modal para ver fotos
function openModal(src, description) {
    const modal = document.getElementById('photoModal');
    const modalImage = document.getElementById('modalImage');
    const modalDescription = document.getElementById('modalDescription');
    const descContainer = document.getElementById('modalDescriptionContainer');
    
    modalImage.src = src;
    modalDescription.textContent = description || 'Sin descripción';
    
    // Mostrar/ocultar contenedor de descripción según si hay descripción
    if (description && description.trim() !== '' && description !== 'Sin descripción') {
        descContainer.classList.remove('hidden');
    } else {
        descContainer.classList.add('hidden');
    }
    
    modal.classList.remove('hidden');
    document.body.style.overflow = 'hidden'; // Prevenir scroll
}

// Modal usando data attributes
function openModalData(button) {
    const src = button.getAttribute('data-url');
    const description = button.getAttribute('data-desc');
    openModal(src, description);
}

function closeModal() {
    const modal = document.getElementById('photoModal');
    modal.classList.add('hidden');
    document.body.style.overflow = 'auto'; // Restaurar scroll
}

// Cerrar modal con ESC
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        const modal = document.getElementById('photoModal');
        if (!modal.classList.contains('hidden')) {
            closeModal();
        }
    }
});

// Drag and drop - Ejecutar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', function() {
    const dropZone = document.querySelector('label[for="foto"]').parentElement;
    
    if (dropZone) {
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, preventDefaults, false);
        });

        ['dragenter', 'dragover'].forEach(eventName => {
            dropZone.addEventListener(eventName, highlight, false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, unhighlight, false);
        });

        dropZone.addEventListener('drop', handleDrop, false);
    }
});

function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
}

function highlight(e) {
    const dropZone = document.querySelector('label[for="foto"]').parentElement;
    dropZone.classList.add('border-blue-400');
}

function unhighlight(e) {
    const dropZone = document.querySelector('label[for="foto"]').parentElement;
    dropZone.classList.remove('border-blue-400');
}

function handleDrop(e) {
    const dt = e.dataTransfer;
    const files = dt.files;
    
    const fotoInput = document.getElementById('foto');
    if (fotoInput) {
        fotoInput.files = files;
        previewImage(fotoInput);
    }
}
