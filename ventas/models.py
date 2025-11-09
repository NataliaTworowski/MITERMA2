from django.db import models
from datetime import date
from usuarios.models import Usuario
from entradas.models import HorarioDisponible

class MetodoPago(models.Model):
    nombre = models.CharField(max_length=50)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre


class Compra(models.Model):
    ESTADO_PAGO = [
        ("pendiente", "Pendiente"),
        ("pagado", "Pagado"),
        ("cancelado", "Cancelado"),
    ]
    
    cantidad = models.IntegerField(default=1)

    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    metodo_pago = models.ForeignKey(MetodoPago, on_delete=models.SET_NULL, null=True, blank=True)
    terma = models.ForeignKey("termas.Terma", on_delete=models.SET_NULL, null=True, blank=True)
    fecha_compra = models.DateTimeField(auto_now_add=True)
    fecha_visita = models.DateField(default=date.today, help_text="Fecha para la que es válida la entrada")
    total = models.DecimalField(max_digits=10, decimal_places=2)
    estado_pago = models.CharField(max_length=20, choices=ESTADO_PAGO)
    visible = models.BooleanField(default=True, help_text="Indica si la compra es visible para el cliente")
    mercado_pago_id = models.CharField(max_length=100, null=True, blank=True, help_text="ID de la preferencia de Mercado Pago")
    codigo_confirmacion = models.CharField(max_length=100, null=True, blank=True)
    pagador_email = models.EmailField(null=True, blank=True)
    monto_pagado = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    fecha_confirmacion_pago = models.DateTimeField(null=True, blank=True)
    payment_id = models.CharField(max_length=100, null=True, blank=True, help_text="Payment ID de Mercado Pago")




class CodigoQR(models.Model):
    compra = models.OneToOneField(Compra, on_delete=models.CASCADE)
    codigo = models.TextField()
    fecha_generacion = models.DateTimeField(auto_now_add=True)
    fecha_uso = models.DateTimeField(null=True, blank=True)
    usado = models.BooleanField(default=False)

class RegistroEscaneo(models.Model):
    codigo_qr = models.ForeignKey(CodigoQR, on_delete=models.CASCADE)
    fecha_escaneo = models.DateTimeField(auto_now_add=True)
    usuario_scanner = models.ForeignKey('usuarios.Usuario', on_delete=models.SET_NULL, null=True)
    exitoso = models.BooleanField(default=False)
    mensaje = models.CharField(max_length=255, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    dispositivo = models.CharField(max_length=255, blank=True)


class CuponDescuento(models.Model):
    codigo = models.CharField(max_length=50, unique=True)
    descuento_porcentaje = models.IntegerField()
    fecha_vencimiento = models.DateField(null=True, blank=True)
    terma = models.ForeignKey("termas.Terma", on_delete=models.SET_NULL, null=True, blank=True)


class CuponUsado(models.Model):
    cupon = models.ForeignKey(CuponDescuento, on_delete=models.CASCADE)
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    compra = models.ForeignKey(Compra, on_delete=models.CASCADE)
    fecha_uso = models.DateTimeField(auto_now_add=True)


class DetalleCompra(models.Model):
    id = models.AutoField(primary_key=True)
    compra = models.ForeignKey(Compra, on_delete=models.CASCADE, related_name="detalles")
    horario_disponible = models.ForeignKey(HorarioDisponible, on_delete=models.CASCADE)
    cantidad = models.IntegerField()
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    servicios = models.ManyToManyField('termas.ServicioTerma', blank=True, related_name='detalles_compra')


class ServicioExtraDetalle(models.Model):
    """Modelo intermedio para manejar cantidades de servicios extra en los detalles de compra"""
    detalle_compra = models.ForeignKey(DetalleCompra, on_delete=models.CASCADE, related_name='servicios_extra')
    servicio = models.ForeignKey('termas.ServicioTerma', on_delete=models.CASCADE)
    cantidad = models.IntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    
    class Meta:
        unique_together = ('detalle_compra', 'servicio')
    
    def __str__(self):
        return f"{self.servicio.servicio} x{self.cantidad} - {self.detalle_compra.compra.id}"


class Carrito(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    horario_disponible = models.ForeignKey(HorarioDisponible, on_delete=models.CASCADE)
    cantidad = models.IntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    fecha_agregado = models.DateTimeField(auto_now_add=True)


class DistribucionPago(models.Model):
    """
    Tabla mediadora para gestionar la distribución de pagos entre terma y plataforma
    """
    ESTADO_DISTRIBUCION = [
        ('pendiente', 'Pendiente'),
        ('procesado', 'Procesado'),
        ('pagado_terma', 'Pagado a Terma'),
        ('completado', 'Completado'),
        ('error', 'Error'),
    ]
    
    compra = models.OneToOneField(Compra, on_delete=models.CASCADE, related_name='distribucion_pago')
    terma = models.ForeignKey("termas.Terma", on_delete=models.CASCADE)
    plan_utilizado = models.ForeignKey("termas.PlanSuscripcion", on_delete=models.SET_NULL, null=True)
    
    # Montos calculados
    monto_total = models.DecimalField(max_digits=10, decimal_places=2)
    porcentaje_comision = models.DecimalField(max_digits=5, decimal_places=2)
    monto_comision_plataforma = models.DecimalField(max_digits=10, decimal_places=2)
    monto_para_terma = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Control de estado
    estado = models.CharField(max_length=20, choices=ESTADO_DISTRIBUCION, default='pendiente')
    fecha_calculo = models.DateTimeField(auto_now_add=True)
    fecha_procesado = models.DateTimeField(null=True, blank=True)
    fecha_pago_terma = models.DateTimeField(null=True, blank=True)
    
    # Información adicional
    observaciones = models.TextField(null=True, blank=True)
    referencia_pago_terma = models.CharField(max_length=100, null=True, blank=True, 
                                           help_text="Referencia del pago enviado a la terma")
    
    class Meta:
        verbose_name = "Distribución de Pago"
        verbose_name_plural = "Distribuciones de Pago"
        ordering = ['-fecha_calculo']
    
    def __str__(self):
        return f"Distribución #{self.id} - Compra #{self.compra.id} - {self.terma.nombre_terma}"
    
    def calcular_distribucion(self):
        """Recalcula los montos de distribución basado en el plan actual de la terma"""
        from decimal import Decimal
        
        self.monto_total = self.compra.total
        
        # Obtener el porcentaje de comisión del plan actual de la terma
        if self.terma.plan_actual:
            self.porcentaje_comision = self.terma.plan_actual.porcentaje_comision
            self.plan_utilizado = self.terma.plan_actual
        else:
            # Si no tiene plan, usar comisión por defecto
            self.porcentaje_comision = self.terma.porcentaje_comision_actual
        
        # Calcular montos
        self.monto_comision_plataforma = (self.monto_total * self.porcentaje_comision) / Decimal('100')
        self.monto_para_terma = self.monto_total - self.monto_comision_plataforma
        
        self.save()
    
    def marcar_como_procesado(self):
        """Marca la distribución como procesada"""
        from django.utils import timezone
        self.estado = 'procesado'
        self.fecha_procesado = timezone.now()
        self.save()
    
    def marcar_pago_terma_enviado(self, referencia=None):
        """Marca que el pago fue enviado a la terma"""
        from django.utils import timezone
        self.estado = 'pagado_terma'
        self.fecha_pago_terma = timezone.now()
        if referencia:
            self.referencia_pago_terma = referencia
        self.save()
    
    def marcar_completado(self):
        """Marca todo el proceso como completado"""
        self.estado = 'completado'
        self.save()


class HistorialPagoTerma(models.Model):
    """
    Registro histórico de todos los pagos realizados a las termas
    """
    distribucion = models.ForeignKey(DistribucionPago, on_delete=models.CASCADE, related_name='pagos_realizados')
    terma = models.ForeignKey("termas.Terma", on_delete=models.CASCADE)
    
    monto_pagado = models.DecimalField(max_digits=10, decimal_places=2)
    fecha_pago = models.DateTimeField(auto_now_add=True)
    metodo_pago_usado = models.CharField(max_length=100, help_text="Método usado para pagar a la terma")
    referencia_externa = models.CharField(max_length=200, null=True, blank=True, 
                                        help_text="Referencia del sistema de pago externo")
    
    # Información bancaria o de contacto de la terma al momento del pago
    info_pago_terma = models.JSONField(null=True, blank=True, 
                                     help_text="Información de pago de la terma al momento del envío")
    
    observaciones = models.TextField(null=True, blank=True)
    exitoso = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Historial de Pago a Terma"
        verbose_name_plural = "Historial de Pagos a Termas"
        ordering = ['-fecha_pago']
    
    def __str__(self):
        return f"Pago a {self.terma.nombre_terma} - ${self.monto_pagado} - {self.fecha_pago.strftime('%d/%m/%Y')}"


class ResumenComisionesPlataforma(models.Model):
    """
    Resumen mensual de comisiones ganadas por la plataforma
    """
    mes = models.IntegerField()
    año = models.IntegerField()
    total_ventas = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_comisiones = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_pagado_termas = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    cantidad_transacciones = models.IntegerField(default=0)
    
    fecha_calculo = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('mes', 'año')
        verbose_name = "Resumen de Comisiones"
        verbose_name_plural = "Resúmenes de Comisiones"
        ordering = ['-año', '-mes']
    
    def __str__(self):
        return f"Comisiones {self.mes}/{self.año} - ${self.total_comisiones}"
