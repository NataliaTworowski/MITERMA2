from termas.forms import SolicitudTermaForm
from termas.models import SolicitudTerma, Comuna, Terma, PlanSuscripcion
from django.shortcuts import render
from django.http import JsonResponse

def mostrar_termas(request):
    termas = Terma.objects.all()
    context = {
        'usuario': request.user,
        'termas': termas,
        'navbar_mode': 'termas_only'
    }
    return render(request, 'mostrar_termas.html', context)


def home(request):
    """Vista principal del sitio."""
    termas_destacadas = Terma.objects.prefetch_related(
        'entradatipo_set',
        'imagenes',  
        'calificacion_set'
    ).select_related('comuna__region').all()[:3]
    
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

