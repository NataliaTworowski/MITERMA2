from django import forms

class ReservaForm(forms.Form):
    """Formulario básico para reservas."""
    cliente = forms.CharField(max_length=100)
    fecha = forms.DateTimeField()
    servicio = forms.CharField(max_length=200)