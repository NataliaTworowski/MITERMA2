from django.db import models
from termas.models import Terma
from usuarios.models import Usuario

class EntradaTipo(models.Model):
    DURACION_CHOICES = [
        ('dia', 'Por el día'),
        ('medio_dia', 'Medio día'),
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
    
    # Campos agregados de HorarioDisponible
    fecha = models.DateField(null=True, blank=True, help_text='Fecha para la cual esta entrada está disponible')
    cupos_totales = models.IntegerField(null=True, blank=True, help_text='Total de cupos disponibles para esta fecha')
    cupos_disponibles = models.IntegerField(null=True, blank=True, help_text='Cupos restantes para esta fecha')

    
    class Meta:
        # Permitir múltiples entradas por fecha, pero únicas por terma, nombre y fecha
        unique_together = ['terma', 'nombre', 'fecha']

    def save(self, *args, **kwargs):
        # Set default duracion_horas based on duracion_tipo if not specified
        if not self.duracion_horas:
            if self.duracion_tipo == 'dia':
                self.duracion_horas = 12
            elif self.duracion_tipo == 'noche':
                self.duracion_horas = 12
            elif self.duracion_tipo == 'dia_completo':
                self.duracion_horas = 24
        
        # Set default cupos if fecha is specified but cupos are not
        if self.fecha and not self.cupos_totales:
            self.cupos_totales = self.terma.limite_ventas_diario if self.terma else 50
        if self.fecha and self.cupos_disponibles is None:
            self.cupos_disponibles = self.cupos_totales or 50
            
        super().save(*args, **kwargs)

    def __str__(self):
        if self.fecha:
            return f"{self.nombre} - {self.fecha} ({self.cupos_disponibles}/{self.cupos_totales})"
        return self.nombre

    def crear_instancia_para_fecha(self, fecha):
        """Crea una instancia específica de esta entrada para una fecha determinada."""
        instancia, created = EntradaTipo.objects.get_or_create(
            terma=self.terma,
            nombre=self.nombre,
            fecha=fecha,
            defaults={
                'descripcion': self.descripcion,
                'precio': self.precio,
                'duracion_horas': self.duracion_horas,
                'duracion_tipo': self.duracion_tipo,
                'estado': self.estado,
                'cupos_totales': self.terma.limite_ventas_diario,
                'cupos_disponibles': self.terma.limite_ventas_diario
            }
        )
        
        if created:
            # Copiar servicios de la entrada template
            instancia.servicios.set(self.servicios.all())
            
        return instancia

    def reducir_cupos(self, cantidad):
        """Reduce los cupos disponibles en la cantidad especificada."""
        if self.cupos_disponibles is not None:
            self.cupos_disponibles = max(0, self.cupos_disponibles - cantidad)
            self.save(update_fields=['cupos_disponibles'])

    def aumentar_cupos(self, cantidad):
        """Aumenta los cupos disponibles en la cantidad especificada."""
        if self.cupos_disponibles is not None and self.cupos_totales is not None:
            self.cupos_disponibles = min(self.cupos_totales, self.cupos_disponibles + cantidad)
            self.save(update_fields=['cupos_disponibles'])

    def tiene_cupos_suficientes(self, cantidad):
        """Verifica si hay cupos suficientes para la cantidad solicitada."""
        if self.cupos_disponibles is None:
            return True  # Si no hay límite de cupos, siempre hay disponibilidad
        return self.cupos_disponibles >= cantidad

    @classmethod
    def get_entrada_template(cls, terma, nombre):
        """Obtiene la entrada template (sin fecha) para una terma y nombre específico."""
        return cls.objects.filter(terma=terma, nombre=nombre, fecha__isnull=True).first()

    @classmethod  
    def get_entrada_para_fecha(cls, terma, nombre, fecha):
        """Obtiene o crea la entrada específica para una fecha."""
        # Primero buscar si ya existe para esa fecha
        entrada = cls.objects.filter(terma=terma, nombre=nombre, fecha=fecha).first()
        if entrada:
            return entrada
        
        # Si no existe, buscar el template y crear la instancia
        template = cls.get_entrada_template(terma, nombre)
        if template:
            return template.crear_instancia_para_fecha(fecha)
        
        return None
