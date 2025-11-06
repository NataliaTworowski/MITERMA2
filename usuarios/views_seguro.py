from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Usuario

def login_usuario_seguro(request):
    """Vista de login usando el sistema de autenticación seguro de Django."""
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        
        if not email or not password:
            messages.error(request, 'Por favor completa todos los campos.')
            return redirect('core:home')
        
        # Usar el sistema de autenticación seguro de Django
        usuario = authenticate(request, email=email, password=password)
        
        if usuario:
            # Login seguro con Django
            login(request, usuario)
            messages.success(request, f'¡Bienvenid@ {usuario.nombre}!')
            
            # Redirigir según el rol del usuario
            if usuario.rol.nombre == 'administrador_terma':
                return redirect('usuarios:adm_termas')
            elif usuario.rol.nombre == 'administrador_general':
                return redirect('usuarios:admin_general')
            elif usuario.rol.nombre == 'trabajador':
                return redirect('usuarios:empleado')
            else:  # Usuario Cliente
                return redirect('usuarios:inicio')
        else:
            messages.error(request, 'Email o contraseña incorrectos.')
            return redirect('core:home')
    
    return redirect('core:home')

@login_required
def billetera_segura(request):
    """
    Vista para mostrar la billetera usando autenticación segura de Django
    """
    try:
        # Con Django Auth, request.user ya es tu modelo Usuario
        usuario = request.user
        
        # Verificar que el usuario tenga una terma asociada
        if not usuario.terma:
            messages.error(request, 'No tienes una terma asociada para acceder a la billetera.')
            return redirect('usuarios:adm_termas')
        
        terma = usuario.terma
        
        # Obtener información de la suscripción actual
        suscripcion_actual = None
        if hasattr(terma, 'suscripcion_actual') and terma.suscripcion_actual:
            suscripcion_actual = terma.suscripcion_actual
        
        context = {
            'terma': terma,
            'suscripcion_actual': suscripcion_actual,
            'usuario': usuario,
            'title': 'Billetera - MiTerma',
        }
        
        return render(request, 'administrador_termas/billetera.html', context)
        
    except Exception as e:
        messages.error(request, f'Error al cargar la billetera: {str(e)}')
        return redirect('usuarios:adm_termas')

@login_required        
def logout_usuario_seguro(request):
    """Vista de logout usando el sistema seguro de Django."""
    logout(request)
    messages.success(request, 'Has cerrado sesión correctamente.')
    return redirect('core:home')