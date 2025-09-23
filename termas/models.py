from django.db import models
from usuarios.models import Usuario
# Ciudad está definida en este mismo archivo

class Terma(models.Model):
    ESTADOS = [
        ("activa", "Activa"),
        ("inactiva", "Inactiva"),
    ]
    nombre_terma = models.CharField(max_length=100)
    descripcion_terma = models.TextField(null=True, blank=True)
    direccion_terma = models.TextField(null=True, blank=True)
    ciudad = models.ForeignKey('Ciudad', on_delete=models.SET_NULL, null=True, blank=True)
    telefono_terma = models.CharField(max_length=20, null=True, blank=True)
    email_terma = models.EmailField(max_length=100, null=True, blank=True)
    estado_suscripcion = models.CharField(max_length=20, choices=ESTADOS, default='inactiva')
    fecha_suscripcion = models.DateField(null=True, blank=True)
    calificacion_promedio = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    administrador = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True, related_name='termas_administradas')

    def __str__(self):
        return self.nombre_terma


class Calificacion(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    terma = models.ForeignKey(Terma, on_delete=models.CASCADE)
    puntuacion = models.IntegerField()
    comentario = models.TextField(null=True, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)


class ImagenTerma(models.Model):
    terma = models.ForeignKey(Terma, on_delete=models.CASCADE, related_name="imagenes")
    url_imagen = models.TextField()
    descripcion = models.TextField(null=True, blank=True)


class ServicioTerma(models.Model):
    terma = models.ForeignKey(Terma, on_delete=models.CASCADE, related_name="servicios")
    servicio = models.CharField(max_length=100)


class SolicitudTerma(models.Model):
    usuario = models.ForeignKey("usuarios.Usuario", on_delete=models.CASCADE)  
    nombre_terma = models.CharField(max_length=100)
    descripcion = models.TextField(null=True, blank=True)
    estado = models.CharField(max_length=20, choices=[('pendiente', 'Pendiente'), ('aceptada', 'Aceptada'), ('rechazada', 'Rechazada')], default='pendiente')
    fecha_solicitud = models.DateTimeField(auto_now_add=True)

class Region(models.Model):
    nombre = models.CharField(max_length=100)

    def __str__(self):
        return self.nombre


class Ciudad(models.Model):
    nombre = models.CharField(max_length=100)
    region = models.ForeignKey(Region, on_delete=models.CASCADE, related_name="ciudades")

    def __str__(self):
        return self.nombre