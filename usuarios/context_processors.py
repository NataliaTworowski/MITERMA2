from termas.models import SolicitudTerma
from .models import Usuario
import logging

logger = logging.getLogger(__name__)

def navbar_context(request):
    """
    Context processor para el navbar usando Django Auth.
    Proporciona datos del usuario y estadísticas para las plantillas.
    """
    context = {}
    
    try:
        # Usar Django Auth para obtener usuario
        if request.user.is_authenticated:
            context['usuario'] = request.user
            
            # Agregar contexto específico por rol
            if hasattr(request.user, 'rol') and request.user.rol:
                context['usuario_rol'] = request.user.rol.nombre
                
                # Context específico para admin general
                if request.user.rol.nombre == 'administrador_general':
                    try:
                        solicitudes_count = SolicitudTerma.objects.filter(estado='pendiente').count()
                        context['solicitudes_count'] = solicitudes_count
                    except Exception as e:
                        logger.warning(f"Error obteniendo solicitudes pendientes: {str(e)}")
                        context['solicitudes_count'] = 0
                
                # Context específico para admin de terma  
                elif request.user.rol.nombre == 'administrador_terma':
                    if request.user.terma:
                        context['terma_usuario'] = request.user.terma
                        context['tiene_terma'] = True
                    else:
                        context['tiene_terma'] = False
                
                # Context para cliente
                elif request.user.rol.nombre == 'cliente':
                    context['es_cliente'] = True
            
            # Proporcionar backward compatibility con middleware
            # Esto se eliminará gradualmente
            context['usuario_id'] = request.user.id
            context['usuario_nombre'] = request.user.nombre
            context['usuario_email'] = request.user.email
        else:
            # Usuario no autenticado
            context['usuario'] = None
            context['usuario_rol'] = None
    
    except Exception as e:
        logger.error(f"Error en navbar_context: {str(e)}")
        context = {
            'usuario': None,
            'usuario_rol': None,
            'solicitudes_count': 0
        }
    
    return context