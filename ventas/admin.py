from django.contrib import admin
from .models import (
    Compra, CodigoQR, RegistroEscaneo, 
    DistribucionPago, HistorialPagoTerma, ResumenComisionesPlataforma
)

@admin.register(CodigoQR)
class CodigoQRAdmin(admin.ModelAdmin):
    list_display = ['id', 'compra', 'usado', 'fecha_generacion', 'fecha_uso']
    list_filter = ['usado']
    search_fields = ['compra__usuario__email', 'compra__terma__nombre_terma']
    readonly_fields = ['fecha_generacion']
    
    def get_readonly_fields(self, request, obj=None):
        if obj:  # Si el objeto ya existe
            return self.readonly_fields + ('compra', 'codigo')
        return self.readonly_fields

@admin.register(RegistroEscaneo)
class RegistroEscaneoAdmin(admin.ModelAdmin):
    list_display = ['codigo_qr', 'fecha_escaneo', 'usuario_scanner', 'exitoso', 'ip_address']
    list_filter = ['exitoso', 'fecha_escaneo']
    search_fields = ['codigo_qr__compra__usuario__email', 'mensaje']
    readonly_fields = ['fecha_escaneo']

@admin.register(Compra)
class CompraAdmin(admin.ModelAdmin):
    list_display = ['id', 'usuario', 'terma', 'fecha_compra', 'fecha_visita', 'estado_pago', 'total']
    list_filter = ['estado_pago', 'fecha_compra', 'fecha_visita']
    search_fields = ['usuario__email', 'terma__nombre_terma', 'pagador_email']
    date_hierarchy = 'fecha_compra'


@admin.register(DistribucionPago)
class DistribucionPagoAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'compra', 'terma', 'plan_utilizado', 'monto_total', 
        'porcentaje_comision', 'monto_comision_plataforma', 'monto_para_terma', 
        'estado', 'fecha_calculo'
    ]
    list_filter = ['estado', 'plan_utilizado', 'fecha_calculo']
    search_fields = ['compra__id', 'terma__nombre_terma', 'compra__usuario__email']
    readonly_fields = [
        'compra', 'terma', 'monto_total', 'porcentaje_comision', 
        'monto_comision_plataforma', 'monto_para_terma', 'fecha_calculo',
        'fecha_procesado', 'fecha_pago_terma'
    ]
    date_hierarchy = 'fecha_calculo'
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('compra', 'terma', 'plan_utilizado')
        }),
        ('Cálculos de Distribución', {
            'fields': (
                'monto_total', 'porcentaje_comision', 
                'monto_comision_plataforma', 'monto_para_terma'
            )
        }),
        ('Estado y Fechas', {
            'fields': (
                'estado', 'fecha_calculo', 'fecha_procesado', 
                'fecha_pago_terma', 'referencia_pago_terma'
            )
        }),
        ('Observaciones', {
            'fields': ('observaciones',),
            'classes': ('collapse',)
        })
    )
    
    actions = ['recalcular_distribucion', 'simular_pago_terma']
    
    def recalcular_distribucion(self, request, queryset):
        """Acción para recalcular distribuciones seleccionadas"""
        count = 0
        for distribucion in queryset:
            if distribucion.estado == 'pendiente':
                distribucion.calcular_distribucion()
                count += 1
        
        self.message_user(
            request, 
            f"Se recalcularon {count} distribuciones."
        )
    recalcular_distribucion.short_description = "Recalcular distribuciones pendientes"
    
    def simular_pago_terma(self, request, queryset):
        """Acción para simular pago a termas"""
        from .utils import simular_pago_terma
        count = 0
        for distribucion in queryset:
            if distribucion.estado == 'procesado':
                pago = simular_pago_terma(distribucion)
                if pago:
                    count += 1
        
        self.message_user(
            request,
            f"Se simularon {count} pagos a termas."
        )
    simular_pago_terma.short_description = "Simular pago a termas (solo procesados)"


@admin.register(HistorialPagoTerma)
class HistorialPagoTermaAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'terma', 'monto_pagado', 'fecha_pago', 
        'metodo_pago_usado', 'referencia_externa', 'exitoso'
    ]
    list_filter = ['exitoso', 'metodo_pago_usado', 'fecha_pago']
    search_fields = [
        'terma__nombre_terma', 'referencia_externa', 
        'distribucion__compra__id'
    ]
    readonly_fields = ['fecha_pago', 'distribucion']
    date_hierarchy = 'fecha_pago'
    
    fieldsets = (
        ('Información del Pago', {
            'fields': (
                'distribucion', 'terma', 'monto_pagado', 
                'fecha_pago', 'exitoso'
            )
        }),
        ('Detalles del Método de Pago', {
            'fields': (
                'metodo_pago_usado', 'referencia_externa'
            )
        }),
        ('Información Adicional', {
            'fields': ('info_pago_terma', 'observaciones'),
            'classes': ('collapse',)
        })
    )


@admin.register(ResumenComisionesPlataforma)
class ResumenComisionesPlataformaAdmin(admin.ModelAdmin):
    list_display = [
        'mes', 'año', 'total_ventas', 'total_comisiones', 
        'total_pagado_termas', 'cantidad_transacciones', 'fecha_actualizacion'
    ]
    list_filter = ['año', 'mes']
    readonly_fields = [
        'total_ventas', 'total_comisiones', 'total_pagado_termas', 
        'cantidad_transacciones', 'fecha_calculo', 'fecha_actualizacion'
    ]
    ordering = ['-año', '-mes']
    
    actions = ['recalcular_resumen']
    
    def recalcular_resumen(self, request, queryset):
        """Acción para recalcular resúmenes mensuales"""
        from django.db.models import Sum, Count
        
        count = 0
        for resumen in queryset:
            # Obtener distribuciones del mes/año
            distribuciones = DistribucionPago.objects.filter(
                fecha_calculo__month=resumen.mes,
                fecha_calculo__year=resumen.año,
                estado__in=['procesado', 'pagado_terma', 'completado']
            )
            
            # Recalcular totales
            totales = distribuciones.aggregate(
                total_ventas=Sum('monto_total'),
                total_comisiones=Sum('monto_comision_plataforma'),
                total_pagado=Sum('monto_para_terma'),
                cantidad=Count('id')
            )
            
            resumen.total_ventas = totales['total_ventas'] or 0
            resumen.total_comisiones = totales['total_comisiones'] or 0
            resumen.total_pagado_termas = totales['total_pagado'] or 0
            resumen.cantidad_transacciones = totales['cantidad'] or 0
            resumen.save()
            count += 1
        
        self.message_user(
            request,
            f"Se recalcularon {count} resúmenes mensuales."
        )
    recalcular_resumen.short_description = "Recalcular resúmenes seleccionados"
