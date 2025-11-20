"""
Middleware para limpiar cache automáticamente en operaciones críticas.
"""

from django.utils.deprecation import MiddlewareMixin
from django.core.cache import cache
import logging

logger = logging.getLogger('cache')

class AutoCacheClearMiddleware(MiddlewareMixin):
    """
    Middleware que puede limpiar cache automáticamente en rutas específicas.
    Opcional - solo usar si los signals no son suficientes.
    """
    
    # Rutas donde se debe limpiar cache después de POST
    CACHE_CLEAR_PATHS = [
        '/usuarios/activar/',
        '/usuarios/desactivar/',
        '/termas/admin/usuarios/',
        '/admin/usuarios/',
    ]

    def process_response(self, request, response):
        """
        Procesa la respuesta y limpia cache si es necesario.
        """
        if (request.method == 'POST' and 
            response.status_code in [200, 302] and
            any(path in request.path for path in self.CACHE_CLEAR_PATHS)):
            
            # Limpiar cache selectivamente
            cache.delete_many([
                key for key in cache._cache.keys() 
                if key.startswith(('user_', 'auth_attempts_'))
            ])
            
            logger.info(f"Cache limpiado automáticamente por middleware en ruta: {request.path}")
        
        return response