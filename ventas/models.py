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
    compra = models.ForeignKey(Compra, on_delete=models.CASCADE, related_name="detalles")
    horario_disponible = models.ForeignKey(HorarioDisponible, on_delete=models.CASCADE)
    cantidad = models.IntegerField()
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    servicios = models.ManyToManyField('termas.ServicioTerma', blank=True, related_name='detalles_compra')


class Carrito(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    horario_disponible = models.ForeignKey(HorarioDisponible, on_delete=models.CASCADE)
    cantidad = models.IntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    fecha_agregado = models.DateTimeField(auto_now_add=True)
