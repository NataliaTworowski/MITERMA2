from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
import logging

logger = logging.getLogger(__name__)

def enviar_email_confirmacion(usuario_email, nombre_usuario):
    """Envía email de confirmación de registro usando template"""
    
    asunto = "¡Bienvenido a MITERMA! 🌊"
    
    # Renderizar template HTML
    mensaje_html = render_to_string('correo/correo_confirmacion.html', {
        'nombre_usuario': nombre_usuario,
        'usuario_email': usuario_email,
    })
    
    # Mensaje en texto plano (fallback)
    mensaje_texto = f"""
    ¡Hola {nombre_usuario}!
    
    Tu cuenta ha sido creada exitosamente en MITERMA.
    
    ✅ Cuenta activada
    📧 Email: {usuario_email}
    🎉 ¡Ya puedes disfrutar de nuestras termas!
    
    
    Gracias por unirte a MITERMA
    El equipo de MITERMA 💙
    """
    
    try:
        send_mail(
            subject=asunto,
            message=mensaje_texto,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@miterma.com'),
            recipient_list=[usuario_email],
            html_message=mensaje_html,
            fail_silently=False,
        )
        logger.info("Email enviado exitosamente")
        return True
    except Exception as e:
        logger.error(f"Error enviando email a {usuario_email}: {str(e)}")
        print(f"Error detallado: {e}")  
        return False
    
def enviar_email_reset_password(usuario_email, codigo_verificacion, nombre_usuario):
    """Envía email con código de verificación para resetear contraseña"""
    
    asunto = "Código de verificación - MITERMA 🔐"
    
    # Renderizar template HTML
    mensaje_html = render_to_string('correo/correo_reset_password.html', {
        'nombre_usuario': nombre_usuario,
        'usuario_email': usuario_email,
        'codigo_verificacion': codigo_verificacion,  # Asegúrate que sea este nombre
    })
    
    mensaje_texto = f"""
    Hola {nombre_usuario},
    
    Tu código de verificación es: {codigo_verificacion}
    
    Este código expira en 15 minutos.
    
    Equipo de MITERMA
    """
    
    try:
        send_mail(
            subject=asunto,
            message=mensaje_texto,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@miterma.com'),
            recipient_list=[usuario_email],
            html_message=mensaje_html,
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Error enviando email de reset: {e}")
        return False