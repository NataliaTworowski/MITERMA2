from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from ventas.models import Compra, CodigoQR
from django.db.models import Prefetch
from ventas.utils import generar_datos_qr, generar_qr
from .decorators import cliente_required
from .models import Favorito
from termas.models import Terma
import base64
from io import BytesIO
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt

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


@cliente_required
def favoritos(request):
    """Vista para mostrar las termas favoritas del usuario."""
    usuario = request.user
    
    # Obtener termas favoritas del usuario
    favoritos = Favorito.objects.filter(usuario=usuario).select_related(
        'terma',
        'terma__comuna',
        'terma__comuna__region'
    ).prefetch_related(
        'terma__imagenes',
        'terma__entradatipo_set'
    ).order_by('-fecha_agregado')
    
    context = {
        'title': 'Mis Favoritos - MiTerma',
        'favoritos': favoritos,
    }
    return render(request, 'clientes/favoritos.html', context)


@csrf_exempt
@require_POST
def toggle_favorito(request, terma_id):
    """Vista para agregar o quitar una terma de favoritos."""
    if not request.user.is_authenticated:
        return JsonResponse({
            'success': False,
            'error': 'Debes iniciar sesión para usar favoritos',
            'redirect': 'login'
        }, status=401)
    
    # Verificar que sea cliente
    if not hasattr(request.user, 'rol') or not request.user.rol or request.user.rol.nombre != 'cliente':
        return JsonResponse({
            'success': False,
            'error': 'No tienes permisos para esta acción'
        }, status=403)
    
    usuario = request.user
    
    try:
        terma = get_object_or_404(Terma, id=terma_id, estado_suscripcion='activa')
        
        favorito, created = Favorito.objects.get_or_create(
            usuario=usuario,
            terma=terma
        )
        
        if created:
            # Se agregó a favoritos
            return JsonResponse({
                'success': True,
                'action': 'added',
                'message': f'{terma.nombre_terma} agregado a favoritos'
            })
        else:
            # Ya estaba en favoritos, lo eliminamos
            favorito.delete()
            return JsonResponse({
                'success': True,
                'action': 'removed',
                'message': f'{terma.nombre_terma} eliminado de favoritos'
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


def verificar_favorito(request, terma_id):
    """Vista para verificar si una terma está en favoritos."""
    if not request.user.is_authenticated:
        return JsonResponse({
            'es_favorito': False
        })
    
    # Verificar que sea cliente
    if not hasattr(request.user, 'rol') or not request.user.rol or request.user.rol.nombre != 'cliente':
        return JsonResponse({
            'es_favorito': False
        })
    
    usuario = request.user
    
    es_favorito = Favorito.objects.filter(
        usuario=usuario,
        terma_id=terma_id
    ).exists()
    
    return JsonResponse({
        'es_favorito': es_favorito
    })