from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.http import HttpResponse
from usuarios.models import Usuario


def login_debug(request):
    """Vista de login simplificada para debugging"""
    
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        
        print(f"DEBUG: Intento de login con email: {email}")
        
        # Verificar si el usuario existe
        try:
            user_exists = Usuario.objects.get(email=email)
            print(f"DEBUG: Usuario encontrado: {user_exists.email}, Rol: {user_exists.rol}")
        except Usuario.DoesNotExist:
            print(f"DEBUG: Usuario no existe: {email}")
            return HttpResponse(f"Usuario {email} no existe en la base de datos")
        
        # Intentar autenticación
        usuario = authenticate(request, email=email, password=password)
        
        if usuario:
            print(f"DEBUG: Autenticación exitosa para: {usuario.email}")
            login(request, usuario)
            print(f"DEBUG: Login realizado. Usuario autenticado: {request.user.is_authenticated}")
            print(f"DEBUG: Usuario en request: {request.user}")
            print(f"DEBUG: Rol del usuario: {usuario.rol.nombre if usuario.rol else 'Sin rol'}")
            
            # Test de redirección simple
            if usuario.rol:
                if usuario.rol.nombre == 'cliente':
                    return HttpResponse(f"Login exitoso! Deberías ser redirigido a inicio de cliente. Rol: {usuario.rol.nombre}")
                elif usuario.rol.nombre == 'administrador_terma':
                    return HttpResponse(f"Login exitoso! Deberías ser redirigido a admin terma. Rol: {usuario.rol.nombre}")
                elif usuario.rol.nombre == 'administrador_general':
                    return HttpResponse(f"Login exitoso! Deberías ser redirigido a admin general. Rol: {usuario.rol.nombre}")
                else:
                    return HttpResponse(f"Login exitoso! Rol no reconocido: {usuario.rol.nombre}")
            else:
                return HttpResponse("Login exitoso pero usuario sin rol asignado")
        else:
            print(f"DEBUG: Autenticación falló para: {email}")
            return HttpResponse(f"Autenticación falló para {email}. Verifica la contraseña.")
    
    # Formulario simple para debug
    html = """
    <form method="post">
        {% csrf_token %}
        <p>Email: <input type="email" name="email" required></p>
        <p>Contraseña: <input type="password" name="password" required></p>
        <p><input type="submit" value="Login Debug"></p>
    </form>
    """
    
    return render(request, 'debug_login.html', {'form_html': html})


def check_user_status(request):
    """Vista para verificar el estado actual del usuario"""
    
    html = f"""
    <h2>Estado del Usuario</h2>
    <p><strong>Autenticado:</strong> {request.user.is_authenticated}</p>
    <p><strong>Usuario:</strong> {request.user}</p>
    <p><strong>ID Usuario:</strong> {getattr(request.user, 'id', 'N/A')}</p>
    <p><strong>Email:</strong> {getattr(request.user, 'email', 'N/A')}</p>
    <p><strong>Rol:</strong> {getattr(request.user.rol, 'nombre', 'Sin rol') if hasattr(request.user, 'rol') and request.user.rol else 'Sin rol'}</p>
    <p><strong>Sesiones:</strong> {dict(request.session)}</p>
    
    <hr>
    <a href="/debug/login/">Ir a Login Debug</a> | 
    <a href="/usuarios/logout/">Logout</a>
    """
    
    return HttpResponse(html)