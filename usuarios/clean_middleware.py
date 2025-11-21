"""
Middleware para limpiar variables de sesión específicas entre usuarios.
"""
import logging
from django.core.cache import cache

logger = logging.getLogger('usuarios')


class CleanRequestMiddleware:
    """
    Middleware que limpia variables específicas del request para evitar
    que se mantengan entre diferentes usuarios o sesiones.
    También limpia automáticamente el caché de autenticación.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Excluir rutas de API móvil para evitar interferencias
        if self.is_api_request(request):
            return self.get_response(request)
        
        # Limpiar variables específicas al inicio de cada request
        self.clean_request_variables(request)
        
        # Limpiar caché de autenticación automáticamente
        self.clean_auth_cache(request)
        
        response = self.get_response(request)
        
        return response
    
    def is_api_request(self, request):
        """
        Determina si la request es para la API móvil
        """
        api_paths = [
            '/usuarios/api/',
            '/api/',
        ]
        return any(request.path.startswith(path) for path in api_paths)
    
    def clean_request_variables(self, request):
        """
        Limpia variables específicas que no deberían persistir entre requests
        o usuarios diferentes.
        """
        # Variables a limpiar
        variables_to_clean = [
            '_terma_inactiva',
            '_user_cache',
            '_auth_cache'
        ]
        
        for var in variables_to_clean:
            if hasattr(request, var):
                delattr(request, var)
                logger.debug(f"Variable {var} limpiada del request")
    
    def clean_auth_cache(self, request):
        """
        Limpia automáticamente el caché de autenticación cuando cambia el usuario.
        """
        current_user_id = request.user.id if request.user.is_authenticated else None
        session_user_id = request.session.get('_auth_user_id')
        
        # Si el usuario en la sesión es diferente al usuario en caché, limpiar
        if current_user_id != session_user_id:
            # Limpiar cachés específicos de usuarios
            if session_user_id:
                cache.delete(f"user_{session_user_id}")
                cache.delete(f"user_email_{request.session.get('_last_email', '')}")
                logger.info(f"Caché de usuario {session_user_id} limpiado")
            
            # Limpiar caché general de autenticación cada cierto tiempo
            if not hasattr(request, '_cache_cleaned'):
                cache.delete_many([
                    f"user_{current_user_id}" if current_user_id else None,
                    'auth_attempts_ip_' + self._get_client_ip(request),
                ])
                request._cache_cleaned = True
                logger.debug("Caché de autenticación limpiado")
    
    def _get_client_ip(self, request):
        """Obtiene la IP del cliente"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip or 'unknown'
    
    def process_view(self, request, view_func, view_args, view_kwargs):
        """
        Se ejecuta antes de que Django llame a la vista.
        Aquí podemos hacer limpieza adicional si es necesario.
        """
        # Excluir rutas de API móvil
        if self.is_api_request(request):
            return None
            
        # Si el usuario cambió desde la última request, limpiar todo
        if hasattr(request, '_last_user_id') and request.user.is_authenticated:
            if request._last_user_id != request.user.id:
                logger.info(f"Usuario cambió de {request._last_user_id} a {request.user.id}, limpiando variables")
                self.clean_request_variables(request)
                # Limpiar caché específico del usuario anterior
                cache.delete(f"user_{request._last_user_id}")
        
        # Guardar el ID del usuario actual para la próxima request
        if request.user.is_authenticated:
            request._last_user_id = request.user.id
            request.session['_last_email'] = request.user.email
        else:
            request._last_user_id = None
            request.session.pop('_last_email', None)
        
        return None