from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.hashers import check_password
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
def perfil_cliente(request):
    """Vista para mostrar el perfil del cliente."""
    # SIEMPRE obtener datos frescos desde la BD para evitar cache
    from django.contrib.auth import get_user_model
    User = get_user_model()
    usuario = User.objects.get(id=request.user.id)
    
    context = {
        'title': 'Mi Perfil - MiTerma',
        'usuario': usuario,
    }
    return render(request, 'clientes/perfil_cliente.html', context)

@cliente_required
@require_POST
def actualizar_perfil(request):
    """Vista para actualizar la información personal del cliente."""
    usuario = request.user
    
    try:
        # Verificar que es el formulario correcto
        form_type = request.POST.get('form_type')
        if form_type != 'perfil':
            print(f"DEBUG - Tipo de formulario inválido: {form_type}")
            messages.error(request, 'Tipo de formulario inválido.')
            return redirect('usuarios:perfil_cliente')
        
        # Obtener datos del formulario
        nombre = request.POST.get('nombre', '').strip()
        apellido = request.POST.get('apellido', '').strip()
        telefono = request.POST.get('telefono', '').strip()
        
        print(f"DEBUG - Actualizando perfil: nombre='{nombre}', apellido='{apellido}', telefono='{telefono}'")
        
        # Validaciones
        if not nombre or not apellido:
            messages.error(request, 'El nombre y apellido son obligatorios.')
            return redirect('usuarios:perfil_cliente')
        
        # Validar teléfono si se proporciona
        if telefono and not telefono.replace('+', '').replace(' ', '').replace('-', '').isdigit():
            messages.error(request, 'El número de teléfono debe contener solo números, espacios, guiones y el símbolo +.')
            return redirect('usuarios:perfil_cliente')
        
        # Actualizar datos en la base de datos
        usuario.nombre = nombre
        usuario.apellido = apellido
        usuario.telefono = telefono if telefono else None
        usuario.save(update_fields=['nombre', 'apellido', 'telefono'])
        
        print(f"DEBUG - Perfil actualizado exitosamente para usuario {usuario.id}")
        print(f"DEBUG - Valores guardados: nombre='{usuario.nombre}', apellido='{usuario.apellido}', telefono='{usuario.telefono}'")
        messages.success(request, 'Tu información personal ha sido actualizada correctamente.')
        
        # Los datos frescos se obtendrán en la vista perfil_cliente() que ahora
        # siempre consulta la BD directamente
        
    except Exception as e:
        print(f"DEBUG - Error al actualizar perfil: {str(e)}")
        import traceback
        print(f"DEBUG - Traceback: {traceback.format_exc()}")
        messages.error(request, f'Error al actualizar la información: {str(e)}')
    
    return redirect('usuarios:perfil_cliente')

@cliente_required
@require_POST
def cambiar_contrasena(request):
    """Vista para cambiar la contraseña del cliente."""
    usuario = request.user
    
    try:
        # Obtener datos del formulario
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        # Validaciones
        if not current_password or not new_password or not confirm_password:
            messages.error(request, 'Todos los campos de contraseña son obligatorios.')
            return redirect('usuarios:perfil_cliente')
        
        # Verificar contraseña actual
        if not check_password(current_password, usuario.password):
            messages.error(request, 'La contraseña actual es incorrecta.')
            return redirect('usuarios:perfil_cliente')
        
        # Verificar que las nuevas contraseñas coincidan
        if new_password != confirm_password:
            messages.error(request, 'Las nuevas contraseñas no coinciden.')
            return redirect('usuarios:perfil_cliente')
        
        # Validar longitud mínima
        if len(new_password) < 8:
            messages.error(request, 'La nueva contraseña debe tener al menos 8 caracteres.')
            return redirect('usuarios:perfil_cliente')
        
        # Cambiar la contraseña
        usuario.set_password(new_password)
        usuario.save()
        
        messages.success(request, 'Tu contraseña ha sido cambiada correctamente. Por favor, inicia sesión nuevamente.')
        
        # Redirigir al login para que inicie sesión con la nueva contraseña
        from django.contrib.auth import logout
        logout(request)
        return redirect('usuarios:login')
        
    except Exception as e:
        messages.error(request, f'Error al cambiar la contraseña: {str(e)}')
    
    return redirect('usuarios:perfil_cliente')

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
        'terma', 'codigoqr'  # Incluir la relación con CodigoQR
    ).prefetch_related('detalles', 'detalles__entrada_tipo', 'detalles__servicios')
    
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