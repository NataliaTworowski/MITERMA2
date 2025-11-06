from django import forms
from .models import EntradaTipo
from termas.models import ServicioTerma

class ReservaForm(forms.Form):
    """Formulario básico para reservas."""
    cliente = forms.CharField(max_length=100)
    fecha = forms.DateTimeField()
    servicio = forms.CharField(max_length=200)

class EntradaTipoForm(forms.ModelForm):
    """Formulario para crear y editar tipos de entrada."""
    
    class Meta:
        model = EntradaTipo
        fields = ['nombre', 'descripcion', 'precio', 'duracion_horas', 'duracion_tipo', 'servicios']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-400',
                'placeholder': 'Nombre del tipo de entrada'
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-400',
                'placeholder': 'Descripción del tipo de entrada',
                'rows': 3
            }),
            'precio': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-400',
                'placeholder': 'Precio en pesos chilenos'
            }),
            'duracion_horas': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-400',
                'placeholder': 'Duración en horas'
            }),
            'duracion_tipo': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-400'
            }),
            'servicios': forms.CheckboxSelectMultiple(attrs={
                'class': 'space-y-2'
            })
        }
        labels = {
            'nombre': 'Nombre de la entrada',
            'descripcion': 'Descripción',
            'precio': 'Precio (CLP)',
            'duracion_horas': 'Duración en horas',
            'duracion_tipo': 'Tipo de duración',
            'servicios': 'Servicios incluidos'
        }
    
    def __init__(self, *args, **kwargs):
        terma = kwargs.pop('terma', None)
        super().__init__(*args, **kwargs)
        
        if terma:
            # Filtrar servicios solo de la terma específica
            self.fields['servicios'].queryset = ServicioTerma.objects.filter(terma=terma)