from termas.forms import SolicitudTermaForm
from termas.models import SolicitudTerma, Comuna, Terma, PlanSuscripcion
from django.shortcuts import render
from django.http import JsonResponse

def mostrar_termas(request):
    # Obtener solo termas que tienen calificaciones
    termas_query = Terma.objects.all()
    
    # Aplicar filtros basados en los parámetros GET
    comuna_filtro = request.GET.get('comuna')
    region_filtro = request.GET.get('region')
    calificacion_filtro = request.GET.get('calificacion')
    precio_min = request.GET.get('precio_min')
    precio_max = request.GET.get('precio_max')
    
    # Filtro por comuna
    if comuna_filtro:
        termas_query = termas_query.filter(comuna__nombre=comuna_filtro)
    
    # Filtro por región
    if region_filtro:
        termas_query = termas_query.filter(comuna__region__nombre=region_filtro)
    
    # Filtro por calificación mínima
    if calificacion_filtro:
        try:
            calificacion_min = float(calificacion_filtro)
            # Filtrar termas que tengan calificación promedio >= calificacion_min
            # Solo incluir termas que tengan calificaciones
            termas_query = termas_query.filter(
                calificacion_promedio__gte=calificacion_min,
                calificacion_promedio__isnull=False
            )
        except (ValueError, TypeError):
            pass
    
    # Filtro por precio mínimo
    if precio_min:
        try:
            precio_min_val = float(precio_min)
            # Filtrar termas que tengan algún tipo de entrada con precio >= precio_min
            termas_query = termas_query.filter(entradatipo__precio__gte=precio_min_val).distinct()
        except (ValueError, TypeError):
            pass
    
    # Filtro por precio máximo
    if precio_max:
        try:
            precio_max_val = float(precio_max)
            # Filtrar termas que tengan algún tipo de entrada con precio <= precio_max
            termas_query = termas_query.filter(entradatipo__precio__lte=precio_max_val).distinct()
        except (ValueError, TypeError):
            pass
    
    # Obtener termas finales con disponibilidad
    termas_raw = termas_query.prefetch_related(
        'entradatipo_set',
        'imagenes',  
        'calificacion_set',
        'comuna__region'
    ).distinct()
    
    # Las termas se mostrarán independiente de la disponibilidad del día actual
    # La verificación de disponibilidad se hará al seleccionar fecha de visita
    termas = termas_raw
    
    context = {
        'usuario': request.user,
        'termas': termas,
        'navbar_mode': 'termas_only'
    }
    return render(request, 'mostrar_termas.html', context)


def home(request):
    """Vista principal del sitio."""
    
    # Obtener termas destacadas
    termas_destacadas = Terma.objects.prefetch_related(
        'entradatipo_set',
        'imagenes',  
        'calificacion_set'
    ).select_related('comuna__region').all()[:3]  # Primeras 3 termas
    
    context = {
        'title': 'Inicio - MiTerma',
        'termas_destacadas': termas_destacadas
    }
    return render(request, 'home.html', context)


def get_comunas(request, region_id):
    """Vista para obtener las comunas de una región específica."""
    comunas = Comuna.objects.filter(region_id=region_id).values('id', 'nombre')
    return JsonResponse(list(comunas), safe=False)

from django.contrib import messages
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from termas.models import PlanSuscripcion

def planes(request):
    """Vista para mostrar los planes de MiTerma."""
    # Obtener todos los planes activos ordenados por comisión
    planes_disponibles = PlanSuscripcion.objects.filter(activo=True).order_by('porcentaje_comision')
    
    # Verificar si viene del redirect exitoso
    success = request.GET.get('success')
    context = {
        'planes': planes_disponibles,
        'show_success_popup': success == '1'
    }
    return render(request, 'planes.html', context)


def solicitud_terma(request):
    """Vista para procesar solicitud de terma."""
    plan_id = request.GET.get('plan')
    plan_seleccionado = None
    
    if plan_id:
        try:
            plan_seleccionado = PlanSuscripcion.objects.get(id=plan_id, activo=True)
        except PlanSuscripcion.DoesNotExist:
            pass
    
    if request.method == 'POST':
        form = SolicitudTermaForm(request.POST)
        if form.is_valid():
            try:
                solicitud = form.save(commit=False)
                # Si el usuario está autenticado, lo asignamos
                if request.user.is_authenticated:
                    solicitud.usuario = request.user
                solicitud.save()
                # Redirigir con parámetro de éxito para mostrar popup
                return redirect('/planes/?success=1')
            except Exception as e:
                messages.error(request, 'Ha ocurrido un error al procesar tu solicitud. Por favor, intenta nuevamente.')
                return render(request, 'solicitud_terma.html', {
                    'form': form,
                    'plan_seleccionado': plan_seleccionado
                })
        else:
            messages.error(request, 'Por favor, verifica que todos los campos estén correctamente completados.')
            return render(request, 'solicitud_terma.html', {
                'form': form,
                'plan_seleccionado': plan_seleccionado
            })
    else:
        # Crear formulario inicial
        initial_data = {}
        if plan_seleccionado:
            initial_data['plan_seleccionado'] = plan_seleccionado
            
        form = SolicitudTermaForm(initial=initial_data)
        
        context = {
            'form': form,
            'plan_seleccionado': plan_seleccionado
        }
        return render(request, 'solicitud_terma.html', context)

