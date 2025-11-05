from django.db import models
from termas.models import Terma
from usuarios.models import Usuario

class EntradaTipo(models.Model):
    DURACION_CHOICES = [
        ('dia', 'Por el día'),
        ('noche', 'Por la noche'),
        ('dia_completo', 'Día completo'),
    ]
    
    terma = models.ForeignKey(Terma, on_delete=models.CASCADE)
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(null=True, blank=True)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    duracion_horas = models.IntegerField(
        null=True, 
        blank=True,
        help_text='Duración en horas para este tipo de entrada'
    )
    duracion_tipo = models.CharField(
        max_length=20,
        choices=DURACION_CHOICES,
        default='dia',
        help_text='Define si la entrada es para uso diurno, nocturno o día completo'
    )
    estado = models.BooleanField(default=True)
    servicios = models.ManyToManyField('termas.ServicioTerma', blank=True, related_name='entradas')

    def save(self, *args, **kwargs):
        # Set default duracion_horas based on duracion_tipo if not specified
        if not self.duracion_horas:
            if self.duracion_tipo == 'dia':
                self.duracion_horas = 12
            elif self.duracion_tipo == 'noche':
                self.duracion_horas = 12
            elif self.duracion_tipo == 'dia_completo':
                self.duracion_horas = 24
        super().save(*args, **kwargs)

    def create_horario_disponible(self, fecha):
        """Crea un horario disponible para esta entrada en la fecha especificada."""
        from datetime import datetime, time
        if self.duracion_tipo == 'dia':
            hora_inicio = time(8, 0)  # 8:00 AM
            hora_fin = time(20, 0)    # 8:00 PM
        elif self.duracion_tipo == 'noche':
            hora_inicio = time(18, 0)  # 6:00 PM
            hora_fin = time(10, 0)     # 10:00 AM (siguiente día)
        else:  # dia_completo
            hora_inicio = time(8, 0)   # 8:00 AM
            hora_fin = time(8, 0)      # 8:00 AM (siguiente día)

        return HorarioDisponible.objects.create(
            terma=self.terma,
            entrada_tipo=self,
            fecha=fecha,
            hora_inicio=hora_inicio,
            hora_fin=hora_fin,
            cupos_totales=self.terma.limite_ventas_diario,
            cupos_disponibles=self.terma.limite_ventas_diario
        )


class HorarioDisponible(models.Model):
    terma = models.ForeignKey(Terma, on_delete=models.CASCADE)
    entrada_tipo = models.ForeignKey(EntradaTipo, on_delete=models.CASCADE)
    fecha = models.DateField()
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    cupos_totales = models.IntegerField()
    cupos_disponibles = models.IntegerField()
