from django import forms
from .models import Terma

class TermaForm(forms.ModelForm):
    """Formulario para gestión de termas."""
    class Meta:
        model = Terma
        fields = ['nombre', 'descripcion', 'tipo', 'capacidad_personas', 
                 'precio_por_hora', 'temperatura_agua', 'disponible', 'ubicacion']
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 4}),
            'precio_por_hora': forms.NumberInput(attrs={'step': '0.01'}),
            'temperatura_agua': forms.NumberInput(attrs={'min': '20', 'max': '50'}),
        }