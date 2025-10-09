from django import forms
from .models import SolicitudTerma

class SolicitudTermaForm(forms.ModelForm):
    class Meta:
        model = SolicitudTerma
        fields = [
            'nombre_terma',
            'descripcion',
            'rut_empresa',
            'correo_institucional',
            'telefono_contacto',
            'region',
            'comuna',
            'direccion',
        ]
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 3}),
            'direccion': forms.Textarea(attrs={'rows': 2}),
        }
from django import forms
from .models import Terma

class TermaForm(forms.ModelForm):
    """Formulario para gestión de termas."""
    class Meta:
        model = Terma
        fields = [
            'nombre_terma',
            'descripcion_terma',
            'direccion_terma',
            'comuna',
            'telefono_terma',
            'email_terma',
            'estado_suscripcion'
        ]
        widgets = {
            'descripcion_terma': forms.Textarea(attrs={'rows': 4}),
            'direccion_terma': forms.Textarea(attrs={'rows': 3}),
        }
