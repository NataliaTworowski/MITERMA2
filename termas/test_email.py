"""
Test simple para envío de emails
"""
from django.core.mail import send_mail
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def test_email_simple(destinatario):
    """Test básico de envío de email"""
    try:
        logger.info(f"=== TEST EMAIL SIMPLE ===")
        logger.info(f"Enviando test a: {destinatario}")
        
        resultado = send_mail(
            subject='Test Email - MiTerma',
            message='Este es un email de prueba desde MiTerma.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[destinatario],
            fail_silently=False,
        )
        
        logger.info(f"Resultado test email: {resultado}")
        return resultado > 0
        
    except Exception as e:
        logger.error(f"Error en test email: {str(e)}")
        return False