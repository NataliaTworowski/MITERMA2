from django.contrib import admin
from .models import EntradaTipo

@admin.register(EntradaTipo)
class EntradaTipoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'terma', 'precio', 'fecha', 'duracion_tipo', 'duracion_horas', 'cupos_disponibles', 'cupos_totales', 'estado')
    list_filter = ('terma', 'estado', 'duracion_tipo', 'fecha')
    search_fields = ('nombre', 'descripcion')
    list_editable = ('cupos_disponibles', 'cupos_totales')
    date_hierarchy = 'fecha'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('terma')
