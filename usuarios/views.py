from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.hashers import make_password, check_password
from .models import Usuario, Rol, TokenRestablecerContrasena  # Agregar esta importación
import re
from .utils import enviar_email_confirmacion, enviar_email_reset_password  # Agregar enviar_email_reset_password
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

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
        from termas.models import Region, Comuna, Terma
        regiones = Region.objects.all().order_by('nombre')
        comunas = Comuna.objects.all().select_related('region').order_by('region__nombre', 'nombre')
        termas_destacadas = Terma.objects.filter(estado_suscripcion="activa").order_by('-calificacion_promedio')[:4]
        context = {
            'title': 'Inicio - MiTerma',
            'usuario': usuario,
            'regiones': regiones,
            'comunas': comunas,
            'region_seleccionada': request.GET.get('region', ''),
            'comuna_seleccionada': request.GET.get('comuna', ''),
            'busqueda': request.GET.get('busqueda', ''),
            'termas_destacadas': termas_destacadas,
        }
        return render(request, 'clientes/Inicio_cliente.html', context)
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
            
            # Enviar email de confirmación
            email_enviado = enviar_email_confirmacion(
                usuario_email=nuevo_usuario.email,
                nombre_usuario=nuevo_usuario.nombre
            )
            
            if email_enviado:
                messages.success(request, 'Registro exitoso. Te hemos enviado un email de confirmación.')
            else:
                messages.warning(request, 'Registro exitoso, pero hubo un problema enviando el email.')
            
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
        terma = usuario.terma
        # métricas de la terma
        if terma:
            # Calcular métricas usando los métodos del modelo
            terma.ingresos_totales = terma.ingresos_totales()
            terma.total_visitantes = terma.total_visitantes()
            terma.total_fotos = terma.total_fotos()
            terma.calificaciones_recientes = terma.calificaciones_recientes()
            # Usar el promedio ya calculado
            terma.calificacion_promedio = terma.calificacion_promedio or 0
            terma.total_calificaciones = terma.total_calificaciones()
        
        # Obtener filtro de comentarios desde GET parameter
        filtro_comentarios = request.GET.get('filtro_comentarios', 'recientes')
        
        context = {
            'title': 'Administración de Termas - MiTerma',
            'usuario': usuario,
        }
        
        if terma:
            context.update({
                'terma': terma,
                'calificaciones_filtradas': terma.filtro_calificaciones(filtro_comentarios),
                'estadisticas_calificaciones': terma.estadisticas_calificaciones(),
                'filtro_actual': filtro_comentarios,
            })
        
        return render(request, 'administrador_termas/adm_termas.html', context)
    except Usuario.DoesNotExist:
        messages.error(request, 'Sesión inválida.')
        return redirect('core:home')

def admin_general(request):
    """Vista para mostrar la página de administración general del sistema."""
    # Verificar si el usuario está logueado
    if 'usuario_id' not in request.session:
        messages.error(request, 'Debes iniciar sesión para acceder.')
        return redirect('core:home')
    
    # Verificar si el usuario tiene el rol correcto (ID=4 para administrador_general)
    if request.session.get('usuario_rol') != 4:
        messages.error(request, 'No tienes permisos para acceder a esta sección.')
        return redirect('usuarios:inicio')
    
    try:
        from termas.models import SolicitudTerma, Terma
        usuario = Usuario.objects.get(id=request.session['usuario_id'])
        
        # Obtener estadísticas para el dashboard
        total_termas = Terma.objects.count()
        solicitudes_pendientes = SolicitudTerma.objects.filter(estado='pendiente').count()
        total_usuarios = Usuario.objects.count()
        
        context = {
            'title': 'Administración General - MiTerma',
            'usuario': usuario,
            'stats': {
                'terma': Terma,
                'total_termas': total_termas,
                'solicitudes_pendientes': solicitudes_pendientes,
                'total_usuarios': total_usuarios,
            }
        }
        return render(request, 'administrador_general/admin_general.html', context)
    except Usuario.DoesNotExist:
        messages.error(request, 'Sesión inválida.')
        return redirect('core:home')

def solicitudes_pendientes(request):
    """Vista para mostrar las solicitudes pendientes."""
    # Verificar si el usuario está logueado
    if 'usuario_id' not in request.session:
        messages.error(request, 'Debes iniciar sesión para acceder.')
        return redirect('core:home')
    
    # Verificar si el usuario tiene el rol correcto (ID=4 para administrador_general)
    if request.session.get('usuario_rol') != 4:
        messages.error(request, 'No tienes permisos para acceder a esta sección.')
        return redirect('usuarios:inicio')
    
    try:
        from termas.models import SolicitudTerma
        usuario = Usuario.objects.get(id=request.session['usuario_id'])
        
        # Obtener todas las solicitudes pendientes
        solicitudes_pendientes = SolicitudTerma.objects.filter(
            estado='pendiente'
        ).order_by('-fecha_solicitud')
        
        context = {
            'title': 'Solicitudes Pendientes - MiTerma',
            'usuario': usuario,
            'solicitudes': solicitudes_pendientes,
        }
        return render(request, 'administrador_termas/solicitudes_pendientes.html', context)
    except Usuario.DoesNotExist:
        messages.error(request, 'Sesión inválida.')
        return redirect('core:home')

def logout_usuario(request):
    """Vista para cerrar sesión del usuario."""
    # Limpiar todas las variables de sesión
    request.session.flush()
    
    messages.success(request, 'Has cerrado sesión correctamente.')
    return redirect('core:home')

def reset_password(request):
    """Vista para solicitar código de verificación"""
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        
        if not email:
            messages.error(request, 'Por favor ingresa tu email.')
            return redirect('core:home')
        
        try:
            usuario = Usuario.objects.get(email=email)
            
            # Crear token con código
            reset_token = TokenRestablecerContrasena.objects.create(usuario=usuario)
            
            # Enviar email con código - CORREGIR AQUÍ
            email_enviado = enviar_email_reset_password(
                usuario_email=usuario.email,
                codigo_verificacion=reset_token.codigo,  # Usar 'codigo_verificacion'
                nombre_usuario=usuario.nombre
            )
            
            if email_enviado:
                messages.success(request, f'Te hemos enviado un código de verificación a tu email.')
            else:
                messages.error(request, 'Hubo un problema enviando el email.')
                
        except Usuario.DoesNotExist:
            messages.success(request, 'Si el email existe, te hemos enviado un código.')
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
        
        return redirect('core:home')
    
    return render(request, 'usuarios/reset_password.html')

def reset_password_confirm(request):
    """Vista para verificar código y cambiar contraseña"""
    if request.method == 'POST':
        codigo = request.POST.get('codigo', '').strip()
        new_password = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')
        
        if not codigo or not new_password or not confirm_password:
            messages.error(request, 'Todos los campos son requeridos.')
            return redirect('core:home')
        
        try:
            # Buscar token válido
            reset_token = TokenRestablecerContrasena.objects.get(
                codigo=codigo,
                usado=False
            )
            
            if not reset_token.es_valido():
                messages.error(request, 'El código ha expirado. Solicita uno nuevo.')
                return redirect('core:home')
            
            if len(new_password) < 8:
                messages.error(request, 'La contraseña debe tener al menos 8 caracteres.')
                return redirect('core:home')
            
            if new_password == confirm_password:
                # Cambiar contraseña
                usuario = reset_token.usuario
                usuario.password = make_password(new_password)
                usuario.save()
                
                # Marcar código como usado
                reset_token.usado = True
                reset_token.save()
                
                messages.success(request, 'Tu contraseña ha sido cambiada exitosamente.')
                return redirect('core:home')
            else:
                messages.error(request, 'Las contraseñas no coinciden.')
        
        except TokenRestablecerContrasena.DoesNotExist:
            messages.error(request, 'Código inválido o expirado.')
        except Exception as e:
            messages.error(request, f'Error al procesar la solicitud: {str(e)}')
        
        return redirect('core:home')
    
    return redirect('core:home')

# Vista AJAX para cargar comentarios filtrados
@require_http_methods(["GET"])
def cargar_comentarios_filtrados(request, terma_id):
    """Vista AJAX para cargar comentarios filtrados"""
    # Verificar que el usuario esté logueado
    if 'usuario_id' not in request.session:
        return JsonResponse({'error': 'No autorizado'}, status=401)
    
    try:
        from termas.models import Terma
        # Obtener la terma y verificar que el usuario tenga acceso
        usuario = Usuario.objects.get(id=request.session['usuario_id'])
        terma = get_object_or_404(Terma, id=terma_id)
        
        # Verificar que es el administrador de la terma
        if usuario.terma != terma:
            return JsonResponse({'error': 'Sin permisos'}, status=403)
        
        filtro = request.GET.get('filtro', 'recientes')
        calificaciones = terma.filtro_calificaciones(filtro)

        calificaciones_data = []
        for calificacion in calificaciones:
            calificaciones_data.append({
                'usuario_nombre': calificacion.usuario.nombre,
                'puntuacion': calificacion.puntuacion,
                'comentario': calificacion.comentario,
                'fecha': calificacion.fecha.strftime('%d/%m/%Y'),
                'fecha_completa': calificacion.fecha.strftime('%d/%m/%Y %H:%M'),
            })
        
        return JsonResponse({
            'calificaciones': calificaciones_data,
            'total': len(calificaciones_data)
        })
    except Usuario.DoesNotExist:
        return JsonResponse({'error': 'Usuario no encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    

def analisis_terma(request):
    """Vista para mostrar el análisis de la terma."""
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
        terma = usuario.terma
        
        context = {
            'title': 'Análisis de Terma - MiTerma',
            'usuario': usuario,
            'terma': terma,
        }
        
        return render(request, 'administrador_termas/analisis_terma.html', context)
        
    except Usuario.DoesNotExist:
        messages.error(request, 'Sesión inválida.')
        return redirect('core:home')
    except Exception as e:
        messages.error(request, f'Error al cargar análisis: {str(e)}')
        return redirect('usuarios:adm_termas')


