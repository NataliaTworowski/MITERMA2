from django.contrib import admin
from django.shortcuts import render, redirect
from django.core.mail import send_mail
from django.contrib import messages
from django.utils import timezone
from django.template.loader import render_to_string
from django.contrib.auth.hashers import make_password
from django.utils.crypto import get_random_string
from django.urls import path
from django.utils.html import format_html
from .models import (
    Terma, Calificacion, ImagenTerma, ServicioTerma, SolicitudTerma,
    PlanSuscripcion, HistorialSuscripcion
)

@admin.register(Terma)
class TermaAdmin(admin.ModelAdmin):
    list_display = [
        'nombre_terma', 'comuna', 'estado_suscripcion', 'plan_actual',
        'porcentaje_comision_actual', 'calificacion_promedio', 'administrador'
    ]
    list_filter = ['estado_suscripcion', 'plan_actual', 'comuna', 'fecha_suscripcion']
    search_fields = ['nombre_terma', 'descripcion_terma', 'direccion_terma', 'email_terma']
    list_editable = ['estado_suscripcion']
    ordering = ['nombre_terma']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('nombre_terma', 'descripcion_terma', 'direccion_terma', 'comuna')
        }),
        ('Contacto', {
            'fields': ('telefono_terma', 'email_terma', 'rut_empresa')
        }),
        ('Suscripción', {
            'fields': ('estado_suscripcion', 'fecha_suscripcion', 'administrador')
        }),
        ('Plan y Configuración', {
            'fields': (
                'plan_actual', 'porcentaje_comision_actual', 
                'limite_fotos_actual', 'fecha_ultimo_pago'
            )
        }),
        ('Configuración Operativa', {
            'fields': ('limite_ventas_diario',)
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

from django.shortcuts import render, redirect
from django.core.mail import send_mail
from django.contrib import messages
from django.utils import timezone
from django.template.loader import render_to_string
from django.contrib.auth.hashers import make_password
from django.utils.crypto import get_random_string

@admin.register(SolicitudTerma)
class SolicitudTermaAdmin(admin.ModelAdmin):
    list_display = [
        'nombre_terma', 'correo_institucional', 'plan_seleccionado', 
        'estado', 'fecha_solicitud'
    ]
    list_filter = ['estado', 'plan_seleccionado', 'fecha_solicitud']
    search_fields = ['nombre_terma', 'correo_institucional']
    readonly_fields = ['fecha_solicitud']
    exclude = ['usuario', 'terma']

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path('gestionar-solicitudes/', 
                 self.admin_site.admin_view(self.gestionar_solicitudes), 
                 name='gestionar_solicitudes_termas'),
        ]
        return custom_urls + urls

    def gestionar_solicitudes(self, request):
        if request.method == 'POST':
            solicitud_id = request.POST.get('solicitud_id')
            action = request.POST.get('action')
            try:
                solicitud = SolicitudTerma.objects.get(id=solicitud_id)
                if action == 'aprobar':
                    self.aprobar_solicitud(request, solicitud)
                elif action == 'rechazar':
                    motivo = request.POST.get('motivo_rechazo')
                    self.rechazar_solicitud(request, solicitud, motivo)
            except Exception as e:
                messages.error(request, f'Error al procesar la solicitud: {str(e)}')
        
        solicitudes = SolicitudTerma.objects.all().order_by('-fecha_solicitud')
        return render(request, 'admin/solicitudes_termas.html', {'solicitudes': solicitudes})

    def aprobar_solicitud(self, request, solicitud):
        try:
            # Generar contraseña temporal
            temp_password = get_random_string(12)
            
            # Crear usuario administrador
            from usuarios.models import Usuario, Rol
            rol_admin_terma = Rol.objects.get(nombre='administrador_terma')
            usuario = Usuario.objects.create(
                email=solicitud.correo_institucional,
                nombre=solicitud.nombre_terma,
                password=make_password(temp_password),
                estado=True,
                rol=rol_admin_terma,
                tiene_password_temporal=True
            )

            # Obtener el plan seleccionado
            plan_seleccionado = solicitud.plan_seleccionado
            if not plan_seleccionado:
                # Si no hay plan seleccionado, asignar plan básico por defecto
                plan_seleccionado = PlanSuscripcion.objects.filter(nombre='basico').first()

            # Crear terma con configuración del plan
            terma = Terma.objects.create(
                nombre_terma=solicitud.nombre_terma,
                descripcion_terma=solicitud.descripcion,
                direccion_terma=solicitud.direccion,
                comuna=solicitud.comuna,
                telefono_terma=solicitud.telefono_contacto,
                email_terma=solicitud.correo_institucional,
                rut_empresa=solicitud.rut_empresa,
                estado_suscripcion='activa',
                fecha_suscripcion=timezone.now(),
                administrador=usuario,
                plan_actual=plan_seleccionado,
                porcentaje_comision_actual=plan_seleccionado.porcentaje_comision if plan_seleccionado else 5.00,
                limite_fotos_actual=plan_seleccionado.limite_fotos if plan_seleccionado else 5
            )

            # Actualizar solicitud
            solicitud.estado = 'aceptada'
            solicitud.fecha_respuesta = timezone.now()
            solicitud.usuario = usuario
            solicitud.terma = terma
            solicitud.save()

            # Enviar correo electrónico
            context = {
                'nombre_terma': solicitud.nombre_terma,
                'email': solicitud.correo_institucional,
                'password': temp_password,
                'login_url': request.build_absolute_uri('/login/')
            }
            
            html_message = render_to_string('emails/solicitud_aprobada.html', context)
            
            send_mail(
                'Tu solicitud de terma ha sido aprobada',
                'Tu solicitud ha sido aprobada. Por favor revisa el contenido en HTML.',
                'noreply@miterma.cl',
                [solicitud.correo_institucional],
                html_message=html_message,
                fail_silently=False,
            )

            messages.success(request, f'Solicitud aprobada correctamente para {solicitud.nombre_terma}')
        except Exception as e:
            messages.error(request, f'Error al aprobar la solicitud: {str(e)}')

    def rechazar_solicitud(self, request, solicitud, motivo):
        try:
            solicitud.estado = 'rechazada'
            solicitud.motivo_rechazo = motivo
            solicitud.fecha_respuesta = timezone.now()
            solicitud.save()

            # Enviar correo de rechazo
            send_mail(
                'Tu solicitud de terma ha sido rechazada',
                f'Lo sentimos, tu solicitud para {solicitud.nombre_terma} ha sido rechazada.\n\nMotivo: {motivo}',
                'noreply@miterma.cl',
                [solicitud.correo_institucional],
                fail_silently=False,
            )

            messages.success(request, f'Solicitud rechazada para {solicitud.nombre_terma}')
        except Exception as e:
            messages.error(request, f'Error al rechazar la solicitud: {str(e)}')


# Nuevos admins para sistema de suscripciones

@admin.register(PlanSuscripcion)
class PlanSuscripcionAdmin(admin.ModelAdmin):
    list_display = [
        'nombre', 'porcentaje_comision', 'limite_fotos', 
        'posicion_preferencial', 'marketing_premium', 'activo'
    ]
    list_filter = ['activo', 'posicion_preferencial', 'marketing_premium']
    list_editable = ['activo']
    ordering = ['porcentaje_comision']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('nombre', 'descripcion', 'activo')
        }),
        ('Comisión (Solo se cobra por venta)', {
            'fields': ('porcentaje_comision',)
        }),
        ('Límites y Beneficios', {
            'fields': (
                'limite_fotos', 'posicion_preferencial', 'marketing_premium',
                'dashboard_avanzado', 'soporte_prioritario', 'aparece_destacadas'
            )
        }),
        ('Precios (No se usan - Solo para referencia)', {
            'fields': ('precio_mensual', 'precio_anual'),
            'classes': ('collapse',),
            'description': 'Estos campos no se usan ya que solo se cobra comisión por venta.'
        }),
    )

@admin.register(HistorialSuscripcion)
class HistorialSuscripcionAdmin(admin.ModelAdmin):
    list_display = [
        'terma', 'plan_anterior', 'plan_nuevo', 'fecha_cambio', 'usuario_admin'
    ]
    list_filter = ['plan_anterior', 'plan_nuevo', 'fecha_cambio']
    search_fields = ['terma__nombre_terma', 'motivo']
    ordering = ['-fecha_cambio']
    date_hierarchy = 'fecha_cambio'
    readonly_fields = ['fecha_cambio']
