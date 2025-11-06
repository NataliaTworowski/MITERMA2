from django import forms
from .models import SolicitudTerma, PlanSuscripcion

class SolicitudTermaForm(forms.ModelForm):
    plan_seleccionado = forms.ModelChoiceField(
        queryset=PlanSuscripcion.objects.filter(activo=True),
        empty_label="Selecciona un plan",
        widget=forms.Select(attrs={
            'class': 'form-control',
            'required': True
        }),
        help_text="Selecciona el plan de suscripción que mejor se adapte a tus necesidades"
    )
    
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
            'plan_seleccionado',
        ]
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 3}),
            'direccion': forms.Textarea(attrs={'rows': 2}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Personalizar labels y añadir clases CSS
        self.fields['nombre_terma'].widget.attrs.update({'class': 'form-control'})
        self.fields['descripcion'].widget.attrs.update({'class': 'form-control'})
        self.fields['rut_empresa'].widget.attrs.update({'class': 'form-control'})
        self.fields['correo_institucional'].widget.attrs.update({'class': 'form-control'})
        self.fields['telefono_contacto'].widget.attrs.update({'class': 'form-control'})
        self.fields['region'].widget.attrs.update({'class': 'form-control'})
        self.fields['comuna'].widget.attrs.update({'class': 'form-control'})
        self.fields['direccion'].widget.attrs.update({'class': 'form-control'})
        
        # Si viene un plan en initial, hacer que sea readonly
        if 'plan_seleccionado' in self.initial and self.initial['plan_seleccionado']:
            self.fields['plan_seleccionado'].widget.attrs.update({
                'readonly': True,
                'class': 'form-control bg-gray-100'
            })
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
