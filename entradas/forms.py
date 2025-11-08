from django import forms
from .models import EntradaTipo
from termas.models import ServicioTerma
import re
from decimal import Decimal

class ReservaForm(forms.Form):
    """Formulario básico para reservas."""
    cliente = forms.CharField(max_length=100)
    fecha = forms.DateTimeField()
    servicio = forms.CharField(max_length=200)

class EntradaTipoForm(forms.ModelForm):
    """Formulario para crear y editar tipos de entrada."""
    
    # Campo personalizado para precio con formato chileno
    precio = forms.CharField(
        max_length=20,
        help_text='Ingrese el precio sin puntos ni comas. Ejemplo: 15000'
    )
    
    class Meta:
        model = EntradaTipo
        fields = ['nombre', 'descripcion', 'precio', 'duracion_horas', 'duracion_tipo', 'servicios']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:border-blue-500 focus:ring-4 focus:ring-blue-50 transition-all duration-200 font-medium',
                'placeholder': 'Ej: Entrada General, VIP, Familiar...'
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:border-blue-500 focus:ring-4 focus:ring-blue-50 transition-all duration-200 resize-none',
                'placeholder': 'Describe los beneficios y características de esta entrada...',
                'rows': 4
            }),
            'duracion_horas': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:border-orange-500 focus:ring-4 focus:ring-orange-50 transition-all duration-200 font-medium',
                'placeholder': '2',
                'min': '1',
                'max': '24'
            }),
            'duracion_tipo': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:border-blue-500 focus:ring-4 focus:ring-blue-50 transition-all duration-200'
            }),
            'servicios': forms.CheckboxSelectMultiple(attrs={
                'class': 'grid grid-cols-1 md:grid-cols-2 gap-3'
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
        help_texts = {
            'nombre': 'Un nombre descriptivo para el tipo de entrada',
            'precio': 'Precio en pesos chilenos sin puntos ni comas',
            'duracion_horas': 'Duración de la experiencia (1-24 horas)',
            'servicios': 'Selecciona los servicios que están incluidos en esta entrada'
        }

    def __init__(self, *args, **kwargs):
        self.terma = kwargs.pop('terma', None)
        super().__init__(*args, **kwargs)
        
        # Personalizar el campo de precio
        self.fields['precio'].widget = forms.TextInput(attrs={
            'class': 'w-full pl-10 pr-16 py-3 border-2 border-gray-200 rounded-xl focus:border-green-500 focus:ring-4 focus:ring-green-50 transition-all duration-200 font-bold text-lg',
            'placeholder': '15000',
            'oninput': 'formatearPrecio(this)'
        })
        
        # Filtrar servicios por terma si está disponible
        if self.terma:
            self.fields['servicios'].queryset = ServicioTerma.objects.filter(terma=self.terma)
        
        # Si estamos editando, formatear el precio inicial
        if self.instance and self.instance.pk and self.instance.precio:
            self.fields['precio'].initial = f"{int(self.instance.precio):,}".replace(',', '.')

    def clean_precio(self):
        """Validar y limpiar el campo precio."""
        precio_str = self.cleaned_data.get('precio', '')
        
        if not precio_str:
            raise forms.ValidationError('El precio es obligatorio.')
        
        # Limpiar formato chileno (puntos y comas)
        precio_limpio = re.sub(r'[^\d]', '', precio_str)
        
        if not precio_limpio:
            raise forms.ValidationError('El precio debe contener solo números.')
        
        try:
            precio_decimal = Decimal(precio_limpio)
            if precio_decimal <= 0:
                raise forms.ValidationError('El precio debe ser mayor a 0.')
            if precio_decimal > 9999999:
                raise forms.ValidationError('El precio es demasiado alto.')
            return precio_decimal
        except (ValueError, TypeError):
            raise forms.ValidationError('El precio ingresado no es válido.')

    def clean_duracion_horas(self):
        """Validar duración en horas."""
        duracion = self.cleaned_data.get('duracion_horas')
        
        if duracion is None:
            raise forms.ValidationError('La duración es obligatoria.')
        
        if duracion < 1 or duracion > 24:
            raise forms.ValidationError('La duración debe ser entre 1 y 24 horas.')
        
        return duracion
    
    def __init__(self, *args, **kwargs):
        terma = kwargs.pop('terma', None)
        super().__init__(*args, **kwargs)
        
        if terma:
            # Filtrar servicios solo de la terma específica
            self.fields['servicios'].queryset = ServicioTerma.objects.filter(terma=terma)