# -*- coding: utf-8 -*-
import qrcode
import json
import logging
import os
import base64
import hashlib
from cryptography.fernet import Fernet
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import Table, TableStyle
from django.core.mail import EmailMessage
from django.conf import settings
from django.core.signing import TimestampSigner
from django.utils import timezone

# Configurar logger
logger = logging.getLogger(__name__)


def _get_encryption_key():
    """Obtiene o genera una clave de encriptación"""
    key = getattr(settings, 'QR_ENCRYPTION_KEY', None)
    if not key:
        key = Fernet.generate_key()
        # En producción, esta clave debería guardarse de forma segura
    return key

def generar_datos_qr(compra):
    """Genera los datos encriptados que contendrá el QR"""
    from .models import CodigoQR
    
    # Verificar si ya existe un código QR para esta compra
    codigo_qr_existente = CodigoQR.objects.filter(compra=compra).first()
    if codigo_qr_existente:
        logger.info("Código QR existente encontrado")
        return codigo_qr_existente.codigo
    
    # Datos mínimos necesarios para validación
    datos = {
        'ticket_id': f"{compra.id}-{timezone.now().timestamp()}",
        'fecha_visita': str(compra.fecha_visita),
        'terma_id': compra.terma.id
    }
    
    # Crear un token firmado con timestamp
    signer = TimestampSigner()
    token = signer.sign(json.dumps(datos))
    
    # Encriptar el token
    fernet = Fernet(_get_encryption_key())
    datos_encriptados = fernet.encrypt(token.encode())
    datos_qr = datos_encriptados.decode('utf-8')
    
    # Crear registro en la base de datos
    try:
        CodigoQR.objects.create(
            compra=compra,
            codigo=datos_qr,
            fecha_generacion=timezone.now()
        )
        logger.info(f"Código QR guardado en la base de datos para compra {compra.id}")
    except Exception as e:
        logger.error(f"Error al guardar código QR en la base de datos: {str(e)}")
        # Continuar aunque haya error al guardar, ya que el código igual se generó
    
    return datos_qr


def generar_qr(datos):
    """Genera un código QR a partir de los datos proporcionados"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(datos)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convertir la imagen a bytes
    img_buffer = BytesIO()
    img.save(img_buffer)
    img_buffer.seek(0)
    return img_buffer


def generar_pdf_entrada(compra):
    """Genera un PDF con el código QR y los detalles de la entrada"""
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    from reportlab.platypus import Table, TableStyle
    
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    # Línea decorativa superior
    c.setStrokeColor(colors.blue)
    c.setLineWidth(2)
    c.line(50, height - 30, width - 50, height - 30)
    
    # Título
    c.setFont("Helvetica-Bold", 28)
    c.setFillColor(colors.blue)
    c.drawString(50, height - 80, "Entrada MiTerma")
    
    # Subtítulo
    c.setFont("Helvetica", 14)
    c.setFillColor(colors.black)
    c.drawString(50, height - 100, f"Entrada válida para {compra.terma.nombre_terma}")
    
    # Marco de información principal
    c.setStrokeColor(colors.lightgrey)
    c.setLineWidth(1)
    c.rect(50, height - 280, width - 100, 150)
    
    # Información del cliente y compra
    c.setFillColor(colors.blue)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(70, height - 140, "INFORMACIÓN DEL CLIENTE")
    
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(70, height - 170, "Nombre:")
    c.setFont("Helvetica", 12)
    c.drawString(250, height - 170, f"{compra.usuario.nombre} {compra.usuario.apellido}")
    
    c.setFont("Helvetica-Bold", 12)
    c.drawString(70, height - 190, "Nº de Compra:")
    c.setFont("Helvetica", 12)
    c.drawString(250, height - 190, f"#{compra.id:06d}")
    
    c.setFont("Helvetica-Bold", 12)
    c.drawString(70, height - 210, "Fecha de Visita:")
    c.setFont("Helvetica", 12)
    c.drawString(250, height - 210, f"{compra.fecha_visita}")
    
    # Información de entradas y servicios
    c.setFillColor(colors.blue)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(70, height - 250, "DETALLE DE LA COMPRA")
    
    y_position = height - 280
    
    # Mostrar detalles de la entrada
    detalles = compra.detalles.first()
    if detalles:
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 12)
        c.drawString(70, y_position, "Tipo de Entrada:")
        c.setFont("Helvetica", 12)
        c.drawString(250, y_position, f"{detalles.entrada_tipo.nombre}")
        y_position -= 25
        
        # Mostrar cantidad de entradas
        c.setFont("Helvetica-Bold", 12)
        c.drawString(70, y_position, "Cantidad:")
        c.setFont("Helvetica", 12)
        c.drawString(250, y_position, f"{compra.cantidad if hasattr(compra, 'cantidad') else 1} entrada(s)")
        y_position -= 25
        
        # Servicios incluidos
        servicios_incluidos = detalles.entrada_tipo.servicios.all()
        if servicios_incluidos.exists():
            c.setFont("Helvetica-Bold", 12)
            c.drawString(70, y_position, "Servicios Incluidos:")
            c.setFont("Helvetica", 10)
            for servicio in servicios_incluidos:
                c.drawString(250, y_position, f"• {servicio.servicio}")
                y_position -= 15
            y_position -= 10
        
        # Servicios extra contratados
        servicios_extra = detalles.servicios.all()
        if servicios_extra.exists():
            c.setFillColor(colors.blue)
            c.setFont("Helvetica-Bold", 12)
            c.drawString(70, y_position, "Servicios Extra:")
            c.setFillColor(colors.black)
            c.setFont("Helvetica", 10)
            for servicio in servicios_extra:
                precio_formateado = "{:,.0f}".format(float(servicio.precio))
                c.drawString(250, y_position, f"• {servicio.servicio} (${precio_formateado} CLP)")
                y_position -= 15
    
    # Generar y colocar el QR
    qr_data = generar_datos_qr(compra)
    qr_img = generar_qr(qr_data)
    img = ImageReader(qr_img)
    
    # Línea separadora antes del QR
    y_position -= 30
    c.setStrokeColor(colors.blue)
    c.setLineWidth(1)
    c.line(50, y_position, width - 50, y_position)
    
    # Marco para el QR
    qr_size = 180
    qr_x = (width - qr_size) / 2
    qr_y = y_position - qr_size - 40
    
    # Título para el QR
    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(colors.blue)
    c.drawCentredString(width/2, y_position - 25, "CÓDIGO QR DE ACCESO")
    
    # Sombra para el QR
    c.setFillColor(colors.lightgrey)
    c.rect(qr_x + 3, qr_y - 3, qr_size, qr_size, fill=1)
    
    # QR con marco blanco
    c.setFillColor(colors.white)
    c.rect(qr_x, qr_y, qr_size, qr_size, fill=1)
    c.drawImage(img, qr_x, qr_y, width=qr_size, height=qr_size)
    
    # Texto informativo debajo del QR
    c.setFont("Helvetica", 10)
    c.setFillColor(colors.grey)
    c.drawCentredString(width/2, qr_y - 20, "Presenta este código QR al ingresar a la terma")
    c.drawCentredString(width/2, qr_y - 35, "El personal escaneará este código para validar tu entrada")
    
    # Marco informativo
    c.setStrokeColor(colors.lightgrey)
    c.setLineWidth(0.5)
    c.rect(50, 70, width - 100, 40)
    
    # Información importante
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(width/2, 95, "IMPORTANTE: Esta entrada es válida únicamente para la fecha indicada")
    c.setFont("Helvetica", 9)
    c.drawCentredString(width/2, 80, "Conserva este documento hasta finalizar tu visita")
    
    # Pie de página
    c.setFont("Helvetica", 8)
    c.setFillColor(colors.grey)
    c.drawCentredString(width/2, 40, "Este documento es una entrada oficial de MiTerma")
    c.drawCentredString(width/2, 30, f"Generado el {timezone.now().strftime('%d/%m/%Y %H:%M')}")
    
    # Línea decorativa inferior
    c.setStrokeColor(colors.blue)
    c.setLineWidth(2)
    c.line(50, 20, width - 50, 20)
    
    c.save()
    buffer.seek(0)
    return buffer


def enviar_entrada_por_correo(compra):
    """Envía el PDF con la entrada por correo electrónico"""
    logger = logging.getLogger(__name__)
    
    try:
        print(f"[EMAIL] Iniciando envío de correo para compra {compra.id}")
        logger.info("[EMAIL] Enviando correo de confirmación")
        print(f"[EMAIL] FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")
        
        # Verificar que la compra esté pagada
        if compra.estado_pago != 'pagado':
            raise ValueError(f"La compra {compra.id} no está marcada como pagada")
        
        # Verificar que existe el código QR (debería existir ya)
        from .models import CodigoQR
        if not CodigoQR.objects.filter(compra=compra).exists():
            print(f"[EMAIL] Código QR no existe, generando uno nuevo para compra {compra.id}")
            generar_datos_qr(compra)
        
        # Generar el PDF
        try:
            pdf_buffer = generar_pdf_entrada(compra)
            print("[EMAIL] PDF generado correctamente")
        except Exception as e:
            print(f"[EMAIL] Error al generar PDF: {str(e)}")
            raise
        
        # Preparar el correo
        asunto = f"Tu entrada para {compra.terma.nombre_terma}"
        mensaje = f"""¡Hola {compra.usuario.nombre}!

Adjunto encontrarás tu entrada para {compra.terma.nombre_terma}.
Fecha de visita: {compra.fecha_visita}

Por favor, presenta este código QR al llegar a la terma.

¡Gracias por tu compra!"""
        
        logger.info("[EMAIL] Preparando correo para enviar")
        
        # Verificar configuración de email
        if not settings.DEFAULT_FROM_EMAIL:
            raise ValueError("DEFAULT_FROM_EMAIL no está configurado")
        
        # Crear el correo
        email = EmailMessage(
            asunto,
            mensaje,
            settings.DEFAULT_FROM_EMAIL,
            [compra.usuario.email]
        )
        
        # Adjuntar el PDF
        email.attach(f'entrada_{compra.id}.pdf', pdf_buffer.getvalue(), 'application/pdf')
        print("[EMAIL] PDF adjuntado al correo")
        
        # Enviar el correo
        print("[EMAIL] Intentando enviar el correo...")
        email.send(fail_silently=False)
        print("[EMAIL] Correo enviado exitosamente")
        
    except Exception as e:
        error_msg = f"Error al enviar correo para compra {compra.id}: {str(e)}"
        print(f"[EMAIL] {error_msg}")
        logger.error(error_msg, exc_info=True)
        
        # No re-lanzar la excepción para evitar que falle todo el proceso
        # El código QR ya está generado y disponible en la plataforma
        print(f"[EMAIL] El código QR está disponible en la plataforma para compra {compra.id}")
        return False  # Indicar que falló el envío
    
    return True  # Indicar que fue exitoso


# =================== SISTEMA DE DISTRIBUCIÓN DE PAGOS ===================

def crear_distribucion_pago(compra):
    """
    Crea y calcula la distribución de pago para una compra
    """
    from .models import DistribucionPago
    from django.utils import timezone
    from decimal import Decimal
    
    try:
        # Verificar si ya existe una distribución para esta compra
        distribucion_existente = DistribucionPago.objects.filter(compra=compra).first()
        if distribucion_existente:
            logging.info(f"Distribución ya existe para compra {compra.id}")
            return distribucion_existente
        
        # Obtener el porcentaje de comisión del plan actual de la terma
        if compra.terma.plan_actual:
            porcentaje_comision = compra.terma.plan_actual.porcentaje_comision
            plan_utilizado = compra.terma.plan_actual
        else:
            # Si no tiene plan, usar comisión por defecto
            porcentaje_comision = compra.terma.porcentaje_comision_actual
            plan_utilizado = None
        
        # Calcular montos
        monto_total = compra.total
        monto_comision_plataforma = (monto_total * porcentaje_comision) / Decimal('100')
        monto_para_terma = monto_total - monto_comision_plataforma
        
        # Crear nueva distribución con todos los campos calculados
        distribucion = DistribucionPago.objects.create(
            compra=compra,
            terma=compra.terma,
            plan_utilizado=plan_utilizado,
            monto_total=monto_total,
            porcentaje_comision=porcentaje_comision,
            monto_comision_plataforma=monto_comision_plataforma,
            monto_para_terma=monto_para_terma
        )
        
        logging.info(f"Distribución creada para compra {compra.id}: "
                    f"Total: ${distribucion.monto_total}, "
                    f"Comisión: ${distribucion.monto_comision_plataforma}, "
                    f"Para terma: ${distribucion.monto_para_terma}")
        
        return distribucion
        
    except Exception as e:
        logging.error(f"Error al crear distribución de pago para compra {compra.id}: {str(e)}")
        raise


def procesar_distribucion_pago(distribucion):
    """
    Procesa la distribución de pago (marca como procesado y actualiza resúmenes)
    """
    from .models import ResumenComisionesPlataforma
    from django.utils import timezone
    from datetime import datetime
    
    try:
        # Marcar como procesado
        distribucion.marcar_como_procesado()
        
        # Actualizar resumen mensual de comisiones
        fecha = distribucion.fecha_calculo
        mes = fecha.month
        año = fecha.year
        
        resumen, created = ResumenComisionesPlataforma.objects.get_or_create(
            mes=mes,
            año=año,
            defaults={
                'total_ventas': 0,
                'total_comisiones': 0,
                'total_pagado_termas': 0,
                'cantidad_transacciones': 0
            }
        )
        
        # Actualizar totales
        resumen.total_ventas += distribucion.monto_total
        resumen.total_comisiones += distribucion.monto_comision_plataforma
        resumen.total_pagado_termas += distribucion.monto_para_terma
        resumen.cantidad_transacciones += 1
        resumen.save()
        
        logging.info(f"Distribución {distribucion.id} procesada y resumen mensual actualizado")
        
        return True
        
    except Exception as e:
        logging.error(f"Error al procesar distribución {distribucion.id}: {str(e)}")
        return False


def simular_pago_terma(distribucion, metodo_pago="Transferencia Bancaria", referencia=None):
    """
    Simula el envío de pago a la terma (para ambiente de testing)
    En producción, aquí se integraría con el sistema de pagos real
    """
    from .models import HistorialPagoTerma
    from django.utils import timezone
    import uuid
    
    try:
        # Generar referencia si no se proporciona
        if not referencia:
            referencia = f"SIM-{uuid.uuid4().hex[:8].upper()}"
        
        # Crear registro de pago
        pago = HistorialPagoTerma.objects.create(
            distribucion=distribucion,
            terma=distribucion.terma,
            monto_pagado=distribucion.monto_para_terma,
            metodo_pago_usado=metodo_pago,
            referencia_externa=referencia,
            info_pago_terma={
                'email_terma': distribucion.terma.email_terma,
                'rut_empresa': distribucion.terma.rut_empresa,
                'nombre_terma': distribucion.terma.nombre_terma,
                'plan_utilizado': distribucion.plan_utilizado.nombre if distribucion.plan_utilizado else 'Sin plan'
            },
            observaciones=f"Pago simulado para testing - Plan: {distribucion.plan_utilizado.nombre if distribucion.plan_utilizado else 'Sin plan'}",
            exitoso=True
        )
        
        # Marcar distribución como pagada
        distribucion.marcar_pago_terma_enviado(referencia)
        
        logging.info(f"Pago simulado enviado a {distribucion.terma.nombre_terma}: "
                    f"${distribucion.monto_para_terma} - Ref: {referencia}")
        
        return pago
        
    except Exception as e:
        logging.error(f"Error al simular pago para distribución {distribucion.id}: {str(e)}")
        return None


def completar_distribucion_pago(distribucion):
    """
    Completa todo el proceso de distribución de pago
    """
    try:
        # Marcar como completado
        distribucion.marcar_completado()
        
        logging.info(f"Distribución {distribucion.id} completada exitosamente")
        return True
        
    except Exception as e:
        logging.error(f"Error al completar distribución {distribucion.id}: {str(e)}")
        return False


def procesar_pago_completo(compra):
    """
    Función principal que maneja todo el flujo de distribución de pago
    Esta función debe ser llamada cuando una compra cambia a estado 'pagado'
    """
    try:
        logging.info(f"Iniciando procesamiento completo de pago para compra {compra.id}")
        
        # 1. Crear distribución de pago
        distribucion = crear_distribucion_pago(compra)
        
        # 2. Procesar la distribución (actualizar resúmenes)
        if not procesar_distribucion_pago(distribucion):
            raise Exception("Error al procesar distribución")
        
        # 3. Simular envío de pago a la terma (en testing)
        pago = simular_pago_terma(distribucion)
        if not pago:
            raise Exception("Error al simular pago a terma")
        
        # 4. Completar el proceso
        if not completar_distribucion_pago(distribucion):
            raise Exception("Error al completar distribución")
        
        logging.info(f"Pago procesado completamente para compra {compra.id}")
        return distribucion
        
    except Exception as e:
        logging.error(f"Error en procesamiento completo de pago para compra {compra.id}: {str(e)}")
        # Marcar distribución con error si existe
        if 'distribucion' in locals():
            distribucion.estado = 'error'
            distribucion.observaciones = f"Error en procesamiento: {str(e)}"
            distribucion.save()
        raise


def obtener_resumen_comisiones_terma(terma, mes=None, año=None):
    """
    Obtiene un resumen de las comisiones y pagos para una terma específica
    """
    from .models import DistribucionPago, HistorialPagoTerma
    from django.db.models import Sum, Count
    from django.utils import timezone
    
    # Si no se especifica mes/año, usar el mes actual
    if not mes or not año:
        hoy = timezone.now()
        mes = hoy.month
        año = hoy.year
    
    # Filtrar distribuciones de la terma para el período
    distribuciones = DistribucionPago.objects.filter(
        terma=terma,
        fecha_calculo__month=mes,
        fecha_calculo__year=año
    )
    
    # Calcular totales
    resumen = distribuciones.aggregate(
        total_ventas=Sum('monto_total'),
        total_comisiones_pagadas=Sum('monto_comision_plataforma'),
        total_recibido=Sum('monto_para_terma'),
        cantidad_transacciones=Count('id')
    )
    
    # Obtener historial de pagos
    pagos = HistorialPagoTerma.objects.filter(
        terma=terma,
        fecha_pago__month=mes,
        fecha_pago__year=año,
        exitoso=True
    )
    
    resumen.update({
        'mes': mes,
        'año': año,
        'terma': terma.nombre_terma,
        'plan_actual': terma.plan_actual.nombre if terma.plan_actual else 'Sin plan',
        'porcentaje_comision_actual': terma.porcentaje_comision_actual,
        'pagos_realizados': pagos.count(),
        'ultimo_pago': pagos.first().fecha_pago if pagos.exists() else None
    })
    
    return resumen


def obtener_reporte_comisiones_diarias(fecha_inicio=None, fecha_fin=None, terma_id=None):
    """
    Obtiene reporte detallado de comisiones diarias por terma
    """
    from .models import DistribucionPago
    from django.db.models import Sum, Count, Q
    from django.utils import timezone
    from datetime import datetime, timedelta
    from collections import defaultdict
    
    # Fechas por defecto (último mes)
    if not fecha_fin:
        fecha_fin = timezone.now().date()
    if not fecha_inicio:
        fecha_inicio = fecha_fin - timedelta(days=30)
    
    # Query base
    query = Q(fecha_calculo__date__gte=fecha_inicio, fecha_calculo__date__lte=fecha_fin)
    if terma_id:
        query &= Q(terma_id=terma_id)
    
    distribuciones = DistribucionPago.objects.filter(query).select_related('terma', 'plan_utilizado')
    
    # Agrupar por fecha y terma
    reporte_diario = defaultdict(lambda: defaultdict(lambda: {
        'ventas': 0,
        'comisiones': 0,
        'pagado_terma': 0,
        'transacciones': 0,
        'plan': 'Sin plan',
        'porcentaje_comision': 0
    }))
    
    totales_dia = defaultdict(lambda: {
        'total_ventas': 0,
        'total_comisiones': 0,
        'total_pagado_termas': 0,
        'total_transacciones': 0
    })
    
    for dist in distribuciones:
        fecha = dist.fecha_calculo.date()
        terma_nombre = dist.terma.nombre_terma
        
        reporte_diario[fecha][terma_nombre]['ventas'] += float(dist.monto_total)
        reporte_diario[fecha][terma_nombre]['comisiones'] += float(dist.monto_comision_plataforma)
        reporte_diario[fecha][terma_nombre]['pagado_terma'] += float(dist.monto_para_terma)
        reporte_diario[fecha][terma_nombre]['transacciones'] += 1
        reporte_diario[fecha][terma_nombre]['plan'] = dist.plan_utilizado.get_nombre_display() if dist.plan_utilizado else 'Sin plan'
        reporte_diario[fecha][terma_nombre]['porcentaje_comision'] = float(dist.porcentaje_comision)
        
        # Totales del día
        totales_dia[fecha]['total_ventas'] += float(dist.monto_total)
        totales_dia[fecha]['total_comisiones'] += float(dist.monto_comision_plataforma)
        totales_dia[fecha]['total_pagado_termas'] += float(dist.monto_para_terma)
        totales_dia[fecha]['total_transacciones'] += 1
    
    # Convertir a formato de lista ordenada
    reporte_final = []
    for fecha in sorted(reporte_diario.keys(), reverse=True):
        dia_data = {
            'fecha': fecha,
            'termas': dict(reporte_diario[fecha]),
            'totales': totales_dia[fecha]
        }
        reporte_final.append(dia_data)
    
    # Calcular totales generales del período
    totales_periodo = distribuciones.aggregate(
        total_ventas=Sum('monto_total'),
        total_comisiones=Sum('monto_comision_plataforma'),
        total_pagado_termas=Sum('monto_para_terma'),
        total_transacciones=Count('id')
    )
    
    return {
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'reporte_diario': reporte_final,
        'totales_periodo': totales_periodo,
        'dias_con_actividad': len(reporte_final)
    }


def obtener_acumulado_comisiones_plataforma():
    """
    Obtiene el monto total acumulado histórico de comisiones de la plataforma
    """
    from .models import DistribucionPago
    from django.db.models import Sum
    
    total_historico = DistribucionPago.objects.filter(
        estado__in=['procesado', 'pagado_terma', 'completado']
    ).aggregate(
        total_comisiones=Sum('monto_comision_plataforma')
    )
    
    return total_historico['total_comisiones'] or 0


def obtener_top_termas_comisiones(limite=10, mes=None, año=None):
    """
    Obtiene las termas que más comisiones han generado
    """
    from .models import DistribucionPago
    from django.db.models import Sum, Count
    from django.utils import timezone
    
    query = DistribucionPago.objects.all()
    
    if mes and año:
        query = query.filter(fecha_calculo__month=mes, fecha_calculo__year=año)
    
    top_termas = query.values('terma__nombre_terma', 'terma__id').annotate(
        total_comisiones=Sum('monto_comision_plataforma'),
        total_ventas=Sum('monto_total'),
        transacciones=Count('id')
    ).order_by('-total_comisiones')[:limite]
    
    return list(top_termas)