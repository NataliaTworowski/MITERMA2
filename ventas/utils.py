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
    
    print("Generando QR para compra:", compra.id)  # Debug
    
    # Verificar si ya existe un código QR para esta compra
    codigo_qr_existente = CodigoQR.objects.filter(compra=compra).first()
    if codigo_qr_existente:
        print("Código QR existente encontrado, retornando código guardado")  # Debug
        return codigo_qr_existente.codigo
    
    # Datos mínimos necesarios para validación
    datos = {
        'ticket_id': f"{compra.id}-{timezone.now().timestamp()}",
        'fecha_visita': str(compra.fecha_visita),
        'terma_id': compra.terma.id
    }
    print("Datos a encriptar:", datos)  # Debug
    
    # Crear un token firmado con timestamp
    signer = TimestampSigner()
    token = signer.sign(json.dumps(datos))
    print("Token firmado:", token)  # Debug
    
    # Encriptar el token
    fernet = Fernet(_get_encryption_key())
    print("Clave de encriptación:", _get_encryption_key())  # Debug
    datos_encriptados = fernet.encrypt(token.encode())
    datos_qr = datos_encriptados.decode('utf-8')
    print("Datos encriptados:", datos_qr)  # Debug
    
    # Crear registro en la base de datos
    try:
        CodigoQR.objects.create(
            compra=compra,
            codigo=datos_qr,
            fecha_generacion=timezone.now()
        )
        print(f"Código QR guardado en la base de datos para compra {compra.id}")  # Debug
    except Exception as e:
        print(f"Error al guardar código QR en la base de datos: {str(e)}")  # Debug
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
        c.drawString(250, y_position, f"{detalles.horario_disponible.entrada_tipo.nombre}")
        y_position -= 25
        
        # Mostrar cantidad de entradas
        c.setFont("Helvetica-Bold", 12)
        c.drawString(70, y_position, "Cantidad:")
        c.setFont("Helvetica", 12)
        c.drawString(250, y_position, f"{compra.cantidad if hasattr(compra, 'cantidad') else 1} entrada(s)")
        y_position -= 25
        
        # Servicios incluidos
        servicios_incluidos = detalles.horario_disponible.entrada_tipo.servicios.all()
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
        print(f"[EMAIL] Usuario: {compra.usuario.email}")
        print(f"[EMAIL] FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")
        
        # Generar el PDF
        pdf_buffer = generar_pdf_entrada(compra)
        print("[EMAIL] PDF generado correctamente")
        
        # Preparar el correo
        asunto = f"Tu entrada para {compra.terma.nombre_terma}"
        mensaje = f"""¡Hola {compra.usuario.nombre}!

Adjunto encontrarás tu entrada para {compra.terma.nombre_terma}.
Fecha de visita: {compra.fecha_visita}

Por favor, presenta este código QR al llegar a la terma.

¡Gracias por tu compra!"""
        
        print(f"[EMAIL] Preparando correo para enviar a {compra.usuario.email}")
        
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
        print(f"[EMAIL] Error al enviar correo: {str(e)}")
        logger.error(f"Error al enviar correo: {str(e)}", exc_info=True)
        raise  # Re-lanzar la excepción para que se maneje en la vista