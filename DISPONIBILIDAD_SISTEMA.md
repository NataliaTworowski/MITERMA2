# Sistema de Control de Disponibilidad de Entradas

## Descripción General

Este sistema implementa un control completo de disponibilidad de entradas por día para las termas, evitando la sobreventa y mejorando la experiencia del usuario.

## Funcionalidades Implementadas

### 1. Filtrado Automático de Termas
- **Ubicación**: `usuarios/views.py` (inicio_cliente), `core/views.py` (mostrar_termas, home)
- **Funcionalidad**: Solo muestra termas que tienen disponibilidad para el día actual
- **Impacto**: Los clientes solo ven termas donde realmente pueden comprar entradas

### 2. Validación en Proceso de Compra
- **Ubicación**: `ventas/views.py` (función pago)
- **Funcionalidad**: Valida disponibilidad antes de crear la compra
- **Impacto**: Previene sobreventa y muestra mensajes claros de error

### 3. Utilidades de Disponibilidad
- **Archivo**: `ventas/disponibilidad_utils.py`
- **Funciones principales**:
  - `calcular_disponibilidad_terma(terma_id, fecha)`: Calcula disponibilidad actual
  - `validar_cantidad_disponible(terma_id, cantidad, fecha)`: Valida si se puede vender cantidad específica
  - `obtener_termas_con_disponibilidad(fecha)`: Lista termas con disponibilidad
  - `limpiar_compras_pendientes_vencidas()`: Libera cupos de compras vencidas

### 4. APIs REST para Disponibilidad
- **Archivo**: `ventas/api_disponibilidad.py`
- **Endpoints**:
  - `GET /ventas/api/disponibilidad/`: Verificar disponibilidad de una terma
  - `GET /ventas/api/termas-disponibles/`: Lista de termas disponibles
  - `POST /ventas/api/limpiar-compras-vencidas/`: Limpiar compras vencidas (admin)
  - `GET /ventas/api/estadisticas-disponibilidad/`: Estadísticas del sistema

### 5. Template Tags Personalizados
- **Archivo**: `core/templatetags/disponibilidad_tags.py`
- **Tags disponibles**:
  - `{{ terma.id|disponibilidad_terma }}`: Información de disponibilidad
  - `{{ terma.id|puede_vender_cantidad:2 }}`: Verificar cantidad específica
  - `{% disponibilidad_detallada terma.id %}`: Disponibilidad detallada
  - `{% mensaje_disponibilidad terma.id 2 %}`: Mensaje descriptivo
  - `{% badge_disponibilidad terma.id %}`: Badge visual de disponibilidad

### 6. Comando de Gestión
- **Archivo**: `ventas/management/commands/limpiar_compras_vencidas.py`
- **Uso**: `python manage.py limpiar_compras_vencidas [--horas 2] [--dry-run]`
- **Funcionalidad**: Limpia compras pendientes vencidas automáticamente

## Ejemplos de Uso

### En Templates
```html
<!-- Cargar los template tags -->
{% load disponibilidad_tags %}

<!-- Mostrar badge de disponibilidad -->
{% badge_disponibilidad terma.id %}

<!-- Verificar si puede vender cantidad específica -->
{% if terma.id|puede_vender_cantidad:2 %}
    <button>Comprar 2 entradas</button>
{% else %}
    <span>No hay suficientes entradas disponibles</span>
{% endif %}

<!-- Mensaje descriptivo -->
<p>{% mensaje_disponibilidad terma.id 1 %}</p>
```

### En Python (Views)
```python
from ventas.disponibilidad_utils import calcular_disponibilidad_terma, validar_cantidad_disponible
from datetime import date

# Verificar disponibilidad de una terma
disponibilidad = calcular_disponibilidad_terma(terma_id=1, fecha=date.today())
print(f"Puede vender: {disponibilidad['puede_vender']}")
print(f"Disponibles: {disponibilidad['disponibles']}")

# Validar cantidad específica
validacion = validar_cantidad_disponible(terma_id=1, cantidad_solicitada=3)
if validacion['es_valida']:
    print("Puede proceder con la compra")
else:
    print(f"Error: {validacion['mensaje']}")
```

### API Calls (JavaScript)
```javascript
// Verificar disponibilidad
fetch('/ventas/api/disponibilidad/?terma_id=1&cantidad=2&fecha=2024-01-15')
    .then(response => response.json())
    .then(data => {
        if (data.puede_proceder) {
            console.log('Puede comprar');
        } else {
            console.log('No disponible:', data.validacion.mensaje);
        }
    });

// Obtener termas disponibles
fetch('/ventas/api/termas-disponibles/?fecha=2024-01-15')
    .then(response => response.json())
    .then(data => {
        console.log(`${data.total_termas} termas disponibles`);
        data.termas.forEach(terma => {
            console.log(`${terma.nombre_terma}: ${terma.disponibilidad.disponibles} entradas`);
        });
    });
```

### Comando de Terminal
```bash
# Limpiar compras vencidas (modo prueba)
python manage.py limpiar_compras_vencidas --dry-run

# Limpiar compras vencidas de más de 2 horas
python manage.py limpiar_compras_vencidas --horas 2

# Ver ayuda
python manage.py limpiar_compras_vencidas --help
```

## Configuración Requerida

### 1. Campo en Modelo Terma
Asegúrate de que el modelo `Terma` tenga el campo `limite_ventas_diario`:
```python
limite_ventas_diario = models.PositiveIntegerField(
    null=True, blank=True,
    help_text="Límite máximo de entradas que se pueden vender por día (0 o vacío = sin límite)"
)
```

### 2. Estados de Compra
El sistema usa estos estados en el modelo `Compra`:
- `pendiente`: Compra iniciada pero no pagada
- `pagado`: Compra completada
- `cancelado_timeout`: Compra cancelada por vencimiento automático

### 3. Registro de Template Tags
En los templates que usen los tags, agregar:
```html
{% load disponibilidad_tags %}
```

## Beneficios del Sistema

1. **Previene Sobreventa**: No permite vender más entradas del límite diario
2. **Mejora UX**: Los clientes solo ven opciones realmente disponibles
3. **Automatización**: Limpia automáticamente compras vencidas
4. **APIs Flexibles**: Permite verificación en tiempo real desde frontend
5. **Feedback Visual**: Badges y mensajes claros sobre disponibilidad
6. **Administración**: Herramientas para monitorear y gestionar el sistema

## Flujo de Funcionamiento

1. **Cliente busca termas**: Sistema filtra automáticamente por disponibilidad
2. **Cliente inicia compra**: Sistema valida disponibilidad antes de proceder
3. **Compra pendiente**: Se reservan temporalmente los cupos
4. **Compra completada**: Se confirma la reducción de disponibilidad
5. **Limpieza automática**: Compras vencidas liberan cupos automáticamente

Este sistema asegura una gestión eficiente y confiable de la disponibilidad de entradas para todas las termas de la plataforma.