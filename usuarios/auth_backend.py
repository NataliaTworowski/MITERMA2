from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.hashers import check_password
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.conf import settings
import logging
from datetime import datetime, timedelta

logger = logging.getLogger('security')
Usuario = get_user_model()


class CustomAuthBackend(BaseBackend):
    """
    Backend de autenticación personalizado mejorado con características de seguridad.
    
    Características:
    - Rate limiting por IP y usuario
    - Logging de intentos de autenticación
    - Validación de estado del usuario
    - Cache de usuarios para mejor rendimiento
    - Soporte para migración de contraseñas legacy
    """
    
    def authenticate(self, request, email=None, password=None, **kwargs):
        """
        Autentica un usuario con validaciones de seguridad mejoradas.
        """
        logger.info(f"=== INICIANDO AUTENTICACIÓN ===")
        logger.info(f"Email recibido: '{email}' (tipo: {type(email)})")
        logger.info(f"Password recibido: '***' (longitud: {len(password) if password else 0})")
        logger.info(f"IP cliente: {self._get_client_ip(request)}")
        
        if not email or not password:
            logger.warning(f"Email o password faltante: email={bool(email)}, password={bool(password)}")
            return None
        
        email = email.lower().strip()
        logger.info(f"Email normalizado: '{email}'")
        
        # Verificar rate limiting
        if not self._check_rate_limit(request, email):
            logger.warning(f"Rate limit excedido para email: {email} desde IP: {self._get_client_ip(request)}")
            return None
        
        try:
            # IMPORTANTE: No usar caché para búsqueda de usuario - buscar directamente en DB
            logger.info(f"=== BUSCANDO USUARIO DIRECTAMENTE EN DB ===")
            logger.info(f"Query: Usuario.objects.get(email='{email}')")
            
            # Buscar directamente en la base de datos, SIN caché
            usuario = Usuario.objects.select_related('rol', 'terma').filter(email=email).first()
            
            if not usuario:
                logger.warning(f"Usuario NO encontrado en DB: {email}")
                # Verificar si hay algún usuario con email similar
                usuarios_similares = Usuario.objects.filter(email__icontains=email[:10]).values_list('email', flat=True)[:5]
                logger.info(f"Usuarios con email similar: {list(usuarios_similares)}")
                self._record_failed_attempt(request, email, 'user_not_found')
                return None
            
            logger.info(f"=== USUARIO ENCONTRADO ===")
            logger.info(f"Usuario ID: {usuario.id}")
            logger.info(f"Usuario email DB: '{usuario.email}'")
            logger.info(f"Usuario nombre: '{usuario.nombre}'")
            logger.info(f"Usuario rol: {usuario.rol.nombre if usuario.rol else 'None'}")
            logger.info(f"Usuario activo: {usuario.estado}")
            
            # Verificar estado del usuario
            if not self._is_user_valid(usuario):
                logger.warning(f"Usuario inválido o inactivo: {email}")
                self._record_failed_attempt(request, email, 'user_inactive')
                return None
            
            logger.info(f"=== VERIFICANDO PASSWORD ===")
            logger.info(f"Hash en DB: {usuario.password[:20]}...")
            
            # Verificar contraseña
            password_valida = self._verify_password(usuario, password)
            logger.info(f"Password válida: {password_valida}")
            
            if password_valida:
                logger.info(f"=== AUTENTICACIÓN EXITOSA ===")
                logger.info(f"Retornando usuario: ID={usuario.id}, email={usuario.email}")
                self._record_successful_login(request, usuario)
                self._clear_failed_attempts(request, email)
                return usuario
            else:
                logger.warning(f"Password incorrecto para: {email}")
                self._record_failed_attempt(request, email, 'invalid_password')
                return None
                
        except Exception as e:
            logger.error(f"Error durante autenticación para {email}: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None
    
    def get_user(self, user_id):
        """
        Obtiene un usuario por ID con cache mínimo para evitar problemas.
        """
        try:
            # Usar caché muy corto (30 segundos) para evitar problemas
            cache_key = f"user_{user_id}"
            usuario = cache.get(cache_key)
            
            if usuario is None:
                usuario = Usuario.objects.select_related('rol', 'terma').get(
                    pk=user_id, 
                    estado=True
                )
                # Cachear solo por 30 segundos para evitar problemas
                cache.set(cache_key, usuario, 30)
            
            return usuario if self._is_user_valid(usuario) else None
            
        except Usuario.DoesNotExist:
            # Limpiar caché si el usuario no existe
            cache.delete(cache_key)
            return None
    
    def _get_user_by_email(self, email):
        """
        Obtiene usuario por email con cache mínimo.
        """
        cache_key = f"user_email_{email}"
        usuario = cache.get(cache_key)
        
        if usuario is None:
            try:
                usuario = Usuario.objects.select_related('rol', 'terma').get(
                    email=email
                )
                # Cache muy corto para evitar problemas
                cache.set(cache_key, usuario, 30)
            except Usuario.DoesNotExist:
                return None
        
        return usuario
    
    def _is_user_valid(self, usuario):
        """
        Verifica si el usuario está en estado válido para autenticación.
        """
        if not usuario:
            return False
        
        # Usuario debe estar activo
        if not usuario.estado or not usuario.is_active:
            return False
        
        # Usuario debe tener un rol asignado
        if not usuario.rol or not usuario.rol.activo:
            return False
        
        # Si es admin de terma, debe tener terma asignada (pero puede estar inactiva)
        if usuario.rol.nombre == 'administrador_terma':
            if not usuario.terma:
                return False
        
        return True
    
    def _verify_password(self, usuario, password):
        """
        Verifica la contraseña con soporte para migración de hashes legacy.
        """
        # Intentar verificación con hash de Django
        if usuario.password.startswith(('pbkdf2_', 'bcrypt', 'argon2')):
            return check_password(password, usuario.password)
        
        # Si no es hash de Django, podría ser hash legacy
        # Esto permite migrar contraseñas gradualmente
        if self._verify_legacy_password(usuario, password):
            # Actualizar a hash seguro de Django
            usuario.set_password(password)
            usuario.save(update_fields=['password'])
            logger.info(f"Contraseña migrada a hash seguro para usuario: {usuario.email}")
            return True
        
        return False
    
    def _verify_legacy_password(self, usuario, password):
        """
        Verifica contraseñas con hashes legacy (para migración).
        Implementar según el sistema de hash anterior.
        """
        # Si las contraseñas estaban en texto plano (¡muy inseguro!)
        if usuario.password == password:
            logger.warning(f"Contraseña en texto plano detectada para: {usuario.email}")
            return True
        
        # Si usaban otro sistema de hash, implementar aquí
        # Por ejemplo, MD5, SHA1, etc. (todos inseguros)
        import hashlib
        
        # Ejemplo para MD5 (solo para migración)
        if len(usuario.password) == 32:  # MD5 hash length
            md5_hash = hashlib.md5(password.encode()).hexdigest()
            if usuario.password == md5_hash:
                logger.warning(f"Hash MD5 legacy detectado para: {usuario.email}")
                return True
        
        return False
    
    def _check_rate_limit(self, request, email):
        """
        Implementa rate limiting para prevenir ataques de fuerza bruta.
        """
        if not request:
            return True
        
        ip = self._get_client_ip(request)
        
        # Rate limit por IP
        ip_key = f"auth_attempts_ip_{ip}"
        ip_attempts = cache.get(ip_key, 0)
        
        # Rate limit por email
        email_key = f"auth_attempts_email_{email}"
        email_attempts = cache.get(email_key, 0)
        
        # Límites configurables
        max_attempts_per_ip = getattr(settings, 'AUTH_MAX_ATTEMPTS_PER_IP', 20)
        max_attempts_per_email = getattr(settings, 'AUTH_MAX_ATTEMPTS_PER_EMAIL', 5)
        
        if ip_attempts >= max_attempts_per_ip:
            return False
        
        if email_attempts >= max_attempts_per_email:
            return False
        
        return True
    
    def _record_failed_attempt(self, request, email, reason):
        """
        Registra un intento fallido de autenticación.
        """
        if not request:
            return
        
        ip = self._get_client_ip(request)
        
        # Incrementar contadores
        ip_key = f"auth_attempts_ip_{ip}"
        email_key = f"auth_attempts_email_{email}"
        
        cache.set(ip_key, cache.get(ip_key, 0) + 1, 3600)  # 1 hora
        cache.set(email_key, cache.get(email_key, 0) + 1, 1800)  # 30 minutos
        
        # Log del evento
        logger.warning(f"Intento de autenticación fallido: {email} desde {ip} - Razón: {reason}")
    
    def _record_successful_login(self, request, usuario):
        """
        Registra un login exitoso.
        """
        if not request:
            return
        
        ip = self._get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # Actualizar última conexión
        usuario.last_login = datetime.now()
        usuario.save(update_fields=['last_login'])
        
        # Log del evento
        logger.info(f"Login exitoso: {usuario.email} desde {ip}")
        
        # Limpiar cache del usuario para refrescar datos
        cache.delete(f"user_{usuario.id}")
        cache.delete(f"user_email_{usuario.email}")
    
    def _clear_failed_attempts(self, request, email):
        """
        Limpia los contadores de intentos fallidos tras login exitoso.
        """
        if not request:
            return
        
        ip = self._get_client_ip(request)
        
        ip_key = f"auth_attempts_ip_{ip}"
        email_key = f"auth_attempts_email_{email}"
        
        cache.delete(ip_key)
        cache.delete(email_key)
    
    def _get_client_ip(self, request):
        """
        Obtiene la IP real del cliente considerando proxies.
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', 'unknown')
        return ip