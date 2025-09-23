from django.shortcuts import render

def home(request):
    """Vista principal del sitio."""
    context = {
        'title': 'Inicio - MiTerma'
    }
    return render(request, 'home.html', context)
