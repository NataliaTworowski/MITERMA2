"""
Utilidades para envío de emails en la aplicación de termas.
"""
import logging
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

def enviar_email_bienvenida_trabajador(trabajador, password_temporal, terma):
    """
    Envía un email de bienvenida a un nuevo trabajador.
    
    Args:
        trabajador (Usuario): El usuario trabajador
        password_temporal (str): La contraseña temporal generada
        terma (Terma): La terma a la que fue asignado
    
    Returns:
        bool: True si el email se envió correctamente, False en caso contrario
    """
    try:
        logger.info(f"=== INICIO FUNCION EMAIL ===")
        logger.info(f"Iniciando envío de email de bienvenida para {trabajador.email}")
        
        # Verificar configuración básica
        logger.info(f"Settings - DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")
        logger.info(f"Settings - EMAIL_BACKEND: {settings.EMAIL_BACKEND}")
        
        # URL del sitio (configuración simple para desarrollo)
        site_url = "http://localhost:8000"  # Cambiar en producción
        
        # Contexto para las plantillas
        context = {
            'trabajador_nombre': f"{trabajador.nombre} {trabajador.apellido}",
            'trabajador_email': trabajador.email,
            'password_temporal': password_temporal,
            'terma_nombre': terma.nombre_terma,
            'terma_direccion': getattr(terma, 'direccion', None),
            'terma_telefono': getattr(terma, 'telefono', None),
            'terma_email': getattr(terma, 'email', None),
            'fecha_actual': timezone.now(),
            'site_url': site_url,
        }
        
        # Renderizar plantilla HTML
        subject = f"Bienvenido al equipo de {terma.nombre_terma}"
        logger.info(f"Renderizando plantilla para {trabajador.email}")
        html_content = render_to_string('emails/bienvenida_trabajador.html', context)
        logger.info(f"Plantilla renderizada, enviando email a {trabajador.email}")
        
        # Verificar configuración de email
        logger.info(f"Email backend: {settings.EMAIL_BACKEND}")
        logger.info(f"Email host: {settings.EMAIL_HOST}")
        logger.info(f"From email: {settings.DEFAULT_FROM_EMAIL}")
        
        # Enviar email solo HTML
        resultado = send_mail(
            subject=subject,
            message='',  # Mensaje vacío
            html_message=html_content,  # Solo HTML
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[trabajador.email],
            fail_silently=False,
        )
        
        logger.info(f"Resultado del envío de email: {resultado}")
        
        if resultado:
            logger.info(f"Email de bienvenida enviado exitosamente a {trabajador.email} para terma {terma.nombre_terma}")
            return True
        else:
            logger.error(f"Error al enviar email de bienvenida a {trabajador.email} - resultado: {resultado}")
            return False
            
    except Exception as e:
        logger.error(f"Error al enviar email de bienvenida a {trabajador.email}: {str(e)}")
        return False

def enviar_email_cambio_estado_trabajador(trabajador, terma, nuevo_estado, motivo=None):
    """
    Envía un email cuando cambia el estado de un trabajador.
    
    Args:
        trabajador (Usuario): El usuario trabajador
        terma (Terma): La terma
        nuevo_estado (bool): El nuevo estado (True=activo, False=inactivo)
        motivo (str, optional): Motivo del cambio de estado
    
    Returns:
        bool: True si el email se envió correctamente, False en caso contrario
    """
    try:
        estado_texto = "reactivado" if nuevo_estado else "desactivado"
        
        subject = f"Cambio de estado en {terma.nombre_terma}"
        
        # Crear mensaje simple para cambio de estado
        mensaje = f"""
Estimado/a {trabajador.nombre} {trabajador.apellido},

Te informamos que tu estado como trabajador en {terma.nombre_terma} ha sido {estado_texto}.

{'Estado: ACTIVO - Puedes acceder al sistema nuevamente.' if nuevo_estado else 'Estado: INACTIVO - Tu acceso al sistema ha sido suspendido.'}
        
{f'Motivo: {motivo}' if motivo else ''}

Para consultas, contacta con la administración de la terma.

Saludos,
Equipo de {terma.nombre_terma}
        """
        
        # Enviar email simple
        resultado = send_mail(
            subject=subject,
            message=mensaje,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[trabajador.email],
            fail_silently=False,
        )
        
        if resultado:
            logger.info(f"Email de cambio de estado enviado a {trabajador.email} - Estado: {estado_texto}")
            return True
        else:
            logger.error(f"Error al enviar email de cambio de estado a {trabajador.email}")
            return False
            
    except Exception as e:
        logger.error(f"Error al enviar email de cambio de estado a {trabajador.email}: {str(e)}")
        return False

def enviar_email_actualizacion_trabajador(trabajador, terma, campos_actualizados):
    """
    Envía un email cuando se actualiza la información de un trabajador.
    
    Args:
        trabajador (Usuario): El usuario trabajador
        terma (Terma): La terma
        campos_actualizados (dict): Diccionario con los campos actualizados
    
    Returns:
        bool: True si el email se envió correctamente, False en caso contrario
    """
    try:
        subject = f"Información actualizada - {terma.nombre_terma}"
        
        # Construir mensaje con cambios
        cambios = []
        for campo, valor in campos_actualizados.items():
            cambios.append(f"- {campo}: {valor}")
        
        mensaje = f"""
Estimado/a {trabajador.nombre} {trabajador.apellido},

Te informamos que la siguiente información de tu perfil ha sido actualizada:

{chr(10).join(cambios)}

Si tienes alguna consulta sobre estos cambios, contacta con la administración de la terma.

Saludos,
Equipo de {terma.nombre_terma}
        """
        
        # Enviar email
        resultado = send_mail(
            subject=subject,
            message=mensaje,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[trabajador.email],
            fail_silently=False,
        )
        
        if resultado:
            logger.info(f"Email de actualización enviado a {trabajador.email}")
            return True
        else:
            logger.error(f"Error al enviar email de actualización a {trabajador.email}")
            return False
            
    except Exception as e:
        logger.error(f"Error al enviar email de actualización a {trabajador.email}: {str(e)}")
        return False