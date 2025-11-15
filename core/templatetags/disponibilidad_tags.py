"""
Template tags para mostrar información de disponibilidad de termas
"""
from django import template
from datetime import date, datetime
from ventas.disponibilidad_utils import calcular_disponibilidad_terma, validar_cantidad_disponible

register = template.Library()


@register.filter
def disponibilidad_terma(terma_id, fecha_str=None):
    """
    Retorna información de disponibilidad para una terma
    
    Uso en template: {{ terma.id|disponibilidad_terma }}
    """
    try:
        if fecha_str:
            fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        else:
            fecha = date.today()
            
        return calcular_disponibilidad_terma(terma_id, fecha)
    except:
        return {
            'puede_vender': False,
            'disponibles': 0,
            'error': 'Error al calcular disponibilidad'
        }


@register.filter
def puede_vender_cantidad(terma_id, cantidad):
    """
    Verifica si se puede vender una cantidad específica
    
    Uso en template: {{ terma.id|puede_vender_cantidad:2 }}
    """
    try:
        validacion = validar_cantidad_disponible(terma_id, int(cantidad))
        return validacion['es_valida']
    except:
        return False


@register.simple_tag
def disponibilidad_detallada(terma_id, fecha_str=None):
    """
    Retorna disponibilidad detallada como tag
    
    Uso en template: {% disponibilidad_detallada terma.id %}
    """
    try:
        if fecha_str:
            fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        else:
            fecha = date.today()
            
        return calcular_disponibilidad_terma(terma_id, fecha)
    except:
        return {
            'puede_vender': False,
            'disponibles': 0,
            'error': 'Error al calcular disponibilidad'
        }


@register.simple_tag
def mensaje_disponibilidad(terma_id, cantidad=1, fecha_str=None):
    """
    Genera un mensaje descriptivo sobre la disponibilidad
    
    Uso en template: {% mensaje_disponibilidad terma.id 2 %}
    """
    try:
        if fecha_str:
            fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        else:
            fecha = date.today()
            
        disponibilidad = calcular_disponibilidad_terma(terma_id, fecha)
        
        if 'error' in disponibilidad:
            return disponibilidad['error']
            
        if disponibilidad['sin_limite']:
            return "Disponibilidad ilimitada"
            
        if not disponibilidad['puede_vender']:
            return f"Sin disponibilidad para el {fecha.strftime('%d/%m/%Y')}"
            
        disponibles = disponibilidad['disponibles']
        
        if cantidad <= disponibles:
            if disponibles == 1:
                return "Última entrada disponible"
            elif disponibles <= 5:
                return f"Quedan solo {disponibles} entradas"
            else:
                return f"{disponibles} entradas disponibles"
        else:
            return f"Solo quedan {disponibles} entradas (solicitas {cantidad})"
            
    except Exception as e:
        return f"Error: {str(e)}"


@register.inclusion_tag('ventas/disponibilidad_badge.html')
def badge_disponibilidad(terma_id, fecha_str=None):
    """
    Renderiza un badge de disponibilidad
    
    Uso en template: {% badge_disponibilidad terma.id %}
    """
    try:
        if fecha_str:
            fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        else:
            fecha = date.today()
            
        disponibilidad = calcular_disponibilidad_terma(terma_id, fecha)
        
        # Determinar el tipo de badge
        if 'error' in disponibilidad:
            badge_type = 'error'
            mensaje = 'Error'
        elif disponibilidad['sin_limite']:
            badge_type = 'success'
            mensaje = 'Disponible'
        elif not disponibilidad['puede_vender']:
            badge_type = 'danger'
            mensaje = 'Sin disponibilidad'
        else:
            disponibles = disponibilidad['disponibles']
            if disponibles <= 3:
                badge_type = 'warning'
                mensaje = f'Últimas {disponibles}'
            elif disponibles <= 10:
                badge_type = 'info'
                mensaje = f'{disponibles} disponibles'
            else:
                badge_type = 'success'
                mensaje = 'Disponible'
        
        return {
            'disponibilidad': disponibilidad,
            'badge_type': badge_type,
            'mensaje': mensaje,
            'fecha': fecha
        }
        
    except Exception as e:
        return {
            'disponibilidad': {'puede_vender': False, 'disponibles': 0},
            'badge_type': 'error',
            'mensaje': 'Error',
            'fecha': date.today()
        }