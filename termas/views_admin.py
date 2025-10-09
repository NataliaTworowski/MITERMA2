from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods
from .models import SolicitudTerma, Terma
from usuarios.models import Usuario, Rol
import json
from django.utils import timezone
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.conf import settings
import random
import string
from django.contrib.auth.hashers import make_password

def verificar_admin_general(view_func):
    """Decorador personalizado para verificar si el usuario es administrador general."""
    def wrapper(request, *args, **kwargs):
        # Verificar si el usuario está logueado
        if 'usuario_id' not in request.session:
            return JsonResponse({
                'success': False,
                'message': 'Debes iniciar sesión para acceder.'
            }, status=401)
        
        # Verificar si el usuario tiene el rol correcto (ID=4 para administrador_general)
        if request.session.get('usuario_rol') != 4:
            return JsonResponse({
                'success': False,
                'message': 'No tienes permisos para realizar esta acción.'
            }, status=403)
        
        return view_func(request, *args, **kwargs)
    
    return wrapper

@verificar_admin_general
@require_http_methods(["POST"])
def aprobar_solicitud(request, solicitud_id):
    """Vista para aprobar una solicitud de terma."""
    print(f"[DEBUG] Entrando a aprobar_solicitud con ID: {solicitud_id}")
    print(f"[DEBUG] Usuario rol: {request.session.get('usuario_rol')}")
    print(f"[DEBUG] Método: {request.method}")
    
    try:
        solicitud = get_object_or_404(SolicitudTerma, id=solicitud_id, estado='pendiente')
        print(f"[DEBUG] Solicitud encontrada: {solicitud.nombre_terma}")
        print(f"[DEBUG] Usuario asociado: {solicitud.usuario}")
        
        # Crear la terma
        terma = Terma.objects.create(
            nombre_terma=solicitud.nombre_terma,
            descripcion_terma=solicitud.descripcion,
            direccion_terma=solicitud.direccion,
            comuna=solicitud.comuna,
            telefono_terma=solicitud.telefono_contacto,
            email_terma=solicitud.correo_institucional,
            estado_suscripcion='activa',
            fecha_suscripcion=timezone.now().date()
        )
        print(f"[DEBUG] Terma creada con ID: {terma.id}")

        # Gestión del usuario administrador
        usuario_admin = None
        password_temporal = None  
        
        if solicitud.usuario:
            # Ya existe un usuario asociado a la solicitud
            usuario_admin = solicitud.usuario
            print(f"[DEBUG] Usuario existente encontrado: {usuario_admin.email}")
        else:
            # No hay usuario asociado, verificar si existe un usuario con el correo institucional
            try:
                usuario_admin = Usuario.objects.get(email=solicitud.correo_institucional)
                print(f"[DEBUG] Usuario encontrado por correo institucional: {usuario_admin.email}")
            except Usuario.DoesNotExist:
                # No existe usuario, crear uno nuevo
                try:
                    rol_admin = Rol.objects.get(id=2)  # ID 2 = Administrador
                    
                    # Generar contraseña temporal
                    password_temporal = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
                    
                    # Crear el nuevo usuario
                    usuario_admin = Usuario.objects.create(
                        email=solicitud.correo_institucional,
                        password=make_password(password_temporal),
                        nombre="Administrador",  
                        apellido="Terma",
                        telefono=solicitud.telefono_contacto,
                        rol=rol_admin,
                        estado=True,
                        terma=terma
                    )
                    print(f"[DEBUG] Nuevo usuario creado: {usuario_admin.email} con contraseña temporal")
                    
                except Rol.DoesNotExist:
                    print("[DEBUG] Error: Rol de administrador no encontrado")
                    return JsonResponse({
                        'success': False,
                        'message': 'Error: Rol de administrador no encontrado en el sistema.'
                    }, status=500)

        # Asignar el rol de administrador y la terma al usuario
        if usuario_admin:
            try:
                rol_admin = Rol.objects.get(id=2)  # ID 2 = Administrador
                usuario_admin.rol = rol_admin
                usuario_admin.terma = terma
                usuario_admin.save()
                print(f"[DEBUG] Usuario {usuario_admin.email} actualizado con rol admin y terma asignada")
                
                # Asignar el usuario como administrador de la terma
                terma.administrador = usuario_admin
                terma.save()
                print(f"[DEBUG] Usuario asignado como administrador de la terma")
                
                # Actualizar la solicitud para vincular el usuario si no estaba vinculado
                if not solicitud.usuario:
                    solicitud.usuario = usuario_admin
                    
            except Rol.DoesNotExist:
                print("[DEBUG] Error: Rol de administrador no encontrado")
                return JsonResponse({
                    'success': False,
                    'message': 'Error: Rol de administrador no encontrado en el sistema.'
                }, status=500)
        else:
            print("[DEBUG] Error: No se pudo crear o encontrar usuario administrador")

        # Actualizar la solicitud
        solicitud.estado = 'aceptada'
        solicitud.terma = terma
        solicitud.fecha_respuesta = timezone.now()
        solicitud.save()
        print(f"[DEBUG] Solicitud actualizada a estado: {solicitud.estado}")

        # Enviar correo de aprobación
        try:
            contexto_email = {
                'nombre_terma': solicitud.nombre_terma,
                'direccion': solicitud.direccion,
                'comuna': solicitud.comuna.nombre if solicitud.comuna else '',
                'telefono': solicitud.telefono_contacto,
                'email': solicitud.correo_institucional,
                'usuario_nombre': f"{usuario_admin.nombre} {usuario_admin.apellido}" if usuario_admin else "Administrador",
                'password': password_temporal,  # Agregar contraseña temporal
                'login_url': request.build_absolute_uri('/usuarios/login/')  # URL de login
            }
            
            mensaje_html = render_to_string('emails/solicitud_aprobada.html', contexto_email)
            
            # Determinar el destinatario del correo
            email_destinatario = usuario_admin.email if usuario_admin else solicitud.correo_institucional
            
            send_mail(
                subject='Solicitud de Terma Aprobada - MiTerma',
                message='',  # Mensaje en texto plano vacío
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email_destinatario],
                html_message=mensaje_html,
                fail_silently=False,
            )
            print(f"[DEBUG] Correo de aprobación enviado a: {email_destinatario}")
            
        except Exception as e:
            print(f"[DEBUG] Error al enviar correo de aprobación: {str(e)}")
            # No retornamos error porque la solicitud ya fue aprobada exitosamente

        return JsonResponse({
            'success': True,
            'message': 'Solicitud aprobada correctamente.'
        })

    except Exception as e:
        print(f"[DEBUG] Error en aprobar_solicitud: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'Error al procesar la solicitud: {str(e)}'
        }, status=500)

@verificar_admin_general
@require_http_methods(["POST"])
def rechazar_solicitud(request, solicitud_id):
    """Vista para rechazar una solicitud de terma."""
    
    try:
        data = json.loads(request.body)
        motivo_rechazo = data.get('motivo_rechazo', '')
        
        if not motivo_rechazo:
            return JsonResponse({
                'success': False,
                'message': 'Debes proporcionar un motivo de rechazo.'
            }, status=400)

        solicitud = get_object_or_404(SolicitudTerma, id=solicitud_id, estado='pendiente')
        
        # Actualizar la solicitud
        solicitud.estado = 'rechazada'
        solicitud.motivo_rechazo = motivo_rechazo
        solicitud.fecha_respuesta = timezone.now()
        solicitud.save()

        # Enviar correo de rechazo
        try:
            contexto_email = {
                'nombre_terma': solicitud.nombre_terma,
                'motivo_rechazo': motivo_rechazo,
                'usuario_nombre': f"{solicitud.usuario.nombre} {solicitud.usuario.apellido}" if solicitud.usuario else "Solicitante"
            }
            
            mensaje_html = render_to_string('emails/solicitud_rechazada.html', contexto_email)
            
            # Determinar el destinatario del correo
            email_destinatario = solicitud.usuario.email if solicitud.usuario else solicitud.correo_institucional
            
            send_mail(
                subject='Solicitud de Terma Rechazada - MiTerma',
                message='',  # Mensaje en texto plano vacío
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email_destinatario],
                html_message=mensaje_html,
                fail_silently=False,
            )
            print(f"[DEBUG] Correo de rechazo enviado a: {email_destinatario}")
            
        except Exception as e:
            print(f"[DEBUG] Error al enviar correo de rechazo: {str(e)}")
            # No retornamos error porque el rechazo ya fue procesado exitosamente

        return JsonResponse({
            'success': True,
            'message': 'Solicitud rechazada correctamente.'
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error al procesar la solicitud: {str(e)}'
        }, status=500)

@verificar_admin_general
@require_http_methods(["GET"])
def detalles_solicitud(request, solicitud_id):
    """Vista para obtener los detalles de una solicitud."""
    
    try:
        solicitud = get_object_or_404(SolicitudTerma, id=solicitud_id)
        
        datos = {
            'id': solicitud.id,
            'nombre_terma': solicitud.nombre_terma,
            'descripcion': solicitud.descripcion,
            'rut_empresa': solicitud.rut_empresa,
            'correo_institucional': solicitud.correo_institucional,
            'telefono_contacto': solicitud.telefono_contacto,
            'region': solicitud.region.nombre if solicitud.region else None,
            'comuna': solicitud.comuna.nombre if solicitud.comuna else None,
            'direccion': solicitud.direccion,
            'estado': solicitud.estado,
            'fecha_solicitud': solicitud.fecha_solicitud.strftime('%d/%m/%Y %H:%M'),
            'solicitante': {
                'nombre': f"{solicitud.usuario.nombre} {solicitud.usuario.apellido}" if solicitud.usuario else "No registrado",
                'email': solicitud.usuario.email if solicitud.usuario else None,
            } if solicitud.usuario else None
        }

        return JsonResponse({
            'success': True,
            'data': datos
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error al obtener los detalles: {str(e)}'
        }, status=500)