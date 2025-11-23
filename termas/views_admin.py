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
def aprobar_solicitud(request, solicitud_uuid):
    """Vista para aprobar una solicitud de terma."""
    print(f"[DEBUG] Entrando a aprobar_solicitud con UUID: {solicitud_uuid}")
    print(f"[DEBUG] Usuario rol: {request.session.get('usuario_rol')}")
    print(f"[DEBUG] Método: {request.method}")
    
    try:
        solicitud = get_object_or_404(SolicitudTerma, uuid=solicitud_uuid, estado='pendiente')
        
        # Crear la terma
        terma = Terma.objects.create(
            nombre_terma=solicitud.nombre_terma,
            descripcion_terma=solicitud.descripcion,
            direccion_terma=solicitud.direccion,
            comuna=solicitud.comuna,
            telefono_terma=solicitud.telefono_contacto,
            email_terma=solicitud.correo_institucional,
            rut_empresa=solicitud.rut_empresa if hasattr(solicitud, 'rut_empresa') and solicitud.rut_empresa else "",
            estado_suscripcion='activa',
            fecha_suscripcion=timezone.now().date()
        )

        # Si la solicitud incluye un plan seleccionado, asignarlo a la terma
        try:
            plan_seleccionado = solicitud.plan_seleccionado
            if plan_seleccionado:
                terma.plan_actual = plan_seleccionado
                # Actualizar campos derivados del plan en la terma
                terma.porcentaje_comision_actual = plan_seleccionado.porcentaje_comision
                terma.limite_fotos_actual = plan_seleccionado.limite_fotos
                terma.save()
        except Exception as e:
            # No bloquear la aprobación por un fallo al asignar plan; solo loguear
            pass

        # Gestión del usuario administrador
        usuario_admin = None
        password_temporal = None  
        
        if solicitud.usuario:
            # Ya existe un usuario asociado a la solicitud
            usuario_admin = solicitud.usuario
        else:
            # No hay usuario asociado, verificar si existe un usuario con el correo institucional
            try:
                usuario_admin = Usuario.objects.get(email=solicitud.correo_institucional)
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
                        terma=terma,
                        tiene_password_temporal=True
                    )
                    
                except Rol.DoesNotExist:
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
                
                # Actualizar la solicitud para vincular el usuario si no estaba vinculado
                if not solicitud.usuario:
                    solicitud.usuario = usuario_admin
                    
            except Rol.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': 'Error: Rol de administrador no encontrado en el sistema.'
                }, status=500)
        else:
            pass

        # Actualizar la solicitud
        solicitud.estado = 'aceptada'
        solicitud.terma = terma
        solicitud.fecha_respuesta = timezone.now()
        solicitud.save()

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
def rechazar_solicitud(request, solicitud_uuid):
    """Vista para rechazar una solicitud de terma."""
    
    try:
        data = json.loads(request.body)
        motivo_rechazo = data.get('motivo_rechazo', '')
        
        if not motivo_rechazo:
            return JsonResponse({
                'success': False,
                'message': 'Debes proporcionar un motivo de rechazo.'
            }, status=400)

        solicitud = get_object_or_404(SolicitudTerma, uuid=solicitud_uuid, estado='pendiente')
        
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
def detalles_solicitud(request, solicitud_uuid):
    """Vista para obtener los detalles de una solicitud."""
    
    try:
        solicitud = get_object_or_404(SolicitudTerma, uuid=solicitud_uuid)
        
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
    
    # Convertir mes y año a enteros si no están vacíos
    if mes_filtro:
        try:
            mes_filtro = int(mes_filtro)
        except (ValueError, TypeError):
            mes_filtro = None
    else:
        mes_filtro = None
        
    if año_filtro:
        try:
            año_filtro = int(año_filtro)
        except (ValueError, TypeError):
            año_filtro = None
    else:
        año_filtro = None
    
    # Query base
    distribuciones = DistribucionPago.objects.select_related(
        'compra', 'terma', 'plan_utilizado'
    ).order_by('-fecha_calculo')
    
    # Aplicar filtros
    if estado_filtro:
        distribuciones = distribuciones.filter(estado=estado_filtro)
    
    if terma_filtro:
        distribuciones = distribuciones.filter(terma__nombre_terma__icontains=terma_filtro)
    
    if mes_filtro:
        distribuciones = distribuciones.filter(fecha_calculo__month=mes_filtro)
    
    if año_filtro:
        distribuciones = distribuciones.filter(fecha_calculo__year=año_filtro)
    
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
            'mes': request.GET.get('mes', ''),  # Usar valor original de string
            'año': request.GET.get('año', ''),  # Usar valor original de string
        },
        'estados_choices': DistribucionPago.ESTADO_DISTRIBUCION,
        'current_year': timezone.now().year,
    }
    
    return render(request, 'administrador_general/distribuciones_pago.html', context)


def dashboard_comisiones_terma(request, terma_uuid):
    """Vista para que una terma vea sus propias comisiones y pagos"""
    from ventas.models import DistribucionPago, HistorialPagoTerma
    from ventas.utils import obtener_resumen_comisiones_terma
    from django.db.models import Sum, Count
    from usuarios.decorators import admin_terma_required
    
    # Verificar que el usuario es admin de esta terma
    terma = get_object_or_404(Terma, uuid=terma_uuid)
    
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
    
    return render(request, 'administrador_termas/dashboard_comisiones.html', context)


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
    
    # Convertir terma_id a entero si no está vacío
    if terma_id:
        try:
            terma_id = int(terma_id)
        except (ValueError, TypeError):
            terma_id = None
    else:
        terma_id = None
    
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
            'terma_id': request.GET.get('terma_id', '')  # Usar valor original de string
        },
        'mes_actual': mes_actual,
        'año_actual': año_actual,
    }
    
    return render(request, 'administrador_general/reporte_comisiones_diarias.html', context)


@admin_general_required
def ver_detalle_distribucion(request, distribucion_uuid):
    """
    Vista para mostrar los detalles completos de una distribución de pago
    """
    distribucion = get_object_or_404(DistribucionPago, uuid=distribucion_uuid)
    
    context = {
        'distribucion': distribucion,
        'compra': distribucion.compra,
        'terma': distribucion.terma,
        'plan': distribucion.plan_utilizado,
    }
    
    return render(request, 'administrador_general/detalle_distribucion.html', context)


@admin_general_required
def exportar_comisiones_diarias_csv(request):
    """Exporta el reporte de comisiones diarias a CSV para el administrador general."""
    from datetime import datetime
    from django.http import HttpResponse
    import csv

    fecha_inicio_str = request.GET.get('fecha_inicio')
    fecha_fin_str = request.GET.get('fecha_fin')
    terma_id_str = request.GET.get('terma_id')

    # Validar fechas
    if not fecha_inicio_str or not fecha_fin_str:
        return HttpResponse('Faltan parámetros de fecha', status=400)
    try:
        fecha_inicio = datetime.strptime(fecha_inicio_str, '%Y-%m-%d').date()
        fecha_fin = datetime.strptime(fecha_fin_str, '%Y-%m-%d').date()
    except ValueError:
        return HttpResponse('Formato de fecha inválido', status=400)

    # Procesar terma opcional
    terma_id = None
    if terma_id_str:
        try:
            terma_id = int(terma_id_str)
        except (ValueError, TypeError):
            terma_id = None

    # Obtener datos usando la utilidad existente
    from ventas.utils import obtener_reporte_comisiones_diarias
    reporte = obtener_reporte_comisiones_diarias(fecha_inicio, fecha_fin, terma_id)

    # Crear respuesta CSV
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = (
        f'attachment; filename="comisiones_diarias_{fecha_inicio}_{fecha_fin}.csv"'
    )
    response.write('\ufeff')  # BOM UTF-8

    writer = csv.writer(response)
    writer.writerow([
        'Fecha', 'Terma', 'Plan', '% Comisión', 'Ventas Totales',
        'Comisión Ganada', 'Pagado a Terma', 'Transacciones'
    ])

    # Estructura real: lista de días [{'fecha': date, 'termas': {nombre: datos}, 'totales': {...}}, ...]
    reporte_diario = reporte.get('reporte_diario', [])
    for dia in reporte_diario:
        fecha_obj = dia.get('fecha')
        fecha_str = fecha_obj.strftime('%Y-%m-%d') if hasattr(fecha_obj, 'strftime') else str(fecha_obj)
        termas_dict = dia.get('termas', {})
        for terma_nombre, datos in termas_dict.items():
            writer.writerow([
                fecha_str,
                terma_nombre,
                datos.get('plan', ''),
                datos.get('porcentaje_comision', ''),
                datos.get('ventas', 0),
                datos.get('comisiones', 0),
                datos.get('pagado_terma', 0),
                datos.get('transacciones', 0)
            ])

    return response


@admin_general_required
def usuarios_registrados(request):
    """Vista principal para gestión de usuarios registrados"""
    from django.core.paginator import Paginator
    from django.db.models import Q, Count
    
    # Filtros
    filtros = {
        'nombre': request.GET.get('nombre', ''),
        'email': request.GET.get('email', ''),
        'rol': request.GET.get('rol', ''),
        'estado': request.GET.get('estado', ''),
        'terma': request.GET.get('terma', '')
    }
    
    # Query base
    usuarios = Usuario.objects.select_related('rol', 'terma').order_by('-fecha_registro')
    
    # Aplicar filtros
    if filtros['nombre']:
        usuarios = usuarios.filter(
            Q(nombre__icontains=filtros['nombre']) |
            Q(apellido__icontains=filtros['nombre'])
        )
    
    if filtros['email']:
        usuarios = usuarios.filter(email__icontains=filtros['email'])
    
    if filtros['rol']:
        usuarios = usuarios.filter(rol__id=filtros['rol'])
    
    if filtros['estado']:
        estado_bool = filtros['estado'] == 'activo'
        usuarios = usuarios.filter(estado=estado_bool)
    
    if filtros['terma']:
        usuarios = usuarios.filter(terma__id=filtros['terma'])
    
    # Paginación
    paginator = Paginator(usuarios, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Estadísticas
    stats = {
        'total_usuarios': Usuario.objects.count(),
        'usuarios_activos': Usuario.objects.filter(estado=True).count(),
        'usuarios_inactivos': Usuario.objects.filter(estado=False).count(),
        'admins_terma': Usuario.objects.filter(rol__nombre='administrador_terma').count(),
        'clientes': Usuario.objects.filter(rol__nombre='cliente').count(),
    }
    
    # Datos para formularios
    roles = Rol.objects.filter(activo=True).order_by('nombre')
    termas = Terma.objects.filter(estado_suscripcion='activa').order_by('nombre_terma')
    
    context = {
        'page_obj': page_obj,
        'usuarios': page_obj,
        'stats': stats,
        'roles': roles,
        'termas': termas,
        'filtros': filtros
    }
    
    return render(request, 'administrador_general/usuarios_registrados.html', context)


@admin_general_required
@require_http_methods(["POST"])
def crear_usuario(request):
    """Vista para crear un nuevo usuario"""
    try:
        data = json.loads(request.body)
        
        # Validar datos requeridos
        required_fields = ['email', 'nombre', 'apellido', 'rol_id']
        for field in required_fields:
            if not data.get(field):
                return JsonResponse({
                    'success': False,
                    'message': f'El campo {field} es requerido.'
                }, status=400)
        
        # Verificar que el email no exista
        if Usuario.objects.filter(email=data['email']).exists():
            return JsonResponse({
                'success': False,
                'message': 'Ya existe un usuario con este email.'
            }, status=400)
        
        # Obtener el rol
        try:
            rol = Rol.objects.get(id=data['rol_id'], activo=True)
        except Rol.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Rol no válido.'
            }, status=400)
        
        # Validar terma si es administrador de terma
        terma = None
        if rol.nombre == 'administrador_terma' and data.get('terma_id'):
            try:
                terma = Terma.objects.get(id=data['terma_id'])
                # Verificar que la terma no tenga ya un administrador
                if Usuario.objects.filter(terma=terma, rol__nombre='administrador_terma').exists():
                    return JsonResponse({
                        'success': False,
                        'message': 'Esta terma ya tiene un administrador asignado.'
                    }, status=400)
            except Terma.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': 'Terma no válida.'
                }, status=400)
        
        # Generar contraseña temporal
        password_temporal = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
        
        # Crear el usuario
        usuario = Usuario.objects.create(
            email=data['email'],
            nombre=data['nombre'],
            apellido=data['apellido'],
            telefono=data.get('telefono', ''),
            rol=rol,
            terma=terma,
            estado=True,
            tiene_password_temporal=True
        )
        usuario.set_password(password_temporal)
        usuario.save()
        
        # Si es administrador de terma, asignarlo a la terma
        if terma and rol.nombre == 'administrador_terma':
            terma.administrador = usuario
            terma.save()
        
        # Enviar email con credenciales (opcional)
        try:
            contexto_email = {
                'usuario_nombre': usuario.get_full_name(),
                'email': usuario.email,
                'password': password_temporal,
                'rol': rol.nombre,
                'terma': terma.nombre_terma if terma else None,
                'login_url': request.build_absolute_uri('/usuarios/login/')
            }
            
            mensaje_html = render_to_string('emails/nuevo_usuario.html', contexto_email)
            
            send_mail(
                subject='Cuenta creada en MiTerma',
                message='',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[usuario.email],
                html_message=mensaje_html,
                fail_silently=True,
            )
        except Exception as e:
            print(f"Error enviando email: {e}")
        
        return JsonResponse({
            'success': True,
            'message': 'Usuario creado exitosamente.',
            'password_temporal': password_temporal
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error al crear usuario: {str(e)}'
        }, status=500)


@admin_general_required
@require_http_methods(["POST"])
def editar_usuario(request, usuario_uuid):
    """Vista para editar un usuario existente"""
    try:
        usuario = get_object_or_404(Usuario, uuid=usuario_uuid)
        data = json.loads(request.body)
        
        # Validar datos requeridos
        required_fields = ['nombre', 'apellido', 'rol_id']
        for field in required_fields:
            if not data.get(field):
                return JsonResponse({
                    'success': False,
                    'message': f'El campo {field} es requerido.'
                }, status=400)
        
        # Obtener el rol
        try:
            rol = Rol.objects.get(id=data['rol_id'], activo=True)
        except Rol.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Rol no válido.'
            }, status=400)
        
        # Validar terma si es administrador de terma
        terma = None
        if rol.nombre == 'administrador_terma':
            if data.get('terma_id'):
                try:
                    terma = Terma.objects.get(id=data['terma_id'])
                    # Verificar que la terma no tenga ya otro administrador
                    otro_admin = Usuario.objects.filter(
                        terma=terma, 
                        rol__nombre='administrador_terma'
                    ).exclude(id=usuario.id).first()
                    
                    if otro_admin:
                        return JsonResponse({
                            'success': False,
                            'message': 'Esta terma ya tiene otro administrador asignado.'
                        }, status=400)
                except Terma.DoesNotExist:
                    return JsonResponse({
                        'success': False,
                        'message': 'Terma no válida.'
                    }, status=400)
        
        # Actualizar usuario
        usuario.nombre = data['nombre']
        usuario.apellido = data['apellido']
        usuario.telefono = data.get('telefono', '')
        
        # Manejar cambio de rol
        rol_anterior = usuario.rol
        usuario.rol = rol
        
        # Manejar asignación de terma
        terma_anterior = usuario.terma
        usuario.terma = terma
        
        usuario.save()
        
        # Actualizar relaciones de terma
        if terma_anterior and terma_anterior != terma:
            # Remover de terma anterior
            if terma_anterior.administrador == usuario:
                terma_anterior.administrador = None
                terma_anterior.save()
        
        if terma and rol.nombre == 'administrador_terma':
            # Asignar a nueva terma
            terma.administrador = usuario
            terma.save()
        elif rol.nombre != 'administrador_terma' and usuario.terma:
            # Si cambió de rol y ya no es admin de terma, remover asignación
            if usuario.terma.administrador == usuario:
                usuario.terma.administrador = None
                usuario.terma.save()
            usuario.terma = None
            usuario.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Usuario actualizado exitosamente.'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error al actualizar usuario: {str(e)}'
        }, status=500)


@admin_general_required
@require_http_methods(["POST"])
def cambiar_estado_usuario(request, usuario_uuid):
    """Vista para habilitar/deshabilitar un usuario"""
    try:
        print(f"[DEBUG] Intentando cambiar estado de usuario UUID: {usuario_uuid}")
        usuario = get_object_or_404(Usuario, uuid=usuario_uuid)
        print(f"[DEBUG] Usuario encontrado: {usuario.email}")
        
        # No permitir desactivar al propio usuario
        # Usar múltiples métodos para obtener el usuario actual
        usuario_actual = None
        if hasattr(request, 'user') and hasattr(request.user, 'id'):
            usuario_actual = request.user
            print(f"[DEBUG] Usuario actual desde request.user: {usuario_actual.email}")
        elif 'usuario_id' in request.session:
            try:
                usuario_actual = Usuario.objects.get(id=request.session.get('usuario_id'))
                print(f"[DEBUG] Usuario actual desde sesión: {usuario_actual.email}")
            except Usuario.DoesNotExist:
                print(f"[DEBUG] No se encontró usuario con ID: {request.session.get('usuario_id')}")
                pass
        
        if usuario_actual and usuario_actual.id == usuario.id:
            print(f"[DEBUG] Intento de auto-desactivación bloqueado")
            return JsonResponse({
                'success': False,
                'message': 'No puedes desactivar tu propia cuenta.'
            }, status=400)
        
        # Cambiar estado
        estado_anterior = usuario.estado
        usuario.estado = not usuario.estado
        usuario.is_active = usuario.estado
        usuario.save()
        print(f"[DEBUG] Estado cambiado de {estado_anterior} a {usuario.estado}")
        
        # IMPORTANTE: NO remover al administrador de la terma al desactivar
        # Las vinculaciones se preservan para poder reactivar sin perder las asignaciones
        # Solo se desactiva el acceso, pero no se pierde la relación
        
        estado_texto = 'activado' if usuario.estado else 'desactivado'
        mensaje_vinculacion = ""
        
        if usuario.terma and usuario.rol and usuario.rol.nombre == 'administrador_terma':
            if usuario.estado:
                mensaje_vinculacion = f" Vinculación con terma '{usuario.terma.nombre_terma}' reactivada."
            else:
                mensaje_vinculacion = f" Vinculación con terma '{usuario.terma.nombre_terma}' preservada (inactiva)."
        
        print(f"[DEBUG] Usuario {estado_texto} exitosamente{mensaje_vinculacion}")
        
        return JsonResponse({
            'success': True,
            'message': f'Usuario {estado_texto} exitosamente.{mensaje_vinculacion}',
            'nuevo_estado': usuario.estado
        })
        
    except Exception as e:
        print(f"[DEBUG] Error en cambiar_estado_usuario: {e}")
        print(f"[DEBUG] Tipo de error: {type(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'message': f'Error al cambiar estado del usuario: {str(e)}'
        }, status=500)
        
    except Exception as e:
        print(f"Error en cambiar_estado_usuario: {e}")
        return JsonResponse({
            'success': False,
            'message': f'Error al cambiar estado del usuario: {str(e)}'
        }, status=500)


@admin_general_required
@require_http_methods(["GET"])
def detalle_usuario(request, usuario_uuid):
    """Vista para obtener los detalles de un usuario"""
    try:
        print(f"[DEBUG] Obteniendo detalles para usuario UUID: {usuario_uuid}")
        usuario = get_object_or_404(Usuario, uuid=usuario_uuid)
        print(f"[DEBUG] Usuario encontrado: {usuario.email}")
        
        # Obtener estadísticas si es cliente
        estadisticas = {}
        try:
            if usuario.rol and usuario.rol.nombre == 'cliente':
                print(f"[DEBUG] Calculando estadísticas para cliente")
                from ventas.models import Compra
                compras = Compra.objects.filter(cliente=usuario)
                total_gastado = 0
                for compra in compras:
                    if compra.monto_total:
                        total_gastado += float(compra.monto_total)
                
                ultima_compra = compras.last()
                estadisticas = {
                    'total_compras': compras.count(),
                    'total_gastado': total_gastado,
                    'ultima_compra': ultima_compra.fecha_compra.isoformat() if ultima_compra and ultima_compra.fecha_compra else None
                }
                print(f"[DEBUG] Estadísticas calculadas: {estadisticas}")
        except Exception as e:
            print(f"[DEBUG] Error al calcular estadísticas: {e}")
            estadisticas = {}
        
        # Preparar datos con manejo seguro de None
        try:
            data = {
                'id': usuario.id,
                'email': usuario.email or '',
                'nombre': usuario.nombre or '',
                'apellido': usuario.apellido or '',
                'telefono': usuario.telefono or '',
                'estado': bool(usuario.estado),
                'fecha_registro': usuario.fecha_registro.strftime('%d/%m/%Y %H:%M') if usuario.fecha_registro else 'No disponible',
                'rol': {
                    'id': usuario.rol.id if usuario.rol else None,
                    'nombre': usuario.rol.nombre if usuario.rol else 'Sin rol'
                },
                'terma': {
                    'id': usuario.terma.id if usuario.terma else None,
                    'nombre': usuario.terma.nombre_terma if usuario.terma else 'Sin asignar'
                },
                'estadisticas': estadisticas
            }
            print(f"[DEBUG] Datos preparados exitosamente")
        except Exception as e:
            print(f"[DEBUG] Error al preparar datos: {e}")
            raise e
        
        return JsonResponse({
            'success': True,
            'data': data
        })
        
    except Exception as e:
        print(f"[DEBUG] Error general en detalle_usuario: {e}")
        print(f"[DEBUG] Tipo de error: {type(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'message': f'Error al obtener detalles del usuario: {str(e)}'
        }, status=500)


@admin_general_required
@require_http_methods(["POST"])
def resetear_password_usuario(request, usuario_uuid):
    """Vista para resetear la contraseña de un usuario"""
    try:
        usuario = get_object_or_404(Usuario, uuid=usuario_uuid)
        
        # Generar nueva contraseña temporal
        password_temporal = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
        
        # Actualizar contraseña
        usuario.set_password(password_temporal)
        usuario.tiene_password_temporal = True
        usuario.save()
        
        # Enviar email con nueva contraseña (opcional)
        try:
            contexto_email = {
                'usuario_nombre': usuario.get_full_name(),
                'email': usuario.email,
                'password': password_temporal,
                'login_url': request.build_absolute_uri('/usuarios/login/')
            }
            
            mensaje_html = render_to_string('emails/password_reset_admin.html', contexto_email)
            
            send_mail(
                subject='Contraseña restablecida - MiTerma',
                message='',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[usuario.email],
                html_message=mensaje_html,
                fail_silently=True,
            )
        except Exception as e:
            print(f"Error enviando email: {e}")
        
        return JsonResponse({
            'success': True,
            'message': 'Contraseña restablecida exitosamente.',
            'password_temporal': password_temporal
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error al restablecer contraseña: {str(e)}'
        }, status=500)