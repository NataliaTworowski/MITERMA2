from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods
from .models import SolicitudTerma, Terma
from usuarios.models import Usuario, Rol
from ventas.models import DistribucionPago
import json
from django.utils import timezone
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.conf import settings
import random
import string
from django.contrib.auth.hashers import make_password
from usuarios.decorators import admin_general_required

@admin_general_required
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

        # Si la solicitud incluye un plan seleccionado, asignarlo a la terma
        try:
            plan_seleccionado = solicitud.plan_seleccionado
            if plan_seleccionado:
                terma.plan_actual = plan_seleccionado
                # Actualizar campos derivados del plan en la terma
                terma.porcentaje_comision_actual = plan_seleccionado.porcentaje_comision
                terma.limite_fotos_actual = plan_seleccionado.limite_fotos
                terma.save()
                print(f"[DEBUG] Plan asignado a la terma: {plan_seleccionado.nombre} (ID {plan_seleccionado.id})")
        except Exception as e:
            # No bloquear la aprobación por un fallo al asignar plan; solo loguear
            print(f"[DEBUG] No se pudo asignar plan a la terma automáticamente: {e}")

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

@admin_general_required
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

@admin_general_required
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


@admin_general_required
def ver_distribuciones_pago(request):
    """Vista para que los administradores vean las distribuciones de pago"""
    from ventas.models import DistribucionPago, ResumenComisionesPlataforma
    from django.db.models import Sum, Count
    from django.core.paginator import Paginator
    import json
    
    # Filtros
    estado_filtro = request.GET.get('estado', '')
    terma_filtro = request.GET.get('terma', '')
    mes_filtro = request.GET.get('mes', '')
    año_filtro = request.GET.get('año', '')
    
    # Query base
    distribuciones = DistribucionPago.objects.select_related(
        'compra', 'terma', 'plan_utilizado'
    ).order_by('-fecha_calculo')
    
    # Aplicar filtros
    if estado_filtro:
        distribuciones = distribuciones.filter(estado=estado_filtro)
    
    if terma_filtro:
        distribuciones = distribuciones.filter(terma__nombre_terma__icontains=terma_filtro)
    
    if mes_filtro and año_filtro:
        distribuciones = distribuciones.filter(
            fecha_calculo__month=mes_filtro,
            fecha_calculo__year=año_filtro
        )
    
    # Paginación
    paginator = Paginator(distribuciones, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Estadísticas generales
    stats = DistribucionPago.objects.aggregate(
        total_ventas=Sum('monto_total'),
        total_comisiones=Sum('monto_comision_plataforma'),
        total_pagado_termas=Sum('monto_para_terma'),
        total_transacciones=Count('id')
    )
    
    # Resúmenes mensuales recientes
    resumenes = ResumenComisionesPlataforma.objects.order_by('-año', '-mes')[:12]
    
    # Obtener lista de termas para el filtro
    termas = Terma.objects.filter(estado_suscripcion='activa').order_by('nombre_terma')
    
    context = {
        'page_obj': page_obj,
        'distribuciones': page_obj,
        'stats': stats,
        'resumenes': resumenes,
        'termas': termas,
        'filtros': {
            'estado': estado_filtro,
            'terma': terma_filtro,
            'mes': mes_filtro,
            'año': año_filtro,
        },
        'estados_choices': DistribucionPago.ESTADO_DISTRIBUCION,
        'current_year': timezone.now().year,
    }
    
    return render(request, 'termas/admin/distribuciones_pago.html', context)


def dashboard_comisiones_terma(request, terma_id):
    """Vista para que una terma vea sus propias comisiones y pagos"""
    from ventas.models import DistribucionPago, HistorialPagoTerma
    from ventas.utils import obtener_resumen_comisiones_terma
    from django.db.models import Sum, Count
    from usuarios.decorators import admin_terma_required
    
    # Verificar que el usuario es admin de esta terma
    terma = get_object_or_404(Terma, id=terma_id)
    
    # Obtener mes y año de los parámetros o usar el actual
    mes = request.GET.get('mes', timezone.now().month)
    año = request.GET.get('año', timezone.now().year)
    
    try:
        mes = int(mes)
        año = int(año)
    except (ValueError, TypeError):
        mes = timezone.now().month
        año = timezone.now().year
    
    # Obtener resumen del mes actual
    resumen_actual = obtener_resumen_comisiones_terma(terma, mes, año)
    
    # Distribuciones del mes
    distribuciones_mes = DistribucionPago.objects.filter(
        terma=terma,
        fecha_calculo__month=mes,
        fecha_calculo__year=año
    ).select_related('compra', 'plan_utilizado').order_by('-fecha_calculo')
    
    # Historial de pagos del mes
    pagos_mes = HistorialPagoTerma.objects.filter(
        terma=terma,
        fecha_pago__month=mes,
        fecha_pago__year=año
    ).order_by('-fecha_pago')
    
    # Resumen histórico (últimos 12 meses)
    resumen_historico = []
    from datetime import datetime, timedelta
    
    for i in range(12):
        fecha = datetime.now() - timedelta(days=30*i)
        resumen = obtener_resumen_comisiones_terma(terma, fecha.month, fecha.year)
        if resumen['cantidad_transacciones'] > 0:
            resumen_historico.append(resumen)
    
    context = {
        'terma': terma,
        'resumen_actual': resumen_actual,
        'distribuciones_mes': distribuciones_mes,
        'pagos_mes': pagos_mes,
        'resumen_historico': resumen_historico[:6],  # Solo 6 meses más recientes
        'mes_actual': mes,
        'año_actual': año,
        'plan_actual': terma.plan_actual,
    }
    
    return render(request, 'termas/dashboard_comisiones.html', context)


@admin_general_required
def reporte_comisiones_diarias(request):
    """Vista para mostrar reportes detallados de comisiones diarias"""
    from ventas.utils import (
        obtener_reporte_comisiones_diarias, 
        obtener_acumulado_comisiones_plataforma,
        obtener_top_termas_comisiones
    )
    from datetime import datetime, timedelta
    from django.utils import timezone
    
    # Obtener parámetros de filtro
    fecha_inicio_str = request.GET.get('fecha_inicio')
    fecha_fin_str = request.GET.get('fecha_fin')
    terma_id = request.GET.get('terma_id')
    
    # Procesar fechas
    try:
        if fecha_inicio_str:
            fecha_inicio = datetime.strptime(fecha_inicio_str, '%Y-%m-%d').date()
        else:
            fecha_inicio = (timezone.now() - timedelta(days=30)).date()
            
        if fecha_fin_str:
            fecha_fin = datetime.strptime(fecha_fin_str, '%Y-%m-%d').date()
        else:
            fecha_fin = timezone.now().date()
    except ValueError:
        # Si hay error en las fechas, usar valores por defecto
        fecha_inicio = (timezone.now() - timedelta(days=30)).date()
        fecha_fin = timezone.now().date()
    
    # Obtener reporte
    reporte = obtener_reporte_comisiones_diarias(fecha_inicio, fecha_fin, terma_id)
    
    # Obtener acumulado histórico
    acumulado_total = obtener_acumulado_comisiones_plataforma()
    
    # Obtener top termas del período
    mes_actual = timezone.now().month
    año_actual = timezone.now().year
    top_termas_mes = obtener_top_termas_comisiones(10, mes_actual, año_actual)
    top_termas_historico = obtener_top_termas_comisiones(10)
    
    # Obtener lista de termas para el filtro
    termas = Terma.objects.filter(estado_suscripcion='activa').order_by('nombre_terma')
    
    # Calcular estadísticas adicionales
    if reporte['reporte_diario']:
        promedio_diario = {
            'comisiones': reporte['totales_periodo']['total_comisiones'] / len(reporte['reporte_diario']) if len(reporte['reporte_diario']) > 0 else 0,
            'ventas': reporte['totales_periodo']['total_ventas'] / len(reporte['reporte_diario']) if len(reporte['reporte_diario']) > 0 else 0,
            'transacciones': reporte['totales_periodo']['total_transacciones'] / len(reporte['reporte_diario']) if len(reporte['reporte_diario']) > 0 else 0
        }
    else:
        promedio_diario = {'comisiones': 0, 'ventas': 0, 'transacciones': 0}
    
    context = {
        'reporte': reporte,
        'acumulado_total': acumulado_total,
        'top_termas_mes': top_termas_mes,
        'top_termas_historico': top_termas_historico,
        'promedio_diario': promedio_diario,
        'termas': termas,
        'filtros': {
            'fecha_inicio': fecha_inicio.strftime('%Y-%m-%d'),
            'fecha_fin': fecha_fin.strftime('%Y-%m-%d'),
            'terma_id': terma_id
        },
        'mes_actual': mes_actual,
        'año_actual': año_actual,
    }
    
    return render(request, 'termas/admin/reporte_comisiones_diarias.html', context)


@admin_general_required
def ver_detalle_distribucion(request, distribucion_id):
    """
    Vista para mostrar los detalles completos de una distribución de pago
    """
    distribucion = get_object_or_404(DistribucionPago, id=distribucion_id)
    
    context = {
        'distribucion': distribucion,
        'compra': distribucion.compra,
        'terma': distribucion.terma,
        'plan': distribucion.plan_utilizado,
    }
    
    return render(request, 'termas/admin/detalle_distribucion.html', context)