"""
Views para manejo de usuarios invitados y su conversión a usuarios registrados
"""
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect
from django.db import transaction
import logging

from .models import Usuario
from ventas.models import Compra

logger = logging.getLogger(__name__)


def registro_con_historial(request):
    """
    Permite a usuarios que compraron como invitados registrarse y heredar su historial
    """
    if request.user.is_authenticated:
        return redirect('usuarios:inicio')
    
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        nombre = request.POST.get('nombre', '').strip()
        apellido = request.POST.get('apellido', '').strip()
        password = request.POST.get('password', '')
        password_confirm = request.POST.get('password_confirm', '')
        
        # Validaciones básicas
        if not all([email, nombre, apellido, password]):
            messages.error(request, 'Todos los campos son obligatorios.')
            return render(request, 'usuarios/registro_con_historial.html')
        
        if password != password_confirm:
            messages.error(request, 'Las contraseñas no coinciden.')
            return render(request, 'usuarios/registro_con_historial.html')
        
        if len(password) < 6:
            messages.error(request, 'La contraseña debe tener al menos 6 caracteres.')
            return render(request, 'usuarios/registro_con_historial.html')
        
        try:
            with transaction.atomic():
                # Buscar usuario invitado con este email
                usuario_invitado = Usuario.objects.filter(
                    email=email, 
                    es_invitado=True
                ).first()
                
                if usuario_invitado:
                    # Convertir usuario invitado a registrado
                    usuario = usuario_invitado.convertir_a_registrado(apellido, password)
                    
                    # Contar compras del historial
                    compras_count = Compra.objects.filter(usuario=usuario).count()
                    
                    logger.info(f"Usuario invitado convertido a registrado: {email}, {compras_count} compras heredadas")
                    
                    # Login automático
                    login(request, usuario, backend='usuarios.auth_backend.CustomAuthBackend')
                    
                    messages.success(
                        request, 
                        f'¡Cuenta creada exitosamente! Tienes {compras_count} compra(s) en tu historial.'
                    )
                    
                else:
                    # Crear nuevo usuario (verificar que no exista uno registrado)
                    if Usuario.objects.filter(email=email, es_invitado=False).exists():
                        messages.error(request, 'Ya existe una cuenta registrada con este email.')
                        return render(request, 'usuarios/registro_con_historial.html')
                    
                    # Obtener rol de cliente
                    try:
                        from .models import Rol
                        rol_cliente = Rol.objects.get(id=1)
                    except:
                        rol_cliente = None
                    
                    usuario = Usuario.objects.create_user(
                        email=email,
                        nombre=nombre,
                        apellido=apellido,
                        password=password,
                        rol=rol_cliente
                    )
                    
                    logger.info(f"Nuevo usuario registrado: {email}")
                    
                    # Login automático
                    login(request, usuario, backend='usuarios.auth_backend.CustomAuthBackend')
                    
                    messages.success(request, '¡Cuenta creada exitosamente!')
                
                return redirect('usuarios:inicio')
                
        except Exception as e:
            logger.error(f"Error en registro con historial: {str(e)}")
            messages.error(request, 'Error al crear la cuenta. Inténtalo nuevamente.')
            return render(request, 'usuarios/registro_con_historial.html')
    
    return render(request, 'usuarios/registro_con_historial.html')


@require_POST
@csrf_protect
def verificar_historial_email(request):
    """
    API para verificar si un email tiene compras como invitado
    """
    email = request.POST.get('email', '').strip().lower()
    
    if not email:
        return JsonResponse({'error': 'Email requerido'}, status=400)
    
    try:
        # Buscar usuario invitado
        usuario_invitado = Usuario.objects.filter(
            email=email, 
            es_invitado=True
        ).first()
        
        if usuario_invitado:
            # Contar compras
            compras_count = Compra.objects.filter(usuario=usuario_invitado).count()
            
            return JsonResponse({
                'tiene_historial': True,
                'compras_count': compras_count,
                'nombre': usuario_invitado.nombre
            })
        else:
            return JsonResponse({'tiene_historial': False})
            
    except Exception as e:
        logger.error(f"Error verificando historial: {str(e)}")
        return JsonResponse({'error': 'Error interno'}, status=500)