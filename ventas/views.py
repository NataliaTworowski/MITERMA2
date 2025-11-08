from django.shortcuts import render
import mercadopago
import os
from dotenv import load_dotenv
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.http import JsonResponse
from django.utils import timezone
from termas.models import Terma
from usuarios.models import Usuario
from usuarios.models import Usuario
from usuarios.decorators import cliente_required

# Cargar variables de entorno
load_dotenv()

def pago(request, terma_id=None):
    datos = {}
    if request.method == 'POST':
        datos['terma_id'] = request.POST.get('terma_id') or terma_id
        access_token = os.getenv("MP_ACCESS_TOKEN")
        if not access_token:
            return JsonResponse({'error': 'Error: No se encontró el token de acceso de Mercado Pago'}, status=500)
        sdk = mercadopago.SDK(access_token)
        datos['entrada_id'] = request.POST.get('entrada_id')
        datos['experiencia'] = request.POST.get('input_experiencia')
        datos['precio'] = request.POST.get('input_precio')
        datos['incluidos'] = request.POST.get('input_incluidos')
        datos['extras'] = request.POST.get('input_extras')
        datos['total'] = request.POST.get('input_total')
        datos['cantidad'] = request.POST.get('cantidad')
        datos['fecha'] = request.POST.get('fecha')
        datos['cantidad_entradas'] = request.POST.get('cantidad')
        
                # Obtener descripción detallada de servicios extra
        from termas.models import ServicioTerma
        if datos.get('extras') and datos['extras'].strip():
            try:
                print(f"\n[DEBUG] Procesando servicio extra: {datos['extras']}")
                # Obtener el servicio por nombre
                nombre_servicio = datos['extras'].split('x1')[0].strip()  # "Gimnasio x1 ($17.000 CLP)" -> "Gimnasio"
                print(f"[DEBUG] Buscando servicio con nombre: {nombre_servicio}")
                
                servicio = ServicioTerma.objects.filter(servicio__icontains=nombre_servicio).first()
                if servicio:
                    print(f"[DEBUG] Servicio encontrado - ID: {servicio.id}, Nombre: {servicio.servicio}")
                    datos['extras_descripcion'] = f"{servicio.servicio} (${servicio.precio} CLP)"
                    datos['servicio_extra_id'] = servicio.id
                    # Save the service ID in session for later use
                    request.session['servicio_extra_id'] = servicio.id
                else:
                    print(f"[DEBUG] No se encontró el servicio: {nombre_servicio}")
                    datos['extras_descripcion'] = '-'
                    datos['servicio_extra_id'] = None
            except Exception as e:
                print(f"[DEBUG] Error al procesar servicio extra: {str(e)}")
                import traceback
                print(traceback.format_exc())
                datos['extras_descripcion'] = '-'
                datos['servicio_extra_id'] = None
        else:
            datos['extras_descripcion'] = '-'
            datos['servicio_extra_id'] = None        # Obtener usuario
        usuario = None
        if request.user.is_authenticated:
            # Usuario autenticado con Django Auth
            usuario = request.user
        else:
            # Fallback para casos especiales (si aplica)
            usuario_id = request.POST.get('usuario_id')
            if usuario_id:
                usuario = Usuario.objects.filter(id=usuario_id).first()
        
        # Obtener terma
        terma_id = request.POST.get('terma_id')
        terma = None
        if terma_id:
            terma = Terma.objects.filter(id=terma_id).first()
        
        # Validar datos antes de crear la compra
        if not usuario:
            datos['compra_error'] = "No se encontró el usuario para la compra. Debes iniciar sesión."
            return render(request, 'ventas/pago.html', datos)
        
        # Validar datos requeridos
        if not datos.get('entrada_id'):
            datos['compra_error'] = "No se especificó la entrada a comprar."
            return render(request, 'ventas/pago.html', datos)

        if not datos.get('total'):
            datos['compra_error'] = "No se recibió el monto total de la compra."
            return render(request, 'ventas/pago.html', datos)

        if not terma:
            datos['compra_error'] = "No se encontró la terma seleccionada para la compra."
            return render(request, 'ventas/pago.html', datos)
            
            # Validar que la entrada exista
        from entradas.models import HorarioDisponible, EntradaTipo
        try:
            # Primero validar que sea un ID válido
            entrada_id = str(datos.get('entrada_id')).strip()
            if not entrada_id:
                datos['compra_error'] = "No se seleccionó ningún tipo de entrada."
                return render(request, 'ventas/pago.html', datos)

            # Validar que el tipo de entrada exista y pertenezca a la terma
            entrada_tipo = EntradaTipo.objects.filter(id=entrada_id, terma=terma, estado=True).first()
            if not entrada_tipo:
                datos['compra_error'] = "El tipo de entrada seleccionado no es válido para esta terma."
                return render(request, 'ventas/pago.html', datos)

            # Todo está correcto, asignar la entrada validada
            datos['entrada_tipo'] = entrada_tipo

        except (ValueError, EntradaTipo.DoesNotExist):
            datos['compra_error'] = "La entrada seleccionada no es válida."
            return render(request, 'ventas/pago.html', datos)

        # Verificar disponibilidad para la fecha seleccionada
        fecha_visita = datos.get('fecha')
        if fecha_visita:
            from datetime import datetime
            fecha_visita = datetime.strptime(fecha_visita, '%Y-%m-%d').date()
            hay_disponibilidad, cupos_restantes = terma.verificar_disponibilidad_diaria(fecha_visita)
            
            cantidad_solicitada = int(datos.get('cantidad_entradas', 1))
            if not hay_disponibilidad:
                datos['compra_error'] = "Lo sentimos, no hay disponibilidad para la fecha seleccionada."
                return render(request, 'ventas/pago.html', datos)
            elif cantidad_solicitada > cupos_restantes:
                datos['compra_error'] = f"Solo quedan {cupos_restantes} cupos disponibles para la fecha seleccionada."
                return render(request, 'ventas/pago.html', datos)

            # CREAR LA COMPRA ANTES de generar la preferencia
        try:
            from ventas.models import Compra, MetodoPago, DetalleCompra
            from entradas.models import HorarioDisponible
            from termas.models import ServicioTerma
            import uuid

            metodo_pago = MetodoPago.objects.filter(nombre__icontains="Mercado Pago").first()

            # Generar un ID único para esta compra ANTES de crear la preferencia
            mercado_pago_id = f"{access_token[:10]}-{uuid.uuid4()}"

            # Validar y obtener o crear el horario disponible
            if not datos.get('entrada_id') or not datos.get('fecha'):
                raise ValueError("No se especificó el ID de la entrada o la fecha")

            try:
                entrada_tipo = EntradaTipo.objects.get(id=datos['entrada_id'])
                fecha_visita = datetime.strptime(datos['fecha'], '%Y-%m-%d').date()
                
                # Intentar obtener un horario existente o crear uno nuevo
                horario = HorarioDisponible.objects.filter(
                    entrada_tipo=entrada_tipo,
                    fecha=fecha_visita
                ).first()

                if not horario:
                    # Crear nuevo horario disponible
                    horario = entrada_tipo.create_horario_disponible(fecha_visita)

                # Verificar disponibilidad
                if horario.cupos_disponibles < int(datos['cantidad_entradas']):
                    raise ValueError(f"Solo quedan {horario.cupos_disponibles} cupos disponibles para esta fecha")

            except Exception as e:
                raise ValueError(f"Error al obtener o crear el horario disponible: {str(e)}")
            
            # Calcular precio con extras si hay
            try:
                precio_unitario = float(datos['precio'].replace(',', '.')) if datos.get('precio') else 0.0
                cantidad = int(datos['cantidad_entradas']) if datos.get('cantidad_entradas') else 1
                if cantidad <= 0:
                    raise ValueError("La cantidad debe ser mayor a 0")
                subtotal = precio_unitario * cantidad
            except (ValueError, TypeError) as e:
                raise ValueError(f"Error en los datos de precio o cantidad: {str(e)}")

            # Crear la compra
            compra = Compra.objects.create(
                usuario=usuario,
                metodo_pago=metodo_pago,
                terma=terma,
                fecha_visita=datos['fecha'] if datos['fecha'] else None,
                total=datos['total'] if datos['total'] else 0,
                estado_pago="pendiente",
                mercado_pago_id=mercado_pago_id,
                cantidad=cantidad,
            )
            
            # Crear el detalle de compra
            print(f"\n[DEBUG] Creando detalle de compra...")
            detalle = DetalleCompra.objects.create(
                compra=compra,
                horario_disponible=horario,
                cantidad=cantidad,
                precio_unitario=precio_unitario,
                subtotal=subtotal
            )
            print(f"[DEBUG] Detalle creado: ID={detalle.id}")
            
            # Debug de datos recibidos
            print(f"[DEBUG] Datos de extras recibidos: {datos.get('extras', 'No hay extras')}")
            print(f"[DEBUG] Tipo de datos extras: {type(datos.get('extras', ''))}")
            
            # Agregar servicios extra
            if 'servicio_extra_id' in request.session:
                try:
                    servicio_id = request.session['servicio_extra_id']
                    print(f"\n[DEBUG] Recuperando servicio_extra_id de sesión: {servicio_id}")
                    
                    servicio = ServicioTerma.objects.get(id=servicio_id)
                    print(f"[DEBUG] Servicio encontrado para agregar: {servicio.servicio}")
                    
                    # Limpiar servicios existentes y agregar el nuevo
                    detalle.servicios.clear()
                    detalle.servicios.add(servicio)
                    
                    # Guardar explícitamente
                    detalle.save()
                    
                    # Verificar que se guardó
                    servicios_guardados = list(detalle.servicios.all())
                    print(f"[DEBUG] Servicios guardados en detalle {detalle.id}: {[s.servicio for s in servicios_guardados]}")
                    
                    # Limpiar la sesión
                    del request.session['servicio_extra_id']
                except Exception as e:
                    print(f"[DEBUG] Error al agregar servicio extra: {str(e)}")
                    import traceback
                    print(traceback.format_exc())
                    try:
                        # Asegurarnos de limpiar la sesión en caso de error
                        if 'servicio_extra_id' in request.session:
                            del request.session['servicio_extra_id']
                    except:
                        pass
            
            print(f"Compra creada: id={compra.id}, mercado_pago_id={compra.mercado_pago_id}")

        except Exception as e:
            datos['compra_error'] = f"Error al guardar la compra: {str(e)}"
            return render(request, 'ventas/pago.html', datos)

        # Mercado Pago integración
        env_base = os.getenv('MP_BASE_URL')
        if env_base:
            base_url = env_base.rstrip('/')
        else:
            base_url = request.build_absolute_uri('/')[:-1]
        
        # Obtener el total real desde el input_total que incluye entradas y servicios
        total = float(datos.get('total', '0').replace('.', '').replace(',', '.'))
        
        # Crear un solo ítem con el total completo
        items = [{
            "title": f"Reserva: {datos['experiencia']} - {datos.get('cantidad_entradas', 1)} entrada(s)",
            "quantity": 1,
            "unit_price": total,
            "currency_id": "CLP",
            "description": f"Incluye: {datos.get('incluidos', '-')}. Servicios extra: {datos.get('extras_descripcion', '-')}"
        }]

        preference_data = {
            "items": items,
            "external_reference": mercado_pago_id,  
            "back_urls": {
                "success": f"{base_url}/ventas/pago/success/",  
                "failure": f"{base_url}/ventas/pago/failure/",
                "pending": f"{base_url}/ventas/pago/pending/"
            },
            "auto_return": "approved",
            "notification_url": f"{base_url}/ventas/webhook/mercadopago/",  
            "statement_descriptor": "TERMAS",
            "metadata": {
                "compra_id": compra.id,
                "usuario_id": usuario.id,
                "terma_id": terma.id
            }
        }
        
        preference_response = sdk.preference().create(preference_data)
        response_data = preference_response.get("response", {})
        
        if "init_point" in response_data:
            datos['mercadopago_url'] = response_data["init_point"]
        else:
            datos['mercadopago_error'] = response_data.get("message", "No se pudo generar el enlace de pago. Intenta nuevamente.")
            compra.estado_pago = "error"
            compra.save()

    # Si no está en POST, buscar la terma por entrada_id en EntradaTipo
    if request.method != 'POST' and terma_id:
        datos['terma_id'] = terma_id
    
    if not datos.get('terma_id') and datos.get('entrada_id'):
        from entradas.models import EntradaTipo
        entrada_tipo = EntradaTipo.objects.filter(id=datos['entrada_id']).first()
        if entrada_tipo and entrada_tipo.terma_id:
            datos['terma_id'] = entrada_tipo.terma_id
        else:
            datos['terma_id'] = datos['entrada_id']
    
    datos['usuario'] = usuario
    return render(request, 'ventas/pago.html', datos)

@csrf_exempt
def mercadopago_webhook(request):
    import os
    from django.conf import settings
    print(f"[WEBHOOK] Método: {request.method}")

    if request.method == 'POST':
        try:
            import json
            # Detectar si estamos en modo prueba o de desarrollo
            access_token = os.getenv("MP_ACCESS_TOKEN")
            is_test = access_token.startswith("TEST-") if access_token else False
            print(f"[WEBHOOK] Modo: {'PRUEBA' if is_test else 'PRODUCCIÓN'}")
            print(f"[WEBHOOK] Headers: {dict(request.headers)}")
            body = request.body.decode('utf-8')
            print(f"[WEBHOOK] Body: {body}")
            print(f"[WEBHOOK] Query params: {dict(request.GET)}")

            # VALIDAR FIRMA SOLO EN PRODUCCIÓN Y SI NO ESTAMOS EN DEBUG
            if not is_test and not settings.DEBUG:
                x_signature = request.headers.get('x-signature')
                x_request_id = request.headers.get('x-request-id')
                if x_signature and x_request_id:
                    webhook_secret = os.getenv("MP_WEBHOOK_SECRET")
                    if webhook_secret:
                        import hashlib
                        import hmac
                        parts = {}
                        for part in x_signature.split(','):
                            if '=' in part:
                                key, value = part.split('=', 1)
                                parts[key.strip()] = value.strip()
                        ts = parts.get('ts')
                        received_signature = parts.get('v1')
                        data_id = request.GET.get('data.id') or request.GET.get('id')
                        if not data_id and body:
                            try:
                                body_json = json.loads(body)
                                data_id = body_json.get('data', {}).get('id') or body_json.get('id')
                            except:
                                pass
                        message = f"id:{data_id};request-id:{x_request_id};ts:{ts};"
                        expected_signature = hmac.new(
                            webhook_secret.encode(),
                            message.encode(),
                            hashlib.sha256
                        ).hexdigest()
                        if not hmac.compare_digest(received_signature, expected_signature):
                            print("[WEBHOOK] ❌ Firma inválida en PRODUCCIÓN")
                            return JsonResponse({
                                'status': 'error',
                                'message': 'Invalid signature'
                            }, status=401)
                        print("[WEBHOOK] Firma válida")
                    else:
                        print("[WEBHOOK] MP_WEBHOOK_SECRET no configurado en producción")
                else:
                    print("[WEBHOOK] No se recibió x-signature en producción")
            else:
                print("[WEBHOOK] Modo PRUEBA o DEBUG: Saltando validación de firma")

            # Procesar webhook (igual para ambos modos)
            data = {}
            if body:
                try:
                    data = json.loads(body)
                except:
                    pass

            resource_type = data.get('type') or request.GET.get('topic')
            resource_id = data.get('data', {}).get('id') or request.GET.get('data.id') or request.GET.get('id')
            print(f"[WEBHOOK] type: {resource_type}, id: {resource_id}")

            if resource_type == 'payment' and resource_id:
                # SIEMPRE consultar la API de MP
                sdk = mercadopago.SDK(access_token)
                payment_info = sdk.payment().get(resource_id)
                if payment_info['status'] == 200:
                    payment_data = payment_info['response']
                    external_reference = payment_data.get('external_reference')
                    status = payment_data.get('status')
                    print(f"[WEBHOOK] Payment status: {status}, external_reference: {external_reference}")
                    if is_test:
                        print(f"[WEBHOOK] PRUEBA - Payment data: {payment_data}")
                    if status == 'approved' and external_reference:
                        from ventas.models import Compra
                        from django.utils import timezone
                        from django.db import transaction
                        with transaction.atomic():
                            compra = Compra.objects.select_for_update().filter(
                                mercado_pago_id=str(external_reference),
                                estado_pago="pendiente"
                            ).first()
                            if compra:
                                if not Compra.objects.filter(payment_id=str(resource_id)).exclude(id=compra.id).exists():
                                    print(f"[WEBHOOK] Procesando pago aprobado para compra {compra.id}")
                                    compra.estado_pago = "pagado"
                                    compra.payment_id = str(resource_id)
                                    compra.pagador_email = payment_data.get('payer', {}).get('email', '')
                                    compra.monto_pagado = payment_data.get('transaction_amount', compra.total)
                                    compra.fecha_confirmacion_pago = timezone.now()
                                    compra.save()
                                    print(f"[WEBHOOK] Compra {compra.id} actualizada")
                                    
                                    # Enviar correo con la entrada
                                    try:
                                        from ventas.utils import enviar_entrada_por_correo
                                        print(f"[WEBHOOK] Preparando envío de correo para compra {compra.id}")
                                        print(f"[WEBHOOK] Email del usuario: {compra.usuario.email}")
                                        enviar_entrada_por_correo(compra)
                                        print(f"[WEBHOOK] Correo enviado exitosamente para la compra {compra.id}")
                                    except Exception as e:
                                        import traceback
                                        print(f"[WEBHOOK] Error al enviar correo: {str(e)}")
                                        print("[WEBHOOK] Traceback completo:")
                                        print(traceback.format_exc())

                                    if is_test:
                                        print(f"[WEBHOOK] PRUEBA - Compra aprobada: {compra.id}")
                                    return JsonResponse({"status": "success"}, status=200)
                                else:
                                    print(f"[WEBHOOK] payment_id ya registrado")
                                    return JsonResponse({"status": "duplicate"}, status=200)
                            else:
                                print(f"[WEBHOOK] Compra ya procesada")
                                return JsonResponse({"status": "already_processed"}, status=200)
                return JsonResponse({"status": "received"}, status=200)
            return JsonResponse({"status": "ignored"}, status=200)
        except Exception as e:
            print(f"[WEBHOOK] Error: {str(e)}")
            import traceback
            traceback.print_exc()
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error'}, status=405)
    

def pago_exitoso(request):
    import os
    import mercadopago
    from ventas.models import Compra
    from django.utils import timezone
    
    # Obtener todos los parámetros de Mercado Pago
    payment_id = request.GET.get('payment_id') or request.GET.get('collection_id')
    collection_id = request.GET.get('collection_id')
    preference_id = request.GET.get('preference_id')
    status = request.GET.get('status') or request.GET.get('collection_status')
    
    print(f"[PAGO_EXITOSO] payment_id: {payment_id}, preference_id: {preference_id}, status: {status}")
    
    compra = None
    error_message = None
    
    # Si el pago fue aprobado, actualizar la compra y enviar correo
    if status == 'approved' and payment_id:
        try:
            # Consultar la API de Mercado Pago para obtener el external_reference
            access_token = os.getenv("MP_ACCESS_TOKEN")
            sdk = mercadopago.SDK(access_token)
            payment_info = sdk.payment().get(payment_id)
            
            if payment_info['status'] == 200:
                payment_data = payment_info['response']
                external_reference = payment_data.get('external_reference')  # Este es nuestro mercado_pago_id
                
                print(f"[PAGO_EXITOSO] external_reference: {external_reference}")
                
                if external_reference:
                    # Buscar la compra por el external_reference con todas sus relaciones
                    compra = Compra.objects.select_related('terma').prefetch_related(
                        'detalles',
                        'detalles__horario_disponible',
                        'detalles__horario_disponible__entrada_tipo',
                        'detalles__horario_disponible__entrada_tipo__terma'
                    ).filter(
                        mercado_pago_id=str(external_reference),
                        estado_pago="pendiente"
                    ).first()
                    
                    if compra:
                        # Validar que el payment_id no esté ya registrado en otra compra
                        compra_duplicada = Compra.objects.filter(
                            payment_id=str(payment_id)
                        ).exclude(id=compra.id).exists()

                        # Validar monto pagado
                        monto_esperado = float(compra.total)
                        monto_pagado = float(payment_data.get('transaction_amount', 0))
                        if abs(monto_esperado - monto_pagado) > 0.01:
                            error_message = f"El monto pagado (${monto_pagado}) no coincide con el esperado (${monto_esperado})"
                            print(f"[SEGURIDAD] ⚠️ {error_message}")
                            compra.estado_pago = "revisión"
                            compra.save()
                            context = {
                                'usuario': request.user,
                                'payment_id': payment_id,
                                'collection_id': collection_id,
                                'preference_id': preference_id,
                                'status': status,
                                'compra': compra,
                                'error_message': "Error en el monto del pago. Contacta a soporte.",
                                'success': False,
                                
                            }
                            return render(request, 'ventas/pago_exitoso.html', context)

                        if not compra_duplicada:
                            # Actualizar la compra a pagado
                            compra.estado_pago = "pagado"
                            compra.payment_id = str(payment_id)
                            compra.pagador_email = payment_data.get('payer', {}).get('email', '')
                            compra.monto_pagado = payment_data.get('transaction_amount', compra.total)
                            compra.fecha_confirmacion_pago = timezone.now()
                            compra.save()
                            print(f"[PAGO_EXITOSO] Compra {compra.id} actualizada a aprobado")
                            
                            # Enviar correo con la entrada
                            try:
                                from ventas.utils import enviar_entrada_por_correo
                                print(f"[PAGO_EXITOSO] Preparando envío de correo para compra {compra.id}")
                                print(f"[PAGO_EXITOSO] Email del usuario: {compra.usuario.email}")
                                enviar_entrada_por_correo(compra)
                                print(f"[PAGO_EXITOSO] Correo enviado exitosamente para la compra {compra.id}")
                            except Exception as e:
                                import traceback
                                print(f"[PAGO_EXITOSO] Error al enviar correo: {str(e)}")
                                print("[PAGO_EXITOSO] Traceback completo:")
                                print(traceback.format_exc())
                        else:
                            print(f"[PAGO_EXITOSO] payment_id {payment_id} ya registrado en otra compra")
                            error_message = "Este pago ya fue procesado anteriormente."
                    else:
                        print(f"[PAGO_EXITOSO] No se encontró compra pendiente con external_reference: {external_reference}")
                        # Intentar buscar si la compra ya existe con este payment_id (ya fue procesada)
                        compra = Compra.objects.filter(payment_id=str(payment_id)).first()
                        if compra:
                            print(f"[PAGO_EXITOSO] Compra ya procesada: {compra.id}")
                        else:
                            error_message = "No se encontró la compra asociada a este pago."
                else:
                    error_message = "No se pudo obtener la referencia del pago."
            else:
                error_message = f"Error al consultar el pago: {payment_info.get('status')}"
                print(f"[PAGO_EXITOSO] Error en API de MP: {payment_info}")
                
        except Exception as e:
            error_message = f"Error al procesar el pago: {str(e)}"
            print(f"[PAGO_EXITOSO] Exception: {str(e)}")
            import traceback
            traceback.print_exc()
    
    # Si no hay payment_id o el status no es approved
    elif not payment_id:
        error_message = "No se recibió el ID del pago."
    elif status != 'approved':
        error_message = f"El pago no fue aprobado. Estado: {status}"
    
    context = {
        'payment_id': payment_id,
        'collection_id': collection_id,
        'preference_id': preference_id,
        'status': status,
        'compra': compra,
        'error_message': error_message,
        'success': compra is not None and compra.estado_pago == 'pagado'
    }
    
    return render(request, 'ventas/pago_exitoso.html', context)

def pago_fallido(request):
    """Vista para pagos fallidos o rechazados"""
    payment_id = request.GET.get('payment_id')
    status = request.GET.get('status')
    preference_id = request.GET.get('preference_id')
    
    print(f"[PAGO_FALLIDO] payment_id: {payment_id}, status: {status}")
    
    context = {
        'payment_id': payment_id,
        'status': status,
        'preference_id': preference_id,
    }
    return render(request, 'ventas/pago_fallido.html', context)


def pago_pendiente(request):
    """Vista para pagos pendientes (ej: pago en efectivo en punto de pago)"""
    payment_id = request.GET.get('payment_id')
    status = request.GET.get('status')
    preference_id = request.GET.get('preference_id')
    
    print(f"[PAGO_PENDIENTE] payment_id: {payment_id}, status: {status}")
    
    # Opcional: Actualizar la compra a estado "pendiente_confirmacion"
    if payment_id and preference_id:
        try:
            import os
            import mercadopago
            from ventas.models import Compra
            
            access_token = os.getenv("MP_ACCESS_TOKEN")
            sdk = mercadopago.SDK(access_token)
            payment_info = sdk.payment().get(payment_id)
            
            if payment_info['status'] == 200:
                payment_data = payment_info['response']
                external_reference = payment_data.get('external_reference')
                
                if external_reference:
                    compra = Compra.objects.filter(
                        mercado_pago_id=str(external_reference),
                        estado_pago="pendiente"
                    ).first()
                    
                    if compra:
                        compra.estado_pago = "pendiente_confirmacion"
                        compra.payment_id = str(payment_id)
                        compra.save()
                        print(f"[PAGO_PENDIENTE] Compra {compra.id} marcada como pendiente de confirmación")
        except Exception as e:
            print(f"[PAGO_PENDIENTE] Error: {str(e)}")
    
    context = {
        'payment_id': payment_id,
        'status': status,
        'preference_id': preference_id,
    }
    return render(request, 'ventas/pago_pendiente.html', context)