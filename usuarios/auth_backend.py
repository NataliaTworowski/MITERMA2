from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.hashers import check_password
from .models import Usuario

class CustomAuthBackend(BaseBackend):
    """
    Backend de autenticación personalizado para integrar tu modelo Usuario
    con el sistema de autenticación de Django de manera segura.
    """
    
    def authenticate(self, request, email=None, password=None, **kwargs):
        try:
            # Buscar usuario por email
            usuario = Usuario.objects.get(email=email.lower(), estado=True)
            
            # Verificar contraseña
            if check_password(password, usuario.password):
                return usuario
            return None
            
        except Usuario.DoesNotExist:
            return None
    
    def get_user(self, user_id):
        try:
            return Usuario.objects.get(pk=user_id, estado=True)
        except Usuario.DoesNotExist:
            return None