from django.shortcuts import render, redirect

def mostrar_entradas(request):
    """Vista para mostrar las entradas del cliente."""
    context = {
        'title': 'Mis Entradas - MiTerma',
        'usuario': request.user,
    }
    return render(request, 'clientes/mis_entradas.html', context)