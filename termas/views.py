from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q
from .models import Terma, Region, Ciudad

def lista_termas(request):
    """Vista para mostrar lista de termas."""
    termas = Terma.objects.filter(estado_suscripcion='activa').select_related('ciudad', 'ciudad__region')
    context = {
        'title': 'Termas Disponibles - MiTerma',
        'termas': termas
    }
    return render(request, 'termas/lista.html', context)

def detalle_terma(request, pk):
    """Vista para mostrar detalle de una terma."""
    terma = get_object_or_404(Terma, pk=pk, estado_suscripcion='activa')
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
        ciudades = Ciudad.objects.all().select_related('region').order_by('region__nombre', 'nombre')
        
        # Manejar búsqueda de termas
        busqueda = request.GET.get('busqueda', '').strip()
        region_id = request.GET.get('region', '')
        ciudad_id = request.GET.get('ciudad', '')
        
        # Construir query de búsqueda
        query = Q(estado_suscripcion='activa')
        
        # Aplicar filtros si hay criterios de búsqueda
        if busqueda or region_id or ciudad_id:
            # Filtro por texto de búsqueda
            if busqueda:
                query &= (
                    Q(nombre_terma__icontains=busqueda) |
                    Q(descripcion_terma__icontains=busqueda) |
                    Q(ciudad__nombre__icontains=busqueda) |
                    Q(ciudad__region__nombre__icontains=busqueda)
                )
            
            # Filtro por región
            if region_id:
                query &= Q(ciudad__region__id=region_id)
            
            # Filtro por ciudad
            if ciudad_id:
                query &= Q(ciudad__id=ciudad_id)
        
        # Ejecutar la consulta
        termas = Terma.objects.filter(query).select_related('ciudad', 'ciudad__region')
        
        context = {
            'title': 'Inicio - MiTerma',
            'usuario': usuario,
            'termas': termas,
            'busqueda': busqueda,
            'region_seleccionada': region_id,
            'ciudad_seleccionada': ciudad_id,
            'regiones': regiones,
            'ciudades': ciudades,
            'total_resultados': len(termas)
        }
        
        # Renderizar el template de usuarios con los resultados
        return render(request, 'Inicio.html', context)
        
    except Usuario.DoesNotExist:
        messages.error(request, 'Sesión inválida.')
        return redirect('core:home')
