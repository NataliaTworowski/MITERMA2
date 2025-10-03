from django.shortcuts import render
from termas.models import Terma


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

def mostrar_termas(request):
    termas = Terma.objects.all()
    context = {
        'termas' : termas,
        'navbar_mode': 'termas_only'
    }
    return render(request, 'mostrar_termas.html', context)
