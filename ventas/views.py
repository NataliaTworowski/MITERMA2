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
from ventas.models import Compra

# Cargar variables de entorno
load_dotenv()

def pago(request, terma_id=None):
    datos = {}
    
    # VALIDACIÓN PREVIA: Verificar compras recientes antes de mostrar el formulario
    if request.user.is_authenticated and request.method == 'GET':
        # Obtener parámetros de la URL para validar
        entrada_id = request.GET.get('entrada_id')
        fecha_visita_str = request.GET.get('fecha')
        cantidad = request.GET.get('cantidad', 1)
        
        if entrada_id and fecha_visita_str:
            from datetime import datetime, timedelta
            from django.utils import timezone
            
            try:
                fecha_visita_obj = datetime.strptime(fecha_visita_str, '%Y-%m-%d').date()
                tiempo_limite = timezone.now() - timedelta(minutes=15)
                
                # Buscar compra idéntica muy reciente (pagada O pendiente)
                compra_reciente = Compra.objects.filter(
                    usuario=request.user,
                    terma_id=terma_id,
                    fecha_visita=fecha_visita_obj,
                    estado_pago__in=['pagado', 'pendiente'],  # Incluir pendientes también
                    detalles__entrada_tipo_id=entrada_id,
                    cantidad=int(cantidad),
                    fecha_compra__gt=tiempo_limite
                ).first()
                
                if compra_reciente:
                    if compra_reciente.estado_pago == 'pagado':
                        datos['compra_error'] = f"Ya realizaste esta compra hace pocos minutos (ID: {compra_reciente.id}). Revisa tu historial de compras."
                    else:
                        datos['compra_error'] = f"Ya tienes una compra pendiente idéntica (ID: {compra_reciente.id}). Espera a que se procese antes de intentar otra."
                    return render(request, 'ventas/pago.html', datos)
                    
            except (ValueError, TypeError):
                pass  # Continúa normal si hay error en los parámetros
    
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
        
        # VALIDACION ANTI-DUPLICADOS: Verificar usuario autenticado
        if not request.user.is_authenticated:
            datos['compra_error'] = "Debes iniciar sesión para realizar una compra."
            return render(request, 'ventas/pago.html', datos)
        
        usuario = request.user
        
        # Obtener datos críticos para verificación
        entrada_id = datos.get('entrada_id')
        fecha_visita = datos.get('fecha')
        total_amount = datos.get('total')
        
        if not all([entrada_id, fecha_visita, total_amount]):
            datos['compra_error'] = "Faltan datos requeridos para procesar el pago."
            return render(request, 'ventas/pago.html', datos)
        
        # VERIFICAR SI YA EXISTE UNA COMPRA ACTIVA/EXITOSA PARA ESTOS MISMOS PARÁMETROS
        from ventas.models import Compra
        from datetime import datetime
        
        try:
            fecha_visita_obj = datetime.strptime(fecha_visita, '%Y-%m-%d').date()
        except ValueError:
            datos['compra_error'] = "Fecha de visita inválida."
            return render(request, 'ventas/pago.html', datos)
        
        # VALIDACIÓN ANTI-SPAM: Solo bloquear clicks múltiples accidentales inmediatos
        # Buscar compra muy reciente (últimos 15 minutos) con parámetros idénticos
        from django.utils import timezone
        from datetime import timedelta
        
        tiempo_limite = timezone.now() - timedelta(minutes=15)
        compra_reciente = Compra.objects.filter(
            usuario=usuario,
            terma_id=datos['terma_id'],
            fecha_visita=fecha_visita_obj,
            estado_pago__in=['pendiente', 'pagado'],
            detalles__entrada_tipo_id=entrada_id,
            cantidad=int(datos.get('cantidad_entradas', 1)),
            fecha_compra__gt=tiempo_limite  # Solo últimos 15 minutos
        ).first()
        
        if compra_reciente:
            if compra_reciente.estado_pago == 'pagado':
                datos['compra_error'] = f"Ya realizaste esta compra (ID: {compra_reciente.id}). Revisa tu historial de compras."
                return render(request, 'ventas/pago.html', datos)
            elif compra_reciente.estado_pago == 'pendiente':
                datos['compra_error'] = f"Ya tienes una compra pendiente idéntica (ID: {compra_reciente.id}). No hagas múltiples pagos."
                return render(request, 'ventas/pago.html', datos)
        
        # Buscar compra pendiente para reutilizar
        compra_existente = Compra.objects.filter(
            usuario=usuario,
            terma_id=datos['terma_id'],
            fecha_visita=fecha_visita_obj,
            estado_pago='pendiente',
            detalles__entrada_tipo_id=entrada_id,
            cantidad=int(datos.get('cantidad_entradas', 1))
        ).first()
        
        if compra_existente:
            # Verificar si la compra pendiente es reciente (últimos 30 minutos)
            tiempo_limite_pendiente = timezone.now() - timedelta(minutes=30)
            if compra_existente.fecha_compra > tiempo_limite_pendiente:
                # Usar la compra existente
                compra = compra_existente
                datos['compra_existente'] = True
                datos['compra_id'] = compra.id
                print(f"[SEGURIDAD] Usando compra existente ID: {compra.id}")
                
                # Generar nueva preferencia para la compra existente
                if compra.mercado_pago_id:
                    mercado_pago_id = compra.mercado_pago_id
                else:
                    import uuid
                    mercado_pago_id = f"{access_token[:10]}-{uuid.uuid4()}"
                    compra.mercado_pago_id = mercado_pago_id
                    compra.save()
            else:
                # Compra pendiente muy antigua, marcar como cancelada y crear nueva
                compra_existente.estado_pago = 'cancelado'
                compra_existente.save()
                print(f"[SEGURIDAD] Compra {compra_existente.id} cancelada por timeout")
                compra = None
        
        # Obtener descripción detallada de servicios extra
        from termas.models import ServicioTerma
        if datos.get('extras') and datos['extras'].strip():
            try:
                print(f"\n[DEBUG] Procesando servicios extra: {datos['extras']}")
                
                # Procesar múltiples servicios separados por coma
                servicios_texto = datos['extras'].strip()
                if servicios_texto == '-':
                    datos['extras_descripcion'] = '-'
                    datos['servicios_extra_ids'] = []
                else:
                    # Dividir por comas para obtener cada servicio
                    servicios_individuales = [s.strip() for s in servicios_texto.split(',') if s.strip()]
                    servicios_encontrados = []
                    servicios_ids = []
                    
                    for servicio_texto in servicios_individuales:
                        print(f"[DEBUG] Procesando servicio individual: {servicio_texto}")
                        
                        # Extraer nombre del servicio (antes de 'x' y los paréntesis)
                        # Ejemplo: "Gimnasio x1 ($17.000)" -> "Gimnasio"
                        # Ejemplo: "Masajes relajantes x2 ($28.000)" -> "Masajes relajantes"
                        if ' x' in servicio_texto:
                            nombre_servicio = servicio_texto.split(' x')[0].strip()
                        else:
                            nombre_servicio = servicio_texto.split('(')[0].strip()
                        
                        print(f"[DEBUG] Buscando servicio con nombre: {nombre_servicio}")
                        
                        # Extraer cantidad
                        cantidad = 1
                        if ' x' in servicio_texto:
                            try:
                                cantidad_texto = servicio_texto.split(' x')[1].split(' ')[0]
                                cantidad = int(cantidad_texto)
                            except:
                                cantidad = 1
                        
                        # Buscar el servicio en la base de datos
                        servicio = ServicioTerma.objects.filter(servicio__icontains=nombre_servicio).first()
                        if servicio:
                            print(f"[DEBUG] Servicio encontrado - ID: {servicio.id}, Nombre: {servicio.servicio}, Cantidad: {cantidad}")
                            # Agregar el servicio tantas veces como la cantidad especificada
                            for _ in range(cantidad):
                                servicios_ids.append(servicio.id)
                            servicios_encontrados.append(f"{servicio.servicio} x{cantidad} (${servicio.precio} CLP)")
                        else:
                            print(f"[DEBUG] No se encontró el servicio: {nombre_servicio}")
                    
                    if servicios_encontrados:
                        datos['extras_descripcion'] = ', '.join(servicios_encontrados)
                        datos['servicios_extra_ids'] = servicios_ids
                        # Guardar los IDs en la sesión
                        request.session['servicios_extra_ids'] = servicios_ids
                        print(f"[DEBUG] Servicios guardados en sesión: {servicios_ids}")
                    else:
                        datos['extras_descripcion'] = '-'
                        datos['servicios_extra_ids'] = []
                        
            except Exception as e:
                print(f"[DEBUG] Error al procesar servicios extra: {str(e)}")
                import traceback
                print(traceback.format_exc())
                datos['extras_descripcion'] = '-'
                datos['servicios_extra_ids'] = []
        else:
            datos['extras_descripcion'] = '-'
            datos['servicios_extra_ids'] = []        

        # Obtener terma
        terma_id = datos.get('terma_id')
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
        from entradas.models import EntradaTipo
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

        # Verificar disponibilidad usando el nuevo sistema centralizado
        fecha_visita_para_validacion = datos.get('fecha')
        if fecha_visita_para_validacion:
            from datetime import datetime
            from ventas.disponibilidad_utils import validar_cantidad_disponible
            
            fecha_visita_obj = datetime.strptime(fecha_visita_para_validacion, '%Y-%m-%d').date()
            cantidad_solicitada = int(datos.get('cantidad_entradas', 1))
            
            # Usar solo nuestro sistema de validación de disponibilidad
            validacion = validar_cantidad_disponible(terma.id, cantidad_solicitada, fecha_visita_obj)
            
            if not validacion['es_valida']:
                datos['compra_error'] = validacion['mensaje']
                return render(request, 'ventas/pago.html', datos)

            # CREAR LA COMPRA ANTES de generar la preferencia (solo si no existe una)
        if not locals().get('compra'):  # Solo crear si no hay compra existente
            try:
                from ventas.models import Compra, MetodoPago, DetalleCompra
                from entradas.models import EntradaTipo
                from termas.models import ServicioTerma
                import uuid

                metodo_pago = MetodoPago.objects.filter(nombre__icontains="Mercado Pago").first()

                # Generar un ID único para esta compra ANTES de crear la preferencia
                mercado_pago_id = f"{access_token[:10]}-{uuid.uuid4()}"

                # Validar y obtener o crear la entrada para la fecha específica
                if not datos.get('entrada_id') or not datos.get('fecha'):
                    raise ValueError("No se especificó el ID de la entrada o la fecha")

                try:
                    entrada_template = EntradaTipo.objects.get(id=datos['entrada_id'])
                    fecha_visita = datetime.strptime(datos['fecha'], '%Y-%m-%d').date()
                    
                    # Obtener o crear la entrada específica para esta fecha
                    entrada_tipo = EntradaTipo.get_entrada_para_fecha(
                        terma=entrada_template.terma,
                        nombre=entrada_template.nombre,
                        fecha=fecha_visita
                    )

                    if not entrada_tipo:
                        raise ValueError("No se pudo crear la entrada para la fecha especificada")

                except Exception as e:
                    raise ValueError(f"Error al obtener o crear la entrada para la fecha: {str(e)}")
                
                # Calcular precio con extras si hay
                try:
                    precio_unitario = float(datos['precio'].replace(',', '.')) if datos.get('precio') else 0.0
                    cantidad = int(datos['cantidad_entradas']) if datos.get('cantidad_entradas') else 1
                    if cantidad <= 0:
                        raise ValueError("La cantidad debe ser mayor a 0")
                    subtotal = precio_unitario * cantidad
                except (ValueError, TypeError) as e:
                    raise ValueError(f"Error en los datos de precio o cantidad: {str(e)}")
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
                    entrada_tipo=entrada_tipo,
                    cantidad=cantidad,
                    precio_unitario=precio_unitario,
                    subtotal=subtotal
                )
                print(f"[DEBUG] Detalle creado: ID={detalle.id}")
                
                # Reducir cupos disponibles
                entrada_tipo.reducir_cupos(cantidad)
                
                print(f"[NUEVA COMPRA] Compra creada: id={compra.id}, mercado_pago_id={compra.mercado_pago_id}")

            except Exception as e:
                datos['compra_error'] = f"Error al guardar la compra: {str(e)}"
                return render(request, 'ventas/pago.html', datos)
        else:
            print(f"[COMPRA EXISTENTE] Usando compra existente: id={compra.id}, estado={compra.estado_pago}")
            # Para compra existente, obtener el detalle para procesar servicios extra
            detalle = compra.detalles.first()
            if not detalle:
                datos['compra_error'] = "Error: La compra existente no tiene detalles válidos."
                return render(request, 'ventas/pago.html', datos)
            
        # Procesar servicios extra (tanto para compras nuevas como existentes)
        # Debug de datos recibidos
        print(f"[DEBUG] Datos de extras recibidos: {datos.get('extras', 'No hay extras')}")
        print(f"[DEBUG] Tipo de datos extras: {type(datos.get('extras', ''))}")
        
        # Agregar servicios extra
        try:
            if 'servicios_extra_ids' in request.session and request.session['servicios_extra_ids']:
                from .models import ServicioExtraDetalle
                servicios_ids = request.session['servicios_extra_ids']
                print(f"\n[DEBUG] Recuperando servicios_extra_ids de sesión: {servicios_ids}")
                
                # Crear diccionario para contar servicios
                servicios_conteo = {}
                for servicio_id in servicios_ids:
                    servicios_conteo[servicio_id] = servicios_conteo.get(servicio_id, 0) + 1
                
                print(f"[DEBUG] Conteo de servicios: {servicios_conteo}")
                
                # Limpiar servicios existentes del método anterior
                detalle.servicios.clear()
                
                # Crear registros en ServicioExtraDetalle
                for servicio_id, cantidad in servicios_conteo.items():
                    try:
                        servicio = ServicioTerma.objects.get(id=servicio_id)
                        ServicioExtraDetalle.objects.create(
                            detalle_compra=detalle,
                            servicio=servicio,
                            cantidad=cantidad,
                            precio_unitario=servicio.precio
                        )
                        print(f"[DEBUG] ServicioExtraDetalle creado: {servicio.servicio} x{cantidad}")
                    except ServicioTerma.DoesNotExist:
                        print(f"[DEBUG] Servicio no encontrado con ID: {servicio_id}")
                
                # Guardar explícitamente
                detalle.save()
                
                # Verificar que se guardaron
                servicios_extra_guardados = detalle.servicios_extra.all()
                print(f"[DEBUG] Total servicios extra guardados: {len(servicios_extra_guardados)}")
                for extra in servicios_extra_guardados:
                    print(f"[DEBUG] - {extra.servicio.servicio} x{extra.cantidad}")
                
                # Limpiar la sesión
                del request.session['servicios_extra_ids']
            
            # Mantener compatibilidad con el código anterior (servicios individuales)
            elif 'servicio_extra_id' in request.session:
                servicio_id = request.session['servicio_extra_id']
                print(f"\n[DEBUG] Recuperando servicio_extra_id individual de sesión: {servicio_id}")
                
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
            print(f"[DEBUG] Error al agregar servicios extra: {str(e)}")
            import traceback
            print(traceback.format_exc())
            try:
                # Asegurarnos de limpiar la sesión en caso de error
                if 'servicios_extra_ids' in request.session:
                    del request.session['servicios_extra_ids']
                if 'servicio_extra_id' in request.session:
                    del request.session['servicio_extra_id']
            except:
                pass

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
    
    # Agregar información de duración si tenemos la entrada
    if datos.get('entrada_id'):
        from entradas.models import EntradaTipo
        entrada_tipo = EntradaTipo.objects.filter(id=datos['entrada_id']).first()
        if entrada_tipo:
            datos['duracion_horas'] = entrada_tipo.duracion_horas
            datos['duracion_tipo'] = entrada_tipo.get_duracion_tipo_display()
            
            # Crear texto descriptivo de duración más claro
            if entrada_tipo.duracion_horas:
                if entrada_tipo.duracion_horas == 24:
                    datos['duracion_texto'] = "Día completo (24 horas)"
                elif entrada_tipo.duracion_horas >= 12:
                    datos['duracion_texto'] = f"{entrada_tipo.duracion_horas} horas"
                elif entrada_tipo.duracion_horas == 1:
                    datos['duracion_texto'] = "1 hora"
                else:
                    datos['duracion_texto'] = f"{entrada_tipo.duracion_horas} horas"
            else:
                datos['duracion_texto'] = entrada_tipo.get_duracion_tipo_display()
    
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
                                    
                                    # NUEVO: Procesar distribución de pago
                                    try:
                                        from ventas.utils import procesar_pago_completo
                                        print(f"[WEBHOOK] Iniciando distribución de pago para compra {compra.id}")
                                        distribucion = procesar_pago_completo(compra)
                                        print(f"[WEBHOOK] Distribución de pago completada: ID {distribucion.id}")
                                    except Exception as e:
                                        import traceback
                                        print(f"[WEBHOOK] Error en distribución de pago: {str(e)}")
                                        print(traceback.format_exc())
                                    
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
                        'detalles__entrada_tipo',
                        'detalles__entrada_tipo__terma'
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
                            
                            # NUEVO: Procesar distribución de pago
                            try:
                                from ventas.utils import procesar_pago_completo
                                print(f"[PAGO_EXITOSO] Iniciando distribución de pago para compra {compra.id}")
                                distribucion = procesar_pago_completo(compra)
                                print(f"[PAGO_EXITOSO] Distribución de pago completada: ID {distribucion.id}")
                            except Exception as e:
                                import traceback
                                print(f"[PAGO_EXITOSO] Error en distribución de pago: {str(e)}")
                                print(traceback.format_exc())
                            
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
                            # No mostrar error si ya fue procesada, mostrar la compra exitosa
                        else:
                            # Buscar compras similares para detectar duplicados
                            from django.db.models import Q
                            from datetime import timedelta
                            compras_similares = Compra.objects.filter(
                                Q(mercado_pago_id__icontains=external_reference[:10]) | 
                                Q(estado_pago='pagado', fecha_compra__gte=timezone.now() - timedelta(hours=1))
                            ).order_by('-fecha_compra')[:5]
                            
                            if compras_similares.exists():
                                print(f"[PAGO_EXITOSO] Encontradas {compras_similares.count()} compras similares recientes")
                                # Buscar una compra que coincida con el usuario actual si está autenticado
                                if hasattr(request, 'user') and request.user.is_authenticated:
                                    compra_usuario = compras_similares.filter(usuario=request.user).first()
                                    if compra_usuario:
                                        compra = compra_usuario
                                        print(f"[PAGO_EXITOSO] Usando compra del usuario actual: {compra.id}")
                                    else:
                                        error_message = f"Pago procesado pero no se encontró tu compra. Payment ID: {payment_id}. Contacta soporte."
                                else:
                                    error_message = f"Pago procesado exitosamente pero no se pudo asociar la compra. Payment ID: {payment_id}. Contacta soporte."
                            else:
                                error_message = f"No se encontró la compra asociada al pago {payment_id}. Contacta soporte."
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