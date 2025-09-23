from django.shortcuts import render

def lista_ventas(request):
    """Vista para mostrar lista de ventas."""
    context = {
        'title': 'Ventas - MiTerma'
    }
    return render(request, 'ventas/lista.html', context)

def nueva_venta(request):
    """Vista para crear nueva venta."""
    context = {
        'title': 'Nueva Venta - MiTerma'
    }
    return render(request, 'ventas/nueva.html', context)
