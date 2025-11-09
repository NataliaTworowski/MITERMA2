from django import template
from decimal import Decimal

register = template.Library()

@register.filter
def precio_chileno(value):
    """
    Formatea un precio en formato chileno.
    Ejemplo: 15000 -> $15.000 CLP
    """
    if value is None or value == '':
        return '$0 CLP'
    
    try:
        # Convertir a entero y formatear
        numero = int(float(value))
        # Formatear con separadores de miles usando locale chileno
        precio_formateado = f"{numero:,}".replace(',', '.')
        return f"${precio_formateado} CLP"
    except (ValueError, TypeError):
        return f"${value} CLP"

@register.filter
def precio_sin_simbolo(value):
    """
    Formatea un precio sin símbolos, solo con separadores de miles.
    Ejemplo: 15000 -> 15.000
    """
    if value is None or value == '':
        return '0'
    
    try:
        numero = int(float(value))
        return f"{numero:,}".replace(',', '.')
    except (ValueError, TypeError):
        return str(value)

@register.filter
def formato_precio(value):
    """
    Formatea un precio con separadores de miles.
    """
    if value is None or value == '':
        return '0'
    
    try:
        numero = int(float(value))
        return f"{numero:,}".replace(',', '.')
    except (ValueError, TypeError):
        return str(value)

@register.filter
def duracion_formato(value):
    """
    Formatea duración en horas.
    Ejemplo: 1 -> 1 hora, 2 -> 2 horas
    """
    if value is None or value == '':
        return '0 horas'
    
    try:
        horas = int(value)
        if horas == 1:
            return '1 hora'
        else:
            return f'{horas} horas'
    except (ValueError, TypeError):
        return f'{value} horas'