from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q
from django.contrib import messages
from .models import Terma, Region, Comuna, ImagenTerma
import os

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
    from usuarios.models import Usuario
    from django.contrib import messages
    
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
        query = Q(estado_suscripcion='true')

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
        termas_destacadas = Terma.objects.filter(query).select_related('comuna', 'comuna__region')
        context = {
            'title': 'Inicio - MiTerma',
            'usuario': usuario,
            'termas_destacadas': termas_destacadas,
            'busqueda': busqueda,
            'region_seleccionada': region_id,
            'comuna_seleccionada': comuna_id,
            'regiones': regiones,
            'comunas': comunas,
            'total_resultados': len(termas_destacadas)
        }
        # Renderizar el template de usuarios con los resultados
        return render(request, 'clientes/Inicio_cliente.html', context)
        
    except Usuario.DoesNotExist:
        messages.error(request, 'Sesión inválida.')
        return redirect('core:home')
    
def subir_fotos(request):
    """Vista para gestionar las fotos de la terma."""
    from usuarios.models import Usuario
    
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
    from usuarios.models import Usuario
    
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
