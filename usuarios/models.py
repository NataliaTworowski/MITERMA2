from django.db import models

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

    def __str__(self):
        return f"{self.nombre} {self.apellido}"
