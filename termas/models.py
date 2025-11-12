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
    
    # Nuevos campos para sistema de suscripciones
    plan_actual = models.ForeignKey(
        'PlanSuscripcion', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        help_text="Plan de suscripción actual"
    )
    porcentaje_comision_actual = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=5.00,
        help_text="Porcentaje de comisión actual basado en el plan"
    )
    limite_fotos_actual = models.IntegerField(
        default=5,
        help_text="Límite actual de fotos basado en el plan (-1 para ilimitado)"
    )

    def __str__(self):
        return self.nombre_terma
    
    # Método para obtener el precio mínimo desde EntradaTipo
    def precio_minimo(self):
        entrada_minima = self.entradatipo_set.filter(estado=True).order_by('precio').first()
        return entrada_minima.precio if entrada_minima else None
    
    # Método para obtener todos los tipos de entrada activos (solo templates, sin fecha)
    def get_tipos_entrada(self):
        return self.entradatipo_set.filter(estado=True, fecha__isnull=True).order_by('precio')
    
    # Método para obtener entradas específicas para una fecha
    def get_entradas_fecha(self, fecha):
        """Obtiene las entradas específicas para una fecha determinada"""
        return self.entradatipo_set.filter(estado=True, fecha=fecha).order_by('precio')
    
    # Método para obtener todas las entradas (templates y específicas)
    def get_todas_entradas(self):
        """Obtiene todas las entradas de la terma (para admin)"""
        return self.entradatipo_set.filter(estado=True).order_by('nombre', 'fecha')
    
    # Método para verificar si tiene tipos de entrada
    def tiene_precios(self):
        return self.entradatipo_set.filter(estado=True).exists()
    
    # Métodos para sistema de planes (sin suscripciones de pago)
    def tiene_plan_activo(self):
        """Verifica si la terma tiene un plan asignado y está activa"""
        return (
            self.plan_actual is not None and 
            self.estado_suscripcion == 'activa'
        )
    
    def puede_subir_mas_fotos(self):
        """Verifica si la terma puede subir más fotos según su plan"""
        fotos_actuales = self.total_fotos()
        if self.limite_fotos_actual == -1:  # Ilimitado
            return True
        return fotos_actuales < self.limite_fotos_actual
    
    def fotos_restantes(self):
        """Calcula cuántas fotos puede subir aún"""
        if self.limite_fotos_actual == -1:
            return "Ilimitado"
        fotos_actuales = self.total_fotos()
        restantes = self.limite_fotos_actual - fotos_actuales
        return max(0, restantes)
    
    def tiene_fotos_excedentes(self):
        """Verifica si la terma tiene más fotos de las permitidas por su plan actual"""
        if self.limite_fotos_actual == -1:  # Plan ilimitado
            return False
        fotos_actuales = self.total_fotos()
        return fotos_actuales > self.limite_fotos_actual
    
    def fotos_excedentes_cantidad(self):
        """Retorna la cantidad de fotos que exceden el límite actual"""
        if not self.tiene_fotos_excedentes():
            return 0
        fotos_actuales = self.total_fotos()
        return fotos_actuales - self.limite_fotos_actual
    
    def actualizar_configuracion_segun_plan(self):
        """Actualiza la configuración de la terma según su plan actual"""
        if self.plan_actual:
            self.porcentaje_comision_actual = self.plan_actual.porcentaje_comision
            self.limite_fotos_actual = self.plan_actual.limite_fotos
            self.save(update_fields=['porcentaje_comision_actual', 'limite_fotos_actual'])
    
    def get_beneficios_plan(self):
        """Retorna los beneficios del plan actual"""
        if not self.plan_actual:
            return []
        
        beneficios = []
        if self.plan_actual.limite_fotos == -1:
            beneficios.append("Fotos ilimitadas")
        else:
            beneficios.append(f"Hasta {self.plan_actual.limite_fotos} fotos")
        
        if self.plan_actual.posicion_preferencial:
            beneficios.append("Posición preferencial en búsquedas")
        
        if self.plan_actual.marketing_premium:
            beneficios.append("Marketing premium")
        
        if self.plan_actual.dashboard_avanzado:
            beneficios.append("Dashboard avanzado")
        
        if self.plan_actual.soporte_prioritario:
            beneficios.append("Soporte prioritario")
        
        if self.plan_actual.aparece_destacadas:
            beneficios.append("Aparece en termas destacadas")
        
        return beneficios
    
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
        """Calcula los ingresos totales del mes actual de la terma"""
        from ventas.models import Compra
        from django.db.models import Sum
        from datetime import date
        
        # Obtener primer día del mes actual
        hoy = date.today()
        primer_dia_mes = hoy.replace(day=1)
        
        total = Compra.objects.filter(
            terma=self,
            estado_pago='pagado',
            fecha_compra__date__gte=primer_dia_mes,
            fecha_compra__date__lte=hoy
        ).aggregate(total=Sum('total'))['total']
        return total or 0

    def ingresos_historicos(self):
        """Calcula los ingresos históricos totales de la terma"""
        from ventas.models import Compra
        from django.db.models import Sum
        total = Compra.objects.filter(
            terma=self,
            estado_pago='pagado'
        ).aggregate(total=Sum('total'))['total']
        return total or 0

    def total_visitantes(self):
        """Calcula el total de visitantes de la terma"""
        from ventas.models import DetalleCompra
        from django.db.models import Sum
        total = DetalleCompra.objects.filter(
            entrada_tipo__terma=self,
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
            entrada_tipo__terma=self,
            entrada_tipo__fecha=fecha,
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

    def servicios_populares(self):
        """Retorna estadísticas de servicios más utilizados"""
        from collections import Counter
        from ventas.models import ServicioExtraDetalle, DetalleCompra
        from django.db.models import Sum
        
        servicios_stats = {}
        
        # 1. Servicios incluidos en entradas vendidas
        entradas_vendidas = DetalleCompra.objects.filter(
            entrada_tipo__terma=self,
            compra__estado_pago='pagado'
        ).select_related('entrada_tipo')
        
        for detalle in entradas_vendidas:
            # Validar que entrada_tipo no sea None
            if not detalle.entrada_tipo:
                continue
                
            servicios_incluidos = detalle.entrada_tipo.servicios.all()
            cantidad_entradas = detalle.cantidad
            
            for servicio in servicios_incluidos:
                if servicio.servicio not in servicios_stats:
                    servicios_stats[servicio.servicio] = 0
                servicios_stats[servicio.servicio] += cantidad_entradas
        
        # 2. Servicios extra vendidos por separado
        servicios_extra = ServicioExtraDetalle.objects.filter(
            detalle_compra__entrada_tipo__terma=self,
            detalle_compra__compra__estado_pago='pagado'
        ).select_related('servicio').values('servicio__servicio').annotate(
            total_cantidad=Sum('cantidad')
        )
        
        for servicio_extra in servicios_extra:
            nombre_servicio = servicio_extra['servicio__servicio']
            cantidad = servicio_extra['total_cantidad']
            
            # Validar que nombre_servicio no sea None
            if not nombre_servicio:
                continue
                
            if nombre_servicio not in servicios_stats:
                servicios_stats[nombre_servicio] = 0
            servicios_stats[nombre_servicio] += cantidad
        
        # Convertir a lista ordenada para el gráfico
        servicios_ordenados = sorted(servicios_stats.items(), key=lambda x: x[1], reverse=True)
        
        # Tomar los top 5 servicios
        top_servicios = servicios_ordenados[:5]
        
        return {
            'labels': [servicio[0] for servicio in top_servicios],
            'data': [servicio[1] for servicio in top_servicios],
            'total_servicios': len(servicios_stats),
            'detalle_completo': servicios_ordenados
        }


class Calificacion(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    terma = models.ForeignKey(Terma, on_delete=models.CASCADE)
    puntuacion = models.IntegerField()
    comentario = models.TextField(null=True, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Calificación"
        verbose_name_plural = "Calificaciones"
        ordering = ['-fecha']

    def __str__(self):
        return f"{self.usuario.get_full_name()} - {self.terma.nombre_terma} ({self.puntuacion}★)"

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

    def __str__(self):
        return self.servicio


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
    plan_seleccionado = models.ForeignKey(
        'PlanSuscripcion', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        help_text="Plan de suscripción seleccionado por la terma"
    )
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


class PlanSuscripcion(models.Model):
    TIPOS_PLAN = [
        ('basico', 'Básico'),
        ('estandar', 'Estándar'),
        ('premium', 'Premium'),
    ]
    
    nombre = models.CharField(max_length=50, choices=TIPOS_PLAN, unique=True)
    descripcion = models.TextField()
    porcentaje_comision = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        help_text="Porcentaje de comisión (ej: 5.00 para 5%)"
    )
    limite_fotos = models.IntegerField(
        help_text="Límite de fotos que puede subir (-1 para ilimitado)"
    )
    posicion_preferencial = models.BooleanField(
        default=False,
        help_text="Si aparece en posiciones preferenciales"
    )
    marketing_premium = models.BooleanField(
        default=False,
        help_text="Si tiene acceso a marketing premium"
    )
    dashboard_avanzado = models.BooleanField(
        default=False,
        help_text="Si tiene acceso a dashboard avanzado"
    )
    soporte_prioritario = models.BooleanField(
        default=False,
        help_text="Si tiene soporte prioritario"
    )
    aparece_destacadas = models.BooleanField(
        default=False,
        help_text="Si aparece en sección de termas destacadas"
    )
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Plan de Suscripción"
        verbose_name_plural = "Planes de Suscripción"
        ordering = ['porcentaje_comision']
    
    def __str__(self):
        return f"{self.get_nombre_display()} - {self.porcentaje_comision}%"


class HistorialSuscripcion(models.Model):
    """Historial de cambios de suscripciones"""
    terma = models.ForeignKey(Terma, on_delete=models.CASCADE, related_name='historial_suscripciones')
    plan_anterior = models.ForeignKey(
        PlanSuscripcion, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='historiales_como_anterior'
    )
    plan_nuevo = models.ForeignKey(
        PlanSuscripcion, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='historiales_como_nuevo'
    )
    fecha_cambio = models.DateTimeField(auto_now_add=True)
    motivo = models.TextField(null=True, blank=True)
    usuario_admin = models.ForeignKey(
        'usuarios.Usuario', 
        on_delete=models.SET_NULL, 
        null=True,
        help_text="Admin que realizó el cambio"
    )
    
    class Meta:
        verbose_name = "Historial de Suscripción"
        verbose_name_plural = "Historiales de Suscripciones"
        ordering = ['-fecha_cambio']
    
    def __str__(self):
        return f"{self.terma.nombre_terma} - Cambio de plan ({self.fecha_cambio.date()})"