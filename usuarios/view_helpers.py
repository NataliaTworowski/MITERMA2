"""
Decorador y funciones helper para limpieza manual de cache en vistas.
"""

from functools import wraps
from .cache_utils import clear_user_cache, clear_all_auth_cache
from django.contrib import messages
import logging

logger = logging.getLogger('cache')

def clear_cache_after_user_modification(view_func):
    """
    Decorador que limpia el cache después de modificar usuarios.
    Usar en vistas que modifican estado, rol o terma de usuarios.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        response = view_func(request, *args, **kwargs)
        
        # Si hay un parámetro de usuario en kwargs o args, limpiar su cache
        user_id = kwargs.get('user_id') or kwargs.get('pk')
        if user_id:
            try:
                from .models import Usuario
                usuario = Usuario.objects.get(pk=user_id)
                clear_user_cache(usuario)
                logger.info("Cache limpiado por modificación manual en vista")
            except Usuario.DoesNotExist:
                pass
        
        return response
    return wrapper


def manual_cache_clear_for_user(user_email_or_instance):
    """
    Función helper para limpiar cache manualmente en vistas.
    
    Usar así en tus vistas:
    ```python
    from usuarios.view_helpers import manual_cache_clear_for_user
    
    def activate_user_view(request, user_id):
        usuario = get_object_or_404(Usuario, pk=user_id)
        usuario.estado = True
        usuario.save()
        
        # Limpiar cache manualmente
        manual_cache_clear_for_user(usuario)
        
        return redirect('success')
    ```
    """
    clear_user_cache(user_email_or_instance)
    logger.info("Limpieza manual de cache ejecutada desde vista")


def manual_cache_clear_all():
    """
    Función helper para limpiar todo el cache manualmente.
    Usar solo cuando sea absolutamente necesario.
    """
    clear_all_auth_cache()
    logger.warning("Limpieza manual completa de cache ejecutada desde vista")


# Funciones específicas para operaciones comunes

def activate_user_and_clear_cache(usuario):
    """
    Activa un usuario y limpia su cache automáticamente.
    """
    usuario.estado = True
    usuario.is_active = True
    usuario.save()
    clear_user_cache(usuario)
    logger.info("Usuario activado y cache limpiado")


def deactivate_user_and_clear_cache(usuario):
    """
    Desactiva un usuario y limpia su cache automáticamente.
    """
    usuario.estado = False
    usuario.save()
    clear_user_cache(usuario)
    logger.info("Usuario desactivado y cache limpiado")


def change_user_role_and_clear_cache(usuario, nuevo_rol):
    """
    Cambia el rol de un usuario y limpia su cache automáticamente.
    """
    old_role = usuario.rol.nombre if usuario.rol else None
    usuario.rol = nuevo_rol
    usuario.save()
    clear_user_cache(usuario)
    logger.info(f"Rol de usuario cambiado de '{old_role}' a '{nuevo_rol.nombre}' y cache limpiado")


def assign_terma_and_clear_cache(usuario, terma):
    """
    Asigna una terma a un usuario y limpia su cache automáticamente.
    """
    old_terma = usuario.terma.nombre_terma if usuario.terma else None
    usuario.terma = terma
    usuario.save()
    clear_user_cache(usuario)
    logger.info(f"Terma de usuario cambiada de '{old_terma}' a '{terma.nombre_terma}' y cache limpiado")