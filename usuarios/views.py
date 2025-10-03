from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.hashers import make_password, check_password
from .models import Usuario, Rol
import re
import os
from django.conf import settings

def login_usuario(request):
    """Vista para iniciar sesión."""
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        
        # Validaciones básicas
        if not email or not password:
            messages.error(request, 'Por favor ingresa email y contraseña.')
            return redirect('core:home')
        
        try:
            # Buscar usuario por email
            usuario = Usuario.objects.get(email=email)
            
            # Verificar contraseña
            if check_password(password, usuario.password):
                # Login exitoso
                # Aquí normalmente usarías Django sessions, pero por simplicidad:
                request.session['usuario_id'] = usuario.id
                request.session['usuario_nombre'] = usuario.nombre
                request.session['usuario_email'] = usuario.email
                request.session['usuario_rol'] = usuario.rol.id
                
                messages.success(request, f'¡Bienvenid@ {usuario.nombre}!')
                # Redirigir según el rol del usuario
                if usuario.rol.id == 2:  # Administrador de termas
                    return redirect('usuarios:adm_termas')
                elif usuario.rol.id == 3:  # Rol 3
                    return redirect('usuarios:rol_tres')
                elif usuario.rol.id == 4:  # Rol 4
                    return redirect('usuarios:rol_cuatro')
                else:  # Usuario normal (rol 1 u otros)
                    return redirect('usuarios:inicio')
            else:
                messages.error(request, 'Email o contraseña incorrectos.')
                return redirect('core:home')
                
        except Usuario.DoesNotExist:
            messages.error(request, 'Email o contraseña incorrectos.')
            return redirect('core:home')
        except Exception as e:
            messages.error(request, f'Error al iniciar sesión: {str(e)}')
            return redirect('core:home')
        
    return redirect('core:home')

def inicio(request):
    """Vista para mostrar la página de inicio del usuario autenticado."""
    # Verificar si el usuario está logueado
    if 'usuario_id' not in request.session:
        messages.error(request, 'Debes iniciar sesión para acceder.')
        return redirect('core:home')
    
    # Solo redirigir si HAY búsqueda real (no parámetros vacíos)
    busqueda = request.GET.get('busqueda', '').strip()
    region = request.GET.get('region', '').strip()
    ciudad = request.GET.get('ciudad', '').strip()
    
    if busqueda or region or ciudad:  
        from django.urls import reverse
        params = request.GET.urlencode()
        url = reverse('termas:buscar')
        return redirect(f'{url}?{params}')
    
    try:
        usuario = Usuario.objects.get(id=request.session['usuario_id'])
        from termas.models import Region, Comuna
        regiones = Region.objects.all().order_by('nombre')
        comunas = Comuna.objects.all().select_related('region').order_by('region__nombre', 'nombre')
        
        context = {
            'title': 'Inicio - MiTerma',
            'usuario': usuario,
            'regiones': regiones,
            'comunas': comunas,
            'region_seleccionada': request.GET.get('region', ''),
            'comuna_seleccionada': request.GET.get('comuna', ''),
            'busqueda': request.GET.get('busqueda', ''),
        }
        return render(request, 'Inicio.html', context)
    except Usuario.DoesNotExist:
        messages.error(request, 'Sesión inválida.')
        return redirect('core:home')

def registro_usuario(request):
    """Vista para registrar nuevos usuarios."""
    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        apellido = request.POST.get('apellido', '').strip()
        email = request.POST.get('email', '').strip().lower()
        telefono = request.POST.get('telefono', '').strip()
        password = request.POST.get('password', '')
        password_confirm = request.POST.get('password_confirm', '')
        errors = []
        # Validar campos requeridos
        if not nombre:
            errors.append('El nombre es requerido.')
        if not apellido:
            errors.append('El apellido es requerido.')
        if not email:
            errors.append('El email es requerido.')
        if not password:
            errors.append('La contraseña es requerida.')
        
        # Validar email formato
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if email and not re.match(email_regex, email):
            errors.append('El formato del email no es válido.')
        
        # Validar email único
        if email and Usuario.objects.filter(email=email).exists():
            errors.append('Ya existe un usuario con este email.')
        
        # Validar contraseña
        if len(password) < 8:
            errors.append('La contraseña debe tener al menos 8 caracteres.')
        
        # Validar confirmación de contraseña
        if password != password_confirm:
            errors.append('Las contraseñas no coinciden.')
        
        # Validar longitud de campos
        if len(nombre) > 50:
            errors.append('El nombre no puede exceder 50 caracteres.')
        if len(apellido) > 50:
            errors.append('El apellido no puede exceder 50 caracteres.')
        if telefono and len(telefono) > 20:
            errors.append('El teléfono no puede exceder 20 caracteres.')
        
        if errors:
            for error in errors:
                messages.error(request, error)
            return redirect('core:home')
        
        try:
            # Obtener rol por defecto (ID 1)
            rol_cliente = Rol.objects.get(id=1)
            
            # Crear nuevo usuario
            nuevo_usuario = Usuario.objects.create(
                email=email,
                password=make_password(password),  
                nombre=nombre,
                apellido=apellido,
                telefono=telefono if telefono else None,
                rol=rol_cliente,
                estado=True
            )
            
            # Login automático después del registro
            request.session['usuario_id'] = nuevo_usuario.id
            request.session['usuario_nombre'] = nuevo_usuario.nombre
            request.session['usuario_email'] = nuevo_usuario.email
            request.session['usuario_rol'] = nuevo_usuario.rol.id
            
            messages.success(request, f'¡Bienvenid@ {nombre}! Tu cuenta ha sido creada exitosamente.')
            return redirect('usuarios:inicio')  
            
        except Rol.DoesNotExist:
            messages.error(request, 'Error del sistema: Rol no encontrado. Contacta al administrador.')
            return redirect('core:home')
        except Exception as e:
            messages.error(request, f'Error al crear la cuenta: {str(e)}')
            return redirect('core:home')
    
    return redirect('core:home')

def adm_termas(request):
    """Vista para mostrar la página de administración de termas."""
    # Verificar si el usuario está logueado
    if 'usuario_id' not in request.session:
        messages.error(request, 'Debes iniciar sesión para acceder.')
        return redirect('core:home')
    
    # Verificar si el usuario tiene el rol correcto (ID=2)
    if request.session.get('usuario_rol') != 2:
        messages.error(request, 'No tienes permisos para acceder a esta sección.')
        return redirect('usuarios:inicio')
    
    try:
        usuario = Usuario.objects.get(id=request.session['usuario_id'])
        
        context = {
            'title': 'Administración de Termas - MiTerma',
            'usuario': usuario,
            'terma': usuario.terma,
        }
        return render(request, 'adm_termas.html', context)
    except Usuario.DoesNotExist:
        messages.error(request, 'Sesión inválida.')
        return redirect('core:home')

def logout_usuario(request):
    """Vista para cerrar sesión del usuario."""
    # Limpiar todas las variables de sesión
    request.session.flush()
    
    messages.success(request, 'Has cerrado sesión correctamente.')
    return redirect('core:home')


