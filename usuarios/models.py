from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.contrib.auth.hashers import make_password, check_password
import uuid
from django.utils import timezone
from datetime import timedelta
import random
import string
import secrets

class UsuarioManager(BaseUserManager):
    """
    Manager personalizado para el modelo Usuario que extiende AbstractBaseUser.
    Maneja la creación segura de usuarios y superusuarios.
    """
    
    def create_user(self, email, nombre, apellido, password=None, **extra_fields):
        """
        Crea y guarda un usuario regular con email y contraseña.
        """
        if not email:
            raise ValueError('El email es obligatorio')
        if not nombre:
            raise ValueError('El nombre es obligatorio')
        if not apellido:
            raise ValueError('El apellido es obligatorio')
        
        email = self.normalize_email(email)
        user = self.model(
            email=email,
            nombre=nombre,
            apellido=apellido,
            **extra_fields
        )
        
        if password:
            user.set_password(password)
        else:
            # Generar una contraseña temporal segura si no se proporciona
            user.set_password(secrets.token_urlsafe(12))
        
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, nombre, apellido, password=None, **extra_fields):
        """
        Crea y guarda un superusuario con email y contraseña.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('estado', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('El superusuario debe tener is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('El superusuario debe tener is_superuser=True.')
        
        # Crear rol de administrador general si no existe
        rol_admin, created = Rol.objects.get_or_create(
            nombre='administrador_general',
            defaults={'nombre': 'administrador_general'}
        )
        extra_fields['rol'] = rol_admin
        
        return self.create_user(email, nombre, apellido, password, **extra_fields)


class Rol(models.Model):
    nombre = models.CharField(max_length=50, unique=True)
    descripcion = models.TextField(blank=True, null=True, help_text="Descripción del rol")
    activo = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Rol"
        verbose_name_plural = "Roles"
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Usuario(AbstractBaseUser, PermissionsMixin):
    """
    Modelo de usuario personalizado que extiende AbstractBaseUser.
    Implementa completamente la interfaz de autenticación de Django.
    """
    
    # Campos principales del usuario
    email = models.EmailField(max_length=100, unique=True, db_index=True)
    nombre = models.CharField(max_length=50)
    apellido = models.CharField(max_length=50)
    telefono = models.CharField(max_length=20, null=True, blank=True)
    
    # Campos de estado y permisos
    estado = models.BooleanField(default=True, help_text="Indica si el usuario está activo")
    is_staff = models.BooleanField(default=False, help_text="Permite acceso al admin de Django")
    is_active = models.BooleanField(default=True, help_text="Usuario activo en el sistema")
    tiene_password_temporal = models.BooleanField(default=False, help_text="Indica si el usuario tiene una contraseña temporal que debe cambiar")
    
    # Relaciones
    rol = models.ForeignKey(Rol, on_delete=models.CASCADE, null=True, blank=True)
    terma = models.ForeignKey('termas.Terma', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Campos de fechas
    fecha_registro = models.DateTimeField(auto_now_add=True)
    date_joined = models.DateTimeField(auto_now_add=True)  # Compatible con Django Auth
    
    # Configuración del manager y campos requeridos
    objects = UsuarioManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nombre', 'apellido']
    
    class Meta:
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"
        ordering = ['-fecha_registro']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['rol']),
        ]
    
    def __str__(self):
        return f"{self.nombre} {self.apellido} ({self.email})"
    
    def get_full_name(self):
        """Retorna el nombre completo del usuario."""
        return f"{self.nombre} {self.apellido}".strip()
    
    def get_short_name(self):
        """Retorna el nombre corto del usuario."""
        return self.nombre
    
    def set_password(self, raw_password):
        """
        Hashea y guarda la contraseña usando el sistema de Django.
        """
        self.password = make_password(raw_password)
    
    def cambiar_password_temporal(self, new_password):
        """
        Cambia la contraseña temporal por una nueva y marca que ya no es temporal.
        """
        self.set_password(new_password)
        self.tiene_password_temporal = False
        self.save()
    
    def check_password(self, raw_password):
        """
        Verifica si la contraseña proporcionada coincide con la hasheada.
        """
        return check_password(raw_password, self.password)
    
    def has_perm(self, perm, obj=None):
        """
        Verifica si el usuario tiene un permiso específico.
        """
        if self.is_superuser:
            return True
        
        # Lógica personalizada de permisos basada en roles
        if not self.rol:
            return False
        
        # Admins generales tienen todos los permisos
        if self.rol.nombre == 'administrador_general':
            return True
        
        return False
    
    def has_module_perms(self, app_label):
        """
        Verifica si el usuario tiene permisos para un módulo específico.
        """
        if self.is_superuser:
            return True
        
        if not self.rol:
            return False
        
        return self.rol.nombre == 'administrador_general'
    
    @property
    def is_admin_terma(self):
        """Verifica si el usuario es administrador de terma."""
        return self.rol and self.rol.nombre == 'administrador_terma'
    
    @property
    def is_admin_general(self):
        """Verifica si el usuario es administrador general."""
        return self.rol and self.rol.nombre == 'administrador_general'
    
    @property
    def is_cliente(self):
        """Verifica si el usuario es cliente."""
        return self.rol and self.rol.nombre == 'cliente'
    
    @property
    def is_empleado(self):
        """Verifica si el usuario es empleado/trabajador."""
        return self.rol and self.rol.nombre == 'trabajador'
    
    def can_access_terma(self, terma_id):
        """
        Verifica si el usuario puede acceder a una terma específica.
        """
        if self.is_admin_general:
            return True
        
        if self.is_admin_terma and self.terma:
            return str(self.terma.id) == str(terma_id)
        
        return False
    
    def get_accessible_termas(self):
        """
        Retorna las termas a las que el usuario tiene acceso.
        """
        from termas.models import Terma
        
        if self.is_admin_general:
            return Terma.objects.all()
        
        if self.is_admin_terma and self.terma:
            return Terma.objects.filter(id=self.terma.id)
        
        return Terma.objects.none()
    
    def save(self, *args, **kwargs):
        """
        Override del método save para validaciones adicionales.
        """
        # Normalizar email
        if self.email:
            self.email = self.email.lower().strip()
        
        # Sincronizar is_active con estado
        self.is_active = self.estado
        
        super().save(*args, **kwargs)
    
class TokenRestablecerContrasena(models.Model):
    """
    Modelo para tokens de restablecimiento de contraseña seguros.
    Versión simplificada para migración gradual.
    """
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    token = models.CharField(max_length=64, unique=True, blank=True, null=True)  # Token más seguro ahora con unique
    codigo = models.CharField(max_length=6)  # Código de 6 dígitos para UX
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    usado = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = "Token para restablecer contraseña"
        verbose_name_plural = "Tokens para restablecer contraseña"
        ordering = ['-fecha_creacion']
    
    def save(self, *args, **kwargs):
        if not self.token:
            # Generar token seguro para uso interno
            import secrets
            self.token = secrets.token_urlsafe(48)
        
        if not self.codigo:
            # Generar código de 6 dígitos para mostrar al usuario
            self.codigo = ''.join(random.choices(string.digits, k=6))
        
        super().save(*args, **kwargs)
    
    def es_valido(self):
        """
        Verifica si el token es válido (no expirado y no usado).
        Tiempo de expiración reducido a 10 minutos para mayor seguridad.
        """
        tiempo_expiracion = self.fecha_creacion + timedelta(minutes=10)
        return not self.usado and timezone.now() < tiempo_expiracion
    
    def marcar_como_usado(self):
        """Marca el token como usado y lo guarda."""
        self.usado = True
        self.save(update_fields=['usado'])
    
    def tiempo_restante(self):
        """Retorna el tiempo restante en minutos para que expire el token."""
        if self.usado:
            return 0
        
        tiempo_expiracion = self.fecha_creacion + timedelta(minutes=10)
        tiempo_restante = tiempo_expiracion - timezone.now()
        
        if tiempo_restante.total_seconds() <= 0:
            return 0
        
        return int(tiempo_restante.total_seconds() / 60)
    
    def __str__(self):
        estado = "Usado" if self.usado else ("Válido" if self.es_valido() else "Expirado")
        return f"Token {self.codigo} para {self.usuario.email} - {estado}"


class Favorito(models.Model):
    """
    Modelo para gestionar las termas favoritas de los usuarios.
    """
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='favoritos')
    terma = models.ForeignKey('termas.Terma', on_delete=models.CASCADE, related_name='favoritos')
    fecha_agregado = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Favorito"
        verbose_name_plural = "Favoritos"
        unique_together = ('usuario', 'terma')  # Un usuario no puede tener la misma terma como favorito más de una vez
        ordering = ['-fecha_agregado']
    
    def __str__(self):
        return f"{self.usuario.get_full_name()} - {self.terma.nombre_terma}"


class HistorialTrabajador(models.Model):
    """
    Modelo para mantener el historial de trabajadores en las termas.
    Permite recordar qué usuarios trabajaron en qué termas y cuándo.
    """
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='historial_trabajador')
    terma = models.ForeignKey('termas.Terma', on_delete=models.CASCADE, related_name='historial_trabajadores')
    rol = models.ForeignKey(Rol, on_delete=models.CASCADE)
    fecha_inicio = models.DateTimeField(auto_now_add=True, help_text="Fecha en que comenzó a trabajar en la terma")
    fecha_fin = models.DateTimeField(null=True, blank=True, help_text="Fecha en que dejó de trabajar (null = aún activo)")
    motivo_fin = models.CharField(
        max_length=20, 
        choices=[
            ('desactivado', 'Cuenta desactivada'),
            ('cambio_rol', 'Cambio de rol'),
            ('transferido', 'Transferido a otra terma'),
            ('renuncia', 'Renuncia voluntaria'),
        ],
        null=True, 
        blank=True,
        help_text="Motivo por el cual dejó de trabajar"
    )
    activo = models.BooleanField(default=True, help_text="Indica si este es el registro actual activo")
    
    class Meta:
        verbose_name = "Historial de Trabajador"
        verbose_name_plural = "Historiales de Trabajadores"
        ordering = ['-fecha_inicio']
        indexes = [
            models.Index(fields=['usuario', 'terma']),
            models.Index(fields=['terma', 'activo']),
            models.Index(fields=['usuario', 'activo']),
        ]
    
    def __str__(self):
        estado = "Activo" if self.activo else f"Finalizado ({self.motivo_fin})"
        return f"{self.usuario.get_full_name()} en {self.terma.nombre_terma} - {estado}"
    
    def finalizar(self, motivo='desactivado'):
        """Marca este historial como finalizado"""
        self.fecha_fin = timezone.now()
        self.motivo_fin = motivo
        self.activo = False
        self.save(update_fields=['fecha_fin', 'motivo_fin', 'activo'])
    
    @classmethod
    def crear_historial(cls, usuario, terma, rol):
        """Crea un nuevo registro de historial para un trabajador"""
        # Finalizar cualquier historial activo existente para este usuario en esta terma
        cls.objects.filter(usuario=usuario, terma=terma, activo=True).update(
            fecha_fin=timezone.now(),
            activo=False
        )
        
        # Crear nuevo registro
        return cls.objects.create(
            usuario=usuario,
            terma=terma,
            rol=rol
        )