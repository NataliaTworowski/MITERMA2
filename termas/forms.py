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


class CambiarSuscripcionForm(forms.Form):
    """Formulario para cambiar el plan de suscripción de una terma"""
    
    nuevo_plan = forms.ModelChoiceField(
        queryset=PlanSuscripcion.objects.filter(activo=True),
        widget=forms.RadioSelect(attrs={
            'class': 'form-radio'
        }),
        label="Nuevo Plan",
        help_text="Selecciona el plan al que deseas cambiar"
    )
    
    motivo_cambio = forms.CharField(
        max_length=500,
        widget=forms.Textarea(attrs={
            'rows': 3,
            'class': 'form-control',
            'placeholder': 'Opcional: Describe el motivo del cambio de plan'
        }),
        label="Motivo del cambio (Opcional)",
        required=False,
        help_text="Puedes agregar una descripción del por qué cambias de plan"
    )
    
    confirmar_cambio = forms.BooleanField(
        widget=forms.CheckboxInput(attrs={
            'class': 'form-checkbox'
        }),
        label="Confirmo que deseo cambiar mi plan de suscripción",
        help_text="Este cambio se aplicará inmediatamente",
        required=True
    )
    
    def __init__(self, *args, **kwargs):
        plan_actual = kwargs.pop('plan_actual', None)
        terma = kwargs.pop('terma', None)
        super().__init__(*args, **kwargs)
        
        # Filtrar para no mostrar el plan actual como opción
        if plan_actual:
            self.fields['nuevo_plan'].queryset = PlanSuscripcion.objects.filter(
                activo=True
            ).exclude(id=plan_actual.id)
        
        # Guardar referencias para validación
        self.plan_actual = plan_actual
        self.terma = terma
    
    def clean_nuevo_plan(self):
        nuevo_plan = self.cleaned_data.get('nuevo_plan')
        
        # Verificar que no sea el mismo plan actual
        if self.plan_actual and nuevo_plan.id == self.plan_actual.id:
            raise forms.ValidationError("No puedes cambiar al mismo plan que ya tienes activo.")
        
        return nuevo_plan
