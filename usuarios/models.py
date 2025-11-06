from django.db import models
import uuid
from django.utils import timezone
from datetime import timedelta
import random
import string

class Rol(models.Model):
    nombre = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.nombre


class Usuario(models.Model):
    email = models.EmailField(max_length=100, unique=True)
    password = models.CharField(max_length=255)
    nombre = models.CharField(max_length=50)
    apellido = models.CharField(max_length=50)
    telefono = models.CharField(max_length=20, null=True, blank=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    rol = models.ForeignKey(Rol, on_delete=models.CASCADE)
    estado = models.BooleanField(default=True)
    terma = models.ForeignKey('termas.Terma', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Campos requeridos para compatibilidad con Django Auth
    last_login = models.DateTimeField(null=True, blank=True)
    
    # Propiedades requeridas por Django Auth
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nombre', 'apellido']
    
    @property
    def is_authenticated(self):
        return True
    
    @property
    def is_anonymous(self):
        return False
    
    @property
    def is_active(self):
        return self.estado
    
    def get_username(self):
        return self.email

    def __str__(self):
        return f"{self.nombre} {self.apellido}"
    
class TokenRestablecerContrasena(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    codigo = models.CharField(max_length=6)  # Código de 6 dígitos
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    usado = models.BooleanField(default=False)
    
    def save(self, *args, **kwargs):
        if not self.codigo:
            # Generar código aleatorio de 6 dígitos
            self.codigo = ''.join(random.choices(string.digits, k=6))
        super().save(*args, **kwargs)
    
    def es_valido(self):
        """Verifica si el código es válido (no expirado y no usado)"""
        tiempo_expiracion = self.fecha_creacion + timedelta(minutes=15)  # 15 minutos
        return not self.usado and timezone.now() < tiempo_expiracion
    
    def __str__(self):
        return f"Código {self.codigo} para {self.usuario.email}"
    
    class Meta:
        verbose_name = "Token para restablecer contraseña"
        verbose_name_plural = "Tokens para restablecer contraseña"