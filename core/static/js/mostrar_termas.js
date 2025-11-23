// Funciones para manejar modales
function toggleModal(modalId) {
  const modal = document.getElementById(modalId);
  modal.classList.toggle("hidden");
}

function openLoginModal() {
  const modal = document.getElementById("loginModal");
  const content = document.getElementById("loginModalContent");
  modal.classList.remove("hidden");
  setTimeout(() => {
    content.classList.remove("scale-95", "opacity-0");
    content.classList.add("scale-100", "opacity-100");
  }, 10);
}

function closeLoginModal() {
  const modal = document.getElementById("loginModal");
  const content = document.getElementById("loginModalContent");
  content.classList.remove("scale-100", "opacity-100");
  content.classList.add("scale-95", "opacity-0");
  setTimeout(() => {
    modal.classList.add("hidden");
  }, 300);
}

function openRegisterModal() {
  const modal = document.getElementById("registerModal");
  const content = document.getElementById("registerModalContent");
  modal.classList.remove("hidden");
  setTimeout(() => {
    content.classList.remove("scale-95", "opacity-0");
    content.classList.add("scale-100", "opacity-100");
  }, 10);
}

function closeRegisterModal() {
  const modal = document.getElementById("registerModal");
  const content = document.getElementById("registerModalContent");
  content.classList.remove("scale-100", "opacity-100");
  content.classList.add("scale-95", "opacity-0");
  setTimeout(() => {
    modal.classList.add("hidden");
  }, 300);
}

// Función para limpiar filtros
function limpiarFiltros() {
  // Obtener el formulario
  const form = document.querySelector("form");
  if (form) {
    // Limpiar todos los campos del formulario
    const inputs = form.querySelectorAll("input, select");
    inputs.forEach((input) => {
      if (input.type === "text" || input.type === "search") {
        input.value = "";
      } else if (input.tagName === "SELECT") {
        input.selectedIndex = 0;
      }
    });

    // Redirigir a la página sin parámetros
    window.location.href = form.action;
  }
}

// Funciones para manejar filtros dinámicos
function cargarComunasPorRegion(regionNombre) {
  const comunaSelect = document.querySelector('select[name="comuna"]');
  if (!comunaSelect) return;

  // Mostrar estado de carga
  comunaSelect.innerHTML = '<option value="">Cargando comunas...</option>';
  comunaSelect.disabled = true;

  if (!regionNombre) {
    comunaSelect.innerHTML = '<option value="">Comuna</option>';
    comunaSelect.disabled = false;
    return;
  }

  // Hacer petición para obtener comunas
  fetch(`/api/comunas-por-region/?region=${encodeURIComponent(regionNombre)}`)
    .then((response) => {
      if (!response.ok) {
        throw new Error("Error en la respuesta del servidor");
      }
      return response.json();
    })
    .then((data) => {
      comunaSelect.innerHTML = '<option value="">Comuna</option>';

      if (data.comunas && data.comunas.length > 0) {
        data.comunas.forEach((comuna) => {
          const option = document.createElement("option");
          option.value = comuna;
          option.textContent = comuna;
          comunaSelect.appendChild(option);
        });
      } else {
        const option = document.createElement("option");
        option.value = "";
        option.textContent = "No hay comunas disponibles";
        option.disabled = true;
        comunaSelect.appendChild(option);
      }

      comunaSelect.disabled = false;
    })
    .catch((error) => {
      console.error("Error al cargar comunas:", error);
      comunaSelect.innerHTML =
        '<option value="">Error al cargar comunas</option>';
      comunaSelect.disabled = false;
    });
}

// Cerrar modal al hacer clic fuera
window.onclick = function (event) {
  const loginModal = document.getElementById("loginModal");
  const registerModal = document.getElementById("registerModal");

  if (event.target === loginModal) {
    closeLoginModal();
  }
  if (event.target === registerModal) {
    closeRegisterModal();
  }
};

// Cerrar modales con la tecla Escape
document.addEventListener("keydown", function (event) {
  if (event.key === "Escape") {
    closeLoginModal();
    closeRegisterModal();
  }
});

// Inicializar funcionalidades cuando se carga la página
document.addEventListener("DOMContentLoaded", function () {
  // Configurar el selector de región para cargar comunas dinámicamente
  const regionSelect = document.querySelector('select[name="region"]');
  if (regionSelect) {
    regionSelect.addEventListener("change", function () {
      cargarComunasPorRegion(this.value);
    });
  }

  // Configurar botón de limpiar filtros
  const limpiarBtn = document.querySelector(".limpiar-filtros");
  if (limpiarBtn) {
    limpiarBtn.addEventListener("click", function (e) {
      e.preventDefault();
      limpiarFiltros();
    });
  }

  // Mejorar UX del formulario de búsqueda
  const searchForm = document.querySelector("form");
  if (searchForm) {
    // Agregar indicador de carga al enviar
    searchForm.addEventListener("submit", function () {
      const submitButton = this.querySelector('button[type="submit"]');
      if (submitButton) {
        const originalText = submitButton.textContent;
        submitButton.textContent = "Buscando...";
        submitButton.disabled = true;

        // Restaurar después de un tiempo (por si hay errores)
        setTimeout(() => {
          submitButton.textContent = originalText;
          submitButton.disabled = false;
        }, 5000);
      }
    });
  }

  // Auto-focus en el campo de búsqueda si está vacío
  const nombreInput = document.querySelector('input[name="nombre"]');
  if (nombreInput && !nombreInput.value.trim()) {
    // Solo hacer focus si no hay otros filtros aplicados
    const hasFilters =
      window.location.search.includes("region=") ||
      window.location.search.includes("comuna=") ||
      window.location.search.includes("precio=") ||
      window.location.search.includes("calificacion=");

    if (!hasFilters) {
      nombreInput.focus();
    }
  }
});
