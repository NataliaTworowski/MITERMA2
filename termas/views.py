from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.db.models import Q
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.utils.html import escape
from .models import Terma, Region, Comuna, ImagenTerma
from usuarios.models import Usuario
from usuarios.decorators import admin_terma_required
import os
import logging
from entradas.models import EntradaTipo

logger = logging.getLogger('termas.views')

def lista_termas(request):
    """Vista para mostrar lista de termas."""
    termas = Terma.objects.filter(estado_suscripcion='true').select_related('ciudad', 'ciudad__region')
    context = {
        'title': 'Termas Disponibles - MiTerma',
        'termas': termas
    }
    return render(request, 'termas/lista.html', context)

def detalle_terma(request, uuid):
    """Vista para mostrar detalle de una terma."""
    terma = get_object_or_404(Terma, uuid=uuid, estado_suscripcion='true')
    context = {
        'title': f'Terma {terma.nombre_terma} - MiTerma',
        'terma': terma
    }
    return render(request, 'termas/detalle.html', context)

def buscar_termas(request):
    """Vista para buscar termas y mostrar resultados en inicio.html de usuarios."""
    
    # Verificar si el usuario está logueado
    if 'usuario_id' not in request.session:
        messages.error(request, 'Debes iniciar sesión para acceder.')
        return redirect('core:home')
    
    try:
        usuario = Usuario.objects.get(id=request.session['usuario_id'])
        
        # Obtener regiones y ciudades para los selectores
        regiones = Region.objects.all().order_by('nombre')
        comunas = Comuna.objects.all().select_related('region').order_by('region__nombre', 'nombre')
        
        # Manejar búsqueda de termas
        busqueda = request.GET.get('busqueda', '').strip()
        region_id = request.GET.get('region', '')
        comuna_id = request.GET.get('comuna', '')
        
        # Construir query de búsqueda
        query = Q(estado_suscripcion='activa')
        # Si hay filtros, agregarlos al query
        if busqueda:
            query &= (
                Q(nombre_terma__icontains=busqueda) |
                Q(descripcion_terma__icontains=busqueda) |
                Q(comuna__nombre__icontains=busqueda) |
                Q(comuna__region__nombre__icontains=busqueda)
            )
        if region_id:
            query &= Q(comuna__region__id=region_id)
        if comuna_id:
            query &= Q(comuna__id=comuna_id)

        # Ejecutar la consulta (si no hay filtros, muestra todas las termas activas)
        termas_activas = Terma.objects.filter(query).select_related('comuna', 'comuna__region')

        # Ofertas Destacadas: 4 termas con el precio de entrada más barato
        # Filtrar termas con precio mínimo válido
        termas_con_precio = [t for t in termas_activas if t.precio_minimo() is not None]
        ofertas_destacadas = sorted(
            termas_con_precio,
            key=lambda t: t.precio_minimo()
        )[:4]

        # Filtrar termas con calificación válida (aunque no tengan precio)
        mejores_termas = sorted(
            [t for t in termas_activas if t.calificacion_promedio is not None],
            key=lambda t: t.calificacion_promedio,
            reverse=True
        )[:4]

        print('DEBUG mejores_termas:', [(t.id, t.nombre_terma, t.calificacion_promedio) for t in mejores_termas])
        context = {
            'title': 'Inicio - MiTerma',
            'usuario': usuario,
            'ofertas_destacadas': ofertas_destacadas,
            'mejores_termas': mejores_termas,
            'busqueda': busqueda,
            'region_seleccionada': region_id,
            'comuna_seleccionada': comuna_id,
            'regiones': regiones,
            'comunas': comunas,
            'total_resultados': len(mejores_termas)
        }
        # Renderizar el template de usuarios con los resultados
        return render(request, 'clientes/Inicio_cliente.html', context)
        
    except Usuario.DoesNotExist:
        messages.error(request, 'Sesión inválida.')
        return redirect('core:home')
    
@admin_terma_required
def subir_fotos(request):
    """Vista para gestionar las fotos de la terma - Migrada a Django Auth."""
    try:
        # El decorador ya verificó que el usuario está autenticado y es admin_terma
        usuario = request.user
        
        # Verificar que el usuario tenga una terma asignada
        if not usuario.terma:
            messages.error(request, 'No tienes una terma asignada. Contacta al administrador.')
            return redirect('usuarios:adm_termas')
        
        # Procesar subida de foto
        if request.method == 'POST':
            foto = request.FILES.get('foto')
            descripcion = request.POST.get('descripcion', '').strip()
            
            # Verificar si es una petición AJAX
            is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            
            if not foto:
                error_msg = 'Por favor selecciona una foto.'
                if is_ajax:
                    return JsonResponse({'success': False, 'message': error_msg})
                messages.error(request, error_msg)
                return redirect('termas:subir_fotos')
            
            # Validar tipo de archivo
            allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp']
            if foto.content_type not in allowed_types:
                error_msg = 'Solo se permiten archivos JPG, PNG y WEBP.'
                if is_ajax:
                    return JsonResponse({'success': False, 'message': error_msg})
                messages.error(request, error_msg)
                return redirect('termas:subir_fotos')
            
            # Validar tamaño (10MB máximo)
            if foto.size > 10 * 1024 * 1024:  # 10MB
                error_msg = 'La foto no puede superar los 10MB.'
                if is_ajax:
                    return JsonResponse({'success': False, 'message': error_msg})
                messages.error(request, error_msg)
                return redirect('termas:subir_fotos')
            
            # Validar límite de fotos según el plan
            fotos_actuales = ImagenTerma.objects.filter(terma=usuario.terma).count()
            
            # Verificar si tiene fotos excedentes primero
            if usuario.terma.tiene_fotos_excedentes():
                fotos_excedentes = usuario.terma.fotos_excedentes_cantidad()
                plan_nombre = usuario.terma.plan_actual.get_nombre_display() if usuario.terma.plan_actual else "Básico"
                error_msg = f'No puedes subir más fotos porque tienes {fotos_excedentes} fotos que exceden el límite de tu plan {plan_nombre} ({usuario.terma.limite_fotos_actual} fotos). Debes eliminar {fotos_excedentes} fotos primero.'
                
                if is_ajax:
                    return JsonResponse({'success': False, 'message': error_msg})
                messages.error(request, error_msg)
                return redirect('termas:subir_fotos')
            
            # Verificar límite normal de fotos
            limite_fotos = usuario.terma.limite_fotos_actual
            
            # Verificar si puede subir más fotos (-1 significa ilimitado)
            if limite_fotos != -1 and fotos_actuales >= limite_fotos:
                plan_nombre = usuario.terma.plan_actual.get_nombre_display() if usuario.terma.plan_actual else "Básico"
                if limite_fotos == 5:
                    error_msg = f'Has alcanzado el límite de {limite_fotos} fotos de tu plan {plan_nombre}. Considera actualizar a un plan superior.'
                else:
                    error_msg = f'Has alcanzado el límite de {limite_fotos} fotos de tu plan {plan_nombre}.'
                
                if is_ajax:
                    return JsonResponse({'success': False, 'message': error_msg})
                messages.error(request, error_msg)
                return redirect('termas:subir_fotos')
            
            try:
                # Generar nombre único para el archivo
                import uuid
                from django.core.files.storage import default_storage
                from django.core.files.base import ContentFile
                
                # Generar nombre único
                extension = os.path.splitext(foto.name)[1]
                filename = f"fotos_termas/{uuid.uuid4()}{extension}"
                
                # Guardar archivo
                saved_path = default_storage.save(filename, ContentFile(foto.read()))
                
                # Crear URL completa
                from django.conf import settings
                url_completa = f"{settings.MEDIA_URL}{saved_path}"
                
                # Crear nueva imagen en la base de datos
                nueva_imagen = ImagenTerma.objects.create(
                    terma=usuario.terma,
                    url_imagen=url_completa,
                    descripcion=descripcion if descripcion else None
                )
                
                success_msg = 'Foto subida exitosamente.'
                if is_ajax:
                    return JsonResponse({'success': True, 'message': success_msg})
                messages.success(request, success_msg)
                return redirect('termas:subir_fotos')
                
            except Exception as e:
                error_msg = f'Error al subir la foto: {str(e)}'
                if is_ajax:
                    return JsonResponse({'success': False, 'message': error_msg})
                messages.error(request, error_msg)
                return redirect('termas:subir_fotos')
        
        # Obtener todas las fotos de la terma
        fotos = ImagenTerma.objects.filter(terma=usuario.terma).order_by('-id')
        
        # Calcular información del límite de fotos
        fotos_actuales = fotos.count()
        if usuario.terma.plan_actual:
            limite_fotos = usuario.terma.plan_actual.limite_fotos
            plan_nombre = usuario.terma.plan_actual.nombre
        else:
            limite_fotos = usuario.terma.limite_fotos_actual or 5
            plan_nombre = "Básico"
        
        # Calcular fotos restantes
        fotos_restantes = None
        porcentaje_uso = 0
        if limite_fotos != -1:
            fotos_restantes = max(0, limite_fotos - fotos_actuales)
            porcentaje_uso = min(100, (fotos_actuales / limite_fotos * 100)) if limite_fotos > 0 else 0
        
        context = {
            'title': 'Gestión de Fotos - MiTerma',
            'usuario': usuario,
            'terma': usuario.terma,
            'fotos': fotos,
            'fotos_actuales': fotos_actuales,
            'limite_fotos': limite_fotos,
            'fotos_restantes': fotos_restantes,
            'plan_nombre': plan_nombre,
            'porcentaje_uso': porcentaje_uso,
        }
        return render(request, 'administrador_termas/subir_fotos.html', context)
        
    except Usuario.DoesNotExist:
        messages.error(request, 'Sesión inválida.')
        return redirect('core:home')

def eliminar_foto(request, foto_uuid):
    """Vista para eliminar una foto de la terma."""
    
    # Verificar si el usuario está logueado
    if 'usuario_id' not in request.session:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': 'Debes iniciar sesión para acceder.'})
        messages.error(request, 'Debes iniciar sesión para acceder.')
        return redirect('core:home')
    
    # Verificar si el usuario tiene el rol correcto (ID=2)
    if request.session.get('usuario_rol') != 2:
        error_msg = 'No tienes permisos para realizar esta acción.'
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': error_msg})
        messages.error(request, error_msg)
        return redirect('usuarios:inicio')
    
    if request.method == 'POST':
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        try:
            usuario = Usuario.objects.get(id=request.session['usuario_id'])
            
            # Verificar que el usuario tenga una terma asignada
            if not usuario.terma:
                error_msg = 'No tienes una terma asignada.'
                if is_ajax:
                    return JsonResponse({'success': False, 'message': error_msg})
                messages.error(request, error_msg)
                return redirect('usuarios:adm_termas')
            
            # Obtener la imagen y verificar que pertenezca a la terma del usuario
            imagen = get_object_or_404(ImagenTerma, uuid=foto_uuid, terma=usuario.terma)
            
            # Eliminar el archivo físico si existe
            try:
                from django.core.files.storage import default_storage
                # Extraer el path del archivo desde la URL
                file_path = imagen.url_imagen.replace('/media/', '')
                if default_storage.exists(file_path):
                    default_storage.delete(file_path)
            except Exception as e:
                print(f"Error al eliminar archivo físico: {e}")
            
            # Eliminar el registro de la base de datos
            imagen.delete()
            
            success_msg = 'Foto eliminada exitosamente.'
            if is_ajax:
                return JsonResponse({'success': True, 'message': success_msg})
            messages.success(request, success_msg)
            
        except Usuario.DoesNotExist:
            error_msg = 'Sesión inválida.'
            if is_ajax:
                return JsonResponse({'success': False, 'message': error_msg})
            messages.error(request, error_msg)
            return redirect('core:home')
        except Exception as e:
            error_msg = f'Error al eliminar la foto: {str(e)}'
            if is_ajax:
                return JsonResponse({'success': False, 'message': error_msg})
            messages.error(request, error_msg)
    
    return redirect('termas:subir_fotos')

@admin_terma_required
def analisis_terma(request):
    """Vista para mostrar el análisis de la terma - Migrada a Django Auth."""
    try:
        from django.db.models import Count, Sum
        from datetime import datetime, timedelta
        import json
        from ventas.models import Compra, DetalleCompra
        from entradas.models import EntradaTipo
        
        # El decorador ya verificó que el usuario está autenticado y es admin_terma
        usuario = request.user
        terma = usuario.terma
        try:
            rango = int(request.GET.get('rango', 7))
            if rango not in [7, 15, 30]:
                rango = 7
        except Exception:
            rango = 7
        hoy = datetime.now().date()
        fechas = []
        ventas_por_dia = []
        ingresos_por_dia = []
        entradas_vendidas_por_dia = []  # Nueva variable para entradas vendidas
        
        for i in range(rango-1, -1, -1):
            fecha = hoy - timedelta(days=i)
            fechas.append(fecha.strftime('%d/%m'))
            
            # Contar número de compras (transacciones)
            ventas_dia = Compra.objects.filter(
                fecha_compra__date=fecha,
                estado_pago='pagado',
                terma=terma
            ).count()
            ventas_por_dia.append(ventas_dia)
            
            # Calcular ingresos del día
            ingresos_dia = Compra.objects.filter(
                fecha_compra__date=fecha,
                estado_pago='pagado',
                terma=terma
            ).aggregate(total=Sum('total'))['total'] or 0
            ingresos_por_dia.append(float(ingresos_dia))
            
            # Calcular cantidad de entradas vendidas (usando misma lógica del calendario)
            entradas_dia = Compra.objects.filter(
                fecha_compra__date=fecha,
                estado_pago='pagado',
                terma=terma
            ).aggregate(total_entradas=Sum('cantidad'))['total_entradas'] or 0
            entradas_vendidas_por_dia.append(int(entradas_dia))
        
        # Estadísticas
        total_ventas_cantidad = sum(ventas_por_dia)  # Número de transacciones
        total_entradas_vendidas = sum(entradas_vendidas_por_dia)  # Total de entradas vendidas
        total_ingresos = sum(ingresos_por_dia)  # Dinero total del rango seleccionado
        promedio_ventas_cantidad = total_ventas_cantidad / rango if ventas_por_dia else 0
        promedio_entradas_diario = total_entradas_vendidas / rango if entradas_vendidas_por_dia else 0
        promedio_ingresos_diario = total_ingresos / rango if ingresos_por_dia else 0
        mejor_dia = max(ventas_por_dia) if ventas_por_dia else 0
        
        # Cálculo de ingresos del mes actual
        primer_dia_mes = hoy.replace(day=1)
        ingresos_mes_actual = Compra.objects.filter(
            terma=terma,
            estado_pago='pagado',
            fecha_compra__date__gte=primer_dia_mes,
            fecha_compra__date__lte=hoy
        ).aggregate(total=Sum('total'))['total'] or 0
        
        # Cálculo de ventas del mes actual
        ventas_mes_actual = Compra.objects.filter(
            terma=terma,
            estado_pago='pagado',
            fecha_compra__date__gte=primer_dia_mes,
            fecha_compra__date__lte=hoy
        ).count()
        fecha_inicio = hoy - timedelta(days=rango-1)
        detalles = DetalleCompra.objects.filter(
            compra__terma=terma,
            compra__estado_pago='pagado',
            compra__fecha_compra__date__gte=fecha_inicio,
            compra__fecha_compra__date__lte=hoy
        ).select_related('entrada_tipo')
        tipos = {}
        for detalle in detalles:
            # Validar que entrada_tipo no sea None
            if not detalle.entrada_tipo:
                continue
            tipo = detalle.entrada_tipo.nombre
            tipos[tipo] = tipos.get(tipo, 0) + detalle.cantidad
        tipos_labels = list(tipos.keys())
        tipos_values = list(tipos.values())

            # Análisis de servicios más vendidos usando el nuevo método del modelo
        servicios_data = terma.servicios_populares()
        servicios_populares = [
            {
                'servicio': label,
                'total_vendidos': data
            }
            for label, data in zip(servicios_data['labels'], servicios_data['data'])
        ]
        servicios_populares_total = sum(servicios_data['data'])

        servicios_labels = servicios_data['labels']
        servicios_values = servicios_data['data']
        
        # Análisis por día de la semana
        dias_semana = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
        ventas_por_dia_semana = [0] * 7
        
        compras_periodo = Compra.objects.filter(
            terma=terma,
            estado_pago='pagado',
            fecha_compra__date__gte=fecha_inicio,
            fecha_compra__date__lte=hoy
        )
        
        for compra in compras_periodo:
            dia_semana = compra.fecha_compra.weekday()  # 0=Lunes, 6=Domingo
            ventas_por_dia_semana[dia_semana] += 1
        context = {
            'title': 'Análisis de Terma - MiTerma',
            'usuario': usuario,
            'terma': terma,
            'fechas_json': json.dumps(fechas),
            'ventas_por_dia_json': json.dumps(ventas_por_dia),
            'ingresos_por_dia_json': json.dumps(ingresos_por_dia),  
            'entradas_vendidas_por_dia_json': json.dumps(entradas_vendidas_por_dia),  
            'total_ventas': total_ventas_cantidad,  
            'total_entradas_vendidas': total_entradas_vendidas, 
            'total_ingresos_rango': round(total_ingresos, 2),  
            'total_ingresos_mes': round(float(ingresos_mes_actual), 2),  
            'total_ventas_mes': ventas_mes_actual,  
            'promedio_ventas': round(promedio_ventas_cantidad, 1), 
            'promedio_entradas': round(promedio_entradas_diario, 1),  
            'promedio_ingresos': round(promedio_ingresos_diario, 2),  
            'mejor_dia': mejor_dia,
            'rango': rango,
            'tipos_labels_json': json.dumps(tipos_labels),
            'tipos_values_json': json.dumps(tipos_values),
            'servicios_populares': servicios_populares,
            'servicios_populares_total': servicios_populares_total,
            'servicios_labels_json': json.dumps(servicios_labels),
            'servicios_values_json': json.dumps(servicios_values),
            # Análisis por día de la semana
            'dias_semana_json': json.dumps(dias_semana),
            'ventas_dia_semana_json': json.dumps(ventas_por_dia_semana),
        }
        return render(request, 'administrador_termas/analisis_terma.html', context)
    except Usuario.DoesNotExist:
        messages.error(request, 'Sesión inválida.')
        return redirect('core:home')
    except Exception as e:
        messages.error(request, f'Error al cargar análisis: {str(e)}')
        return redirect('usuarios:adm_termas')


@admin_terma_required
def editar_terma(request):
    """Vista para editar la información de la terma - Migrada a Django Auth."""
    try:
        usuario = request.user
        terma = usuario.terma
        if request.method == 'POST':
            descripcion = request.POST.get('descripcion_terma', '').strip()
            limite_ventas = request.POST.get('limite_ventas_diario')
            
            print(f"[DEBUG EDITAR TERMA] Usuario: {usuario.email}")
            print(f"[DEBUG EDITAR TERMA] Terma actual: {terma.nombre_terma}")
            print(f"[DEBUG EDITAR TERMA] Límite actual en DB: {terma.limite_ventas_diario}")
            print(f"[DEBUG EDITAR TERMA] Límite recibido del form: {limite_ventas}")
            print(f"[DEBUG EDITAR TERMA] POST data: {dict(request.POST)}")
            
            terma.descripcion_terma = descripcion
            if limite_ventas and limite_ventas.isdigit():
                limite_ventas = int(limite_ventas)
                print(f"[DEBUG EDITAR TERMA] Límite convertido a int: {limite_ventas}")
                if 1 <= limite_ventas <= 1000:
                    terma.limite_ventas_diario = limite_ventas
                    print(f"[DEBUG EDITAR TERMA] Asignando nuevo límite: {limite_ventas}")
                else:
                    print(f"[DEBUG EDITAR TERMA] Límite fuera de rango: {limite_ventas}")
                    messages.error(request, 'El límite de ventas debe estar entre 1 y 1000.')
                    return redirect('termas:editar_terma')
            else:
                print(f"[DEBUG EDITAR TERMA] Límite inválido o vacío: '{limite_ventas}'")
            
            print(f"[DEBUG EDITAR TERMA] Guardando terma...")
            terma.save()
            print(f"[DEBUG EDITAR TERMA] Límite después de guardar: {terma.limite_ventas_diario}")
            
            terma.save()
            
            # Limpiar cache de la terma y forzar recarga
            from django.core.cache import cache
            cache.delete(f'terma_{terma.id}')
            
            # Refrescar el objeto terma desde la base de datos
            terma.refresh_from_db()
            print(f"[DEBUG EDITAR TERMA] Límite después de refresh_from_db: {terma.limite_ventas_diario}")
            
            # También refrescar el usuario para asegurar datos actualizados
            usuario.refresh_from_db()
            
            print(f"[DEBUG EDITAR TERMA] Enviando respuesta con límite: {terma.limite_ventas_diario}")
            
            messages.success(request, 'Información de la terma actualizada correctamente.')
            
            # En lugar de redirect, renderizar directamente con datos actualizados
            context = {
                'title': 'Editar Terma - MiTerma',
                'usuario': usuario,
                'terma': terma,
                'servicios': terma.servicios.all(),
                'actualizado': True,  # Flag para indicar que se actualizó
                'nuevo_limite': terma.limite_ventas_diario  # Pasar el nuevo valor
            }
            return render(request, 'administrador_termas/editar_terma.html', context)
        
        # Para GET request - asegurarse de tener datos frescos
        terma.refresh_from_db()
        print(f"[DEBUG EDITAR TERMA GET] Cargando página con límite: {terma.limite_ventas_diario}")
        
        context = {
            'title': 'Editar Terma - MiTerma',
            'usuario': usuario,
            'terma': terma,
            'servicios': terma.servicios.all()
        }
        return render(request, 'administrador_termas/editar_terma.html', context)
    except Usuario.DoesNotExist:
        messages.error(request, 'Sesión inválida.')
        return redirect('core:home')

@admin_terma_required
def nuevo_servicio(request):
    """Vista para mostrar el formulario de nuevo servicio."""
    try:
        usuario = request.user
        terma = usuario.terma
        context = {
            'title': 'Agregar Nuevo Servicio - MiTerma',
            'usuario': usuario,
            'terma': terma,
        }
        return render(request, 'administrador_termas/nuevo_servicio.html', context)
    except Usuario.DoesNotExist:
        messages.error(request, 'Sesión inválida.')
        return redirect('core:home')

@admin_terma_required
def agregar_servicio(request):
    """Vista para agregar un nuevo servicio a la terma - Migrada a Django Auth."""
    if request.method == 'POST':
        usuario = request.user
        terma = usuario.terma
        
        servicio = request.POST.get('servicio')
        descripcion = request.POST.get('descripcion_servicio')
        precio = request.POST.get('precio_servicio')
        
        from termas.models import ServicioTerma
        nuevo_servicio = ServicioTerma(
            terma=terma,
            servicio=servicio,
            descripcion=descripcion,
            precio=precio
        )
        nuevo_servicio.save()
        messages.success(request, 'Servicio agregado correctamente.')
        logger.info(f"Usuario {usuario.nombre} (ID: {usuario.id}) agregó servicio {servicio} a terma {terma.nombre_terma}")
        return redirect('termas:editar_terma')
    return redirect('termas:editar_terma')

@admin_terma_required
def quitar_servicio(request, servicio_uuid):
    """Vista para quitar un servicio de la terma - Migrada a Django Auth."""
    if request.method == 'POST':
        usuario = request.user
        terma = usuario.terma
        
        from termas.models import ServicioTerma
        servicio = get_object_or_404(ServicioTerma, uuid=servicio_uuid, terma=terma)
        servicio_nombre = servicio.servicio
        servicio.delete()
        messages.success(request, f'Servicio "{servicio_nombre}" eliminado correctamente.')
        logger.info(f"Usuario {usuario.nombre} (ID: {usuario.id}) eliminó servicio {servicio_nombre} de terma {terma.nombre_terma}")
        return redirect('termas:editar_terma')
    return redirect('termas:editar_terma')

@admin_terma_required
def editar_servicio(request, servicio_uuid):
    """Vista para editar un servicio de la terma - Migrada a Django Auth."""
    usuario = request.user
    terma = usuario.terma
    
    from termas.models import ServicioTerma
    servicio = get_object_or_404(ServicioTerma, uuid=servicio_uuid, terma=terma)
    
    if request.method == 'POST':
        servicio_anterior = servicio.servicio
        servicio.servicio = request.POST.get('servicio', servicio.servicio)
        servicio.descripcion = request.POST.get('descripcion_servicio', servicio.descripcion)
        servicio.precio = request.POST.get('precio_servicio', servicio.precio)
        servicio.save()
        messages.success(request, 'Servicio editado correctamente.')
        logger.info(f"Usuario {usuario.nombre} (ID: {usuario.id}) editó servicio {servicio_anterior} en terma {terma.nombre_terma}")
        return redirect('termas:editar_terma')
    context = {
        'title': 'Editar Servicio - MiTerma',
        'usuario': usuario,
        'terma': terma,
        'servicio': servicio,
    }
    return render(request, 'administrador_termas/nuevo_servicio.html', context)

@admin_terma_required
def precios_terma(request): 
    """Vista para mostrar precios de la terma - Migrada a Django Auth."""
    usuario = request.user
    terma = usuario.terma
    
    context = {
        'title': 'Precios de la Terma - MiTerma',
        'usuario': usuario,
        'terma': terma,
        'servicios': terma.servicios.all() if terma else []
    }
    return render(request, 'administrador_termas/precios_terma.html', context)

@admin_terma_required
def editar_entrada(request, entrada_uuid):
    """Vista para editar un tipo de entrada - Migrada a Django Auth."""
    # El decorador ya verificó que el usuario está autenticado y es admin_terma
    usuario = request.user
    terma = usuario.terma
    
    entrada = get_object_or_404(EntradaTipo, uuid=entrada_uuid, terma=terma)
    from termas.models import ServicioTerma
    servicios_disponibles = ServicioTerma.objects.filter(terma=terma)
    
    if request.method == 'POST':
        entrada_anterior = entrada.nombre
        entrada.nombre = request.POST.get('nombre', entrada.nombre)
        entrada.descripcion = request.POST.get('descripcion', entrada.descripcion)
        from decimal import Decimal, InvalidOperation
        import re
        
        precio_str = request.POST.get('precio', None)
        duracion_str = request.POST.get('duracion_horas', None)
        error_messages = []
        
        if precio_str:
            try:
                precio_limpio = re.sub(r'[^\d]', '', precio_str)
                if precio_limpio:
                    entrada.precio = Decimal(precio_limpio)
                else:
                    error_messages.append('El precio no puede estar vacío.')
            except (InvalidOperation, ValueError):
                error_messages.append('El precio ingresado no es válido. Use solo números.')
        
        if duracion_str:
            try:
                duracion_int = int(duracion_str)
                if duracion_int < 1 or duracion_int > 24:
                    error_messages.append('La duración debe ser entre 1 y 24 horas.')
                else:
                    entrada.duracion_horas = duracion_int
            except ValueError:
                error_messages.append('La duración ingresada no es válida.')
        
        if error_messages:
            context = {
                'title': 'Editar Tipo de Entrada',
                'entrada': entrada,
                'servicios_disponibles': servicios_disponibles,
                'servicios_seleccionados': entrada.servicios.values_list('id', flat=True),
                'messages': error_messages
            }
            return render(request, 'administrador_termas/editar_entrada.html', context)
        
        entrada.save()
        servicios_ids = request.POST.getlist('servicios')
        entrada.servicios.set(servicios_ids)
        
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            # Respuesta simple para AJAX
            from django.http import HttpResponse
            return HttpResponse('OK')
        
        messages.success(request, 'Tipo de entrada editado correctamente.')
        logger.info(f"Usuario {usuario.nombre} (ID: {usuario.id}) editó entrada {entrada_anterior} en terma {terma.nombre_terma}")
        return redirect('termas:precios_terma')
    
    context = {
        'title': 'Editar Tipo de Entrada',
        'entrada': entrada,
        'servicios_disponibles': servicios_disponibles,
        'servicios_seleccionados': entrada.servicios.values_list('id', flat=True)
    }
    return render(request, 'administrador_termas/editar_entrada.html', context)

@admin_terma_required
def eliminar_entrada(request, entrada_uuid):
    """Vista para eliminar un tipo de entrada con confirmación - Migrada a Django Auth."""
    # El decorador ya verificó que el usuario está autenticado y es admin_terma
    usuario = request.user
    terma = usuario.terma
    
    entrada = get_object_or_404(EntradaTipo, uuid=entrada_uuid, terma=terma)
    
    if request.method == 'POST':
        entrada_nombre = entrada.nombre
        entrada.delete()
        messages.success(request, 'Tipo de entrada eliminado correctamente.')
        logger.info(f"Usuario {usuario.nombre} (ID: {usuario.id}) eliminó entrada {entrada_nombre} de terma {terma.nombre_terma}")
        return redirect('termas:precios_terma')
    
    context = {
        'title': 'Eliminar Tipo de Entrada',
        'entrada': entrada
    }
    return render(request, 'administrador_termas/eliminar_entrada.html', context)

@admin_terma_required
@require_http_methods(["GET", "POST"])
def crear_entrada(request):
    """Vista para crear un nuevo tipo de entrada - Migrada a Django Auth."""
    # El decorador ya verificó que el usuario está autenticado y es admin_terma
    usuario = request.user
    terma = usuario.terma
    
    from entradas.forms import EntradaTipoForm
    
    if request.method == 'POST':
        form = EntradaTipoForm(request.POST, terma=terma)
        if form.is_valid():
            entrada = form.save(commit=False)
            entrada.terma = terma
            entrada.save()
            form.save_m2m()  # Guardar relaciones many-to-many
            messages.success(request, f'Tipo de entrada "{entrada.nombre}" creado correctamente.')
            logger.info(f"Usuario {usuario.nombre} (ID: {usuario.id}) creó entrada {entrada.nombre} en terma {terma.nombre_terma}")
            return redirect('termas:precios_terma')
    else:
        form = EntradaTipoForm(terma=terma)
    
    context = {
        'title': 'Crear Nueva Entrada - MiTerma',
        'form': form,
        'terma': terma
    }
    return render(request, 'administrador_termas/crear_entrada.html', context)

@admin_terma_required
@require_http_methods(["GET", "POST"])
def gestionar_servicios_entrada(request, entrada_uuid):
    """Vista para gestionar servicios de una entrada específica - Migrada a Django Auth."""
    # El decorador ya verificó que el usuario está autenticado y es admin_terma
    usuario = request.user
    terma = usuario.terma
    
    # Obtener la entrada específica
    entrada = get_object_or_404(EntradaTipo, uuid=entrada_uuid, terma=terma)
    
    if request.method == 'POST':
        # Obtener servicios seleccionados del formulario
        servicios_ids = request.POST.getlist('servicios')
        
        # Limpiar servicios actuales y agregar los nuevos
        entrada.servicios.clear()
        if servicios_ids:
            servicios = entrada.terma.servicios.filter(id__in=servicios_ids)
            entrada.servicios.set(servicios)
        
        messages.success(request, f'Servicios actualizados para "{entrada.nombre}".')
        logger.info(f"Usuario {usuario.nombre} (ID: {usuario.id}) actualizó servicios para entrada {entrada.nombre} en terma {terma.nombre_terma}")
        return redirect('termas:precios_terma')
    
    # Obtener todos los servicios de la terma
    servicios_disponibles = terma.servicios.all()
    servicios_actuales = entrada.servicios.all()
    
    context = {
        'title': f'Gestionar Servicios - {entrada.nombre}',
        'entrada': entrada,
        'terma': terma,
        'servicios_disponibles': servicios_disponibles,
        'servicios_actuales': servicios_actuales
    }
    return render(request, 'administrador_termas/gestionar_servicios_entrada.html', context)

@admin_terma_required
def calendario_termas(request):
    """Vista para mostrar el calendario de la terma - Migrada a Django Auth."""
    try:
        from datetime import datetime, date
        from django.db.models import Sum
        import json
        from ventas.models import Compra
        
        # El decorador ya verificó que el usuario está autenticado y es admin_terma
        usuario = request.user
        terma = usuario.terma
        
        # Obtener mes y año de la URL o usar el actual
        mes = int(request.GET.get('mes', datetime.now().month))
        anio = int(request.GET.get('anio', datetime.now().year))
        
        # Obtener todas las ventas del mes seleccionado agrupadas por fecha_visita
        ventas_mes = Compra.objects.filter(
            terma=terma,
            estado_pago='pagado',
            fecha_visita__year=anio,
            fecha_visita__month=mes
        ).values('fecha_visita').annotate(
            total_entradas=Sum('cantidad')
        )
        
        # Convertir a diccionario con formato YYYY-MM-DD
        ventas_por_dia = {}
        
        # Primero obtenemos todas las compras pagadas del mes
        compras_mes = Compra.objects.filter(
            terma=terma,
            estado_pago='pagado',
            fecha_visita__year=anio,
            fecha_visita__month=mes
        )
        
        # Convertir las ventas a un diccionario con formato YYYY-MM-DD
        for venta in ventas_mes:
            fecha = venta['fecha_visita']
            total = venta['total_entradas']
            ventas_por_dia[fecha.strftime('%Y-%m-%d')] = total
        
        # Imprimir para debug
        print(f"Mes: {mes}, Año: {anio}")
        print("Ventas encontradas:", ventas_por_dia)
        
        context = {
            'title': 'Calendario de la Terma - MiTerma',
            'usuario': usuario,
            'terma': terma,
            'ventas_por_dia': ventas_por_dia,  # Ya no necesitamos json.dumps aquí porque usamos json_script en el template
            'mes_actual': mes,
            'anio_actual': anio
        }
        return render(request, 'administrador_termas/calendario_termas.html', context)
    except Usuario.DoesNotExist:
        messages.error(request, 'Sesión inválida.')
        return redirect('core:home')
    
def vista_termas(request):
    """Vista para mostrar la terma del administrador."""
    if 'usuario_id' not in request.session:
        messages.error(request, 'Debes iniciar sesión para acceder.')
        return redirect('core:home')
    if request.session.get('usuario_rol') != 2:
        messages.error(request, 'No tienes permisos para acceder a esta sección.')
        return redirect('usuarios:inicio')
    try:
        usuario = Usuario.objects.get(id=request.session['usuario_id'])
        terma = usuario.terma
        context = {
            'title': f'Vista de la Terma {terma.nombre_terma} - MiTerma',
            'usuario': usuario,
            'terma': terma,
        }
        return render(request, 'administrador_termas/vista_termas.html', context)
    except Usuario.DoesNotExist:
        messages.error(request, 'Sesión inválida.')
        return redirect('core:home')

def vista_terma(request, terma_uuid):
    """Vista para mostrar los datos de una terma y permitir elegir entrada - Migrada a Django Auth."""
    terma = get_object_or_404(Terma, uuid=terma_uuid)
    
    # Verificar si la terma está activa
    if terma.estado_suscripcion != 'activa':
        # Si el usuario es admin general, permitir el acceso
        if request.user.is_authenticated and hasattr(request.user, 'rol') and request.user.rol and request.user.rol.nombre == 'administrador_general':
            pass  # Permitir acceso sin restricciones
        # Si el usuario es el dueño de la terma (admin terma), mostrar popup informativo
        elif request.user.is_authenticated and hasattr(request.user, 'rol') and request.user.rol and request.user.rol.nombre == 'administrador_terma' and request.user.terma and request.user.terma.id == terma.id:
            context = {
                'terma': terma,
                'terma_inactiva': True,
                'navbar_mode': 'termas_only'
            }
            return render(request, 'administrador_termas/vista_terma.html', context)
        else:
            # Para clientes y otros usuarios, redirigir con error 404
            from core.error_views import custom_error_page
            return custom_error_page(
                request, 
                error_type='not_found',
                message='Esta terma no está disponible en este momento.',
                status_code=404
            )
    
    entradas = terma.get_tipos_entrada()
    imagenes = ImagenTerma.objects.filter(terma=terma)
    calificacion_promedio = terma.promedio_calificacion()

    from django.core import serializers
    import json
    servicios_por_entrada = {}
    
    # Función para escapar datos de servicios de forma segura
    def escape_servicio_data(servicios_list):
        """Escapa los datos de los servicios para prevenir XSS."""
        escaped_servicios = []
        for servicio in servicios_list:
            escaped_servicio = {
                'id': servicio['id'],
                'uuid': str(servicio['uuid']),
                'servicio': escape(str(servicio['servicio'])) if servicio['servicio'] else '',
                'descripcion': escape(str(servicio['descripcion'])) if servicio['descripcion'] else '',
                'precio': servicio['precio']
            }
            escaped_servicios.append(escaped_servicio)
        return escaped_servicios
    
    # Obtener todos los servicios disponibles de la terma una sola vez
    todos_servicios = list(terma.servicios.values('id', 'uuid', 'servicio', 'descripcion', 'precio'))
    todos_servicios_escaped = escape_servicio_data(todos_servicios)
    
    for entrada in entradas:
        # Obtener servicios incluidos de esta entrada específica
        incluidos = list(entrada.servicios.values('id', 'uuid', 'servicio', 'descripcion', 'precio'))
        incluidos_escaped = escape_servicio_data(incluidos)
        
        # Crear un set de IDs de servicios incluidos para búsqueda más eficiente
        servicios_incluidos_ids = {s['id'] for s in incluidos}
        
        # Filtrar servicios extra: excluir los que ya están incluidos en la entrada
        extras = [s for s in todos_servicios if s['id'] not in servicios_incluidos_ids]
        extras_escaped = escape_servicio_data(extras)
        
        servicios_por_entrada[str(entrada.uuid)] = {
            'incluidos': incluidos_escaped,
            'extras': extras_escaped,
            'nombre': escape(str(entrada.nombre)) if entrada.nombre else ''  # Escapar el nombre también
        }

    entrada_seleccionada = entradas.first() if entradas.exists() else None
    servicios_incluidos = servicios_por_entrada[str(entrada_seleccionada.uuid)]['incluidos'] if entrada_seleccionada else []
    servicios_extra = servicios_por_entrada[str(entrada_seleccionada.uuid)]['extras'] if entrada_seleccionada else []

    # Procesar nuevo comentario - Migrado a Django Auth
    if request.method == 'POST' and 'puntuacion' in request.POST and 'comentario' in request.POST:
        puntuacion = int(request.POST.get('puntuacion'))
        comentario = request.POST.get('comentario')
        
        if request.user.is_authenticated:
            from termas.models import Calificacion
            from django.db import IntegrityError, transaction
            
            try:
                # Crear nueva calificación (permitir múltiples comentarios por usuario)
                with transaction.atomic():
                    Calificacion.objects.create(
                        usuario=request.user,
                        terma=terma,
                        puntuacion=puntuacion,
                        comentario=comentario
                    )
                messages.success(request, '¡Tu opinión se ha guardado correctamente!')
                logger.info(f"Usuario {request.user.nombre} (ID: {request.user.id}) dejó nueva calificación {puntuacion} en terma {terma.nombre_terma}")
                
                return redirect(request.path)
                
            except IntegrityError as e:
                logger.error(f"Error de integridad al guardar calificación: {str(e)}")
                messages.error(request, 'Hubo un problema al guardar tu opinión. Por favor intenta de nuevo.')
                return redirect(request.path)
            except Exception as e:
                logger.error(f"Error inesperado al guardar calificación: {str(e)}")
                messages.error(request, 'Hubo un error inesperado. Por favor intenta de nuevo.')
                return redirect(request.path)
        else:
            messages.error(request, 'Debes iniciar sesión para dejar una opinión.')
            logger.warning(f"Usuario no autenticado intentó dejar calificación en terma {terma.nombre_terma}")
            return redirect('usuarios:inicio')

    opiniones = terma.calificacion_set.select_related('usuario').order_by('-fecha')
    calificacion_promedio = terma.promedio_calificacion()
    cantidad_opiniones = terma.total_calificaciones()
    
    # Calcular distribución real de calificaciones por estrella
    distribucion_estrellas = {}
    for i in range(1, 6):
        count = terma.calificacion_set.filter(puntuacion=i).count()
        porcentaje = (count / cantidad_opiniones * 100) if cantidad_opiniones > 0 else 0
        distribucion_estrellas[i] = {
            'count': count,
            'porcentaje': round(porcentaje, 1)
        }
    
    context = {
        'terma': terma,
        'entradas': entradas,
        'entrada_seleccionada': entrada_seleccionada,
        'imagenes': imagenes,
        'calificacion_promedio': calificacion_promedio,
        'cantidad_opiniones': cantidad_opiniones,
        'distribucion_estrellas': distribucion_estrellas,
        # Pasar porcentajes individuales para facilitar acceso en template
        'porcentaje_5_estrellas': distribucion_estrellas[5]['porcentaje'],
        'porcentaje_4_estrellas': distribucion_estrellas[4]['porcentaje'],
        'porcentaje_3_estrellas': distribucion_estrellas[3]['porcentaje'],
        'porcentaje_2_estrellas': distribucion_estrellas[2]['porcentaje'],
        'porcentaje_1_estrellas': distribucion_estrellas[1]['porcentaje'],
        'servicios': servicios_incluidos,
        'servicios_extra': servicios_extra,
        'servicios_por_entrada_json': json.dumps(servicios_por_entrada),
        'opiniones': opiniones,
        'usuario': request.user if request.user.is_authenticated else None,
        'navbar_mode': 'termas_only'  # Para mostrar navbar azul con solo login/registro
    }
    
    return render(request, 'administrador_termas/vista_terma.html', context)

@admin_terma_required
def suscripcion(request):
    """Vista para gestionar la suscripción de la terma - Migrada a Django Auth."""
    try:
        from django.db.models import Sum, Count
        from datetime import datetime, timedelta
        
        # El decorador ya verificó que el usuario está autenticado y es admin_terma
        usuario = request.user
        
        # Verificar que el usuario tenga una terma asignada
        if not usuario.terma:
            messages.error(request, 'No tienes una terma asignada. Contacta al administrador.')
            return redirect('usuarios:adm_termas')
        
        terma = usuario.terma
        
        # Obtener el plan actual de la terma
        from .models import PlanSuscripcion
        
        # La terma tiene plan_actual directamente
        plan_actual = terma.plan_actual
        
        # Si no tiene plan, asignar el plan básico por defecto
        if not plan_actual:
            plan_basico = PlanSuscripcion.objects.filter(nombre='Básico').first()
            if plan_basico:
                terma.plan_actual = plan_basico
                terma.porcentaje_comision_actual = plan_basico.porcentaje_comision
                terma.limite_fotos_actual = plan_basico.limite_fotos
                terma.save()
                plan_actual = plan_basico
        
        # Obtener todos los planes disponibles
        planes_disponibles = PlanSuscripcion.objects.filter(activo=True).order_by('porcentaje_comision')
        
        # Calcular estadísticas de la terma
        hoy = datetime.now().date()
        inicio_mes = hoy.replace(day=1)
        
        # Fotos utilizadas vs límite
        fotos_utilizadas = ImagenTerma.objects.filter(terma=terma).count()
        limite_fotos = plan_actual.limite_fotos if plan_actual else 5
        
        # Ingresos del mes actual
        from ventas.models import Compra
        ingresos_mes = Compra.objects.filter(
            terma=terma,
            estado_pago='pagado',
            fecha_compra__date__gte=inicio_mes,
            fecha_compra__date__lte=hoy
        ).aggregate(total=Sum('total'))['total'] or 0
        
        # Visitantes del mes actual
        visitantes_mes = Compra.objects.filter(
            terma=terma,
            estado_pago='pagado',
            fecha_compra__date__gte=inicio_mes,
            fecha_compra__date__lte=hoy
        ).aggregate(total=Sum('cantidad'))['total'] or 0
        
        # Comisión que se cobraría con el plan actual
        comision_mes = 0
        if plan_actual and ingresos_mes > 0:
            comision_mes = (ingresos_mes * plan_actual.porcentaje_comision) / 100
        
        context = {
            'title': 'Gestión de Suscripción - MiTerma',
            'usuario': usuario,
            'terma': terma,
            'plan_actual': plan_actual,
            'planes_disponibles': planes_disponibles,
            'fotos_utilizadas': fotos_utilizadas,
            'limite_fotos': limite_fotos,
            'ingresos_mes': ingresos_mes,
            'visitantes_mes': visitantes_mes,
            'comision_mes': comision_mes,
        }
        
        return render(request, 'administrador_termas/suscripcion.html', context)
        
    except Usuario.DoesNotExist:
        messages.error(request, 'Sesión inválida.')
        return redirect('core:home')
    except Exception as e:
        messages.error(request, f'Error al cargar la página de suscripción: {str(e)}')
        return redirect('usuarios:adm_termas')


def cambiar_suscripcion(request):
    """Vista para cambiar la suscripción de una terma existente."""
    
    # Verificar autenticación (usando el sistema de sesiones personalizado)
    if not request.user.is_authenticated and 'usuario_id' not in request.session:
        messages.error(request, 'Debes estar autenticado para cambiar tu suscripción.')
        return redirect('usuarios:login')
    
    # Obtener el usuario
    if request.user.is_authenticated:
        usuario = request.user
    else:
        try:
            usuario = Usuario.objects.get(id=request.session['usuario_id'])
        except Usuario.DoesNotExist:
            messages.error(request, 'Sesión inválida.')
            return redirect('usuarios:login')
    
    # Verificar que el usuario tenga una terma asociada
    try:
        # Usar la relación directa terma del usuario primero
        terma = usuario.terma
        if not terma:
            # Si no hay terma directa, buscar por administrador
            terma = Terma.objects.filter(administrador=usuario).first()
        
        if not terma:
            messages.error(request, 'No tienes una terma asociada a tu cuenta.')
            return redirect('core:planes')
            
    except Exception as e:
        messages.error(request, 'Error al acceder a la información de tu terma.')
        return redirect('core:planes')
    
    # Verificar si viene con un plan pre-seleccionado desde la página de planes
    plan_preseleccionado_id = request.GET.get('plan')
    
    if request.method == 'POST':
        from .forms import CambiarSuscripcionForm
        form = CambiarSuscripcionForm(
            request.POST, 
            plan_actual=terma.plan_actual, 
            terma=terma
        )
        
        if form.is_valid():
            try:
                from .models import PlanSuscripcion, HistorialSuscripcion
                
                nuevo_plan = form.cleaned_data['nuevo_plan']
                motivo_cambio = form.cleaned_data['motivo_cambio']
                
                # Obtener el plan anterior
                plan_anterior = terma.plan_actual
                
                # Actualizar el plan de la terma
                terma.plan_actual = nuevo_plan
                terma.save()
                
                # Actualizar configuración según el nuevo plan
                terma.actualizar_configuracion_segun_plan()
                
                # Crear el motivo del historial
                motivo_historial = motivo_cambio if motivo_cambio else f"Cambio de plan solicitado por el usuario desde {plan_anterior.get_nombre_display() if plan_anterior else 'Sin plan'} a {nuevo_plan.get_nombre_display()}"
                
                # Registrar el cambio en el historial
                HistorialSuscripcion.objects.create(
                    terma=terma,
                    plan_anterior=plan_anterior,
                    plan_nuevo=nuevo_plan,
                    motivo=motivo_historial
                )
                
                # Verificar si hay fotos excedentes después del cambio
                if terma.tiene_fotos_excedentes():
                    fotos_excedentes = terma.fotos_excedentes_cantidad()
                    messages.warning(
                        request, 
                        f'Plan actualizado exitosamente a {nuevo_plan.get_nombre_display()}. '
                        f'ATENCIÓN: Tienes {fotos_excedentes} fotos que exceden el límite del nuevo plan '
                        f'({terma.limite_fotos_actual} fotos). Debes eliminar {fotos_excedentes} fotos '
                        f'antes de poder subir nuevas imágenes.'
                    )
                else:
                    messages.success(request, f'¡Tu plan ha sido actualizado exitosamente a {nuevo_plan.get_nombre_display()}!')
                
                return redirect('termas:suscripcion')
                
            except Exception as e:
                messages.error(request, f'Error al procesar el cambio: {str(e)}')
        else:
            messages.error(request, 'Por favor, corrige los errores en el formulario.')
    
    else:
        # GET request - mostrar formulario
        from .forms import CambiarSuscripcionForm
        
        initial_data = {}
        if plan_preseleccionado_id:
            try:
                from .models import PlanSuscripcion
                plan_preseleccionado = PlanSuscripcion.objects.get(id=plan_preseleccionado_id, activo=True)
                initial_data['nuevo_plan'] = plan_preseleccionado
            except PlanSuscripcion.DoesNotExist:
                pass
        
        form = CambiarSuscripcionForm(
            initial=initial_data,
            plan_actual=terma.plan_actual, 
            terma=terma
        )
    
    context = {
        'form': form,
        'terma': terma,
        'plan_actual': terma.plan_actual,
        'planes_disponibles': form.fields['nuevo_plan'].queryset,
        'title': 'Cambiar Plan de Suscripción'
    }
    
    return render(request, 'cambiar_suscripcion.html', context)


@admin_terma_required
def trabajadores_terma(request):
    """Vista para gestionar trabajadores de la terma."""
    try:
        from usuarios.models import Usuario, Rol
        from django.db.models import Q
        from django.contrib.auth.hashers import make_password
        import json
        
        usuario = request.user
        terma = usuario.terma
        
        if not terma:
            messages.error(request, 'No tienes una terma asignada.')
            return redirect('usuarios:adm_termas')
        
        # Obtener todos los trabajadores relacionados con esta terma
        # Esto incluye tanto trabajadores activos como históricos
        from usuarios.models import HistorialTrabajador
        from django.db.models import Q
        
        # Obtener IDs de usuarios que han trabajado en esta terma (activos o históricos)
        usuarios_trabajadores_ids = set()
        
        # 1. Trabajadores actualmente activos en esta terma
        trabajadores_activos = Usuario.objects.filter(
            terma=terma,
            rol__nombre='trabajador',
            is_active=True
        )
        usuarios_trabajadores_ids.update(trabajadores_activos.values_list('id', flat=True))
        
        # 2. Trabajadores que aparecen en el historial de esta terma
        historial_trabajadores_ids = HistorialTrabajador.objects.filter(
            terma=terma
        ).values_list('usuario_id', flat=True)
        usuarios_trabajadores_ids.update(historial_trabajadores_ids)
        
        # Obtener todos los usuarios trabajadores (activos e inactivos)
        trabajadores = Usuario.objects.filter(
            id__in=usuarios_trabajadores_ids
        ).select_related('rol').order_by('date_joined')
        
        # TODO: Eliminar estas líneas comentadas después de confirmar que funciona
        # # Opción 1: Solo trabajadores activos con esta terma
        # trabajadores_activos = Usuario.objects.filter(
        #     terma=terma,
        #     rol__nombre='trabajador',
        #     is_active=True
        # ).select_related('rol')
        # 
        # # Opción 2: Trabajadores inactivos que tienen rol 'cliente' pero que fueron trabajadores
        # # Por ahora, vamos a mostrar solo los activos hasta implementar un mejor sistema
        # trabajadores = trabajadores_activos.order_by('date_joined')
        # 
        # # TODO: Implementar sistema para recordar trabajadores anteriores de la terma
        
        # Obtener roles disponibles para trabajadores (solo 'trabajador')
        roles_trabajador = Rol.objects.filter(nombre='trabajador').order_by('nombre')
        logger.info(f"Roles trabajador disponibles: {[f'{r.nombre} (ID: {r.id})' for r in roles_trabajador]}")
        
        # Logging detallado de trabajadores
        logger.info(f"=== LISTADO COMPLETO DE TRABAJADORES ===")
        for trabajador in trabajadores:
            estado_texto = "ACTIVO" if trabajador.is_active else "INACTIVO"
            logger.info(f"ID: {trabajador.id} | {trabajador.get_full_name()} ({trabajador.email}) | Estado: {estado_texto}")
        
        # Estadísticas básicas
        stats = {
            'total_trabajadores': trabajadores.count(),
            'trabajadores_activos': trabajadores.filter(is_active=True).count(),
            'trabajadores_inactivos': trabajadores.filter(is_active=False).count(),
        }
        
        logger.info(f"=== ESTADÍSTICAS CALCULADAS ===")
        logger.info(f"Total: {stats['total_trabajadores']} | Activos: {stats['trabajadores_activos']} | Inactivos: {stats['trabajadores_inactivos']}")
        
        # Distribución por roles
        distribuciones_roles = {}
        for trabajador in trabajadores:
            rol_nombre = trabajador.rol.nombre if trabajador.rol else 'Sin rol'
            distribuciones_roles[rol_nombre] = distribuciones_roles.get(rol_nombre, 0) + 1
        
        context = {
            'title': f'Trabajadores - {terma.nombre_terma}',
            'usuario': usuario,
            'terma': terma,
            'trabajadores': trabajadores,
            'roles_trabajador': roles_trabajador,
            'stats': stats,
            'distribuciones_roles': distribuciones_roles,
        }
        
        return render(request, 'administrador_termas/trabajadores_terma.html', context)
        
    except Exception as e:
        logger.error(f"Error en vista trabajadores_terma para usuario {request.user.email}: {str(e)}")
        messages.error(request, 'Ocurrió un error al cargar la lista de trabajadores.')
        return redirect('usuarios:adm_termas')


@admin_terma_required
def crear_trabajador(request):
    """Vista para crear nuevo trabajador o actualizar rol de usuario existente."""
    print("DEBUG: INICIO CREAR_TRABAJADOR - PRINT")
    logger.info("=== INICIO CREAR_TRABAJADOR ===")
    try:
        from usuarios.models import Usuario, Rol
        from django.contrib.auth.hashers import make_password
        import json
        import secrets
        import string
        
        logger.info("=== IMPORTS OK ===")
        
        if request.method != 'POST':
            return JsonResponse({'success': False, 'error': 'Método no permitido'})
        
        logger.info("=== METODO POST OK ===")
        
        usuario_admin = request.user
        terma = usuario_admin.terma
        
        logger.info(f"=== USUARIO ADMIN: {usuario_admin.email}, TERMA: {terma.nombre_terma if terma else 'None'} ===")
        
        if not terma:
            return JsonResponse({'success': False, 'error': 'No tienes una terma asignada.'})
        
        # Obtener datos del formulario
        email = request.POST.get('email', '').strip().lower()
        nombre = request.POST.get('nombre', '').strip()
        apellido = request.POST.get('apellido', '').strip()
        telefono = request.POST.get('telefono', '').strip()
        
        logger.info(f"=== DATOS RECIBIDOS: email={email}, nombre={nombre}, apellido={apellido} ===")
        
        # Validaciones
        if not all([email, nombre, apellido]):
            return JsonResponse({'success': False, 'error': 'Email, nombre y apellido son obligatorios.'})
        
        # SIEMPRE usar rol de trabajador - no confiar en el frontend
        try:
            rol = Rol.objects.get(nombre='trabajador')
            logger.info(f"=== ROL ENCONTRADO: {rol.nombre} (ID: {rol.id}) ===")
        except Rol.DoesNotExist:
            logger.error("=== ROL TRABAJADOR NO EXISTE ===")
            return JsonResponse({'success': False, 'error': 'Error: Rol de trabajador no encontrado en el sistema.'})
        
        # Verificar si el usuario ya existe
        usuario_existente = Usuario.objects.filter(email=email).first()
        
        if usuario_existente:
            logger.info(f"=== USUARIO EXISTE: {email} ===")
            # Usuario existe - actualizar rol y terma
            usuario_existente.rol = rol
            usuario_existente.terma = terma
            usuario_existente.is_active = True
            usuario_existente.save()
            
            mensaje = f"Usuario {email} actualizado con rol {rol.nombre} para la terma {terma.nombre_terma}."
            
            return JsonResponse({
                'success': True,
                'mensaje': mensaje,
                'usuario_id': usuario_existente.id
            })
        else:
            logger.info(f"=== CREANDO NUEVO USUARIO: {email} ===")
            # Crear nuevo usuario
            # Generar contraseña temporal
            password_temporal = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))
            
            logger.info(f"=== PASSWORD TEMPORAL GENERADA ===")
            
            try:
                nuevo_usuario = Usuario.objects.create(
                    email=email,
                    nombre=nombre,
                    apellido=apellido,
                    telefono=telefono,
                    rol=rol,
                    terma=terma,
                    password=make_password(password_temporal),
                    is_active=True,
                    estado=True,
                    tiene_password_temporal=True
                )
                logger.info(f"=== USUARIO CREADO: {nuevo_usuario.email} ===")
            except Exception as e:
                logger.error(f"=== ERROR AL CREAR USUARIO: {str(e)} ===")
                return JsonResponse({'success': False, 'error': f'Error al crear usuario: {str(e)}'})
            
            # Enviar email de bienvenida al nuevo trabajador
            logger.info(f"=== INICIO ENVIO EMAIL ===")
            
            try:
                from .email_utils import enviar_email_bienvenida_trabajador
                logger.info(f"=== LLAMANDO FUNCION EMAIL ===")
                email_enviado = enviar_email_bienvenida_trabajador(nuevo_usuario, password_temporal, terma)
                logger.info(f"=== RESULTADO EMAIL: {email_enviado} ===")
            except Exception as e:
                logger.error(f"=== ERROR EN ENVIO EMAIL: {str(e)} ===")
                import traceback
                logger.error(f"=== TRACEBACK: {traceback.format_exc()} ===")
                email_enviado = False
            
            mensaje_email = " Se ha enviado un correo con las credenciales de acceso." if email_enviado else " No se pudo enviar el correo de bienvenida."
            
            logger.info(f"=== ANTES DE RETURN ===")
            
            return JsonResponse({
                'success': True,
                'mensaje': f"Trabajador {nombre} {apellido} creado exitosamente.{mensaje_email}",
                'usuario_id': nuevo_usuario.id,
                'password_temporal': password_temporal
            })
            
    except Exception as e:
        logger.error(f"=== ERROR GENERAL EN CREAR_TRABAJADOR: {str(e)} ===")
        import traceback
        logger.error(f"=== TRACEBACK COMPLETO: {traceback.format_exc()} ===")
        return JsonResponse({'success': False, 'error': f'Error interno: {str(e)}'})


@admin_terma_required
def editar_trabajador(request, trabajador_id):
    """Vista para editar trabajador."""
    try:
        from usuarios.models import Usuario, Rol
        from .email_utils import enviar_email_actualizacion_trabajador
        
        if request.method != 'POST':
            return JsonResponse({'success': False, 'error': 'Método no permitido'})
        
        usuario_admin = request.user
        terma = usuario_admin.terma
        
        # Obtener trabajador
        trabajador = get_object_or_404(Usuario, uuid=trabajador_uuid)
        
        # Verificar que el trabajador pertenece a la terma y tiene rol trabajador
        if trabajador.terma != terma or (trabajador.rol and trabajador.rol.nombre != 'trabajador'):
            return JsonResponse({'success': False, 'error': 'No tienes permisos para editar este trabajador.'})
        
        # Obtener datos del formulario
        nombre = request.POST.get('nombre', '').strip()
        apellido = request.POST.get('apellido', '').strip()
        telefono = request.POST.get('telefono', '').strip()
        rol_id = request.POST.get('rol_id')
        
        # Validaciones
        if not all([nombre, apellido, rol_id]):
            return JsonResponse({'success': False, 'error': 'Nombre, apellido y rol son obligatorios.'})
        
        # Verificar rol
        try:
            rol = Rol.objects.get(id=rol_id)
            if rol.nombre != 'trabajador':
                return JsonResponse({'success': False, 'error': 'Solo puedes asignar el rol de trabajador.'})
        except Rol.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Rol no válido.'})
        
        # Actualizar trabajador
        campos_anteriores = {
            'nombre': trabajador.nombre,
            'apellido': trabajador.apellido,
            'telefono': trabajador.telefono
        }
        
        trabajador.nombre = nombre
        trabajador.apellido = apellido
        trabajador.telefono = telefono or None
        trabajador.rol = rol
        trabajador.save()
        
        # Identificar campos que cambiaron para el email
        campos_actualizados = {}
        if campos_anteriores['nombre'] != nombre:
            campos_actualizados['Nombre'] = nombre
        if campos_anteriores['apellido'] != apellido:
            campos_actualizados['Apellido'] = apellido
        if campos_anteriores['telefono'] != (telefono or None):
            campos_actualizados['Teléfono'] = telefono or 'Sin teléfono'
        
        # Enviar email si hubo cambios
        email_enviado = False
        if campos_actualizados:
            email_enviado = enviar_email_actualizacion_trabajador(trabajador, terma, campos_actualizados)
        
        mensaje_email = " Se ha enviado una notificación por correo." if email_enviado else ""
        
        return JsonResponse({
            'success': True,
            'mensaje': f"Trabajador {nombre} {apellido} actualizado exitosamente.{mensaje_email}"
        })
        
    except Exception as e:
        logger.error(f"Error al editar trabajador: {str(e)}")
        return JsonResponse({'success': False, 'error': f'Error interno: {str(e)}'})


@admin_terma_required
def cambiar_estado_trabajador(request, trabajador_uuid):
    """Vista para habilitar/inhabilitar trabajador."""
    print(f"FUNCIÓN CAMBIAR ESTADO LLAMADA - UUID: {trabajador_uuid} ")
    logger.info(f" FUNCIÓN CAMBIAR ESTADO LLAMADA - UUID: {trabajador_uuid}")
    logger.info(f"=== INICIO CAMBIAR ESTADO TRABAJADOR UUID: {trabajador_uuid} ===")
    try:
        from usuarios.models import Usuario, Rol
        from .email_utils import enviar_email_cambio_estado_trabajador
        
        if request.method != 'POST':
            return JsonResponse({'success': False, 'error': 'Método no permitido'})
        
        usuario_admin = request.user
        terma = usuario_admin.terma
        
        # Obtener trabajador
        trabajador = get_object_or_404(Usuario, uuid=trabajador_uuid)
        logger.info(f"=== TRABAJADOR ENCONTRADO: {trabajador.email}, ESTADO ACTUAL: {trabajador.is_active} ===")
        
        # Verificar permisos: debe ser trabajador actual de la terma O ex-trabajador de esta terma
        es_trabajador_actual = (trabajador.terma == terma and trabajador.rol and trabajador.rol.nombre == 'trabajador')
        
        # Verificar si fue trabajador de esta terma anteriormente (para reactivación)
        from usuarios.models import HistorialTrabajador
        fue_trabajador_anterior = HistorialTrabajador.objects.filter(
            usuario=trabajador, 
            terma=terma
        ).exists()
        
        if not es_trabajador_actual and not fue_trabajador_anterior:
            logger.warning(f"=== PERMISO DENEGADO: {trabajador.email} no es/fue trabajador de {terma.nombre_terma} ===")
            return JsonResponse({'success': False, 'error': 'No tienes permisos para modificar este trabajador.'})
        
        logger.info(f"=== PERMISO CONCEDIDO: es_trabajador_actual={es_trabajador_actual}, fue_trabajador_anterior={fue_trabajador_anterior} ===")
        
        # No permitir desactivar al mismo administrador
        if trabajador.id == usuario_admin.id:
            return JsonResponse({'success': False, 'error': 'No puedes desactivar tu propia cuenta.'})
        
        # Determinar el nuevo estado - para jefe de terma es diferente
        if usuario_admin.rol and usuario_admin.rol.nombre == 'administrador_terma':
            # Para jefe de terma: "desactivar" significa cambiar rol, no desactivar cuenta
            if trabajador.rol and trabajador.rol.nombre == 'trabajador':
                # Está activo como trabajador, lo vamos a convertir a cliente
                nuevo_estado_cuenta = True  # La cuenta sigue activa
                accion_realizada = 'rol_cambiado_a_cliente'
                logger.info(f"=== JEFE DE TERMA: CONVIRTIENDO TRABAJADOR A CLIENTE ===")
            else:
                # Es cliente/ex-trabajador, lo vamos a reactivar como trabajador
                nuevo_estado_cuenta = True  # La cuenta sigue activa
                accion_realizada = 'rol_cambiado_a_trabajador'
                logger.info(f"=== JEFE DE TERMA: CONVIRTIENDO CLIENTE A TRABAJADOR ===")
        else:
            # Para admin general: desactivar/activar cuenta normalmente
            nuevo_estado_cuenta = not trabajador.is_active
            accion_realizada = 'estado_cuenta_cambiado'
            logger.info(f"=== ADMIN GENERAL: CAMBIANDO ESTADO DE CUENTA ===")
        
        logger.info(f"=== ACCIÓN: {accion_realizada}, ESTADO CUENTA: {nuevo_estado_cuenta} ===")
        
        # Aplicar cambios según la acción
        if accion_realizada == 'rol_cambiado_a_cliente':
            # Jefe de terma convierte trabajador a cliente
            logger.info(f"=== CONVIRTIENDO TRABAJADOR A CLIENTE ===")
            logger.info(f"=== ROL ACTUAL: {trabajador.rol.nombre if trabajador.rol else None} ===")
            
            from usuarios.models import HistorialTrabajador
            
            # Finalizar el historial activo del trabajador en esta terma
            historial_activo = HistorialTrabajador.objects.filter(
                usuario=trabajador, 
                terma=terma, 
                activo=True
            ).first()
            

            if historial_activo:
                historial_activo.finalizar(motivo='convertido_a_cliente')
                logger.info(f"=== HISTORIAL FINALIZADO ===")
            else:
                # Si no existe historial, crearlo y finalizarlo inmediatamente
                HistorialTrabajador.objects.create(
                    usuario=trabajador,
                    terma=terma,
                    rol=trabajador.rol,
                    fecha_inicio=trabajador.date_joined,
                    fecha_fin=timezone.now(),
                    motivo_fin='convertido_a_cliente',
                    activo=False
                )
                logger.info(f"=== HISTORIAL CREADO Y FINALIZADO ===")

            # Cambiar rol a cliente
            try:
                rol_cliente = Rol.objects.get(id=1)
                trabajador.rol = rol_cliente
                trabajador.terma = None
                trabajador.is_active = True  # La cuenta permanece activa
                trabajador.estado = True     # El estado también permanece activo
                logger.info(f"=== ROL CAMBIADO A CLIENTE - CUENTA ACTIVA ===")
            except Rol.DoesNotExist:
                logger.warning("=== ROL CLIENTE NO ENCONTRADO ===")

            mensaje_respuesta = f"Trabajador {trabajador.get_full_name()} convertido a cliente exitosamente."
            nuevo_estado_respuesta = True  # Para el frontend
            
        elif accion_realizada == 'rol_cambiado_a_trabajador':
            # Jefe de terma convierte cliente/ex-trabajador a trabajador
            logger.info(f"=== CONVIRTIENDO A TRABAJADOR ===")
            
            from usuarios.models import HistorialTrabajador
            
            try:
                rol_trabajador = Rol.objects.get(nombre='trabajador')
                trabajador.rol = rol_trabajador
                trabajador.terma = terma
                trabajador.is_active = True
                trabajador.estado = True
                
                # Crear nuevo historial activo
                HistorialTrabajador.crear_historial(trabajador, terma, rol_trabajador)
                logger.info(f"=== CONVERTIDO A TRABAJADOR ===")
            except Rol.DoesNotExist:
                logger.warning("=== ROL TRABAJADOR NO ENCONTRADO ===")
                
            mensaje_respuesta = f"Usuario {trabajador.get_full_name()} convertido a trabajador exitosamente."
            nuevo_estado_respuesta = True  # Para el frontend
                
        else:
            # Admin general cambia estado de cuenta (activar/desactivar completamente)
            nuevo_estado = not trabajador.is_active
            logger.info(f"=== ADMIN GENERAL: CAMBIANDO ESTADO DE CUENTA A {nuevo_estado} ===")
            
            trabajador.is_active = nuevo_estado
            trabajador.estado = nuevo_estado
            
            if not nuevo_estado:
                # Desactivando cuenta completamente
                from usuarios.models import HistorialTrabajador
                
                historial_activo = HistorialTrabajador.objects.filter(
                    usuario=trabajador, 
                    terma=terma, 
                    activo=True
                ).first()
                
                if historial_activo:
                    historial_activo.finalizar(motivo='cuenta_desactivada')
                    logger.info(f"=== HISTORIAL FINALIZADO POR DESACTIVACIÓN ===")
                
            estado_texto = "activado" if nuevo_estado else "desactivado"
            mensaje_respuesta = f"Trabajador {trabajador.get_full_name()} {estado_texto} exitosamente."
            nuevo_estado_respuesta = nuevo_estado
        
        trabajador.save()
        
        # Verificar que los cambios se guardaron correctamente
        trabajador.refresh_from_db()
        logger.info(f"=== POST-SAVE: Estado = {trabajador.is_active} ===")
        logger.info(f"=== POST-SAVE: Rol = {trabajador.rol.nombre if trabajador.rol else None} ===")
        logger.info(f"=== POST-SAVE: Terma = {trabajador.terma.nombre_terma if trabajador.terma else None} ===")
        
        # Enviar email de notificación solo para cambios de cuenta (no cambios de rol)
        email_enviado = False
        if accion_realizada == 'estado_cuenta_cambiado':
            logger.info(f"=== ENVIANDO EMAIL DE CAMBIO DE ESTADO ===")
            email_enviado = enviar_email_cambio_estado_trabajador(trabajador, terma, nuevo_estado_respuesta)
        
        mensaje_email = " Se ha enviado una notificación por correo." if email_enviado else ""
        
        logger.info(f"=== RETORNANDO RESPUESTA: {mensaje_respuesta} ===")
        return JsonResponse({
            'success': True,
            'mensaje': f"{mensaje_respuesta}{mensaje_email}",
            'nuevo_estado': nuevo_estado_respuesta
        })
        
    except Exception as e:
        logger.error(f"Error al cambiar estado trabajador: {str(e)}")
        return JsonResponse({'success': False, 'error': f'Error interno: {str(e)}'})


@admin_terma_required
def detalle_trabajador(request, trabajador_uuid):
    """Vista para obtener detalles de un trabajador."""
    try:
        logger.info(f"=== DETALLE TRABAJADOR - UUID: {trabajador_uuid} ===")
        from usuarios.models import Usuario, HistorialTrabajador
        
        usuario_admin = request.user
        terma = usuario_admin.terma
        logger.info(f"=== ADMIN: {usuario_admin.email}, TERMA: {terma.nombre_terma if terma else 'None'} ===")
        
        # Obtener trabajador
        trabajador = get_object_or_404(Usuario, uuid=trabajador_uuid)
        logger.info(f"=== TRABAJADOR ENCONTRADO: {trabajador.email} ===")
        logger.info(f"=== TRABAJADOR - Activo: {trabajador.is_active}, Rol: {trabajador.rol.nombre if trabajador.rol else 'None'}, Terma: {trabajador.terma.nombre_terma if trabajador.terma else 'None'} ===")
        
        # Verificar permisos usando el historial de trabajadores
        tiene_permisos = False
        motivo_permiso = ""
        
        # Verificar si es trabajador activo en esta terma
        if trabajador.is_active and trabajador.terma == terma and trabajador.rol and trabajador.rol.nombre == 'trabajador':
            tiene_permisos = True
            motivo_permiso = "trabajador activo"
            logger.info(f"=== PERMISO CONCEDIDO: {motivo_permiso} ===")
        
        # Verificar si aparece en el historial de trabajadores de esta terma
        elif HistorialTrabajador.objects.filter(usuario=trabajador, terma=terma).exists():
            tiene_permisos = True
            motivo_permiso = "en historial de terma"
            logger.info(f"=== PERMISO CONCEDIDO: {motivo_permiso} ===")
        else:
            logger.warning(f"=== PERMISO DENEGADO - No es trabajador activo ni está en historial ===")
        
        if not tiene_permisos:
            return JsonResponse({'success': False, 'error': 'No tienes permisos para ver este trabajador.'})
        
        # Construir datos del trabajador de forma segura
        try:
            fecha_registro = 'No disponible'
            if hasattr(trabajador, 'date_joined') and trabajador.date_joined:
                fecha_registro = trabajador.date_joined.strftime('%d/%m/%Y %H:%M')
            elif hasattr(trabajador, 'fecha_registro') and trabajador.fecha_registro:
                fecha_registro = trabajador.fecha_registro.strftime('%d/%m/%Y %H:%M')
            
            ultimo_login = 'Nunca'
            if trabajador.last_login:
                ultimo_login = trabajador.last_login.strftime('%d/%m/%Y %H:%M')
                
            rol_info = {
                'id': trabajador.rol.id if trabajador.rol else None,
                'nombre': trabajador.rol.nombre if trabajador.rol else 'Sin rol'
            }
            
            data = {
                'success': True,
                'trabajador': {
                    'id': trabajador.id,
                    'email': trabajador.email,
                    'nombre': trabajador.nombre,
                    'apellido': trabajador.apellido,
                    'telefono': trabajador.telefono or 'No especificado',
                    'rol': rol_info,
                    'is_active': trabajador.is_active,
                    'fecha_registro': fecha_registro,
                    'ultimo_login': ultimo_login,
                    'estado': trabajador.estado
                }
            }
            
            logger.info(f"=== DATOS CONSTRUIDOS EXITOSAMENTE ===")
            return JsonResponse(data)
            
        except Exception as data_error:
            logger.error(f"Error construyendo datos del trabajador: {str(data_error)}")
            return JsonResponse({'success': False, 'error': f'Error procesando datos: {str(data_error)}'})
        
    except Exception as e:
        logger.error(f"Error general en detalle_trabajador: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return JsonResponse({'success': False, 'error': f'Error interno: {str(e)}'})

