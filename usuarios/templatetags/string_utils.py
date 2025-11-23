from django import template

register = template.Library()

@register.filter
def is_empty_or_none(value):
    """
    Verifica si un valor está vacío, es None, o es la cadena 'None'
    """
    if value is None:
        return True
    if value == '':
        return True
    if str(value).strip() == '':
        return True
    if str(value) == 'None':
        return True
    if str(value) == 'null':
        return True
    return False

@register.filter  
def has_valid_content(value):
    """
    Verifica si un valor tiene contenido válido (no está vacío ni es None)
    """
    return not is_empty_or_none(value)

@register.filter
def formato_precio(value):
    """
    Formatea un precio para mostrar con separadores de miles
    """
    try:
        if value is None:
            return "0"
        # Convertir a float si es string
        if isinstance(value, str):
            value = float(value)
        # Formatear con separadores de miles
        return f"{value:,.0f}".replace(",", ".")
    except (ValueError, TypeError):
        return "0"