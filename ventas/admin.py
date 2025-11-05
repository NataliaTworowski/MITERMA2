from django.contrib import admin
from .models import Compra, CodigoQR, RegistroEscaneo

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
