"""
Views para funcionalidades de correos electrónicos
"""
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect
from django.contrib import messages
from django.utils.decorators import method_decorator
from django.core.exceptions import PermissionDenied
import logging

from ventas.models import Compra
from ventas.utils import enviar_entrada_por_correo

logger = logging.getLogger(__name__)


@login_required
@require_POST
@csrf_protect
def reenviar_correo_compra(request, compra_uuid):
    """
    Reenvía el correo electrónico con el PDF de la compra al cliente.
    """
    try:
        # Obtener la compra
        compra = get_object_or_404(Compra, uuid=compra_uuid)
        
        # Verificar que el usuario sea el propietario de la compra
        if compra.usuario != request.user:
            logger.warning(f"Intento no autorizado de reenvío de correo. Usuario: {request.user.id}, Compra: {compra_id}")
            raise PermissionDenied("No tienes permisos para reenviar este correo")
        
        # Verificar que la compra esté pagada
        if compra.estado_pago != 'pagado':
            return JsonResponse({
                'success': False,
                'message': 'Solo se pueden reenviar correos de compras pagadas'
            })
        
        # Verificar que existe el código QR
        if not hasattr(compra, 'codigoqr') or not compra.codigoqr:
            return JsonResponse({
                'success': False,
                'message': 'No se encontró el código QR para esta compra. Contacta soporte.'
            })
        
        # Intentar enviar el correo
        try:
            exito = enviar_entrada_por_correo(compra)
            
            if exito:
                logger.info(f"Correo reenviado exitosamente para compra {compra_id}")
                return JsonResponse({
                    'success': True,
                    'message': 'Correo reenviado exitosamente'
                })
            else:
                logger.error(f"Error al reenviar correo para compra {compra_id}")
                return JsonResponse({
                    'success': False,
                    'message': 'Error al enviar el correo. Inténtalo más tarde.'
                })
                
        except Exception as email_error:
            logger.error(f"Excepción al enviar correo para compra {compra_id}: {str(email_error)}")
            return JsonResponse({
                'success': False,
                'message': 'Error interno al enviar correo. Contacta soporte si persiste.'
            })
            
    except Compra.DoesNotExist:
        logger.warning(f"Intento de reenvío para compra inexistente: {compra_id}")
        return JsonResponse({
            'success': False,
            'message': 'Compra no encontrada'
        })
    
    except PermissionDenied as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=403)
    
    except Exception as e:
        logger.error(f"Error inesperado en reenvío de correo para compra {compra_id}: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': 'Error inesperado. Contacta soporte.'
        }, status=500)