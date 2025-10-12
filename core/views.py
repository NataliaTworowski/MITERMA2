from termas.forms import SolicitudTermaForm
from termas.models import SolicitudTerma, Comuna
from django.shortcuts import render
from termas.models import Terma
from django.http import JsonResponse

def mostrar_termas(request):
    termas = Terma.objects.all()
    context = {
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

def planes(request):
    """Vista para mostrar los planes de MiTerma y procesar solicitud de terma."""
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
                return render(request, 'planes.html', {'form': form})
        else:
            messages.error(request, 'Por favor, verifica que todos los campos estén correctamente completados.')
            return render(request, 'planes.html', {'form': form})
    else:
        form = SolicitudTermaForm()
        # Verificar si viene del redirect exitoso
        success = request.GET.get('success')
        print(f"DEBUG: success parameter = {success}")  # Debug log
        print(f"DEBUG: success == '1' = {success == '1'}")  # Debug log
        context = {
            'form': form,
            'show_success_popup': success == '1'
        }
        print(f"DEBUG: context = {context}")  # Debug log
        return render(request, 'planes.html', context)



