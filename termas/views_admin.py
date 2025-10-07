from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods
from .models import SolicitudTerma, Terma
from usuarios.models import Usuario, Rol
import json
from django.utils import timezone

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

        # Si la solicitud tiene un usuario asociado, asignarle el rol de administrador
        if solicitud.usuario:
            try:
                rol_admin = Rol.objects.get(id=2)  # ID 2 = Administrador
                solicitud.usuario.rol = rol_admin
                solicitud.usuario.terma = terma  # Asignar la terma al usuario
                solicitud.usuario.save()
                print(f"[DEBUG] Usuario {solicitud.usuario.email} actualizado con rol admin")
                
                # Asignar el usuario como administrador de la terma
                terma.administrador = solicitud.usuario
                terma.save()
                print(f"[DEBUG] Usuario asignado como administrador de la terma")
            except Rol.DoesNotExist:
                print("[DEBUG] Error: Rol de administrador no encontrado")
                return JsonResponse({
                    'success': False,
                    'message': 'Error: Rol de administrador no encontrado en el sistema.'
                }, status=500)
        else:
            print("[DEBUG] Solicitud sin usuario asociado - terma creada sin administrador específico")

        # Actualizar la solicitud
        solicitud.estado = 'aceptada'
        solicitud.terma = terma
        solicitud.fecha_respuesta = timezone.now()
        solicitud.save()
        print(f"[DEBUG] Solicitud actualizada a estado: {solicitud.estado}")

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