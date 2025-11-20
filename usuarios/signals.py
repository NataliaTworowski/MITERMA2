"""
Configuración de signals para limpieza automática de cache.
"""

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Usuario, Rol
from .cache_utils import (
    auto_clear_cache_on_user_change,
    auto_clear_cache_on_rol_change,
    clear_user_cache
)
import logging

logger = logging.getLogger('cache')

# Signal para Usuario
@receiver(post_save, sender=Usuario)
def usuario_post_save(sender, instance, **kwargs):
    """Limpia cache cuando se modifica un usuario"""
    auto_clear_cache_on_user_change(sender, instance, **kwargs)

@receiver(post_delete, sender=Usuario)
def usuario_post_delete(sender, instance, **kwargs):
    """Limpia cache cuando se elimina un usuario"""
    clear_user_cache(instance)
    logger.info(f"Cache limpiado por eliminación de usuario: {instance.email}")

# Signal para Rol
@receiver(post_save, sender=Rol)
def rol_post_save(sender, instance, **kwargs):
    """Limpia cache cuando se modifica un rol"""
    auto_clear_cache_on_rol_change(sender, instance, **kwargs)

# Signal para Terma (lo importamos dinámicamente para evitar import circular)
def setup_terma_signals():
    """Configura signals para Terma después de que se importa"""
    try:
        from termas.models import Terma
        from .cache_utils import auto_clear_cache_on_terma_change
        
        @receiver(post_save, sender=Terma)
        def terma_post_save(sender, instance, **kwargs):
            """Limpia cache cuando se modifica una terma"""
            auto_clear_cache_on_terma_change(sender, instance, **kwargs)
        
        logger.info("Signals de Terma configurados correctamente")
        
    except ImportError:
        logger.warning("No se pudieron configurar signals de Terma - modelo no disponible")