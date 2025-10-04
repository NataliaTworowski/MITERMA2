from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
import logging

logger = logging.getLogger(__name__)

def enviar_email_confirmacion(usuario_email, nombre_usuario):
    """Envía email de confirmación de registro usando template"""
    
    asunto = "¡Bienvenido a MITERMA! 🌊"
    
    # Renderizar template HTML
    mensaje_html = render_to_string('correo_confirmacion.html', {
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
        logger.info(f"Email enviado exitosamente a {usuario_email}")
        return True
    except Exception as e:
        logger.error(f"Error enviando email a {usuario_email}: {str(e)}")
        print(f"Error detallado: {e}")  # Para debug
        return False