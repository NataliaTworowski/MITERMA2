from django.contrib import admin
from .models import Terma, Calificacion, ImagenTerma, ServicioTerma, SolicitudTerma

@admin.register(Terma)
class TermaAdmin(admin.ModelAdmin):
    list_display = ['nombre_terma', 'comuna', 'estado_suscripcion', 'calificacion_promedio', 'administrador']
    list_filter = ['estado_suscripcion', 'comuna', 'fecha_suscripcion']
    search_fields = ['nombre_terma', 'descripcion_terma', 'direccion_terma', 'email_terma']
    list_editable = ['estado_suscripcion']
    ordering = ['nombre_terma']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('nombre_terma', 'descripcion_terma', 'direccion_terma', 'comuna')
        }),
        ('Contacto', {
            'fields': ('telefono_terma', 'email_terma')
        }),
        ('Suscripción', {
            'fields': ('estado_suscripcion', 'fecha_suscripcion', 'administrador')
        }),
        ('Calificación', {
            'fields': ('calificacion_promedio',)
        }),
    )

@admin.register(Calificacion)
class CalificacionAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'terma', 'puntuacion', 'fecha']
    list_filter = ['puntuacion', 'fecha']
    search_fields = ['usuario__nombre', 'terma__nombre_terma', 'comentario']

@admin.register(ImagenTerma)
class ImagenTermaAdmin(admin.ModelAdmin):
    list_display = ['terma', 'descripcion']
    search_fields = ['terma__nombre_terma', 'descripcion']

@admin.register(ServicioTerma)
class ServicioTermaAdmin(admin.ModelAdmin):
    list_display = ['terma', 'servicio']
    search_fields = ['terma__nombre_terma', 'servicio']

@admin.register(SolicitudTerma)
class SolicitudTermaAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'nombre_terma', 'estado', 'fecha_solicitud']
    list_filter = ['estado', 'fecha_solicitud']
    search_fields = ['usuario__nombre', 'nombre_terma']
    list_editable = ['estado']
