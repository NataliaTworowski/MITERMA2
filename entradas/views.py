from django.shortcuts import render

def lista_entradas(request):
    """Vista para mostrar lista de entradas."""
    context = {
        'title': 'Entradas - MiTerma'
    }
    return render(request, 'entradas/lista.html', context)

def nueva_entrada(request):
    """Vista para crear nueva entrada."""
    context = {
        'title': 'Nueva Entrada - MiTerma'
    }
    return render(request, 'entradas/nueva.html', context)
