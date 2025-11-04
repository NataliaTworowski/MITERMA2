# -*- coding: utf-8 -*-
import qrcode
import json
import logging
import os
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from django.core.mail import EmailMessage
from django.conf import settings


def generar_datos_qr(compra):
    """Genera los datos que contendrá el QR"""
    datos = {
        'compra_id': compra.id,
        'terma': compra.terma.nombre_terma,
        'fecha_visita': str(compra.fecha_visita),
        'usuario': f"{compra.usuario.nombre} {compra.usuario.apellido}",
        'cantidad': compra.cantidad if hasattr(compra, 'cantidad') else 1
    }
    return json.dumps(datos)


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
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # Título
    c.setFont("Helvetica-Bold", 24)
    c.drawString(50, height - 50, "Entrada MiTerma")
    
    # Detalles de la compra
    c.setFont("Helvetica", 12)
    c.drawString(50, height - 100, f"Terma: {compra.terma.nombre_terma}")
    c.drawString(50, height - 120, f"Fecha de visita: {compra.fecha_visita}")
    c.drawString(50, height - 140, f"Cliente: {compra.usuario.nombre} {compra.usuario.apellido}")
    c.drawString(50, height - 160, f"Cantidad: {compra.cantidad if hasattr(compra, 'cantidad') else 1}")
    
    # Generar y colocar el QR
    qr_data = generar_datos_qr(compra)
    qr_img = generar_qr(qr_data)
    img = ImageReader(qr_img)
    
    # Colocar el QR en el centro del PDF
    qr_size = 200
    c.drawImage(img, (width - qr_size) / 2, height - 400, width=qr_size, height=qr_size)
    
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