from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from datetime import datetime, timedelta
from ventas.models import Compra, CodigoQR
from termas.models import Terma
from .models import Usuario
from .decorators import cliente_required
import json

def trabajador_required(view_func):
    """
    Decorador que verifica que el usuario sea un trabajador (operador/trabajador).
    """
    def wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('usuarios:login')
        
        if not (hasattr(request.user, 'rol') and request.user.rol and 
                request.user.rol.nombre in ['operador', 'trabajador']):
            return redirect('usuarios:login')
        
        return view_func(request, *args, **kwargs)
    return wrapped_view

@trabajador_required
def inicio_trabajador(request):
    """Vista principal del dashboard del trabajador/operador."""
    usuario = request.user
    hoy = timezone.now().date()
    inicio_mes = hoy.replace(day=1)
    
    print(f"DEBUG TRABAJADOR - Usuario: {usuario.email} (ID: {usuario.id})")
    print(f"DEBUG TRABAJADOR - Rol: {usuario.rol.nombre if usuario.rol else 'Sin rol'}")
    
    # Obtener la terma asociada al trabajador
    terma = usuario.terma
    
    print(f"DEBUG TRABAJADOR - Usuario: {usuario.email} (ID: {usuario.id})")
    print(f"DEBUG TRABAJADOR - Rol: {usuario.rol.nombre if usuario.rol else 'Sin rol'}")
    print(f"DEBUG TRABAJADOR - Terma asignada: {terma.nombre_terma if terma else 'Sin terma asignada'}")
    
    # Si no tiene terma asignada, usar la primera terma activa como fallback
    if not terma:
        from termas.models import Terma
        terma = Terma.objects.filter(estado_suscripcion='activa').first()
        if terma:
            print(f"DEBUG TRABAJADOR - Usando fallback a terma activa: {terma.nombre_terma}")
        else:
            print("DEBUG TRABAJADOR - No hay termas activas disponibles")
    
    # Calcular estadísticas del día
    entradas_hoy = 0
    visitantes_actuales = 0
    total_mes = 0
    entradas_invalidas_hoy = 0
    ultimos_registros = []
    
    if terma:
        print(f"DEBUG TRABAJADOR - Calculando estadísticas para terma: {terma.nombre_terma}")
        
        # Entradas escaneadas hoy (códigos QR usados)
        qr_hoy = CodigoQR.objects.filter(
            compra__terma=terma,
            fecha_uso__date=hoy,
            usado=True
        )
        entradas_hoy = qr_hoy.count()
        print(f"DEBUG TRABAJADOR - QRs escaneados hoy: {entradas_hoy}")
        
        # Debug: mostrar algunos QRs de hoy
        for qr in qr_hoy[:3]:
            print(f"  - QR usado: {qr.compra.usuario.email} a las {qr.fecha_uso}")
        
        # Visitantes actuales (estimación basada en entradas del día)
        visitantes_actuales = entradas_hoy
        
        # Total escaneado del mes
        qr_mes = CodigoQR.objects.filter(
            compra__terma=terma,
            fecha_uso__gte=inicio_mes,
            usado=True
        )
        total_mes = qr_mes.count()
        print(f"DEBUG TRABAJADOR - QRs escaneados este mes: {total_mes}")
        
        # Entradas inválidas hoy (por ahora simulamos con 0)
        entradas_invalidas_hoy = 0
        
        # Últimos registros (últimos 10 códigos QR escaneados)
        ultimos_registros = CodigoQR.objects.filter(
            compra__terma=terma,
            usado=True,
            fecha_uso__isnull=False
        ).select_related(
            'compra', 
            'compra__usuario'
        ).order_by('-fecha_uso')[:10]
        
        print(f"DEBUG TRABAJADOR - Últimos registros encontrados: {ultimos_registros.count()}")
    else:
        print("DEBUG TRABAJADOR - Sin terma asignada, estadísticas en 0")
    
    context = {
        'title': f'Dashboard - {terma.nombre_terma if terma else "Trabajador"}',
        'usuario': usuario,
        'terma': terma,
        'estadisticas': {
            'entradas_hoy': entradas_hoy,
            'visitantes_actuales': visitantes_actuales,
            'total_mes': total_mes,
            'entradas_invalidas_hoy': entradas_invalidas_hoy,
        },
        'ultimos_registros': ultimos_registros,
    }
    
    print(f"DEBUG TRABAJADOR - Context preparado para template:")
    print(f"  - Title: {context['title']}")
    print(f"  - Terma en context: {context['terma'].nombre_terma if context['terma'] else 'None'}")
    print(f"  - Estadísticas: {context['estadisticas']}")
    
    return render(request, 'trabajador/inicio_trabajador.html', context)

@trabajador_required
@require_POST
def escanear_qr(request):
    """Vista para procesar el escaneado de códigos QR."""
    try:
        data = json.loads(request.body)
        qr_data = data.get('qr_data', '').strip()
        
        if not qr_data:
            return JsonResponse({
                'success': False,
                'error': 'Código QR vacío o inválido'
            })
        
        # Buscar el código QR
        try:
            codigo_qr = CodigoQR.objects.select_related(
                'compra', 
                'compra__usuario',
                'compra__terma'
            ).get(codigo=qr_data)
        except CodigoQR.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Código QR no encontrado'
            })
        
        # Verificar que el trabajador pertenezca a la misma terma que la entrada
        if not request.user.terma:
            return JsonResponse({
                'success': False,
                'error': 'No tienes una terma asignada para validar entradas'
            })
        
        if codigo_qr.compra.terma != request.user.terma:
            return JsonResponse({
                'success': False,
                'error': f'Esta entrada pertenece a {codigo_qr.compra.terma.nombre_terma}, no puedes validarla desde {request.user.terma.nombre_terma}',
                'terma_incorrecta': True
            })
        
        # Verificar si ya fue usado
        if codigo_qr.usado:
            return JsonResponse({
                'success': False,
                'error': f'Este código QR ya fue utilizado el {codigo_qr.fecha_uso.strftime("%d/%m/%Y %H:%M")}',
                'ya_usado': True
            })
        
        # Verificar si está vigente (ejemplo: válido por 30 días desde la compra)
        dias_vigencia = 30
        fecha_limite = codigo_qr.compra.fecha_compra + timedelta(days=dias_vigencia)
        if timezone.now().date() > fecha_limite.date():
            return JsonResponse({
                'success': False,
                'error': 'Este código QR ha expirado',
                'expirado': True
            })
        
        # Marcar como usado
        codigo_qr.usado = True
        codigo_qr.fecha_uso = timezone.now()
        codigo_qr.save()
        
        return JsonResponse({
            'success': True,
            'mensaje': 'Entrada validada correctamente',
            'cliente': {
                'nombre': f"{codigo_qr.compra.usuario.nombre} {codigo_qr.compra.usuario.apellido}",
                'email': codigo_qr.compra.usuario.email,
                'fecha_compra': codigo_qr.compra.fecha_compra.strftime("%d/%m/%Y"),
                'terma': codigo_qr.compra.terma.nombre_terma,
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Datos JSON inválidos'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error interno: {str(e)}'
        })

@trabajador_required
def buscar_entrada(request):
    """Vista para buscar entradas por email o código."""
    query = request.GET.get('q', '').strip()
    
    if not query:
        return JsonResponse({
            'success': False,
            'error': 'Parámetro de búsqueda requerido'
        })
    
    # Verificar que el trabajador tenga terma asignada
    if not request.user.terma:
        return JsonResponse({
            'success': False,
            'error': 'No tienes una terma asignada para buscar entradas'
        })
    
    # Buscar en múltiples campos solo en la terma del trabajador
    resultados = []
    
    # Buscar por email
    if '@' in query:
        compras = Compra.objects.filter(
            usuario__email__icontains=query,
            estado_pago='pagado',
            terma=request.user.terma
        ).select_related('usuario', 'terma', 'codigoqr')[:10]
    else:
        # Buscar por nombre o código QR
        compras = Compra.objects.filter(
            usuario__nombre__icontains=query,
            estado_pago='pagado',
            terma=request.user.terma
        ).select_related('usuario', 'terma', 'codigoqr')[:10]
    
    for compra in compras:
        if hasattr(compra, 'codigoqr'):
            codigo_qr = compra.codigoqr
            resultados.append({
                'id': compra.id,
                'cliente': f"{compra.usuario.nombre} {compra.usuario.apellido}",
                'email': compra.usuario.email,
                'terma': compra.terma.nombre_terma,
                'fecha_compra': compra.fecha_compra.strftime("%d/%m/%Y"),
                'usado': codigo_qr.usado,
                'fecha_uso': codigo_qr.fecha_uso.strftime("%d/%m/%Y %H:%M") if codigo_qr.fecha_uso else None,
            })
    
    return JsonResponse({
        'success': True,
        'resultados': resultados
    })


@trabajador_required
def registro_entradas_escaneadas(request):
    """Vista para mostrar el registro detallado de entradas escaneadas"""
    from datetime import datetime, timedelta
    
    # Obtener la terma del trabajador
    terma = None
    if hasattr(request.user, 'terma') and request.user.terma:
        terma = request.user.terma
    else:
        from termas.models import Terma
        terma = Terma.objects.filter(estado_suscripcion='activa').first()
    
    if not terma:
        messages.error(request, 'No se encontró una terma activa asignada')
        return redirect('usuarios:inicio_trabajador')
    
    # Obtener parámetros de filtrado
    fecha_desde = request.GET.get('fecha_desde')
    fecha_hasta = request.GET.get('fecha_hasta')
    
    # Configurar fechas por defecto (últimos 7 días)
    if not fecha_desde:
        fecha_desde = (timezone.now() - timedelta(days=7)).date()
    else:
        fecha_desde = datetime.strptime(fecha_desde, '%Y-%m-%d').date()
    
    if not fecha_hasta:
        fecha_hasta = timezone.now().date()
    else:
        fecha_hasta = datetime.strptime(fecha_hasta, '%Y-%m-%d').date()
    
    # Obtener registros de entradas escaneadas
    registros_qr = CodigoQR.objects.select_related(
        'compra', 
        'compra__usuario', 
        'compra__terma'
    ).prefetch_related(
        'compra__detalles',
        'compra__detalles__entrada_tipo'
    ).filter(
        compra__terma=terma,
        usado=True,
        fecha_uso__date__gte=fecha_desde,
        fecha_uso__date__lte=fecha_hasta
    ).order_by('-fecha_uso')
    
    # Procesar cada registro para agregar información de estado
    registros_procesados = []
    ahora = timezone.now()
    
    for registro in registros_qr:
        # Obtener información de la entrada
        detalle = registro.compra.detalles.first()
        duracion_horas = 0
        tipo_entrada_nombre = "Entrada General"
        
        if detalle and detalle.entrada_tipo:
            entrada_tipo = detalle.entrada_tipo
            duracion_horas = getattr(entrada_tipo, 'duracion_horas', 0) or 0
            tipo_entrada_nombre = entrada_tipo.nombre
        
        # Calcular el tiempo de finalización de la entrada
        tiempo_finalizacion = None
        entrada_activa = False
        tiempo_restante_str = None
        
        if duracion_horas > 0:
            tiempo_finalizacion = registro.fecha_uso + timedelta(hours=duracion_horas)
            entrada_activa = ahora < tiempo_finalizacion
            
            if entrada_activa:
                tiempo_restante = tiempo_finalizacion - ahora
                horas = tiempo_restante.seconds // 3600
                minutos = (tiempo_restante.seconds % 3600) // 60
                tiempo_restante_str = f"{horas}h {minutos}m"
        
        registros_procesados.append({
            'registro': registro,
            'cliente': registro.compra.usuario,
            'tipo_entrada': tipo_entrada_nombre,
            'duracion_horas': duracion_horas,
            'tiempo_finalizacion': tiempo_finalizacion,
            'entrada_activa': entrada_activa,
            'tiempo_restante_str': tiempo_restante_str,
            'fecha_compra': registro.compra.fecha_compra,
            'fecha_visita': registro.compra.fecha_visita,
        })
    
    # Calcular estadísticas del período
    total_entradas = len(registros_procesados)
    entradas_activas = sum(1 for r in registros_procesados if r['entrada_activa'])
    entradas_finalizadas = total_entradas - entradas_activas
    
    # Agrupar por días para estadísticas
    registros_por_dia = {}
    for registro in registros_procesados:
        fecha_str = registro['registro'].fecha_uso.strftime('%Y-%m-%d')
        if fecha_str not in registros_por_dia:
            registros_por_dia[fecha_str] = 0
        registros_por_dia[fecha_str] += 1
    
    context = {
        'title': 'Registro de Entradas Escaneadas',
        'usuario': request.user,
        'terma': terma,
        'registros': registros_procesados,
        'fecha_desde': fecha_desde,
        'fecha_hasta': fecha_hasta,
        'estadisticas': {
            'total_entradas': total_entradas,
            'entradas_activas': entradas_activas,
            'entradas_finalizadas': entradas_finalizadas,
            'registros_por_dia': registros_por_dia
        }
    }
    
    return render(request, 'trabajador/registro_entradas_escaneadas.html', context)


@trabajador_required
def perfil_trabajador(request):
    """Vista para mostrar el perfil del trabajador"""
    # Obtener datos frescos del usuario
    from django.contrib.auth import get_user_model
    User = get_user_model()
    try:
        usuario_fresco = User.objects.select_related('rol', 'terma').get(id=request.user.id)
    except User.DoesNotExist:
        usuario_fresco = request.user
    
    # Obtener la terma del trabajador
    terma = None
    if hasattr(usuario_fresco, 'terma') and usuario_fresco.terma:
        terma = usuario_fresco.terma
    else:
        from termas.models import Terma
        terma = Terma.objects.filter(estado_suscripcion='activa').first()
    
    context = {
        'title': 'Mi Perfil',
        'usuario': usuario_fresco,
        'terma': terma
    }
    
    return render(request, 'trabajador/perfil_trabajador.html', context)


@trabajador_required
def actualizar_perfil_trabajador(request):
    """Vista para actualizar el perfil del trabajador"""
    if request.method == 'POST':
        try:
            # Obtener datos del formulario
            nombre = request.POST.get('nombre', '').strip()
            apellido = request.POST.get('apellido', '').strip()
            telefono = request.POST.get('telefono', '').strip()
            
            # Validaciones básicas
            if not nombre or not apellido:
                messages.error(request, 'El nombre y apellido son obligatorios')
                return redirect('usuarios:perfil_trabajador')
            
            if len(nombre) < 2 or len(apellido) < 2:
                messages.error(request, 'El nombre y apellido deben tener al menos 2 caracteres')
                return redirect('usuarios:perfil_trabajador')
            
            # Validar teléfono si se proporciona
            if telefono:
                # Limpiar el teléfono de espacios y guiones
                telefono = telefono.replace(' ', '').replace('-', '').replace('+', '')
                if not telefono.isdigit() or len(telefono) < 8 or len(telefono) > 15:
                    messages.error(request, 'El número de teléfono no es válido')
                    return redirect('usuarios:perfil_trabajador')
            
            # Actualizar los datos del usuario
            request.user.nombre = nombre
            request.user.apellido = apellido
            request.user.telefono = telefono
            request.user.save()
            
            messages.success(request, 'Perfil actualizado correctamente')
            
        except Exception as e:
            messages.error(request, f'Error al actualizar el perfil: {str(e)}')
    
    return redirect('usuarios:perfil_trabajador')


@trabajador_required
def cambiar_contrasena_trabajador(request):
    """Vista para cambiar la contraseña del trabajador"""
    if request.method == 'POST':
        try:
            from django.contrib.auth import update_session_auth_hash
            from django.contrib.auth.hashers import check_password
            
            # Obtener datos del formulario
            contrasena_actual = request.POST.get('contrasena_actual', '').strip()
            nueva_contrasena = request.POST.get('nueva_contrasena', '').strip()
            confirmar_contrasena = request.POST.get('confirmar_contrasena', '').strip()
            
            # Validaciones
            if not contrasena_actual or not nueva_contrasena or not confirmar_contrasena:
                messages.error(request, 'Todos los campos son obligatorios')
                return redirect('usuarios:perfil_trabajador')
            
            # Verificar contraseña actual
            if not check_password(contrasena_actual, request.user.password):
                messages.error(request, 'La contraseña actual es incorrecta')
                return redirect('usuarios:perfil_trabajador')
            
            # Verificar que las contraseñas coinciden
            if nueva_contrasena != confirmar_contrasena:
                messages.error(request, 'Las contraseñas no coinciden')
                return redirect('usuarios:perfil_trabajador')
            
            # Validar longitud de contraseña
            if len(nueva_contrasena) < 6:
                messages.error(request, 'La contraseña debe tener al menos 6 caracteres')
                return redirect('usuarios:perfil_trabajador')
            
            # Cambiar la contraseña
            request.user.set_password(nueva_contrasena)
            request.user.save()
            
            # Actualizar la sesión para que no se cierre
            update_session_auth_hash(request, request.user)
            
            messages.success(request, 'Contraseña cambiada correctamente')
            
        except Exception as e:
            messages.error(request, f'Error al cambiar la contraseña: {str(e)}')
    
    return redirect('usuarios:perfil_trabajador')
