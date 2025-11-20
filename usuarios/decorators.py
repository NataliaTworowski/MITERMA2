"""
CENTRALIZA LA LOGICA D ELOS PERMISOS Y ROLES
Decoradores de autenticación y autorización seguros para MiTerma.
Estos decoradores reemplazan el sistema de sesiones manuales por Django Auth.
"""

from functools import wraps
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.shortcuts import redirect
from django.contrib import messages
from django.http import HttpResponseForbidden
import logging

# Configurar logger de seguridad
logger = logging.getLogger('security')
Usuario = get_user_model()


def role_required(allowed_roles):
    """
    Decorador que verifica que el usuario tenga uno de los roles permitidos.
    
    Args:
        allowed_roles (list): Lista de nombres de roles permitidos
        
    Usage:
        @role_required(['administrador_terma', 'administrador_general'])
        def mi_vista(request):
            pass
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped_view(request, *args, **kwargs):
            user = request.user
            
            # Verificar que el usuario tenga un rol asignado
            if not hasattr(user, 'rol') or not user.rol:
                logger.warning(f"Usuario {user.email} sin rol intentó acceder a {request.path}")
                messages.error(request, 'Tu cuenta no tiene un rol asignado. Contacta al administrador.')
                return redirect('core:home')
            
            # Verificar que el rol esté en la lista de permitidos
            if user.rol.nombre not in allowed_roles:
                logger.warning(f"Usuario {user.email} con rol {user.rol.nombre} intentó acceder a {request.path}")
                messages.error(request, 'No tienes permisos para acceder a esta página.')
                return redirect('core:home')
            
            # Log de acceso exitoso
            logger.info(f"Acceso autorizado: {user.email} ({user.rol.nombre}) a {request.path}")
            
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


def admin_terma_required(view_func):
    """
    Decorador específico para administradores de terma.
    Verifica que el usuario sea admin de terma Y tenga una terma asignada.
    """
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        user = request.user
        
        # IMPORTANTE: Limpiar cualquier variable de terma inactiva anterior
        if hasattr(request, '_terma_inactiva'):
            delattr(request, '_terma_inactiva')
        
        # Verificar rol de administrador de terma
        if not hasattr(user, 'rol') or user.rol.nombre != 'administrador_terma':
            logger.warning(f"Usuario {user.email} sin rol admin_terma intentó acceder a {request.path}")
            messages.error(request, 'Debes ser administrador de terma para acceder a esta página.')
            return redirect('core:home')
        
        # Verificar que tenga una terma asignada
        if not user.terma:
            logger.warning(f"Admin terma {user.email} sin terma asignada intentó acceder a {request.path}")
            messages.error(request, 'No tienes una terma asignada. Contacta al administrador.')
            return redirect('core:home')
        
        # Verificar que la terma esté activa (permitir acceso pero marcar estado)
        if user.terma.estado_suscripcion != 'activa':
            logger.warning(f"Admin terma {user.email} con terma inactiva accedió a {request.path}")
            # En lugar de redirigir, agregar información al request para que la vista la maneje
            request._terma_inactiva = True
        else:
            request._terma_inactiva = False
        
        logger.info(f"Acceso autorizado admin terma: {user.email} para terma {user.terma.nombre_terma}")
        return view_func(request, *args, **kwargs)
    
    return _wrapped_view


def terma_owner_required(view_func):
    """
    Decorador que verifica que el usuario sea propietario de la terma específica.
    Útil para vistas que reciben terma_id como parámetro.
    """
    @wraps(view_func)
    @admin_terma_required
    def _wrapped_view(request, *args, **kwargs):
        user = request.user
        
        # Obtener terma_id de los argumentos de la URL
        terma_id = kwargs.get('terma_id') or kwargs.get('pk')
        
        if terma_id:
            # Verificar que la terma del usuario coincida con la solicitada
            if str(user.terma.id) != str(terma_id):
                logger.warning(f"Admin terma {user.email} intentó acceder a terma {terma_id} no autorizada")
                messages.error(request, 'No tienes permisos para administrar esta terma.')
                return HttpResponseForbidden("No autorizado")
        
        return view_func(request, *args, **kwargs)
    
    return _wrapped_view


def admin_general_required(view_func):
    """
    Decorador específico para administradores generales del sistema.
    """
    @wraps(view_func)
    @role_required(['administrador_general'])
    def _wrapped_view(request, *args, **kwargs):
        return view_func(request, *args, **kwargs)
    
    return _wrapped_view


def cliente_required(view_func):
    """
    Decorador específico para usuarios clientes.
    """
    @wraps(view_func)
    @role_required(['cliente'])
    def _wrapped_view(request, *args, **kwargs):
        return view_func(request, *args, **kwargs)
    
    return _wrapped_view


def empleado_required(view_func):
    """
    Decorador específico para empleados/trabajadores.
    """
    @wraps(view_func)
    @role_required(['trabajador'])
    def _wrapped_view(request, *args, **kwargs):
        return view_func(request, *args, **kwargs)
    
    return _wrapped_view


def any_authenticated_required(view_func):
    """
    Decorador que permite acceso a cualquier usuario autenticado,
    pero registra el acceso para auditoría.
    """
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        user = request.user
        logger.info(f"Acceso autenticado: {user.email} a {request.path}")
        return view_func(request, *args, **kwargs)
    
    return _wrapped_view


# Decorador de conveniencia para múltiples roles
def multiple_roles_required(*roles):
    """
    Decorador de conveniencia para especificar múltiples roles.
    
    Usage:
        @multiple_roles_required('administrador_terma', 'administrador_general')
        def mi_vista(request):
            pass
    """
    return role_required(list(roles))


# Funciones helper para verificaciones en templates y vistas
def user_has_role(user, role_name):
    """
    Función helper para verificar si un usuario tiene un rol específico.
    """
    if not user or not user.is_authenticated:
        return False
    
    if not hasattr(user, 'rol') or not user.rol:
        return False
    
    return user.rol.nombre == role_name


def user_can_access_terma(user, terma_id):
    """
    Función helper para verificar si un usuario puede acceder a una terma específica.
    """
    if not user or not user.is_authenticated:
        return False
    
    if user_has_role(user, 'administrador_general'):
        return True  # Admin general puede acceder a todas
    
    if user_has_role(user, 'administrador_terma'):
        return user.terma and str(user.terma.id) == str(terma_id)
    
    return False


def get_user_accessible_termas(user):
    """
    Función helper que retorna las termas a las que el usuario tiene acceso.
    """
    from termas.models import Terma
    
    if not user or not user.is_authenticated:
        return Terma.objects.none()
    
    if user_has_role(user, 'administrador_general'):
        return Terma.objects.all()
    
    if user_has_role(user, 'administrador_terma') and user.terma:
        return Terma.objects.filter(id=user.terma.id)
    
    return Terma.objects.none()