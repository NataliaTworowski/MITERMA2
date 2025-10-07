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
    comuna = models.ForeignKey('Comuna', on_delete=models.SET_NULL, null=True, blank=True)
    telefono_terma = models.CharField(max_length=20, null=True, blank=True)
    email_terma = models.EmailField(max_length=100, null=True, blank=True)
    estado_suscripcion = models.CharField(max_length=20, choices=ESTADOS, default='inactiva')
    fecha_suscripcion = models.DateField(null=True, blank=True)
    calificacion_promedio = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    administrador = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True, related_name='termas_administradas')

    def __str__(self):
        return self.nombre_terma
    
    # Método para obtener el precio mínimo desde EntradaTipo
    def precio_minimo(self):
        entrada_minima = self.entradatipo_set.filter(estado=True).order_by('precio').first()
        return entrada_minima.precio if entrada_minima else None
    
    # Método para obtener todos los tipos de entrada activos
    def get_tipos_entrada(self):
        return self.entradatipo_set.filter(estado=True).order_by('precio')
    
    # Método para verificar si tiene tipos de entrada
    def tiene_precios(self):
        return self.entradatipo_set.filter(estado=True).exists()
    
    #para calcualr el promedio de calificacion 
    def promedio_calificacion(self):
        """Calcula el promedio de las puntuaciones de calificación"""
        from django.db.models import Avg
        resultado = self.calificacion_set.aggregate(promedio=Avg('puntuacion'))
        return resultado['promedio'] if resultado['promedio'] else None

    #para obtener el nuemro de calificaciones
    def total_calificaciones(self):
        """Retorna el número total de calificaciones"""
        return self.calificacion_set.count()


class Calificacion(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    terma = models.ForeignKey(Terma, on_delete=models.CASCADE)
    puntuacion = models.IntegerField()
    comentario = models.TextField(null=True, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        """Sobrescribir save para actualizar calificacion_promedio de la terma."""
        super().save(*args, **kwargs)
        self.actualizar_promedio_terma()
    
    def delete(self, *args, **kwargs):
        """Sobrescribir delete para actualizar calificacion_promedio de la terma."""
        terma = self.terma
        super().delete(*args, **kwargs)
        self.actualizar_promedio_terma_manual(terma)
    
    def actualizar_promedio_terma(self):
        """Actualiza el promedio de calificación de la terma asociada."""
        from django.db.models import Avg
        promedio = self.terma.calificacion_set.aggregate(promedio=Avg('puntuacion'))['promedio']
        self.terma.calificacion_promedio = promedio
        self.terma.save(update_fields=['calificacion_promedio'])
    
    @staticmethod
    def actualizar_promedio_terma_manual(terma):
        """Actualiza el promedio de calificación para una terma específica."""
        from django.db.models import Avg
        promedio = terma.calificacion_set.aggregate(promedio=Avg('puntuacion'))['promedio']
        terma.calificacion_promedio = promedio
        terma.save(update_fields=['calificacion_promedio'])



class ImagenTerma(models.Model):
    terma = models.ForeignKey(Terma, on_delete=models.CASCADE, related_name="imagenes")
    url_imagen = models.TextField()
    descripcion = models.TextField(null=True, blank=True)


class ServicioTerma(models.Model):
    terma = models.ForeignKey(Terma, on_delete=models.CASCADE, related_name="servicios")
    servicio = models.CharField(max_length=100)


class SolicitudTerma(models.Model):
    usuario = models.ForeignKey("usuarios.Usuario", on_delete=models.CASCADE, null=True, blank=True)  
    nombre_terma = models.CharField(max_length=100)
    descripcion = models.TextField(null=True, blank=True)
    correo_institucional = models.EmailField(null=True, blank=True)
    telefono_contacto = models.CharField(max_length=20, null=True, blank=True)
    region = models.ForeignKey('Region', on_delete=models.SET_NULL, null=True, blank=True)
    comuna = models.ForeignKey('Comuna', on_delete=models.SET_NULL, null=True, blank=True)
    direccion = models.TextField(null=True, blank=True)
    estado = models.CharField(max_length=20, choices=[('pendiente', 'Pendiente'), ('aceptada', 'Aceptada'), ('rechazada', 'Rechazada')], default='pendiente')
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    terma = models.OneToOneField('Terma', on_delete=models.SET_NULL, null=True, blank=True)
    motivo_rechazo = models.TextField(null=True, blank=True)
    observaciones_admin = models.TextField(null=True, blank=True)
    fecha_respuesta = models.DateTimeField(null=True, blank=True)

class Region(models.Model):
    nombre = models.CharField(max_length=100)

    def __str__(self):
        return self.nombre


class Comuna(models.Model):
    nombre = models.CharField(max_length=100)
    region = models.ForeignKey(Region, on_delete=models.CASCADE, related_name="comunas")

    def __str__(self):
        return self.nombre