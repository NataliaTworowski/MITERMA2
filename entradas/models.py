from django.db import models
from termas.models import Terma
from usuarios.models import Usuario

class EntradaTipo(models.Model):
    terma = models.ForeignKey(Terma, on_delete=models.CASCADE)
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(null=True, blank=True)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    duracion_horas = models.IntegerField(null=True, blank=True)
    estado = models.BooleanField(default=True)
    servicios = models.ManyToManyField('termas.ServicioTerma', blank=True, related_name='entradas')


class HorarioDisponible(models.Model):
    terma = models.ForeignKey(Terma, on_delete=models.CASCADE)
    entrada_tipo = models.ForeignKey(EntradaTipo, on_delete=models.CASCADE)
    fecha = models.DateField()
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    cupos_totales = models.IntegerField()
    cupos_disponibles = models.IntegerField()
