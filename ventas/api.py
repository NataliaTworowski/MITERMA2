from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate
from cryptography.fernet import Fernet
from django.utils import timezone
from django.conf import settings
from usuarios.models import Usuario
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from django.urls import resolve, Resolver404
import logging

logger = logging.getLogger(__name__)
import json
import base64
from .models import Compra, CodigoQR, RegistroEscaneo
from .utils import _get_encryption_key
from django.contrib.auth.hashers import check_password

@method_decorator(csrf_exempt, name='dispatch')
class ValidarEntradaQRView(View):
    def validate_auth(self, request):
        """Validar autenticación"""
        if 'HTTP_AUTHORIZATION' not in request.META:
            return None
        
        auth = request.META['HTTP_AUTHORIZATION'].split()
        if len(auth) != 2:
            return None

        auth_type = auth[0].lower()
        
        if auth_type == 'basic':
            try:
                auth_decoded = base64.b64decode(auth[1]).decode('utf-8')
                email, password = auth_decoded.split(':')
                try:
                    usuario = Usuario.objects.get(email=email)
                    if check_password(password, usuario.password):
                        return usuario
                except Usuario.DoesNotExist:
                    return None
            except Exception:
                return None
        elif auth_type == 'bearer':
            # Si en el futuro implementamos tokens JWT u otro tipo de token
            return None
            
        return None

    def post(self, request, *args, **kwargs):
        # Debug: Imprimir información detallada de la solicitud
        logger.info("-------- Nueva solicitud de validación QR --------")
        logger.info(f"URL completa: {request.build_absolute_uri()}")
        logger.info(f"Path: {request.path}")
        logger.info(f"Método: {request.method}")
        logger.info(f"Headers: {dict(request.headers)}")
        logger.info(f"GET params: {dict(request.GET)}")
        logger.info(f"POST data: {request.body.decode()}")
        
        try:
            resolved = resolve(request.path)
            logger.info(f"URL resolved to: {resolved.view_name} - {resolved.url_name}")
            logger.info(f"URL kwargs: {resolved.kwargs}")
            logger.info(f"URL args: {resolved.args}")
        except Resolver404:
            logger.error(f"No route matches {request.path}")
            return JsonResponse({
                'error': 'Ruta no encontrada',
                'detail': f'La ruta {request.path} no existe en el servidor. Las rutas disponibles son /ventas/api/validar-qr/'
            }, status=404)
        
        # Validar autenticación
        user = self.validate_auth(request)
        if not user:
            return JsonResponse({
                'error': 'Autenticación requerida',
                'detail': 'Debes proporcionar credenciales válidas'
            }, status=401)
        
        # Verificar si el usuario es trabajador
        if user.rol.nombre != 'trabajador':
            return JsonResponse({
                'error': 'Acceso denegado',
                'detail': 'Solo los trabajadores pueden validar entradas'
            }, status=403)
        
        request.user = user  # Establecer el usuario autenticado
        
        try:
            # Obtener el código QR encriptado
            print("Headers recibidos:", request.headers)  # Debug
            print("Body recibido:", request.body.decode())  # Debug
            
            data = json.loads(request.body)
            print("Data parseada:", data)  # Debug
            
            qr_data = data.get('qr_data')
            if not qr_data:
                return JsonResponse({
                    'error': 'QR data no proporcionada',
                    'detail': 'El campo qr_data es requerido en el body'
                }, status=400)

            # Desencriptar datos
            try:
                print("Intentando desencriptar QR...")  # Debug
                key = _get_encryption_key()
                print("Clave de encriptación obtenida:", key)  # Debug
                fernet = Fernet(key)
                print("Clave Fernet creada")  # Debug
                
                datos_encriptados = qr_data.encode('utf-8')
                print("Datos encriptados recibidos:", datos_encriptados)  # Debug
                
                try:
                    token = fernet.decrypt(datos_encriptados)
                    print("Datos desencriptados (token firmado):", token.decode())  # Debug
                except Exception as e:
                    print("Error al desencriptar con Fernet:", str(e))  # Debug
                    return JsonResponse({
                        'error': 'QR inválido',
                        'detail': 'Error al desencriptar datos'
                    }, status=400)
                
                try:
                    # Verificar firma del token
                    signer = TimestampSigner()
                    token_sin_firma = signer.unsign(token.decode())
                    datos = json.loads(token_sin_firma)
                    print("Datos después de verificar firma:", datos)  # Debug
                except (BadSignature, SignatureExpired) as e:
                    print("Error en la firma:", str(e))  # Debug
                    return JsonResponse({
                        'error': 'QR inválido',
                        'detail': 'El código QR ha expirado o es inválido'
                    }, status=400)
                except json.JSONDecodeError as e:
                    print("Error al parsear JSON:", str(e))  # Debug
                    return JsonResponse({
                        'error': 'Formato inválido',
                        'detail': 'Los datos desencriptados no son JSON válido'
                    }, status=400)
                
                # Obtener ID de compra
                try:
                    compra_id = datos['ticket_id'].split('-')[0]
                    logger.info(f"Buscando compra con ID: {compra_id}")
                    
                    # Verificar si el ID es válido
                    try:
                        compra_id = int(compra_id)
                    except ValueError:
                        logger.error(f"ID de compra inválido: {compra_id}")
                        return JsonResponse({
                            'valid': False,
                            'error': 'ID de compra inválido',
                            'detail': f'El ID {compra_id} no es válido'
                        }, status=400)

                    # Intentar obtener la compra
                    try:
                        compra = Compra.objects.get(id=compra_id)
                        logger.info(f"Compra encontrada: {compra.id} - Fecha: {compra.fecha_visita}")
                    except Compra.DoesNotExist:
                        logger.error(f"Compra no encontrada: {compra_id}")
                        return JsonResponse({
                            'valid': False,
                            'error': 'Entrada no encontrada',
                            'detail': 'La entrada no existe en el sistema'
                        }, status=404)

                    # Verificar si la entrada ya fue usada
                    try:
                        codigo_qr = CodigoQR.objects.get(compra=compra)
                        logger.info(f"Código QR encontrado - Usado: {codigo_qr.usado}")
                    except CodigoQR.DoesNotExist:
                        logger.error(f"Código QR no encontrado para compra: {compra_id}")
                        return JsonResponse({
                            'valid': False,
                            'error': 'Código QR no encontrado',
                            'detail': 'No se encontró el registro del código QR'
                        }, status=404)
                    
                except Exception as e:
                    logger.error(f"Error inesperado al procesar compra: {str(e)}")
                    return JsonResponse({
                        'valid': False,
                        'error': 'Error al procesar la entrada',
                        'detail': str(e)
                    }, status=400)
                # Verificar si ya fue usada
                if codigo_qr.usado:
                    logger.warning(f"Intento de usar entrada ya utilizada: {compra.id}")
                    return JsonResponse({
                        'valid': False,
                        'error': 'Esta entrada ya fue utilizada',
                        'fecha_uso': codigo_qr.fecha_uso.isoformat() if codigo_qr.fecha_uso else None,
                        'detail': 'La entrada ya fue escaneada previamente'
                    }, status=400)

                # Verificar el estado de la compra
                logger.info(f"Estado de pago de la compra: {compra.estado_pago}")
                if compra.estado_pago != 'pagado':
                    logger.warning(f"Intento de usar entrada no pagada: {compra.id}")
                    return JsonResponse({
                        'valid': False,
                        'error': 'Esta entrada no ha sido pagada',
                        'detail': f'Estado actual: {compra.estado_pago}'
                    }, status=400)

                # Verificar fecha de visita
                # Obtener fecha actual en la zona horaria de Chile
                fecha_actual = timezone.localtime(timezone.now()).date()
                fecha_visita = compra.fecha_visita
                logger.info(f"Verificando fecha - Actual (local): {fecha_actual}, Visita: {fecha_visita}")
                
                if fecha_actual > fecha_visita:
                    logger.warning(f"Intento de usar entrada vencida: {compra.id}")
                    return JsonResponse({
                        'valid': False,
                        'error': 'Fecha incorrecta',
                        'detail': f'Esta entrada venció el {fecha_visita}. No es válida hoy ({fecha_actual})'
                    }, status=400)
                elif fecha_actual < fecha_visita:
                    logger.warning(f"Intento de usar entrada antes de su fecha: {compra.id}")
                    return JsonResponse({
                        'valid': False,
                        'error': 'Fecha incorrecta',
                        'detail': f'Esta entrada es para el {fecha_visita}. No puede usarse antes de esa fecha.'
                    }, status=400)

                # Usar transacción para asegurar que todo se guarde o nada
                from django.db import transaction
                try:
                    with transaction.atomic():
                        # Marcar como usado y guardar fecha de uso
                        fecha_actual = timezone.localtime(timezone.now())
                        codigo_qr.usado = True
                        codigo_qr.fecha_uso = fecha_actual
                        codigo_qr.save()

                        # Registrar el escaneo exitoso
                        try:
                            registro = RegistroEscaneo.objects.create(
                                codigo_qr=codigo_qr,
                                usuario_scanner=request.user,
                                exitoso=True,
                                mensaje='Entrada validada correctamente',
                                ip_address=request.META.get('REMOTE_ADDR', ''),
                                dispositivo=request.META.get('HTTP_USER_AGENT', '')
                            )
                            logger.info(f"Registro de escaneo creado exitosamente: {registro.id}")
                        except Exception as e:
                            logger.error(f"Error al crear registro de escaneo: {str(e)}")

                        # Obtener los detalles de la compra y servicios de la terma
                        try:
                            logger.info(f"Buscando información para la compra {compra.id}")
                            
                            # Intentar obtener detalles específicos de la compra
                            detalles = compra.detalles.select_related(
                                'horario_disponible__entrada_tipo'
                            ).prefetch_related(
                                'servicios',
                                'horario_disponible__entrada_tipo__servicios'
                            ).first()
                            
                            if not detalles:
                                logger.error(f"No se encontraron detalles para la compra {compra.id}")
                                raise Exception("No se encontraron detalles de la compra")
                                
                            logger.info(f"Detalles encontrados para compra {compra.id}")
                            logger.info(f"Tipo de entrada: {detalles.horario_disponible.entrada_tipo.nombre}")
                            logger.info(f"Servicios incluidos: {[s.servicio for s in detalles.horario_disponible.entrada_tipo.servicios.all()]}")
                            logger.info(f"Servicios extra: {[s.servicio for s in detalles.servicios.all()]}")
                                
                            if detalles:
                                # Obtener servicios incluidos del tipo de entrada
                                servicios_incluidos = detalles.horario_disponible.entrada_tipo.servicios.all()
                                logger.info(f"[DEBUG] ID del detalle: {detalles.id}")
                                logger.info(f"[DEBUG] ID de la compra: {compra.id}")
                                logger.info(f"[DEBUG] ID del horario disponible: {detalles.horario_disponible.id}")
                                
                                servicios_incluidos_list = [
                                    {
                                        'nombre': servicio.servicio,
                                        'descripcion': servicio.descripcion
                                    }
                                    for servicio in servicios_incluidos
                                ] if servicios_incluidos.exists() else [
                                    {'nombre': '-', 'descripcion': 'No incluye servicios adicionales'}
                                ]
                                
                                # Obtener servicios extra contratados
                                servicios_extra = detalles.servicios.all().select_related()
                                servicios_extra_list = []
                                if servicios_extra.exists():
                                    for servicio in servicios_extra:
                                        servicio_data = {
                                            'nombre': servicio.servicio,
                                            'descripcion': servicio.descripcion,
                                            'precio': float(servicio.precio) if servicio.precio else None,
                                            'cantidad': 1
                                        }
                                        servicios_extra_list.append(servicio_data)
                                else:
                                    servicios_extra_list = [{
                                        'nombre': '-',
                                        'descripcion': 'No hay servicios extra contratados',
                                        'precio': None,
                                        'cantidad': 0
                                    }]
                                
                                # Preparar información de la entrada
                                entrada_tipo = detalles.horario_disponible.entrada_tipo
                                
                                # Generar texto de duración
                                duracion_texto = ""
                                if entrada_tipo.duracion_horas:
                                    if entrada_tipo.duracion_horas == 1:
                                        duracion_texto = "1 hora"
                                    else:
                                        duracion_texto = f"{entrada_tipo.duracion_horas} horas"
                                    
                                    if entrada_tipo.duracion_tipo:
                                        duracion_texto += f" ({entrada_tipo.duracion_tipo})"
                                else:
                                    duracion_texto = "Duración no especificada"
                                
                                entrada_info = {
                                    'tipo': entrada_tipo.nombre,
                                    'duracion': duracion_texto,
                                    'duracion_horas': entrada_tipo.duracion_horas,
                                    'duracion_tipo': entrada_tipo.duracion_tipo,
                                    'hora_inicio': detalles.horario_disponible.hora_inicio.strftime('%H:%M') if detalles.horario_disponible.hora_inicio else '00:00',
                                    'hora_fin': detalles.horario_disponible.hora_fin.strftime('%H:%M') if detalles.horario_disponible.hora_fin else '23:59',
                                    'cantidad_entradas': compra.cantidad,
                                    'servicios_incluidos': servicios_incluidos_list,
                                }
                                
                                # Obtener los servicios extra usando el nuevo modelo
                                servicios_extra_nuevos = detalles.servicios_extra.all().select_related('servicio')
                                logger.info(f"Recuperando servicios extra con cantidades para detalle {detalles.id}")
                                logger.info(f"Servicios extra con cantidades encontrados: {[(s.servicio.servicio, s.cantidad) for s in servicios_extra_nuevos]}")
                                
                                if servicios_extra_nuevos.exists():
                                    entrada_info['servicios_extra'] = [
                                        {
                                            'nombre': extra.servicio.servicio,
                                            'descripcion': extra.servicio.descripcion,
                                            'precio': float(extra.precio_unitario) if extra.precio_unitario else None,
                                            'cantidad': extra.cantidad
                                        }
                                        for extra in servicios_extra_nuevos
                                    ]
                                else:
                                    # Fallback para servicios guardados con el método anterior
                                    servicios_extra = detalles.servicios.all().select_related()
                                    logger.info(f"Fallback: Recuperando servicios extra para detalle {detalles.id}")
                                    logger.info(f"Servicios extra raw query: {servicios_extra.query}")
                                    logger.info(f"Servicios extra encontrados: {[{'id': s.id, 'servicio': s.servicio} for s in servicios_extra]}")
                                    
                                    if servicios_extra.exists():
                                        entrada_info['servicios_extra'] = [
                                            {
                                                'nombre': s.servicio,
                                                'descripcion': s.descripcion,
                                                'precio': float(s.precio) if s.precio else None,
                                                'cantidad': 1
                                            }
                                            for s in servicios_extra
                                        ]
                                    else:
                                        entrada_info['servicios_extra'] = [{
                                            'nombre': '-',
                                            'descripcion': 'No hay servicios extra contratados',
                                            'precio': None,
                                            'cantidad': 0
                                        }]
                                
                                # Log detallado para debug
                                logger.info(f"Entrada info final: {entrada_info}")
                                if servicios_extra_nuevos.exists():
                                    logger.info(f"Servicios extra nuevos en detalle: {[(s.servicio.servicio, s.cantidad) for s in servicios_extra_nuevos]}")
                                else:
                                    logger.info(f"Servicios extra antiguos en detalle: {[s.servicio for s in detalles.servicios.all()]}")
                            else:
                                # Este caso no debería ocurrir ya que ahora lanzamos una excepción si no hay detalles
                                logger.error(f"No se encontraron detalles para la compra {compra.id}")
                                raise Exception("No se encontraron detalles de la compra")
                        except Exception as e:
                            logger.error(f"Error al obtener detalles de la compra {compra.id}: {str(e)}")
                            entrada_info = {
                                'tipo': 'Entrada General',
                                'duracion': 'Duración no especificada',
                                'duracion_horas': None,
                                'duracion_tipo': None,
                                'hora_inicio': '00:00',
                                'hora_fin': '23:59',
                                'servicios_incluidos': [],
                                'servicios_extra': []
                            }
                        
                        # Preparar respuesta
                        response_data = {
                            'valid': True,
                            'compra_id': compra.id,
                            'terma': compra.terma.nombre_terma,
                            'fecha_visita': str(compra.fecha_visita),
                            'usuario': f"{compra.usuario.nombre} {compra.usuario.apellido}",
                            'cantidad': compra.cantidad if hasattr(compra, 'cantidad') else 1,
                            'entrada': entrada_info,
                            'total_pagado': float(compra.monto_pagado) if compra.monto_pagado else float(compra.total),
                            'mensaje': 'Entrada validada correctamente'
                        }
                        
                        logger.info(f"Enviando respuesta exitosa para compra {compra.id}")
                        logger.debug(f"Datos de respuesta: {response_data}")
                        
                        # Devolver respuesta exitosa
                        return JsonResponse(response_data)
                except Exception as e:
                    # Si algo falla durante la transacción, registrar el intento fallido
                    RegistroEscaneo.objects.create(
                        codigo_qr=codigo_qr,
                        usuario_scanner=request.user,
                        exitoso=False,
                        mensaje=f'Error al procesar: {str(e)}',
                        ip_address=request.META.get('REMOTE_ADDR'),
                        dispositivo=request.META.get('HTTP_USER_AGENT', '')
                    )
                    raise

                return JsonResponse({
                    'valid': True,
                    'compra_id': compra.id,
                    'terma': compra.terma.nombre_terma,
                    'fecha_visita': str(compra.fecha_visita),
                    'usuario': f"{compra.usuario.nombre} {compra.usuario.apellido}",
                    'cantidad': compra.cantidad if hasattr(compra, 'cantidad') else 1
                })
                
            except Exception as e:
                return JsonResponse({
                    'valid': False,
                    'error': str(e)
                }, status=400)

        except Exception as e:
            return JsonResponse({
                'valid': False,
                'error': str(e)
            }, status=500)