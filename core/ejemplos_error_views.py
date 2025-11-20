"""
Ejemplo de uso de las vistas de error personalizadas.

Puedes usar estas vistas en cualquier lugar de tu aplicación
para mostrar errores de forma consistente y profesional.
"""

# Ejemplo 1: En una vista cuando falta un parámetro
def mi_vista(request):
    if not request.GET.get('parametro_requerido'):
        from core.error_views import custom_error_page
        return custom_error_page(
            request,
            error_type='validation',
            message='El parámetro requerido no fue proporcionado.',
            status_code=400
        )
    # ... resto de la vista

# Ejemplo 2: Cuando un usuario no tiene permisos
def vista_restringida(request):
    if not request.user.has_perm('mi_permiso'):
        from core.error_views import custom_error_page
        return custom_error_page(
            request,
            error_type='permission',
            message='No tienes permisos para acceder a esta sección.',
            status_code=403
        )
    # ... resto de la vista

# Ejemplo 3: Cuando un recurso no existe
def vista_detalle(request, id):
    try:
        objeto = MiModelo.objects.get(id=id)
    except MiModelo.DoesNotExist:
        from core.error_views import custom_error_page
        return custom_error_page(
            request,
            error_type='not_found',
            message=f'El objeto con ID {id} no existe.',
            status_code=404
        )
    # ... resto de la vista

# Ejemplo 4: Error genérico
def vista_con_procesamiento(request):
    try:
        # Algún procesamiento que puede fallar
        resultado = procesar_datos()
    except Exception as e:
        from core.error_views import custom_error_page
        return custom_error_page(
            request,
            error_type='server',
            message='Error al procesar los datos. Por favor, intenta más tarde.',
            status_code=500
        )
    # ... resto de la vista