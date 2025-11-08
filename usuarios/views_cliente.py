from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from ventas.models import Compra, CodigoQR
from django.db.models import Prefetch
from ventas.utils import generar_datos_qr, generar_qr
from .decorators import cliente_required
import base64
from io import BytesIO
from django.views.decorators.http import require_POST

@cliente_required
def mostrar_entradas(request):
    """Vista para mostrar las entradas del cliente - Migrada a Django Auth."""
    # El decorador ya verificó que el usuario está autenticado y es cliente
    usuario = request.user
    
    compras = Compra.objects.filter(
        usuario_id=usuario.id,
        estado_pago='pagado',
        visible=True
    ).order_by('-fecha_compra').select_related(
        'terma'
    ).prefetch_related('detalles', 'detalles__horario_disponible', 'detalles__servicios')
    
    context = {
        'title': 'Mis Entradas - MiTerma',
        'compras': compras,
    }
    return render(request, 'clientes/mis_entradas.html', context)

@cliente_required
@require_POST
def ocultar_compra(request, compra_id):
    """Vista para ocultar una compra del historial - Migrada a Django Auth."""
    # El decorador ya verificó que el usuario está autenticado y es cliente
    usuario = request.user
    
    # Verificar que la compra pertenezca al usuario
    compra = get_object_or_404(Compra, 
        id=compra_id, 
        usuario_id=usuario.id
    )
    
    try:
        compra.visible = False
        compra.save()
        return JsonResponse({
            'success': True,
            'message': 'Entrada eliminada del historial correctamente'
        })
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)

@cliente_required
def get_qr_code(request, compra_id):
    """Vista para obtener el código QR de una compra - Migrada a Django Auth."""
    # El decorador ya verificó que el usuario está autenticado y es cliente
    usuario = request.user
    
    # Verificar que la compra pertenezca al usuario
    compra = get_object_or_404(Compra, 
        id=compra_id, 
        usuario_id=usuario.id,
        estado_pago='pagado'
    )
    
    try:
        # Obtener o generar el código QR
        codigo_qr = CodigoQR.objects.filter(compra=compra).first()
        if not codigo_qr:
            # Generar nuevo código QR
            datos_qr = generar_datos_qr(compra)
            qr_img = generar_qr(datos_qr)
        else:
            qr_img = generar_qr(codigo_qr.codigo)
        
        # Convertir la imagen a base64
        image_data = base64.b64encode(qr_img.getvalue()).decode()
        return JsonResponse({
            'qr_code': f'data:image/png;base64,{image_data}'
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)