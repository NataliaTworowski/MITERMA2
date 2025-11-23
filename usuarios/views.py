from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.hashers import make_password, check_password
from .models import Usuario, Rol, TokenRestablecerContrasena
from .decorators import (
    admin_terma_required, admin_general_required, cliente_required,
    empleado_required, role_required, any_authenticated_required
)
import re
from .utils import enviar_email_confirmacion, enviar_email_reset_password
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.cache import never_cache
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
from ventas.models import Compra 
from django.utils import timezone
from django.db.models import Sum
from termas.models import Terma, ServicioTerma
import logging

logger = logging.getLogger('security')


def get_current_user(request):
    """
    Función helper para obtener el usuario actual tanto del sistema antiguo como del nuevo.
    Permite migración gradual.
    """
    # Primero intentar con Django Auth (sistema nuevo)
    if hasattr(request, 'user') and request.user.is_authenticated:
        return request.user
    
    # Si no, usar el sistema de sesiones anterior
    if 'usuario_id' in request.session:
        try:
            return Usuario.objects.get(id=request.session['usuario_id'])
        except Usuario.DoesNotExist:
            return None
    
    return None


def is_user_authenticated(request):
    """
    Función helper para verificar autenticación en ambos sistemas.
    """
    # Django Auth
    if hasattr(request, 'user') and request.user.is_authenticated:
        return True
    
    # Sistema de sesiones anterior
    if 'usuario_id' in request.session:
        return True
    
    return False


@csrf_protect
@never_cache
def login_usuario(request):
    """
    Vista de login segura usando Django Auth.
    Reemplaza completamente el sistema de sesiones manuales.
    """
    
    # IMPORTANTE: Limpiar cualquier variable de terma inactiva anterior
    if hasattr(request, '_terma_inactiva'):
        delattr(request, '_terma_inactiva')
        logger.info("Variable _terma_inactiva anterior limpiada")
    
    # DEBUG: Verificar estado de autenticación
    logger.info(f"=== ESTADO INICIAL LOGIN ===")
    logger.info(f"Usuario actual: {request.user}")
    logger.info(f"¿Está autenticado?: {request.user.is_authenticated}")
    logger.info(f"User ID: {request.user.id if request.user.is_authenticated else 'Anonymous'}")
    
    # Si es POST, significa que viene del formulario - FORZAR LOGOUT primero
    if request.method == 'POST':
        logger.info("=== POST REQUEST - FORZANDO LOGOUT ===")
        if request.user.is_authenticated:
            logger.info(f"Usuario {request.user.email} estaba autenticado, haciendo logout")
            from django.contrib.auth import logout
            logout(request)
            request.session.flush()
            logger.info("Logout forzado y sesión limpiada")
    
    # Verificar nuevamente después del logout
    logger.info(f"=== DESPUÉS DEL LOGOUT ===")
    logger.info(f"¿Está autenticado ahora?: {request.user.is_authenticated}")
    
    # Si TODAVÍA está autenticado después del logout, hay un problema serio
    if request.user.is_authenticated:
        logger.error("PROBLEMA: Usuario sigue autenticado después del logout forzado")
        # Último recurso: limpiar completamente la sesión
        request.session.clear()
        request.session.cycle_key()
        logger.info("Sesión completamente reiniciada")
    
    if request.method == 'POST':
        # Debug: Mostrar TODOS los datos POST
        logger.info(f"=== DATOS DEL FORMULARIO ===")
        logger.info(f"POST data completo: {dict(request.POST)}")
        
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        
        logger.info(f"=== DATOS EXTRAÍDOS ===")
        logger.info(f"Email extraído: '{email}'")
        logger.info(f"Password extraído: '***' (longitud: {len(password)})")
        logger.info(f"Email raw (antes de lower): '{request.POST.get('email', '')}'")
        
        # Validaciones básicas
        if not email or not password:
            logger.warning(f"Login fallido - datos faltantes: email={bool(email)}, password={bool(password)}")
            messages.error(request, 'Por favor ingresa email y contraseña.')
            return redirect('core:home')
        
        # Validar formato de email
        if not _is_valid_email(email):
            logger.warning(f"Login fallido - email inválido: '{email}'")
            messages.error(request, 'Por favor ingresa un email válido.')
            return redirect('core:home')
        
        # Intentar autenticación con Django Auth
        logger.info(f"=== LLAMANDO AUTHENTICATE ===")
        logger.info(f"Llamando authenticate(request, email='{email}', password='***')")
        usuario = authenticate(request, email=email, password=password)
        logger.info(f"=== RESULTADO DE AUTHENTICATE ===")
        logger.info(f"Usuario retornado: {usuario}")
        logger.info(f"Usuario email (si existe): {usuario.email if usuario else 'None'}")
        logger.info(f"Usuario ID (si existe): {usuario.id if usuario else 'None'}")
        
        if usuario:
            # Login exitoso con Django Auth
            logger.info(f"Autenticación exitosa para: {usuario.email}")
            
            # Limpiar cualquier sesión anterior
            request.session.flush()
            logger.info("Sesión anterior limpiada")
            
            login(request, usuario)
            logger.info("Django login() ejecutado")
            
            # Log del evento de login
            logger.info(f"Login exitoso para rol: {usuario.rol.nombre if usuario.rol else 'sin rol'}")
            
            messages.success(request, f'¡Bienvenid@ {usuario.nombre}!')
            
            # Verificar si tiene contraseña temporal
            if usuario.tiene_password_temporal:
                logger.info("Usuario tiene contraseña temporal, mostrando modal de cambio")
                # Renderizar página especial con modal activado
                return render(request, 'cambio_password_temporal.html', {
                    'usuario': usuario,
                    'mostrar_modal': True,
                    'next_url': _get_redirect_url_by_role(usuario)
                })
            
            # Redirigir según el rol del usuario
            logger.info(f"Redirigiendo usuario por rol: {usuario.rol.nombre}")
            redirect_response = _redirect_by_role(usuario, request)
            return redirect_response
        else:
            # Verificar si el usuario existe pero está inactivo
            try:
                usuario_existe = Usuario.objects.get(email=email)
                # Verificar la contraseña manualmente
                if usuario_existe.check_password(password):
                    # Usuario y contraseña correctos, pero está inactivo
                    if not usuario_existe.estado or not usuario_existe.is_active:
                        logger.warning("Usuario inactivo intenta hacer login")
                        # Redirigir a home con parámetro para mostrar modal de usuario inactivo
                        from django.http import HttpResponseRedirect
                        from django.urls import reverse
                        return HttpResponseRedirect(reverse('core:home') + '?usuario_inactivo=1')
                    elif not usuario_existe.rol or not usuario_existe.rol.activo:
                        logger.warning("Usuario con rol inactivo intenta hacer login")
                        return HttpResponseRedirect(reverse('core:home') + '?usuario_inactivo=1')
                    
            except Usuario.DoesNotExist:
                pass
            
            # Log del intento fallido (ya se registra en el backend, pero agregamos contexto)
            logger.warning("Intento de login fallido")
            messages.error(request, 'Email o contraseña incorrectos.')
            return redirect('core:home')
    
    logger.info("Mostrando formulario de login (GET request)")
    return redirect('core:home')


def _get_redirect_url_by_role(user):
    """
    Función helper para obtener la URL de redirección según el rol del usuario.
    """
    if not user.rol:
        return '/core/home'
    
    role_redirects = {
        'administrador_terma': 'usuarios:adm_termas',
        'administrador_general': 'usuarios:admin_general', 
        'trabajador': 'usuarios:inicio_trabajador',
        'operador': 'usuarios:inicio_trabajador',
        'cliente': 'usuarios:inicio',
        'admin': 'usuarios:dashboard_admin',
        'admin_terma': 'usuarios:dashboard_admin_terma'
    }
    
    redirect_url_name = role_redirects.get(user.rol.nombre, 'usuarios:inicio')
    
    try:
        from django.urls import reverse
        return reverse(redirect_url_name)
    except Exception as e:
        logger.error(f"Error resolviendo URL {redirect_url_name}: {str(e)}")
        return '/'


def _get_redirect_url_by_role(user):
    """
    Función helper para obtener la URL de redirección según el rol del usuario.
    Retorna solo la URL sin hacer el redirect.
    """
    if not user.rol:
        return 'core:home'
    
    role_redirects = {
        'administrador_terma': 'usuarios:adm_termas',
        'administrador_general': 'usuarios:admin_general', 
        'trabajador': 'usuarios:inicio_trabajador',
        'operador': 'usuarios:inicio_trabajador',
        'cliente': 'usuarios:inicio',
        'admin': 'usuarios:dashboard_admin',
        'admin_terma': 'usuarios:dashboard_admin_terma'
    }
    
    return role_redirects.get(user.rol.nombre, 'usuarios:inicio')


def _redirect_by_role(user, request=None):
    """
    Función helper para redirigir usuarios según su rol de forma segura.
    """
    
    if not user.rol:
        logger.error("Usuario sin rol durante redirección")
        if request:
            messages.error(request, 'Tu cuenta no tiene un rol asignado. Contacta al administrador.')
            logout(request)
        return redirect('core:home')
    
    rol_nombre = user.rol.nombre
    logger.info(f"Redirección para rol: {rol_nombre}")
    
    # Diccionario actualizado con los roles correctos
    role_redirects = {
        'administrador_terma': 'usuarios:adm_termas',
        'administrador_general': 'usuarios:admin_general', 
        'trabajador': 'usuarios:inicio_trabajador',
        'operador': 'usuarios:inicio_trabajador',
        'cliente': 'usuarios:inicio',
        'admin': 'usuarios:dashboard_admin',
        'admin_terma': 'usuarios:dashboard_admin_terma'
    }
    
    redirect_url = role_redirects.get(rol_nombre, 'usuarios:inicio')
    logger.info(f"URL de redirección calculada: {redirect_url}")
    
    # Verificación de seguridad simplificada
    expected_urls = {
        'administrador_terma': 'usuarios:adm_termas',
        'administrador_general': 'usuarios:admin_general',
        'cliente': 'usuarios:inicio',
        'trabajador': 'usuarios:inicio_trabajador',
        'operador': 'usuarios:inicio_trabajador'
    }
    
    if rol_nombre in expected_urls and redirect_url != expected_urls[rol_nombre]:
        logger.error(f"ERROR CRÍTICO: Rol {rol_nombre} redirigido a URL incorrecta!")
    
    try:
        # Verificar que la URL existe
        from django.urls import reverse
        resolved_url = reverse(redirect_url)
        logger.info("URL resuelta exitosamente")
        return redirect(redirect_url)
    except Exception as e:
        logger.error(f"Error resolviendo URL {redirect_url}: {str(e)}")
        return redirect('core:home')


def _is_valid_email(email):
    """
    Validación básica de formato de email.
    """
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


@csrf_protect
def logout_usuario(request):
    """
    Vista de logout segura que limpia completamente la sesión.
    """
    user_id = None
    user_email = None
    
    if request.user.is_authenticated:
        user_id = request.user.id
        user_email = request.user.email
        logger.info(f"Usuario {user_email} realizando logout")
    
    # Limpiar mensajes acumulados antes del logout
    storage = messages.get_messages(request)
    for _ in storage:
        pass  # Esto consume y limpia todos los mensajes
    
    # Limpiar variables específicas de terma inactiva
    if hasattr(request, '_terma_inactiva'):
        delattr(request, '_terma_inactiva')
        logger.info("Variable _terma_inactiva limpiada")
    
    # Limpiar caché específico del usuario
    if user_id:
        from django.core.cache import cache
        cache.delete(f"user_{user_id}")
        if user_email:
            cache.delete(f"user_email_{user_email}")
        logger.info(f"Caché de usuario {user_id} limpiado")
    
    # Logout de Django Auth
    logout(request)
    
    # Limpiar cualquier dato de sesión restante
    request.session.flush()
    
    logger.info("Logout completo, redirigiendo al home")
    return redirect('core:home')

@login_required
def inicio(request):
    """
    Vista de inicio que redirige según el rol del usuario.
    """
    try:
        usuario = request.user
        
        # Verificar que el usuario tenga rol asignado
        if not hasattr(usuario, 'rol') or not usuario.rol:
            logger.error("Usuario sin rol asignado")
            messages.error(request, 'Tu cuenta no tiene un rol asignado. Contacta al administrador.')
            return redirect('core:home')
        
        # Redirigir según el rol del usuario
        if usuario.rol.nombre == 'cliente':
            return inicio_cliente(request)
        elif usuario.rol.nombre in ['operador', 'trabajador']:
            return redirect('usuarios:inicio_trabajador')
        elif usuario.rol.nombre == 'administrador_general':
            return redirect('usuarios:admin_general')
        elif usuario.rol.nombre in ['admin_terma', 'administrador_terma']:
            return redirect('usuarios:adm_termas')
        else:
            logger.error(f"Rol no reconocido: {usuario.rol.nombre}")
            messages.error(request, 'Tu rol no está configurado correctamente. Contacta al administrador.')
            return redirect('core:home')
            
    except Exception as e:
        logger.error(f"Error en vista de inicio: {str(e)}")
        messages.error(request, 'Error al acceder. Intenta nuevamente.')
        return redirect('core:home')

def inicio_cliente(request):
    """
    Vista de inicio específica para usuarios clientes.
    """
    try:
        usuario = request.user
        
        logger.info("Usuario cliente autenticado correctamente")
        
        # Solo redirigir si HAY búsqueda real (no parámetros vacíos)
        busqueda = request.GET.get('busqueda', '').strip()
        region = request.GET.get('region', '').strip()
        comuna = request.GET.get('comuna', '').strip()

        from termas.models import Region, Comuna, Terma
        from datetime import date
        regiones = Region.objects.all().order_by('nombre')
        comunas = Comuna.objects.all().select_related('region').order_by('region__nombre', 'nombre')
        termas_qs = Terma.objects.filter(estado_suscripcion="activa")
        
        if busqueda:
            from django.db.models import Q
            termas_qs = termas_qs.filter(
                Q(nombre_terma__icontains=busqueda) | Q(descripcion_terma__icontains=busqueda)
            )
        if region:
            termas_qs = termas_qs.filter(comuna__region__id=region)
        if comuna:
            termas_qs = termas_qs.filter(comuna__id=comuna)
        
        # Obtener termas activas con entradas definidas
        termas_qs = Terma.objects.filter(estado_suscripcion="activa").prefetch_related('entradatipo_set')
        
        if busqueda:
            from django.db.models import Q
            termas_qs = termas_qs.filter(
                Q(nombre_terma__icontains=busqueda) | Q(descripcion_terma__icontains=busqueda)
            )
        if region:
            termas_qs = termas_qs.filter(comuna__region__id=region)
        if comuna:
            termas_qs = termas_qs.filter(comuna__id=comuna)
        
        # Filtrar solo termas que tienen entradas definidas
        # No filtramos por disponibilidad aquí porque las reservas son para fechas futuras
        
        termas_con_entradas = []
        for terma in termas_qs:
            # Verificar que tenga tipos de entrada activos
            if not terma.entradatipo_set.filter(estado=True).exists():
                continue
                
            # Solo verificar que la terma tenga límite configurado (si no, disponibilidad ilimitada)
            # La verificación de disponibilidad específica se hará al seleccionar fecha de visita
            if terma.limite_ventas_diario is None or terma.limite_ventas_diario > 0:
                termas_con_entradas.append(terma)
        
        orden = request.GET.get('orden', 'recientes')
        if orden == 'populares':
            # Ordenar por promedio de calificación
            termas_con_entradas.sort(key=lambda t: t.calificacion_promedio or 0, reverse=True)
        elif orden == 'recientes':
            # Ordenar por fecha de suscripción
            termas_con_entradas.sort(key=lambda t: t.fecha_suscripcion if t.fecha_suscripcion else date.min, reverse=True)
        elif orden == 'precio':
            # Ordenar por precio mínimo
            termas_con_entradas.sort(key=lambda t: t.precio_minimo() if t.precio_minimo() is not None else float('inf'))
        
        # Tomar solo 4 termas para "Termas de la plataforma"
        termas_destacadas = termas_con_entradas[:4]
        
        # Termas con plan premium para el carrusel
        termas_premium = Terma.objects.filter(
            estado_suscripcion="activa",
            plan_actual__nombre="premium"
        ).select_related('comuna__region', 'plan_actual').prefetch_related('imagenes')
        
        # Solo filtrar que tengan entradas activas
        termas_premium = [t for t in termas_premium if t.entradatipo_set.filter(estado=True).exists()]
        termas_premium = termas_premium[:12]  # Máximo 12 para 3 slides de 4
        
        # Termas populares (calificación >= 4.0)
        termas_populares = Terma.objects.filter(
            estado_suscripcion="activa",
            calificacion_promedio__gte=4.0
        ).select_related('comuna__region').prefetch_related('imagenes').order_by('-calificacion_promedio')
        
        # Solo filtrar que tengan entradas activas
        termas_populares = [t for t in termas_populares if t.entradatipo_set.filter(estado=True).exists()]
        termas_populares = termas_populares[:4]
        
        context = {
            'title': 'Inicio - MiTerma',
            'usuario': usuario,
            'regiones': regiones,
            'comunas': comunas,
            'region_seleccionada': region,
            'comuna_seleccionada': comuna,
            'busqueda': busqueda,
            'orden': orden,
            'termas_destacadas': termas_destacadas,
            'termas_premium': termas_premium,
            'termas_populares': termas_populares,
            'total_resultados': termas_qs.count() if (busqueda or region or comuna) else None,
        }
        return render(request, 'clientes/Inicio_cliente.html', context)
        
    except Exception as e:
        logger.error(f"Error en vista inicio: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        messages.error(request, 'Ocurrió un error al cargar el dashboard.')
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


@admin_terma_required
def adm_termas(request):
    """
    Vista para mostrar la página de administración de termas usando Django Auth.
    """
    try:
        # El decorador ya verificó autenticación y permisos
        usuario = request.user
        terma = usuario.terma
        
        # Verificar si la terma está inactiva (viene del decorador)
        # IMPORTANTE: Solo leer esta variable si el usuario es realmente admin de terma
        terma_inactiva = False
        if (hasattr(usuario, 'rol') and usuario.rol and 
            usuario.rol.nombre == 'administrador_terma' and 
            hasattr(request, '_terma_inactiva')):
            terma_inactiva = getattr(request, '_terma_inactiva', False)
            logger.info(f"Admin terma {usuario.email}: terma_inactiva = {terma_inactiva}")
        
        # Si la terma está inactiva, mostrar página especial
        if terma_inactiva:
            context = {
                'title': f'Terma Inactiva - {terma.nombre_terma if terma else "Mi Terma"}',
                'usuario': usuario,
                'terma': terma,
                'terma_inactiva': True,
            }
            logger.info(f"Mostrando página de terma inactiva para {usuario.email}")
            return render(request, 'administrador_termas/adm_termas.html', context)
        
        # Obtener filtro de comentarios desde GET parameter
        filtro_comentarios = request.GET.get('filtro_comentarios', 'recientes')
        
        # Métricas de la terma
        if terma:
            from ventas.models import Compra
            from datetime import date
            from ventas.disponibilidad_utils import calcular_disponibilidad_terma
            
            # Calcular métricas usando los métodos del modelo
            terma.ingresos_totales = terma.ingresos_totales()
            terma.total_visitantes = terma.total_visitantes()
            terma.total_fotos = terma.total_fotos()
            terma.calificaciones_recientes = terma.calificaciones_recientes()
            # Usar el promedio ya calculado
            terma.calificacion_promedio = terma.calificacion_promedio or 0
            terma.total_calificaciones = terma.total_calificaciones()
            
            # Calcular disponibilidad para hoy
            disponibilidad_hoy = calcular_disponibilidad_terma(terma.id, date.today())
            
            # Entradas vendidas para hoy (usar la misma lógica que el calendario)
            from ventas.models import DetalleCompra
            entradas_vendidas_hoy = DetalleCompra.objects.filter(
                compra__terma=terma, 
                compra__fecha_visita=date.today(),
                compra__estado_pago='pagado'
            ).aggregate(total=Sum('cantidad'))['total'] or 0
        else:
            entradas_vendidas_hoy = 0
            disponibilidad_hoy = None
        
        context = {
            'title': f'Administrador - {terma.nombre_terma if terma else "Mi Terma"}',
            'usuario': usuario,
            'terma': terma,
            'filtro_comentarios': filtro_comentarios,
            'now': timezone.now(),
        }
        
        # Agregar datos específicos de la terma si existe
        if terma:
            context.update({
                'calificaciones_filtradas': terma.filtro_calificaciones(filtro_comentarios),
                'estadisticas_calificaciones': terma.estadisticas_calificaciones(),
                'servicios_populares': terma.servicios_populares(),
                'filtro_actual': filtro_comentarios,
                'entradas_vendidas_hoy': entradas_vendidas_hoy,
                'disponibilidad_hoy': disponibilidad_hoy,
            })
        
        # Log de acceso exitoso
        logger.info(f"Acceso dashboard admin terma")
        
        return render(request, 'administrador_termas/adm_termas.html', context)
        
    except Exception as e:
        logger.error(f"Error en vista adm_termas: {str(e)}")
        messages.error(request, 'Ocurrió un error al cargar el dashboard.')
        return redirect('core:home')


@admin_terma_required
def limpiar_compras_hoy(request):
    """
    Vista AJAX para limpiar las compras de hoy (útil para pruebas)
    """
    import json
    from datetime import date
    from django.views.decorators.http import require_http_methods
    from django.views.decorators.csrf import csrf_exempt
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método no permitido'})
    
    try:
        usuario = request.user
        terma = usuario.terma
        
        if not terma:
            return JsonResponse({'success': False, 'message': 'No tienes una terma asignada'})
        
        # Eliminar compras de hoy para esta terma
        from ventas.models import Compra
        compras_hoy = Compra.objects.filter(
            terma=terma,
            fecha_visita=date.today()
        )
        
        cantidad_eliminadas = compras_hoy.count()
        compras_hoy.delete()
        
        logger.info(f"Compras de hoy limpiadas por {usuario.email} - Terma: {terma.nombre_terma} - Cantidad: {cantidad_eliminadas}")
        
        return JsonResponse({
            'success': True, 
            'message': f'Se eliminaron {cantidad_eliminadas} compras de hoy',
            'cantidad': cantidad_eliminadas
        })
        
    except Exception as e:
        logger.error(f"Error limpiando compras de hoy: {str(e)}")
        return JsonResponse({'success': False, 'message': 'Error interno del servidor'})


@admin_general_required
def admin_general(request):
    """
    Vista para mostrar la página de administración general del sistema usando Django Auth.
    """
    try:
        from termas.models import SolicitudTerma, Terma
        
        # El decorador ya verificó autenticación y permisos
        usuario = request.user
        
        # Obtener estadísticas para el dashboard
        total_termas = Terma.objects.count()
        solicitudes_pendientes = SolicitudTerma.objects.filter(estado='pendiente').count()
        total_usuarios = Usuario.objects.count()
        
        # Métricas adicionales
        termas_activas = Terma.objects.filter(estado_suscripcion='activa').count()
        termas_inactivas = total_termas - termas_activas
        
        context = {
            'title': 'Administración General - MiTerma',
            'usuario': usuario,
            'stats': {
                'terma': Terma,
                'total_termas': total_termas,
                'termas_activas': termas_activas,
                'termas_inactivas': termas_inactivas,
                'solicitudes_pendientes': solicitudes_pendientes,
                'total_usuarios': total_usuarios,
            }
        }
        
        # Log de acceso exitoso
        logger.info(f"Acceso dashboard admin general: {usuario.email}")
        
        return render(request, 'administrador_general/admin_general.html', context)
        
    except Exception as e:
        logger.error(f"Error en vista admin_general: {str(e)}")
        messages.error(request, 'Ocurrió un error al cargar el dashboard.')
        return redirect('core:home')


@admin_general_required
def solicitudes_pendientes(request):
    """
    Vista para mostrar las solicitudes pendientes usando Django Auth.
    """
    try:
        from termas.models import SolicitudTerma
        
        # El decorador ya verificó autenticación y permisos
        usuario = request.user
        
        # Obtener todas las solicitudes pendientes
        solicitudes_pendientes = SolicitudTerma.objects.filter(
            estado='pendiente'
        ).order_by('-fecha_solicitud')
        
        context = {
            'title': 'Solicitudes Pendientes - MiTerma',
            'usuario': usuario,
            'solicitudes': solicitudes_pendientes,
        }
        
        # Log de acceso
        logger.info(f"Acceso solicitudes pendientes: {usuario.email}")
        
        return render(request, 'administrador_termas/solicitudes_pendientes.html', context)
        
    except Exception as e:
        logger.error(f"Error en vista solicitudes_pendientes: {str(e)}")
        messages.error(request, 'Ocurrió un error al cargar las solicitudes.')
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
@admin_terma_required
def cargar_comentarios_filtrados(request, terma_uuid):
    """Vista AJAX para cargar comentarios filtrados - Migrada a Django Auth"""
    try:
        from termas.models import Terma
        # Obtener la terma y verificar que el usuario tenga acceso
        usuario = request.user
        terma = get_object_or_404(Terma, uuid=terma_uuid)
        
        # Verificar que es el administrador de la terma
        if usuario.terma != terma:
            logger.warning(f"Usuario sin permisos para ver comentarios de terma {terma.nombre_terma}")
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
        
        logger.info(f"Comentarios cargados para terma {terma.nombre_terma}, filtro: {filtro}, total: {len(calificaciones_data)}")
        
        return JsonResponse({
            'calificaciones': calificaciones_data,
            'total': len(calificaciones_data)
        })
    except Exception as e:
        logger.error(f"Error al cargar comentarios filtrados: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)
    

def billetera(request):
    """
    Vista para mostrar la billetera del administrador de termas
    Sistema híbrido: soporta tanto autenticación Django como sesiones personalizadas
    """
    # Verificar autenticación usando función helper
    if not is_user_authenticated(request):
        messages.error(request, 'Debes iniciar sesión para acceder.')
        return redirect('core:home')
    
    try:
        # Obtener usuario usando función helper
        usuario = get_current_user(request)
        
        if not usuario:
            messages.error(request, 'Usuario no encontrado.')
            return redirect('core:home')
        
        # Verificar que el usuario tenga una terma asociada
        if not usuario.terma:
            messages.error(request, 'No tienes una terma asociada para acceder a la billetera.')
            return redirect('usuarios:adm_termas')
        
        terma = usuario.terma
        
        # Obtener información de la suscripción actual
        suscripcion_actual = None
        if hasattr(terma, 'suscripcion_actual') and terma.suscripcion_actual:
            suscripcion_actual = terma.suscripcion_actual
        
        # Calcular estadísticas de ingresos
        from ventas.models import Compra
        from django.db.models import Sum
        from decimal import Decimal
        from django.utils.timezone import now
        
        # Ingresos del mes actual
        current_time = now()
        inicio_mes = current_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        ingresos_mes = Compra.objects.filter(
            terma=terma,
            fecha_compra__gte=inicio_mes,
            estado_pago='pagado'
        ).aggregate(total=Sum('total'))['total'] or Decimal('0.00')
        
        # Total de ventas completadas
        total_ventas = Compra.objects.filter(
            terma=terma,
            estado_pago='pagado'
        ).count()
        
        context = {
            'terma': terma,
            'suscripcion_actual': suscripcion_actual,
            'usuario': usuario,
            'title': 'Billetera - MiTerma',
            'ingresos_mes': ingresos_mes,
            'total_ventas': total_ventas,
        }
        
        return render(request, 'administrador_termas/billetera.html', context)
        
    except Exception as e:
        messages.error(request, f'Error al cargar la billetera: {str(e)}')
        return redirect('usuarios:adm_termas')


def vincular_mercadopago(request):
    """
    Vista para iniciar el proceso de vinculación con Mercado Pago
    """
    # Verificar autenticación
    if not is_user_authenticated(request):
        messages.error(request, 'Debes iniciar sesión para acceder.')
        return redirect('core:home')
    
    try:
        usuario = get_current_user(request)
        
        if not usuario or not usuario.terma:
            messages.error(request, 'No tienes una terma asociada.')
            return redirect('usuarios:adm_termas')
        
        terma = usuario.terma
        
        # URL de login de Mercado Pago
        mp_auth_url = "https://www.mercadolibre.com/jms/mlc/lgz/msl/login/H4sIAAAAAAAEAy1OSw6CMBC9y6yJ-AMDSy_SjGWojYU27WAxxLs7VZfv_zZw3thZ8SsQ9EBrcFZbhgqCQx59nJQdRJiCUMky_aHTxYIRJ2KKCfqtFBkariShUsVxIfHgwnc1Op-F-k4JZ5OiVWIzOpXp9rRU1BFdKgnjBdyZQ-rrOue8myhqHHxA43fa1fCuxJtYcUT9gL4MyU4oz5Gtn38X23PXHA-nfdftz21zgfcHRIHk1esAAAA/user"
        
        context = {
            'terma': terma,
            'mp_auth_url': mp_auth_url,
            'title': 'Vincular Mercado Pago - MiTerma',
        }
        
        return render(request, 'administrador_termas/vincular_mercadopago.html', context)
        
    except Exception as e:
        messages.error(request, f'Error al procesar la solicitud: {str(e)}')
        return redirect('usuarios:billetera')


def mercadopago_callback(request):
    """
    Vista para manejar el callback de autorización de Mercado Pago
    """
    if not is_user_authenticated(request):
        messages.error(request, 'Debes iniciar sesión para acceder.')
        return redirect('core:home')
    
    try:
        # Obtener parámetros del callback
        authorization_code = request.GET.get('code')
        state = request.GET.get('state')  # ID de la terma
        error = request.GET.get('error')
        
        if error:
            messages.error(request, f'Error en la autorización: {error}')
            return redirect('usuarios:billetera')
        
        if not authorization_code or not state:
            messages.error(request, 'Parámetros de autorización inválidos.')
            return redirect('usuarios:billetera')
        
        # Buscar la terma (state contiene el UUID)
        from termas.models import Terma
        terma = get_object_or_404(Terma, uuid=state)
        
        # Verificar que el usuario actual es el administrador de esta terma
        usuario = get_current_user(request)
        if usuario.terma != terma:
            messages.error(request, 'No tienes permisos para vincular esta cuenta.')
            return redirect('usuarios:billetera')
        
        # Aquí normalmente intercambiarías el código por un access token
        # Por ahora, simularemos que la vinculación fue exitosa
        from django.utils.timezone import now
        terma.mercadopago_user_id = f"MP_USER_{terma.id}"
        terma.mercadopago_access_token = f"ENCRYPTED_TOKEN_{authorization_code}"
        terma.mercadopago_cuenta_vinculada = True
        terma.fecha_vinculacion_mp = now()
        terma.save()
        
        messages.success(request, '¡Cuenta de Mercado Pago vinculada exitosamente!')
        return redirect('usuarios:billetera')
        
    except Exception as e:
        messages.error(request, f'Error al procesar la autorización: {str(e)}')
        return redirect('usuarios:billetera')


# =============================================
# VISTAS PARA GESTIÓN DE TERMAS ASOCIADAS
# =============================================

@admin_general_required
def admin_general_termas_asociadas(request):
    """Vista principal para gestionar termas asociadas"""
    from termas.models import Terma, Region, Comuna, PlanSuscripcion
    from django.core.paginator import Paginator
    from django.db.models import Count, Q
    from datetime import datetime, timedelta
    
    # Filtros
    nombre_filtro = request.GET.get('nombre', '')
    estado_filtro = request.GET.get('estado', '')
    region_filtro = request.GET.get('region', '')
    comuna_filtro = request.GET.get('comuna', '')
    
    # Query base
    termas = Terma.objects.select_related('comuna__region', 'administrador', 'plan_actual').all()
    
    # Aplicar filtros
    if nombre_filtro:
        termas = termas.filter(nombre_terma__icontains=nombre_filtro)
    
    if estado_filtro:
        termas = termas.filter(estado_suscripcion=estado_filtro)
    
    if region_filtro:
        termas = termas.filter(comuna__region_id=region_filtro)
    
    if comuna_filtro:
        termas = termas.filter(comuna_id=comuna_filtro)
    
    # Ordenar
    termas = termas.order_by('-fecha_suscripcion', 'nombre_terma')
    
    # Paginación
    paginator = Paginator(termas, 12)  # 12 termas por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Estadísticas
    today = datetime.now().date()
    first_day_month = today.replace(day=1)
    
    stats = {
        'total_termas': Terma.objects.count(),
        'termas_activas': Terma.objects.filter(estado_suscripcion='activa').count(),
        'termas_inactivas': Terma.objects.filter(estado_suscripcion='inactiva').count(),
        'termas_mes': Terma.objects.filter(fecha_suscripcion__gte=first_day_month).count(),
    }
    
    # Obtener regiones y comunas para los filtros
    regiones = Region.objects.all().order_by('nombre')
    comunas = Comuna.objects.all().order_by('nombre')
    
    # Obtener planes disponibles
    planes = PlanSuscripcion.objects.all()
    
    context = {
        'page_obj': page_obj,
        'termas': page_obj,
        'stats': stats,
        'regiones': regiones,
        'comunas': comunas,
        'planes': planes,
        'filtros': {
            'nombre': nombre_filtro,
            'estado': estado_filtro,
            'region': region_filtro,
            'comuna': comuna_filtro,
        },
    }
    
    return render(request, 'administrador_general/termas_asociadas.html', context)


@admin_general_required
@require_http_methods(["POST"])
def admin_general_crear_terma(request):
    """Vista para crear una nueva terma"""
    from termas.models import Terma, Comuna, PlanSuscripcion
    from django.utils import timezone
    import json
    
    try:
        # Obtener datos del formulario
        nombre_terma = request.POST.get('nombre_terma')
        rut_empresa = request.POST.get('rut_empresa', '')
        descripcion_terma = request.POST.get('descripcion_terma', '')
        email_terma = request.POST.get('email_terma')
        telefono_terma = request.POST.get('telefono_terma', '')
        comuna_id = request.POST.get('comuna')
        direccion_terma = request.POST.get('direccion_terma', '')
        plan_actual_id = request.POST.get('plan_actual')
        estado_suscripcion = request.POST.get('estado_suscripcion', 'inactiva')
        
        # Validaciones básicas
        if not nombre_terma or not email_terma or not comuna_id:
            return JsonResponse({
                'success': False,
                'message': 'Faltan campos obligatorios (nombre, email, comuna).'
            }, status=400)
        
        # Verificar que la comuna existe
        try:
            comuna = Comuna.objects.get(id=comuna_id)
        except Comuna.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Comuna seleccionada no válida.'
            }, status=400)
        
        # Verificar que el plan existe (si se seleccionó)
        plan_actual = None
        if plan_actual_id:
            try:
                plan_actual = PlanSuscripcion.objects.get(id=plan_actual_id)
            except PlanSuscripcion.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': 'Plan seleccionado no válido.'
                }, status=400)
        
        # Crear la terma
        print(f"[DEBUG] Creando nueva terma: {nombre_terma}")
        print(f"[DEBUG] RUT para nueva terma: '{rut_empresa}' (tipo: {type(rut_empresa)})")
        
        terma = Terma.objects.create(
            nombre_terma=nombre_terma,
            descripcion_terma=descripcion_terma,
            direccion_terma=direccion_terma,
            comuna=comuna,
            telefono_terma=telefono_terma,
            email_terma=email_terma,
            rut_empresa=rut_empresa,
            estado_suscripcion=estado_suscripcion,
            fecha_suscripcion=timezone.now().date(),
            plan_actual=plan_actual
        )
        
        print(f"[DEBUG] Terma creada con RUT: '{terma.rut_empresa}'")
        
        # Actualizar configuración según plan si se asignó uno
        if plan_actual:
            terma.actualizar_configuracion_segun_plan()
        
        return JsonResponse({
            'success': True,
            'message': f'Terma "{nombre_terma}" creada exitosamente.'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error al crear la terma: {str(e)}'
        }, status=500)


@admin_general_required
@require_http_methods(["GET"])
def admin_general_terma_detalle(request, terma_uuid):
    """Vista para obtener los detalles de una terma"""
    from termas.models import Terma
    from django.template.loader import render_to_string
    
    try:
        terma = get_object_or_404(Terma, uuid=terma_uuid)
        
        # Calcular estadísticas básicas
        estadisticas = {
            'total_visitantes': terma.total_visitantes(),
            'ingresos_historicos': terma.ingresos_historicos(),
            'ingresos_mes': terma.ingresos_totales(),
            'calificacion_promedio': terma.promedio_calificacion(),
            'total_calificaciones': terma.total_calificaciones(),
            'total_fotos': terma.total_fotos(),
        }
        
        html_content = render_to_string('administrador_general/partials/detalle_terma.html', {
            'terma': terma,
            'estadisticas': estadisticas
        })
        
        return JsonResponse({
            'success': True,
            'html': html_content
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error al obtener el detalle: {str(e)}'
        }, status=500)


@admin_general_required
@require_http_methods(["GET"])
def admin_general_terma_editar(request, terma_uuid):
    """Vista para obtener el formulario de edición de una terma"""
    from termas.models import Terma, Region, Comuna, PlanSuscripcion
    from django.template.loader import render_to_string
    
    try:
        terma = get_object_or_404(Terma, uuid=terma_uuid)
        
        # Obtener datos para el formulario
        regiones = Region.objects.all().order_by('nombre')
        comunas = Comuna.objects.all().order_by('nombre')
        planes = PlanSuscripcion.objects.all()
        
        html_content = render_to_string('administrador_general/partials/editar_terma_form.html', {
            'terma': terma,
            'regiones': regiones,
            'comunas': comunas,
            'planes': planes,
        })
        
        return JsonResponse({
            'success': True,
            'html': html_content
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error al cargar los datos para edición: {str(e)}'
        }, status=500)


@admin_general_required
@require_http_methods(["POST"])
def admin_general_terma_actualizar(request, terma_uuid):
    """Vista para actualizar una terma"""
    from termas.models import Terma, Comuna, PlanSuscripcion
    
    try:
        terma = get_object_or_404(Terma, uuid=terma_uuid)
        
        # Obtener datos del formulario
        nombre_terma = request.POST.get('nombre_terma')
        rut_empresa = request.POST.get('rut_empresa', '')
        descripcion_terma = request.POST.get('descripcion_terma', '')
        email_terma = request.POST.get('email_terma')
        telefono_terma = request.POST.get('telefono_terma', '')
        comuna_id = request.POST.get('comuna')
        direccion_terma = request.POST.get('direccion_terma', '')
        plan_actual_id = request.POST.get('plan_actual')
        estado_suscripcion = request.POST.get('estado_suscripcion', 'inactiva')
        email_administrador = request.POST.get('email_administrador', '').strip()
        
        # Debug logging
        print(f"[DEBUG] Actualizando terma {terma_uuid}")
        print(f"[DEBUG] RUT recibido del formulario: '{rut_empresa}' (tipo: {type(rut_empresa)})")
        print(f"[DEBUG] RUT actual en DB: '{terma.rut_empresa}' (tipo: {type(terma.rut_empresa)})")
        print(f"[DEBUG] Datos POST completos: {dict(request.POST)}")
        
        # Validaciones básicas
        if not nombre_terma or not email_terma or not comuna_id:
            return JsonResponse({
                'success': False,
                'message': 'Faltan campos obligatorios (nombre, email, comuna).'
            }, status=400)
        
        # Verificar que la comuna existe
        try:
            comuna = Comuna.objects.get(id=comuna_id)
        except Comuna.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Comuna seleccionada no válida.'
            }, status=400)
        
        # Verificar que el plan existe (si se seleccionó)
        plan_actual = None
        if plan_actual_id:
            try:
                plan_actual = PlanSuscripcion.objects.get(id=plan_actual_id)
            except PlanSuscripcion.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': 'Plan seleccionado no válido.'
                }, status=400)
        
        # Manejar asignación del administrador por email
        nuevo_administrador = None
        if email_administrador:
            try:
                from usuarios.models import Usuario, Rol
                
                # Buscar el usuario por email
                try:
                    nuevo_administrador = Usuario.objects.get(email=email_administrador)
                except Usuario.DoesNotExist:
                    return JsonResponse({
                        'success': False,
                        'message': f'No se encontró un usuario registrado con el email: {email_administrador}'
                    }, status=400)
                
                # Verificar que el usuario tenga el rol adecuado o se le pueda asignar
                rol_admin_terma = Rol.objects.get(nombre='administrador_terma')
                
                if nuevo_administrador.rol.nombre not in ['administrador_terma', 'administrador_general']:
                    # Si no es administrador, intentar cambiar su rol
                    if nuevo_administrador.rol.nombre == 'cliente':
                        # Cambiar de cliente a administrador de terma
                        nuevo_administrador.rol = rol_admin_terma
                    else:
                        return JsonResponse({
                            'success': False,
                            'message': f'El usuario {email_administrador} no puede ser asignado como administrador de terma. Rol actual: {nuevo_administrador.rol.nombre}'
                        }, status=400)
                
                # Verificar que no esté administrando otra terma (excepto la actual)
                if nuevo_administrador.terma and nuevo_administrador.terma != terma:
                    otra_terma = nuevo_administrador.terma
                    return JsonResponse({
                        'success': False,
                        'message': f'El usuario {email_administrador} ya es administrador de la terma "{otra_terma.nombre_terma}"'
                    }, status=400)
                
            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'message': f'Error al procesar el administrador: {str(e)}'
                }, status=500)
        
        # Actualizar la terma
        terma.nombre_terma = nombre_terma
        terma.descripcion_terma = descripcion_terma
        terma.direccion_terma = direccion_terma
        terma.comuna = comuna
        terma.telefono_terma = telefono_terma
        terma.email_terma = email_terma
        
        # Actualizar RUT solo si está vacío actualmente (no se puede cambiar una vez establecido)
        # Verificar si el RUT actual está vacío, es None, o es la cadena 'None'
        rut_actual_vacio = (
            not terma.rut_empresa or 
            terma.rut_empresa == '' or 
            terma.rut_empresa == 'None' or
            terma.rut_empresa is None or
            str(terma.rut_empresa).strip() == ''
        )
        
        if rut_actual_vacio and rut_empresa and rut_empresa.strip():
            terma.rut_empresa = rut_empresa.strip()
            print(f"[DEBUG] RUT actualizado para terma {terma.nombre_terma}: '{rut_empresa.strip()}'")
        else:
            print(f"[DEBUG] RUT NO actualizado para {terma.nombre_terma}. RUT actual: '{terma.rut_empresa}', RUT nuevo: '{rut_empresa}'")
        
        terma.estado_suscripcion = estado_suscripcion
        terma.plan_actual = plan_actual
        
        # Manejar cambios en el administrador
        mensaje_admin = ""
        if nuevo_administrador:
            # Remover administrador anterior de la terma (pero no desactivar usuario)
            admin_anterior = terma.administrador
            if admin_anterior and admin_anterior != nuevo_administrador:
                # Solo remover la asignación de terma, NO cambiar estado ni rol
                admin_anterior.terma = None
                admin_anterior.save()
                mensaje_admin += f" Administrador anterior ({admin_anterior.email}) desvinculado."
            
            # Asignar nuevo administrador
            nuevo_administrador.terma = terma
            nuevo_administrador.save()
            
            terma.administrador = nuevo_administrador
            mensaje_admin += f" Nuevo administrador asignado: {nuevo_administrador.email}."
        
        terma.save()
        
        # Actualizar configuración según plan si se cambió
        if plan_actual:
            terma.actualizar_configuracion_segun_plan()
        
        mensaje_final = f'Terma "{nombre_terma}" actualizada exitosamente.{mensaje_admin}'
        
        return JsonResponse({
            'success': True,
            'message': mensaje_final
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error al actualizar la terma: {str(e)}'
        }, status=500)


@admin_general_required
@require_http_methods(["POST"])
def admin_general_terma_cambiar_estado(request, terma_uuid):
    """Vista para cambiar el estado de una terma (activar/desactivar)"""
    from termas.models import Terma
    import json
    
    try:
        terma = get_object_or_404(Terma, uuid=terma_uuid)
        
        data = json.loads(request.body)
        nuevo_estado = data.get('estado')
        
        if nuevo_estado not in ['activa', 'inactiva']:
            return JsonResponse({
                'success': False,
                'message': 'Estado no válido.'
            }, status=400)
        
        # Guardar estado anterior para log
        estado_anterior = terma.estado_suscripcion
        
        # Cambiar estado de la terma
        terma.estado_suscripcion = nuevo_estado
        terma.save()
        
        # IMPORTANTE: NO cambiar el estado del administrador ni desvincularlo
        # El administrador mantiene su vinculación y estado independientemente del estado de la terma
        
        mensaje = f'Terma "{terma.nombre_terma}" {"activada" if nuevo_estado == "activa" else "desactivada"} exitosamente.'
        
        # Log del cambio (opcional)
        if terma.administrador:
            mensaje += f' La vinculación con el administrador {terma.administrador.email} se mantiene activa.'
        
        return JsonResponse({
            'success': True,
            'message': mensaje
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error al cambiar el estado: {str(e)}'
        }, status=500)


@admin_general_required
@require_http_methods(["GET"])
def admin_general_terma_estadisticas(request, terma_uuid):
    """Vista para obtener estadísticas detalladas de una terma"""
    from termas.models import Terma
    from ventas.models import Compra, DetalleCompra
    from django.template.loader import render_to_string
    from django.db.models import Sum, Count, Avg
    from datetime import datetime, timedelta
    
    try:
        terma = get_object_or_404(Terma, uuid=terma_uuid)
        
        # Calcular estadísticas detalladas
        hoy = datetime.now().date()
        hace_30_dias = hoy - timedelta(days=30)
        primer_dia_mes = hoy.replace(day=1)
        
        # Estadísticas generales
        try:
            estadisticas_generales = {
                'total_visitantes': terma.total_visitantes() or 0,
                'ingresos_historicos': terma.ingresos_historicos() or 0,
                'ingresos_mes_actual': terma.ingresos_totales() or 0,
                'calificacion_promedio': terma.promedio_calificacion(),
                'total_calificaciones': terma.total_calificaciones() or 0,
                'total_fotos': terma.total_fotos() or 0,
            }
        except Exception as e:
            logger.error(f"Error en estadísticas generales: {e}")
            estadisticas_generales = {
                'total_visitantes': 0,
                'ingresos_historicos': 0,
                'ingresos_mes_actual': 0,
                'calificacion_promedio': None,
                'total_calificaciones': 0,
                'total_fotos': 0,
            }
        
        # Estadísticas de ventas del último mes
        try:
            ventas_mes = Compra.objects.filter(
                terma=terma,
                estado_pago='pagado',
                fecha_compra__date__gte=primer_dia_mes,
                fecha_compra__date__lte=hoy
            ).aggregate(
                total_ventas=Count('id'),
                ingresos_totales=Sum('total'),
                visitantes_totales=Sum('detalles__cantidad')
            )
            
            # Asegurar valores no nulos
            ventas_mes = {
                'total_ventas': ventas_mes['total_ventas'] or 0,
                'ingresos_totales': ventas_mes['ingresos_totales'] or 0,
                'visitantes_totales': ventas_mes['visitantes_totales'] or 0,
            }
        except Exception as e:
            logger.error(f"Error en ventas del mes: {e}")
            ventas_mes = {
                'total_ventas': 0,
                'ingresos_totales': 0,
                'visitantes_totales': 0,
            }
        
        # Estadísticas de los últimos 30 días
        try:
            ventas_30_dias = Compra.objects.filter(
                terma=terma,
                estado_pago='pagado',
                fecha_compra__date__gte=hace_30_dias,
                fecha_compra__date__lte=hoy
            ).aggregate(
                total_ventas=Count('id'),
                ingresos_totales=Sum('total'),
                visitantes_totales=Sum('detalles__cantidad')
            )
            
            # Asegurar valores no nulos
            ventas_30_dias = {
                'total_ventas': ventas_30_dias['total_ventas'] or 0,
                'ingresos_totales': ventas_30_dias['ingresos_totales'] or 0,
                'visitantes_totales': ventas_30_dias['visitantes_totales'] or 0,
            }
        except Exception as e:
            logger.error(f"Error en ventas de 30 días: {e}")
            ventas_30_dias = {
                'total_ventas': 0,
                'ingresos_totales': 0,
                'visitantes_totales': 0,
            }
        
        # Ocupación promedio por día (últimos 30 días)
        ocupacion_diaria = []
        for i in range(30):
            fecha = hoy - timedelta(days=i)
            try:
                ventas_dia = DetalleCompra.objects.filter(
                    entrada_tipo__terma=terma,
                    compra__estado_pago='pagado',
                    compra__fecha_visita=fecha
                ).aggregate(
                    total_visitantes=Sum('cantidad')
                )['total_visitantes'] or 0
            except Exception as e:
                logger.error(f"Error calculando ocupación para fecha {fecha}: {e}")
                ventas_dia = 0
            
            ocupacion_diaria.append({
                'fecha': fecha.strftime('%d/%m'),
                'visitantes': ventas_dia
            })
        
        ocupacion_diaria.reverse()  # Mostrar del más antiguo al más reciente
        
        html_content = render_to_string('administrador_general/partials/estadisticas_terma.html', {
            'terma': terma,
            'estadisticas_generales': estadisticas_generales,
            'ventas_mes': ventas_mes,
            'ventas_30_dias': ventas_30_dias,
            'ocupacion_diaria': ocupacion_diaria,
        })
        
        return JsonResponse({
            'success': True,
            'html': html_content
        })
        
    except Exception as e:
        logger.error(f"Error general en estadísticas: {e}")
        return JsonResponse({
            'success': False,
            'message': f'Error al cargar las estadísticas: {str(e)}'
        }, status=500)


@require_http_methods(["GET"])
def api_comunas_por_region(request, region_id):
    """API para obtener comunas de una región"""
    from termas.models import Comuna
    try:
        comunas = Comuna.objects.filter(region_id=region_id).values('id', 'nombre').order_by('nombre')
        return JsonResponse(list(comunas), safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_protect
@login_required
def cambiar_password_temporal(request):
    """
    Vista para cambiar la contraseña temporal de un usuario autenticado.
    """
    if request.method == 'POST':
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        # Validaciones básicas
        if not all([current_password, new_password, confirm_password]):
            messages.error(request, 'Todos los campos son obligatorios.')
            return redirect(request.META.get('HTTP_REFERER', '/'))
        
        if new_password != confirm_password:
            messages.error(request, 'Las contraseñas nuevas no coinciden.')
            return redirect(request.META.get('HTTP_REFERER', '/'))
        
        if len(new_password) < 8:
            messages.error(request, 'La nueva contraseña debe tener al menos 8 caracteres.')
            return redirect(request.META.get('HTTP_REFERER', '/'))
        
        # Verificar contraseña actual
        if not request.user.check_password(current_password):
            messages.error(request, 'La contraseña actual es incorrecta.')
            return redirect(request.META.get('HTTP_REFERER', '/'))
        
        # Verificar que el usuario tenga contraseña temporal
        if not request.user.tiene_password_temporal:
            messages.error(request, 'Tu cuenta no tiene una contraseña temporal.')
            return redirect(request.META.get('HTTP_REFERER', '/'))
        
        try:
            # Cambiar la contraseña y marcar como no temporal
            request.user.cambiar_password_temporal(new_password)
            messages.success(request, '¡Contraseña cambiada exitosamente! Tu cuenta ahora está completamente configurada.')
            logger.info(f"Contraseña temporal cambiada para usuario: {request.user.email}")
            
            # Obtener URL de redirección del formulario o calcular por rol
            next_url = request.POST.get('next')
            if next_url:
                return redirect(next_url)
            else:
                # Redirigir según el rol del usuario
                return _redirect_by_role(request.user, request)
            
        except Exception as e:
            logger.error(f"Error al cambiar contraseña temporal para {request.user.email}: {str(e)}")
            messages.error(request, 'Error interno del servidor. Por favor intenta nuevamente.')
            return redirect(request.META.get('HTTP_REFERER', '/'))
    
    # Si no es POST, redirigir
    return redirect('core:home')

@admin_terma_required
def historial_entradas(request):
    """
    Vista para mostrar el historial de entradas vendidas por el administrador de termas
    """
    # Verificar autenticación usando función helper
    if not is_user_authenticated(request):
        messages.error(request, 'Debes iniciar sesión para acceder.')
        return redirect('core:home')
    
    try:
        # Obtener usuario usando función helper
        usuario = get_current_user(request)
        
        if not usuario:
            messages.error(request, 'Usuario no encontrado.')
            return redirect('core:home')
        
        # Verificar que el usuario tenga una terma asociada
        if not usuario.terma:
            messages.error(request, 'No tienes una terma asociada para acceder al historial de entradas.')
            return redirect('usuarios:adm_termas')
        
        terma = usuario.terma
        
        # Importar modelos necesarios
        from ventas.models import Compra, DetalleCompra, RegistroEscaneo, CodigoQR
        from entradas.models import EntradaTipo
        from django.db.models import Count, Sum, Q
        from datetime import date, timedelta
        from collections import defaultdict
        
        # Obtener parámetros de filtro
        fecha_filtro = request.GET.get('fecha')
        if fecha_filtro:
            fecha_filtro = date.fromisoformat(fecha_filtro)
        else:
            fecha_filtro = date.today()
        
        # Obtener entradas vendidas para la fecha específica
        entradas_vendidas = DetalleCompra.objects.filter(
            compra__terma=terma,
            compra__fecha_visita=fecha_filtro,
            compra__estado_pago='pagado'
        ).select_related(
            'compra__usuario', 'entrada_tipo', 'compra'
        ).prefetch_related(
            'servicios',
            'servicios_extra__servicio', 
            'entrada_tipo__servicios'
        )

        # Calcular total de visitantes y total de cantidades escaneadas
        total_visitantes = 0
        total_cantidades_escaneadas = 0
        for detalle in entradas_vendidas:
            compra = detalle.compra
            codigo_qr = CodigoQR.objects.filter(compra=compra).first()
            if codigo_qr:
                escaneo = RegistroEscaneo.objects.filter(
                    codigo_qr=codigo_qr,
                    fecha_escaneo__date=fecha_filtro,
                    exitoso=True,
                    usuario_scanner__terma=terma
                ).exists()
                if escaneo:
                    total_visitantes += detalle.cantidad
                    total_cantidades_escaneadas += detalle.cantidad

        # Entradas sin escanear: pagadas, pero sin registro de escaneo exitoso
        from ventas.models import RegistroEscaneo, CodigoQR
        entradas_sin_escanear = 0
        for detalle in entradas_vendidas:
            compra = detalle.compra
            codigo_qr = CodigoQR.objects.filter(compra=compra).first()
            if codigo_qr:
                escaneo = RegistroEscaneo.objects.filter(
                    codigo_qr=codigo_qr,
                    exitoso=True,
                    usuario_scanner__terma=terma
                ).exists()
                if not escaneo:
                    entradas_sin_escanear += detalle.cantidad
        

        # Calcular resumen por tipo de entrada mostrando:
        # - total sin descuento (solo entradas base)
        # - total pagado (con extras y descuentos)
        # - total neto para la terma (descontando comisión)
        from ventas.models import DistribucionPago
        resumen_dict = {}
        for detalle in entradas_vendidas:
            tipo_nombre = detalle.entrada_tipo.nombre
            duracion = detalle.entrada_tipo.duracion_tipo
            compra_id = detalle.compra.id
            if (tipo_nombre, duracion) not in resumen_dict:
                resumen_dict[(tipo_nombre, duracion)] = {
                    'entrada_tipo__nombre': tipo_nombre,
                    'entrada_tipo__duracion_tipo': duracion,
                    'total_vendidas': 0,
                    'compras_ids': set(),
                    'total_sin_descuento': 0,
                    'total_pagado': 0,
                    'total_neto_terma': 0,
                }
            resumen_dict[(tipo_nombre, duracion)]['total_vendidas'] += detalle.cantidad
            resumen_dict[(tipo_nombre, duracion)]['compras_ids'].add(compra_id)
            resumen_dict[(tipo_nombre, duracion)]['total_sin_descuento'] += float(detalle.subtotal)

        for key, data in resumen_dict.items():
            compras = Compra.objects.filter(id__in=data['compras_ids'])
            total_pagado = sum([float(c.total) for c in compras])
            data['total_pagado'] = total_pagado
            # Sumar el neto para la terma (descontando comisión)
            distribuciones = DistribucionPago.objects.filter(compra_id__in=data['compras_ids'])
            total_neto = sum([float(d.monto_para_terma) for d in distribuciones])
            data['total_neto_terma'] = total_neto
            del data['compras_ids']

        resumen_entradas = list(resumen_dict.values())
        
        # Obtener códigos QR escaneados para esta fecha solo por trabajadores de la misma terma
        escaneos_hoy = RegistroEscaneo.objects.filter(
            codigo_qr__compra__terma=terma,
            fecha_escaneo__date=fecha_filtro,
            exitoso=True,
            usuario_scanner__terma=terma  # Solo escaneos de trabajadores de esta terma
        ).select_related(
            'codigo_qr__compra__usuario', 
            'usuario_scanner',
            'codigo_qr__compra'
        ).order_by('-fecha_escaneo')
        
        # Agrupar escaneos por empleado
        escaneos_por_empleado = defaultdict(list)
        for escaneo in escaneos_hoy:
            empleado = escaneo.usuario_scanner
            if empleado:
                escaneos_por_empleado[empleado].append(escaneo)
        
        # Obtener estadísticas del día
        total_entradas_vendidas = sum(item['total_vendidas'] for item in resumen_entradas)
        # Entradas escaneadas: cantidad de escaneos únicos (no suma de visitantes)
        total_entradas_escaneadas = escaneos_hoy.count()
        
        # Obtener historial de escaneos de la última semana solo de trabajadores de esta terma
        fecha_inicio_semana = fecha_filtro - timedelta(days=7)
        historial_semana = RegistroEscaneo.objects.filter(
            codigo_qr__compra__terma=terma,
            fecha_escaneo__date__gte=fecha_inicio_semana,
            fecha_escaneo__date__lte=fecha_filtro,
            exitoso=True,
            usuario_scanner__terma=terma  # Solo escaneos de trabajadores de esta terma
        ).values('fecha_escaneo__date').annotate(
            total_escaneos=Count('id')
        ).order_by('fecha_escaneo__date')
        
        # Obtener información detallada de cada entrada vendida
        entradas_detalle = []
        for detalle in entradas_vendidas:
            compra = detalle.compra
            codigo_qr = CodigoQR.objects.filter(compra=compra).first()
            escaneo = None
            
            if codigo_qr:
                escaneo = RegistroEscaneo.objects.filter(
                    codigo_qr=codigo_qr,
                    fecha_escaneo__date=fecha_filtro,
                    exitoso=True,
                    usuario_scanner__terma=terma  # Solo escaneos de trabajadores de esta terma
                ).first()
            
            # Obtener servicios incluidos
            servicios_incluidos = list(detalle.entrada_tipo.servicios.all().values_list('servicio', flat=True))
            servicios_incluidos_str = ', '.join(servicios_incluidos) if servicios_incluidos else 'Sin servicios incluidos'
            
            # Obtener servicios extras
            servicios_extras = []
            
            # Servicios extras del modelo intermedio
            for extra in detalle.servicios_extra.all():
                servicios_extras.append(f"{extra.servicio.servicio} (x{extra.cantidad})")
            
            # Servicios extras directos
            for servicio in detalle.servicios.all():
                servicios_extras.append(servicio.servicio)
            
            servicios_extras_str = ', '.join(servicios_extras) if servicios_extras else 'Sin servicios extras'
            
            entradas_detalle.append({
                'detalle': detalle,
                'compra': compra,
                'codigo_qr': codigo_qr,
                'escaneo': escaneo,
                'estado_escaneo': 'Escaneada' if escaneo else 'Pendiente',
                'servicios_incluidos': servicios_incluidos_str,
                'servicios_extras': servicios_extras_str
            })
        
        # Datos para gráficos
        datos_grafico = {
            'labels': [item['entrada_tipo__nombre'] for item in resumen_entradas],
            'vendidas': [item['total_vendidas'] for item in resumen_entradas],
            'precios': [float(item['total_pagado']) for item in resumen_entradas]
        }
        
        context = {
            'title': f'Historial de Entradas - {fecha_filtro.strftime("%d/%m/%Y")}',
            'usuario': usuario,
            'terma': terma,
            'fecha_filtro': fecha_filtro,
            'fecha_filtro_str': fecha_filtro.strftime('%Y-%m-%d'),
            'resumen_entradas': resumen_entradas,
            'entradas_detalle': entradas_detalle,
            'escaneos_hoy': escaneos_hoy,
            'escaneos_por_empleado': dict(escaneos_por_empleado),
            'total_entradas_vendidas': total_entradas_vendidas,  # Para compatibilidad
            'total_visitantes': total_visitantes,
            'total_entradas_escaneadas': total_entradas_escaneadas,
            'entradas_sin_escanear': entradas_sin_escanear,
            # Porcentaje de uso: entradas escaneadas / entradas vendidas (sin considerar visitantes)
            # Porcentaje de uso: sumatoria de cantidades escaneadas / sumatoria de cantidades vendidas
            'porcentaje_escaneadas': round((total_cantidades_escaneadas / total_entradas_vendidas * 100) if total_entradas_vendidas > 0 else 0, 1),
            'historial_semana': historial_semana,
            'datos_grafico': datos_grafico,
        }
        
        return render(request, 'administrador_termas/historial_entradas.html', context)
        
    except Exception as e:
        messages.error(request, f'Error al cargar el historial de entradas: {str(e)}')
        return redirect('usuarios:adm_termas')


# =============================================
# VISTAS PARA CONFIGURACIÓN DE ADMINISTRADOR GENERAL
# =============================================

@admin_general_required
def configuracion_admin(request):
    """
    Vista para mostrar la página de configuración del administrador general.
    Permite ver y editar información personal y cambiar contraseña.
    """
    try:
        usuario = request.user
        
        context = {
            'title': 'Configuración de Cuenta - MiTerma Admin',
            'usuario': usuario,
            'user': usuario,  # Para compatibilidad con template
        }
        
        return render(request, 'administrador_general/configuracion.html', context)
        
    except Exception as e:
        logger.error(f"Error en configuracion_admin: {str(e)}")
        messages.error(request, 'Ocurrió un error al cargar la configuración.')
        return redirect('usuarios:admin_general')


@admin_general_required
@require_http_methods(["POST"])
def actualizar_perfil_admin(request):
    """
    Vista para actualizar la información personal del administrador general.
    """
    try:
        usuario = request.user
        
        # Verificar que es el formulario correcto
        form_type = request.POST.get('form_type')
        if form_type != 'perfil':
            messages.error(request, 'Tipo de formulario inválido.')
            return redirect('usuarios:configuracion_admin')
        
        # Obtener datos del formulario
        nombre = request.POST.get('nombre', '').strip()
        apellido = request.POST.get('apellido', '').strip()
        telefono = request.POST.get('telefono', '').strip()
        
        # Validaciones
        if not nombre or not apellido:
            messages.error(request, 'El nombre y apellido son obligatorios.')
            return redirect('usuarios:configuracion_admin')
        
        # Validar teléfono si se proporciona
        if telefono and not re.match(r'^[\+]?[0-9\s\-]{8,15}$', telefono):
            messages.error(request, 'El número de teléfono debe contener solo números, espacios, guiones y el símbolo +.')
            return redirect('usuarios:configuracion_admin')
        
        # Actualizar datos del usuario
        usuario.nombre = nombre
        usuario.apellido = apellido
        usuario.telefono = telefono if telefono else None
        usuario.save()
        
        logger.info(f"Perfil actualizado para admin general: {usuario.email}")
        messages.success(request, 'Tu información personal ha sido actualizada correctamente.')
        
        return redirect('usuarios:configuracion_admin')
        
    except Exception as e:
        logger.error(f"Error actualizando perfil admin: {str(e)}")
        messages.error(request, 'Ocurrió un error al actualizar tu información.')
        return redirect('usuarios:configuracion_admin')


@admin_general_required
@require_http_methods(["POST"])
def cambiar_contrasena_admin(request):
    """
    Vista para cambiar la contraseña del administrador general.
    """
    try:
        usuario = request.user
        
        # Verificar que es el formulario correcto
        form_type = request.POST.get('form_type')
        if form_type != 'password':
            messages.error(request, 'Tipo de formulario inválido.')
            return redirect('usuarios:configuracion_admin')
        
        # Obtener datos del formulario
        current_password = request.POST.get('current_password', '')
        new_password = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')
        
        # Validaciones básicas
        if not current_password or not new_password or not confirm_password:
            messages.error(request, 'Todos los campos son obligatorios.')
            return redirect('usuarios:configuracion_admin')
        
        # Verificar contraseña actual
        if not usuario.check_password(current_password):
            logger.warning("Intento fallido de cambio de contraseña para admin - contraseña actual incorrecta")
            messages.error(request, 'La contraseña actual es incorrecta.')
            return redirect('usuarios:configuracion_admin')
        
        # Verificar que las nuevas contraseñas coincidan
        if new_password != confirm_password:
            messages.error(request, 'Las contraseñas nuevas no coinciden.')
            return redirect('usuarios:configuracion_admin')
        
        # Validar fortaleza de la contraseña
        if len(new_password) < 8:
            messages.error(request, 'La contraseña debe tener al menos 8 caracteres.')
            return redirect('usuarios:configuracion_admin')
        
        if not re.search(r'[A-Z]', new_password):
            messages.error(request, 'La contraseña debe contener al menos una letra mayúscula.')
            return redirect('usuarios:configuracion_admin')
        
        if not re.search(r'[a-z]', new_password):
            messages.error(request, 'La contraseña debe contener al menos una letra minúscula.')
            return redirect('usuarios:configuracion_admin')
        
        if not re.search(r'[0-9]', new_password):
            messages.error(request, 'La contraseña debe contener al menos un número.')
            return redirect('usuarios:configuracion_admin')
        
        if not re.search(r'[@$!%*?&]', new_password):
            messages.error(request, 'La contraseña debe contener al menos un carácter especial (@$!%*?&).')
            return redirect('usuarios:configuracion_admin')
        
        # Verificar que no sea la misma contraseña actual
        if usuario.check_password(new_password):
            messages.error(request, 'La nueva contraseña debe ser diferente a la actual.')
            return redirect('usuarios:configuracion_admin')
        
        # Cambiar la contraseña
        usuario.set_password(new_password)
        
        # Si tenía contraseña temporal, marcar como cambiada
        if usuario.tiene_password_temporal:
            usuario.tiene_password_temporal = False
        
        usuario.save()
        
        # Log del cambio exitoso
        logger.info(f"Contraseña cambiada exitosamente para admin general: {usuario.email}")
        
        # Actualizar la sesión para mantener al usuario logueado
        from django.contrib.auth import update_session_auth_hash
        update_session_auth_hash(request, usuario)
        
        messages.success(request, 'Tu contraseña ha sido cambiada correctamente.')
        
        return redirect('usuarios:configuracion_admin')
        
    except Exception as e:
        logger.error(f"Error cambiando contraseña admin: {str(e)}")
        messages.error(request, 'Ocurrió un error al cambiar la contraseña.')
        return redirect('usuarios:configuracion_admin')
