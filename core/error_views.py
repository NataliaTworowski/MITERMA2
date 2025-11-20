"""
Vistas personalizadas para manejo de errores.
"""
from django.shortcuts import render
from django.http import HttpResponseBadRequest, HttpResponseForbidden, HttpResponseNotFound, HttpResponseServerError


def error_400(request, exception=None):
    """Vista personalizada para errores 400 (Bad Request)"""
    return HttpResponseBadRequest(
        render(request, '400.html', {'exception': exception})
    )


def error_403(request, exception=None):
    """Vista personalizada para errores 403 (Forbidden)"""
    return HttpResponseForbidden(
        render(request, '403.html', {'exception': exception})
    )


def error_404(request, exception=None):
    """Vista personalizada para errores 404 (Not Found)"""
    return HttpResponseNotFound(
        render(request, '404.html', {'exception': exception})
    )


def error_500(request):
    """Vista personalizada para errores 500 (Internal Server Error)"""
    return HttpResponseServerError(
        render(request, '500.html')
    )


def custom_error_page(request, error_type='generic', message=None, status_code=400):
    """
    Vista genérica para mostrar páginas de error personalizadas programáticamente.
    
    Args:
        request: HttpRequest
        error_type: Tipo de error ('validation', 'permission', 'not_found', 'server', 'generic')
        message: Mensaje personalizado de error
        status_code: Código de estado HTTP
    """
    
    error_configs = {
        'validation': {
            'title': 'Error de Validación',
            'icon': 'exclamation',
            'color': 'yellow',
            'default_message': 'Los datos enviados no son válidos. Por favor, revisa la información e intenta nuevamente.'
        },
        'permission': {
            'title': 'Sin Permisos',
            'icon': 'lock',
            'color': 'red',
            'default_message': 'No tienes permisos para realizar esta acción.'
        },
        'not_found': {
            'title': 'No Encontrado',
            'icon': 'search',
            'color': 'yellow',
            'default_message': 'El recurso que buscas no existe o ha sido eliminado.'
        },
        'server': {
            'title': 'Error del Servidor',
            'icon': 'warning',
            'color': 'red',
            'default_message': 'Ocurrió un error interno. Estamos trabajando para solucionarlo.'
        },
        'generic': {
            'title': 'Error',
            'icon': 'warning',
            'color': 'red',
            'default_message': 'Ocurrió un error inesperado. Por favor, intenta nuevamente.'
        }
    }
    
    config = error_configs.get(error_type, error_configs['generic'])
    
    context = {
        'error_title': config['title'],
        'error_icon': config['icon'],
        'error_color': config['color'],
        'error_message': message or config['default_message'],
        'status_code': status_code
    }
    
    response = render(request, 'error_custom.html', context)
    response.status_code = status_code
    return response