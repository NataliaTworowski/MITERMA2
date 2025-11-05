from django.contrib import admin
from .models import EntradaTipo, HorarioDisponible

@admin.register(EntradaTipo)
class EntradaTipoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'terma', 'precio', 'duracion_tipo', 'duracion_horas', 'estado')
    list_filter = ('terma', 'estado', 'duracion_tipo')
    search_fields = ('nombre', 'descripcion')
    
@admin.register(HorarioDisponible)
class HorarioDisponibleAdmin(admin.ModelAdmin):
    list_display = ('terma', 'entrada_tipo', 'fecha', 'hora_inicio', 'hora_fin', 'cupos_disponibles', 'cupos_totales')
    list_filter = ('terma', 'entrada_tipo', 'fecha')
    search_fields = ('terma__nombre_terma', 'entrada_tipo__nombre')
