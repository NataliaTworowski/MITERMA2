"""
Utilidades para manejo de cache de usuarios y autenticación.
Estas funciones aseguran que el cache se limpie automáticamente
cuando se modifican datos críticos para la autenticación.
"""

from django.core.cache import cache
import logging

logger = logging.getLogger('cache')

def clear_user_cache(usuario):
    """
    Limpia todo el cache relacionado con un usuario específico.
    
    Args:
        usuario: Instancia del modelo Usuario o email del usuario
    """
    if hasattr(usuario, 'email'):
        # Es una instancia de Usuario
        email = usuario.email
        user_id = usuario.id
    else:
        # Es un string con el email
        email = usuario
        user_id = None
    
    cache_keys = [
        f"user_email_{email}",
    ]
    
    if user_id:
        cache_keys.append(f"user_{user_id}")
    
    for key in cache_keys:
        result = cache.delete(key)
        if result:
            logger.info(f"Cache eliminado: {key}")
        else:
            logger.debug(f"Cache no existía: {key}")
    
    logger.info(f"Cache de usuario limpiado para: {email}")


def clear_terma_related_cache(terma):
    """
    Limpia el cache relacionado con una terma y sus usuarios.
    
    Args:
        terma: Instancia del modelo Terma
    """
    # Limpiar cache de todos los usuarios administradores de esta terma
    from usuarios.models import Usuario
    
    # Buscar usuarios que administran esta terma
    admins = Usuario.objects.filter(terma=terma, rol__nombre='administrador_terma')
    
    for admin in admins:
        clear_user_cache(admin)
    
    logger.info(f"Cache relacionado con terma '{terma.nombre_terma}' limpiado")


def clear_all_auth_cache():
    """
    Limpia todo el cache relacionado con autenticación.
    Usar solo cuando sea necesario un reset completo.
    """
    # Patrones de cache que queremos limpiar
    patterns = [
        'user_email_*',
        'user_*',
        'auth_attempts_*',
    ]
    
    # Django no soporta wildcards nativamente, así que limpiamos todo
    cache.clear()
    logger.warning("Cache completo limpiado - operación drástica realizada")


def clear_rate_limit_cache(email, ip=None):
    """
    Limpia el cache de rate limiting para un usuario específico.
    
    Args:
        email: Email del usuario
        ip: IP opcional para limpiar también
    """
    cache_keys = [
        f"auth_attempts_email_{email}",
    ]
    
    if ip:
        cache_keys.append(f"auth_attempts_ip_{ip}")
    
    for key in cache_keys:
        cache.delete(key)
        logger.info(f"Rate limit cache eliminado: {key}")


def auto_clear_cache_on_user_change(sender, instance, **kwargs):
    """
    Signal handler para limpiar cache automáticamente cuando un usuario cambia.
    """
    # Verificar si cambió algún campo crítico
    if kwargs.get('created', False):
        # Usuario nuevo, no necesita limpieza de cache
        return
    
    # Campos críticos que afectan la autenticación
    critical_fields = ['estado', 'is_active', 'rol', 'terma']
    
    # En Django, no podemos fácilmente detectar campos cambiados en post_save
    # Pero siempre es seguro limpiar el cache cuando se guarda un usuario
    clear_user_cache(instance)
    logger.info(f"Auto-limpieza de cache para usuario: {instance.email}")


def auto_clear_cache_on_terma_change(sender, instance, **kwargs):
    """
    Signal handler para limpiar cache automáticamente cuando una terma cambia.
    """
    if kwargs.get('created', False):
        return
    
    # Limpiar cache de usuarios relacionados
    clear_terma_related_cache(instance)
    logger.info(f"Auto-limpieza de cache para terma: {instance.nombre_terma}")


def auto_clear_cache_on_rol_change(sender, instance, **kwargs):
    """
    Signal handler para limpiar cache automáticamente cuando un rol cambia.
    """
    if kwargs.get('created', False):
        return
    
    # Limpiar cache de todos los usuarios con este rol
    from usuarios.models import Usuario
    usuarios_con_rol = Usuario.objects.filter(rol=instance)
    
    for usuario in usuarios_con_rol:
        clear_user_cache(usuario)
    
    logger.info(f"Auto-limpieza de cache para rol: {instance.nombre}")