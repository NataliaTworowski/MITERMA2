from django.db import models
from usuarios.models import Usuario
from django.utils import timezone
from datetime import timedelta, datetime
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
    rut_empresa = models.CharField(max_length=12, null=True, blank=True, help_text="RUT de la empresa (ej: 12.345.678-9)")
    limite_ventas_diario = models.IntegerField(default=100, help_text="Límite máximo de ventas por día")
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
    
    #datos que se muestran en el dashboard del adm de termas
    
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

    def ingresos_totales(self):
        """Calcula los ingresos totales de la terma"""
        from ventas.models import DetalleCompra
        from django.db.models import Sum
        total = DetalleCompra.objects.filter(
            horario_disponible__terma=self,
            compra__estado_pago='pagado'
        ).aggregate(total=Sum('subtotal'))['total']
        return total or 0

    def total_visitantes(self):
        """Calcula el total de visitantes de la terma"""
        from ventas.models import DetalleCompra
        from django.db.models import Sum
        total = DetalleCompra.objects.filter(
            horario_disponible__terma=self,
            compra__estado_pago='pagado'
        ).aggregate(total=Sum('cantidad'))['total']
        return total or 0

    def total_fotos(self):
        """Retorna el total de fotos subidas de la terma"""
        return self.imagenes.count()
    
    def verificar_disponibilidad_diaria(self, fecha):
        """Verifica si hay disponibilidad para la fecha especificada"""
        from ventas.models import DetalleCompra
        from django.db.models import Sum
        
        # Obtener el total de entradas vendidas para esa fecha
        ventas_dia = DetalleCompra.objects.filter(
            horario_disponible__terma=self,
            horario_disponible__fecha=fecha,
            compra__estado_pago='pagado'
        ).aggregate(total=Sum('cantidad'))['total'] or 0
        
        # Verificar si hay disponibilidad
        return ventas_dia < self.limite_ventas_diario, self.limite_ventas_diario - ventas_dia

    def calificaciones_recientes(self, limite=5):
        """Retorna las calificaciones más recientes"""
        return self.calificacion_set.select_related('usuario').order_by('-fecha')[:limite]
    
    def filtro_calificaciones(self, filtro='recientes', limite=5):
        """Retorna calificaciones filtradas por fecha"""
        queryset = self.calificacion_set.select_related('usuario')
        ahora = timezone.now()

        if filtro == '7_dias':
            fecha_limite = ahora - timedelta(days=7)
            queryset = queryset.filter(fecha__gte=fecha_limite)
        elif filtro == '30_dias':
            fecha_limite = ahora - timedelta(days=30)
            queryset = queryset.filter(fecha__gte=fecha_limite)
        elif filtro == '90_dias':
            fecha_limite = ahora - timedelta(days=90)
            queryset = queryset.filter(fecha__gte=fecha_limite)
        elif filtro == 'este_año':
            fecha_inicio_año = datetime(ahora.year, 1, 1)
            if timezone.is_aware(fecha_inicio_año):
                fecha_inicio_año = timezone.make_aware(fecha_inicio_año)
            else:
                fecha_inicio_año = timezone.make_aware(fecha_inicio_año)
            queryset = queryset.filter(fecha__gte=fecha_inicio_año)
        elif filtro == 'mas_antiguos':
            return queryset.order_by('fecha')[:limite]
        elif filtro == 'todos':
            return queryset.order_by('-fecha')
        else:  # 'recientes' por defecto
            return queryset.order_by('-fecha')[:limite]
        
        # Para filtros con fecha, ordenar por más recientes
        return queryset.order_by('-fecha')[:limite]

    def estadisticas_calificaciones(self):
        """Retorna estadísticas de calificaciones por período"""
        from django.db.models import Count, Avg
        ahora = timezone.now()

        return {
            'total': self.calificacion_set.count(),
            'ultimos_7_dias': self.calificacion_set.filter(
                fecha__gte=ahora - timedelta(days=7)
            ).count(),
            'ultimo_mes': self.calificacion_set.filter(
                fecha__gte=ahora - timedelta(days=30)
            ).count(),
            'promedio_general': self.calificacion_set.aggregate(
                promedio=Avg('puntuacion')
            )['promedio'] or 0,
            'promedio_ultimo_mes': self.calificacion_set.filter(
                fecha__gte=ahora - timedelta(days=30)
            ).aggregate(
                promedio=Avg('puntuacion')
            )['promedio'] or 0,    
        }


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
    descripcion = models.TextField(null=True, blank=True)
    precio = models.CharField(max_length=20, null=True, blank=True)


class SolicitudTerma(models.Model):
    usuario = models.ForeignKey("usuarios.Usuario", on_delete=models.CASCADE, null=True, blank=True)  
    nombre_terma = models.CharField(max_length=100)
    descripcion = models.TextField(null=True, blank=True)
    rut_empresa = models.CharField(max_length=12, null=True, blank=True, help_text="RUT de la empresa (ej: 12.345.678-9)")
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