from termas.models import SolicitudTerma

def navbar_context(request):
    """Context processor para el navbar admin."""
    context = {}
    
    # Solo agregar contexto si el usuario está logueado y es admin general
    if 'usuario_id' in request.session and request.session.get('usuario_rol') == 4:
        try:
            solicitudes_count = SolicitudTerma.objects.filter(estado='pendiente').count()
            context['solicitudes_count'] = solicitudes_count
        except:
            context['solicitudes_count'] = 0
    
    return context