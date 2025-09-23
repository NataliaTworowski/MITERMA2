from django import forms

class VentaForm(forms.Form):
    """Formulario básico para ventas."""
    cliente = forms.CharField(max_length=100)
    fecha = forms.DateField()
    total = forms.DecimalField(max_digits=10, decimal_places=2)