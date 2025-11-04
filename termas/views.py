from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q
from django.contrib import messages
from .models import Terma, Region, Comuna, ImagenTerma
from usuarios.models import Usuario
import os
from entradas.models import EntradaTipo

def lista_termas(request):
    """Vista para mostrar lista de termas."""
    termas = Terma.objects.filter(estado_suscripcion='true').select_related('ciudad', 'ciudad__region')
    context = {
        'title': 'Termas Disponibles - MiTerma',
        'termas': termas
    }
    return render(request, 'termas/lista.html', context)

def detalle_terma(request, pk):
    """Vista para mostrar detalle de una terma."""
    terma = get_object_or_404(Terma, pk=pk, estado_suscripcion='true')
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
    
def subir_fotos(request):
    """Vista para gestionar las fotos de la terma."""
    
    # Verificar si el usuario está logueado
    if 'usuario_id' not in request.session:
        messages.error(request, 'Debes iniciar sesión para acceder.')
        return redirect('core:home')
    
    # Verificar si el usuario tiene el rol correcto (ID=2)
    if request.session.get('usuario_rol') != 2:
        messages.error(request, 'No tienes permisos para acceder a esta sección.')
        return redirect('usuarios:inicio')
    
    try:
        usuario = Usuario.objects.get(id=request.session['usuario_id'])
        
        # Verificar que el usuario tenga una terma asignada
        if not usuario.terma:
            messages.error(request, 'No tienes una terma asignada. Contacta al administrador.')
            return redirect('usuarios:adm_termas')
        
        # Procesar subida de foto
        if request.method == 'POST':
            foto = request.FILES.get('foto')
            descripcion = request.POST.get('descripcion', '').strip()
            
            if not foto:
                messages.error(request, 'Por favor selecciona una foto.')
                return redirect('termas:subir_fotos')
            
            # Validar tipo de archivo
            allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp']
            if foto.content_type not in allowed_types:
                messages.error(request, 'Solo se permiten archivos JPG, PNG y WEBP.')
                return redirect('termas:subir_fotos')
            
            # Validar tamaño (10MB máximo)
            if foto.size > 10 * 1024 * 1024:  # 10MB
                messages.error(request, 'La foto no puede superar los 10MB.')
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
                
                messages.success(request, 'Foto subida exitosamente.')
                return redirect('termas:subir_fotos')
                
            except Exception as e:
                messages.error(request, f'Error al subir la foto: {str(e)}')
                return redirect('termas:subir_fotos')
        
        # Obtener todas las fotos de la terma
        fotos = ImagenTerma.objects.filter(terma=usuario.terma).order_by('-id')
        
        context = {
            'title': 'Gestión de Fotos - MiTerma',
            'usuario': usuario,
            'terma': usuario.terma,
            'fotos': fotos,
        }
        return render(request, 'administrador_termas/subir_fotos.html', context)
        
    except Usuario.DoesNotExist:
        messages.error(request, 'Sesión inválida.')
        return redirect('core:home')

def eliminar_foto(request, foto_id):
    """Vista para eliminar una foto de la terma."""
    
    # Verificar si el usuario está logueado
    if 'usuario_id' not in request.session:
        messages.error(request, 'Debes iniciar sesión para acceder.')
        return redirect('core:home')
    
    # Verificar si el usuario tiene el rol correcto (ID=2)
    if request.session.get('usuario_rol') != 2:
        messages.error(request, 'No tienes permisos para realizar esta acción.')
        return redirect('usuarios:inicio')
    
    if request.method == 'POST':
        try:
            usuario = Usuario.objects.get(id=request.session['usuario_id'])
            
            # Verificar que el usuario tenga una terma asignada
            if not usuario.terma:
                messages.error(request, 'No tienes una terma asignada.')
                return redirect('usuarios:adm_termas')
            
            # Obtener la imagen y verificar que pertenezca a la terma del usuario
            imagen = get_object_or_404(ImagenTerma, id=foto_id, terma=usuario.terma)
            
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
            
            messages.success(request, 'Foto eliminada exitosamente.')
            
        except Usuario.DoesNotExist:
            messages.error(request, 'Sesión inválida.')
            return redirect('core:home')
        except Exception as e:
            messages.error(request, f'Error al eliminar la foto: {str(e)}')
    
    return redirect('termas:subir_fotos')

def analisis_terma(request):
    """Vista para mostrar el análisis de la terma."""
    # Verificar si el usuario está logueado
    if 'usuario_id' not in request.session:
        messages.error(request, 'Debes iniciar sesión para acceder.')
        return redirect('core:home')
    if request.session.get('usuario_rol') != 2:
        messages.error(request, 'No tienes permisos para acceder a esta sección.')
        return redirect('usuarios:inicio')
    try:
        from django.db.models import Count, Sum
        from datetime import datetime, timedelta
        import json
        from ventas.models import Compra, DetalleCompra
        from entradas.models import EntradaTipo
        usuario = Usuario.objects.get(id=request.session['usuario_id'])
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
        for i in range(rango-1, -1, -1):
            fecha = hoy - timedelta(days=i)
            fechas.append(fecha.strftime('%d/%m'))
            ventas_dia = Compra.objects.filter(
                fecha_compra__date=fecha,
                estado_pago='aprobado',
                terma=terma
            ).count()
            ventas_por_dia.append(ventas_dia)
        total_ventas = sum(ventas_por_dia)
        promedio_ventas = total_ventas / rango if ventas_por_dia else 0
        mejor_dia = max(ventas_por_dia) if ventas_por_dia else 0
        fecha_inicio = hoy - timedelta(days=rango-1)
        detalles = DetalleCompra.objects.filter(
            compra__terma=terma,
            compra__estado_pago='pagado',
            compra__fecha_compra__date__gte=fecha_inicio,
            compra__fecha_compra__date__lte=hoy
        ).select_related('horario_disponible__entrada_tipo')
        tipos = {}
        for detalle in detalles:
            tipo = detalle.horario_disponible.entrada_tipo.nombre
            tipos[tipo] = tipos.get(tipo, 0) + detalle.cantidad
        tipos_labels = list(tipos.keys())
        tipos_values = list(tipos.values())

            # Análisis de servicios más vendidos usando ServicioTerma
        from termas.models import ServicioTerma
        servicios_terma = ServicioTerma.objects.filter(terma=terma)
        servicios_populares = []
        servicios_populares_total = 0
        # Contar servicios vendidos usando la relación ManyToMany en DetalleCompra
        for servicio in servicios_terma:
            cantidad_vendida = DetalleCompra.objects.filter(
                compra__terma=terma,
                compra__estado_pago='pagado',
                servicios=servicio
            ).aggregate(total=Sum('cantidad'))['total'] or 0
            servicios_populares.append({
                'servicio': servicio.servicio,
                'total_vendidos': cantidad_vendida
            })
            servicios_populares_total += cantidad_vendida

        servicios_labels = [s['servicio'] for s in servicios_populares]
        servicios_values = [s['total_vendidos'] for s in servicios_populares]
        context = {
            'title': 'Análisis de Terma - MiTerma',
            'usuario': usuario,
            'terma': terma,
            'fechas_json': json.dumps(fechas),
            'ventas_por_dia_json': json.dumps(ventas_por_dia),
            'total_ventas': total_ventas,
            'promedio_ventas': round(promedio_ventas, 1),
            'mejor_dia': mejor_dia,
            'rango': rango,
            'tipos_labels_json': json.dumps(tipos_labels),
            'tipos_values_json': json.dumps(tipos_values),
            'servicios_populares': servicios_populares,
            'servicios_populares_total': servicios_populares_total,
            'servicios_labels_json': json.dumps(servicios_labels),
            'servicios_values_json': json.dumps(servicios_values),
        }
        return render(request, 'administrador_termas/analisis_terma.html', context)
    except Usuario.DoesNotExist:
        messages.error(request, 'Sesión inválida.')
        return redirect('core:home')
    except Exception as e:
        messages.error(request, f'Error al cargar análisis: {str(e)}')
        return redirect('usuarios:adm_termas')


def editar_terma(request):
    """Vista para editar la información de la terma."""
    if 'usuario_id' not in request.session:
        messages.error(request, 'Debes iniciar sesión para acceder.')
        return redirect('core:home')
    if request.session.get('usuario_rol') != 2:
        messages.error(request, 'No tienes permisos para acceder a esta sección.')
        return redirect('usuarios:inicio')
    try:
        usuario = Usuario.objects.get(id=request.session['usuario_id'])
        terma = usuario.terma
        if request.method == 'POST':
            descripcion = request.POST.get('descripcion_terma', '').strip()
            limite_ventas = request.POST.get('limite_ventas_diario')
            
            terma.descripcion_terma = descripcion
            if limite_ventas and limite_ventas.isdigit():
                limite_ventas = int(limite_ventas)
                if 1 <= limite_ventas <= 1000:
                    terma.limite_ventas_diario = limite_ventas
                else:
                    messages.error(request, 'El límite de ventas debe estar entre 1 y 1000.')
                    return redirect('termas:editar_terma')
            
            terma.save()
            messages.success(request, 'Información de la terma actualizada correctamente.')
            return redirect('termas:editar_terma')
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

def agregar_servicio(request):
    """Vista para agregar un nuevo servicio a la terma."""
    if request.method == 'POST':
        servicio = request.POST.get('servicio')
        descripcion = request.POST.get('descripcion_servicio')
        precio = request.POST.get('precio_servicio')
        usuario = Usuario.objects.get(id=request.session['usuario_id'])
        terma = usuario.terma
        from termas.models import ServicioTerma
        nuevo_servicio = ServicioTerma(
            terma=terma,
            servicio=servicio,
            descripcion=descripcion,
            precio=precio
        )
        nuevo_servicio.save()
        messages.success(request, 'Servicio agregado correctamente.')
        return redirect('termas:editar_terma')
    return redirect('termas:editar_terma')

def quitar_servicio(request, servicio_id):
    """Vista para quitar un servicio de la terma."""
    if request.method == 'POST':
        from termas.models import ServicioTerma
        servicio = get_object_or_404(ServicioTerma, id=servicio_id)
        servicio.delete()
        messages.success(request, 'Servicio eliminado correctamente.')
        return redirect('termas:editar_terma')
    return redirect('termas:editar_terma')

def editar_servicio(request, servicio_id):
    """Vista para editar un servicio de la terma."""
    if 'usuario_id' not in request.session:
        messages.error(request, 'Debes iniciar sesión para acceder.')
        return redirect('core:home')
    if request.session.get('usuario_rol') != 2:
        messages.error(request, 'No tienes permisos para acceder a esta sección.')
        return redirect('usuarios:inicio')
    from termas.models import ServicioTerma
    servicio = get_object_or_404(ServicioTerma, id=servicio_id)
    if request.method == 'POST':
        servicio.servicio = request.POST.get('servicio', servicio.servicio)
        servicio.descripcion = request.POST.get('descripcion_servicio', servicio.descripcion)
        servicio.precio = request.POST.get('precio_servicio', servicio.precio)
        servicio.save()
        messages.success(request, 'Servicio editado correctamente.')
        return redirect('termas:editar_terma')
    messages.error(request, 'Método no permitido.')
    return redirect('termas:editar_terma')

def precios_terma(request): 
    usuario = None
    terma = None
    if 'usuario_id' in request.session:
        from usuarios.models import Usuario
        usuario = Usuario.objects.get(id=request.session['usuario_id'])
        terma = usuario.terma
    context = {
        'title': 'Precios de la Terma - MiTerma',
        'usuario': usuario,
        'terma': terma,
        'servicios': terma.servicios.all() if terma else []
    }
    return render(request, 'administrador_termas/precios_terma.html', context)

def editar_entrada(request, entrada_id):
    """Vista para editar un tipo de entrada."""
    if 'usuario_id' not in request.session:
        messages.error(request, 'Debes iniciar sesión para acceder.')
        return redirect('core:home')
    if request.session.get('usuario_rol') != 2:
        messages.error(request, 'No tienes permisos para acceder a esta sección.')
        return redirect('usuarios:inicio')
    entrada = get_object_or_404(EntradaTipo, id=entrada_id)
    from termas.models import ServicioTerma
    servicios_disponibles = ServicioTerma.objects.filter(terma=entrada.terma)
    if request.method == 'POST':
        entrada.nombre = request.POST.get('nombre', entrada.nombre)
        entrada.descripcion = request.POST.get('descripcion', entrada.descripcion)
        from decimal import Decimal, InvalidOperation
        precio_str = request.POST.get('precio', None)
        duracion_str = request.POST.get('duracion_horas', None)
        error_messages = []
        if precio_str:
            try:
                entrada.precio = Decimal(precio_str)
            except InvalidOperation:
                error_messages.append('El precio ingresado no es válido.')
        if duracion_str:
            try:
                entrada.duracion_horas = int(duracion_str)
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
        return redirect('termas:precios_terma')
    context = {
        'title': 'Editar Tipo de Entrada',
        'entrada': entrada,
        'servicios_disponibles': servicios_disponibles,
        'servicios_seleccionados': entrada.servicios.values_list('id', flat=True)
    }
    return render(request, 'administrador_termas/editar_entrada.html', context)

def eliminar_entrada(request, entrada_id):
    """Vista para eliminar un tipo de entrada con confirmación."""
    if 'usuario_id' not in request.session:
        messages.error(request, 'Debes iniciar sesión para acceder.')
        return redirect('core:home')
    if request.session.get('usuario_rol') != 2:
        messages.error(request, 'No tienes permisos para acceder a esta sección.')
        return redirect('usuarios:inicio')
    entrada = get_object_or_404(EntradaTipo, id=entrada_id)
    if request.method == 'POST':
        entrada.delete()
        messages.success(request, 'Tipo de entrada eliminado correctamente.')
        return redirect('termas:precios_terma')
    context = {
        'title': 'Eliminar Tipo de Entrada',
        'entrada': entrada
    }
    return render(request, 'administrador_termas/eliminar_entrada.html', context)

def calendario_termas(request):
    """Vista para mostrar el calendario de la terma."""
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
            'title': 'Calendario de la Terma - MiTerma',
            'usuario': usuario,
            'terma': terma,
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

def vista_terma(request, terma_id):
    """Vista para mostrar los datos de una terma y permitir elegir entrada."""
    terma = get_object_or_404(Terma, id=terma_id)
    entradas = terma.get_tipos_entrada()
    imagenes = ImagenTerma.objects.filter(terma=terma)
    calificacion_promedio = terma.promedio_calificacion()

    from django.core import serializers
    import json
    servicios_por_entrada = {}
    for entrada in entradas:
        incluidos = list(entrada.servicios.values('id', 'servicio', 'descripcion', 'precio'))
        extra_queryset = terma.servicios.exclude(id__in=entrada.servicios.values_list('id', flat=True))
        extras = list(extra_queryset.values('id', 'servicio', 'descripcion', 'precio'))
        servicios_por_entrada[entrada.id] = {
            'incluidos': incluidos,
            'extras': extras,
        }

    entrada_seleccionada = entradas.first() if entradas.exists() else None
    servicios_incluidos = servicios_por_entrada[entrada_seleccionada.id]['incluidos'] if entrada_seleccionada else []
    servicios_extra = servicios_por_entrada[entrada_seleccionada.id]['extras'] if entrada_seleccionada else []

    # Procesar nuevo comentario
    if request.method == 'POST' and 'puntuacion' in request.POST and 'comentario' in request.POST:
        puntuacion = int(request.POST.get('puntuacion'))
        comentario = request.POST.get('comentario')
        usuario_id = request.session.get('usuario_id')
        if usuario_id:
            from usuarios.models import Usuario
            usuario = Usuario.objects.get(id=usuario_id)
            from termas.models import Calificacion
            Calificacion.objects.create(
                usuario=usuario,
                terma=terma,
                puntuacion=puntuacion,
                comentario=comentario
            )
            messages.success(request, '¡Tu opinión se ha guardado correctamente!')
            return redirect(request.path)
        else:
            messages.error(request, 'Debes iniciar sesión para dejar una opinión.')
            return redirect('usuarios:inicio')

    opiniones = terma.calificacion_set.select_related('usuario').order_by('-fecha')
    usuario = None
    usuario_id = request.session.get('usuario_id')
    if usuario_id:
        from usuarios.models import Usuario
        try:
            usuario = Usuario.objects.get(id=usuario_id)
        except Usuario.DoesNotExist:
            usuario = None
    context = {
        'terma': terma,
        'entradas': entradas,
        'entrada_seleccionada': entrada_seleccionada,
        'imagenes': imagenes,
        'calificacion_promedio': calificacion_promedio,
        'servicios': servicios_incluidos,
        'servicios_extra': servicios_extra,
        'servicios_por_entrada_json': json.dumps(servicios_por_entrada),
        'opiniones': opiniones,
        'usuario': usuario,
    }
    return render(request, 'administrador_termas/vista_terma.html', context)

